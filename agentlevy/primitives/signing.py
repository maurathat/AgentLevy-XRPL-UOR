"""Ed25519 sign / verify primitives — the only place AgentLevy code signs.

Uses the ``cryptography`` library's ``ed25519`` module under the hood (a
well-audited binding to the system libssl). Signs the output of
``agentlevy.primitives.canonical.to_canonical_bytes()`` — never raw user
input or Pydantic models directly.

Why Ed25519 specifically
------------------------

Three converging reasons:

1. **UOR MCP compatibility.** The live UOR MCP server's ``uor.mcps``
   capability advertises ``algorithm: "ed25519"`` (verified May 3 2026
   from the initialize handshake). Signatures we produce are directly
   verifiable by UOR-aware clients without algorithm negotiation.

2. **XRPL native support.** The xrpl-py library treats Ed25519 as a
   first-class signing algorithm (matches XRPL's preferred scheme; the
   ``s`` and ``sEd`` seed prefixes correspond to the secp256k1 and
   Ed25519 keypairs respectively). Our XRPL settlement layer can use the
   same keypair the agent uses for cert signing.

3. **Library maturity.** Ed25519 in the ``cryptography`` package has been
   stable since ~2017 with constant-time guarantees. No exotic dependency.

Forward compatibility note
--------------------------

UOR Foundation's deeper agent-identity layer uses **CRYSTALS-Dilithium-3**
(FIPS 204 ML-DSA-65, post-quantum). Ed25519 is not post-quantum-safe.

For Phase 2.3 / Consensus demo we use Ed25519. For production-grade
post-quantum migration (Phase 3+), this module gains a ``algorithm`` field
on signatures and the verify function dispatches to a Dilithium
implementation. The cert envelope already includes an algorithm field
(``cert:algorithm``) so the migration is purely additive — no breaking
change to the surrounding format. UOR ecosystem matures the same way.

Discipline
----------

* Sign canonical bytes only — never raw Python objects, never JSON strings
  produced ad-hoc. The canonical step is non-negotiable.
* Detached signatures — the signature is a separate value from the signed
  payload. Cert envelopes carry the signature in a sibling field, not
  embedded in the canonical bytes. This means re-canonicalizing the
  payload after signing produces the same bytes that were originally
  signed.
* Deterministic key generation in tests via explicit seeds; production
  keys come from a CSPRNG (the library default).

See ``CANONICAL_FORM.md`` for the project-wide signing rules.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric.ed25519 import (
    Ed25519PrivateKey,
    Ed25519PublicKey,
)


# Convenience aliases used throughout the module's public surface.
PublicKeyBytes = bytes  #: 32 raw bytes (Ed25519 public key)
PrivateKeyBytes = bytes  #: 32 raw bytes (Ed25519 private-key seed; never logged)
SignatureBytes = bytes  #: 64 raw bytes (Ed25519 signature)


@dataclass(frozen=True)
class Keypair:
    """An Ed25519 keypair, agent-issuer-friendly.

    Both ``public`` and ``private`` are the **raw 32-byte forms** —
    interoperable with xrpl-py, the ``cryptography`` library, UOR MCP,
    Anthropic SDK signatures, and most other Ed25519 ecosystems.

    Use :meth:`from_seed` for deterministic keypairs in tests; use
    :meth:`generate` for fresh keys in production. Never log
    ``private``.
    """

    private: PrivateKeyBytes
    public: PublicKeyBytes

    @classmethod
    def generate(cls) -> "Keypair":
        """Generate a fresh Ed25519 keypair using the system CSPRNG."""
        sk = Ed25519PrivateKey.generate()
        return cls._from_priv(sk)

    @classmethod
    def from_seed(cls, seed: bytes) -> "Keypair":
        """Build a keypair from a 32-byte seed.

        Use only for tests, fixtures, and reproducible-demo scenarios.
        Production code should call :meth:`generate`.

        Raises
        ------
        ValueError
            If ``seed`` is not exactly 32 bytes.
        """
        if len(seed) != 32:
            raise ValueError(f"Ed25519 seed must be 32 bytes, got {len(seed)}")
        sk = Ed25519PrivateKey.from_private_bytes(seed)
        return cls._from_priv(sk)

    @classmethod
    def _from_priv(cls, sk: Ed25519PrivateKey) -> "Keypair":
        priv_bytes = sk.private_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PrivateFormat.Raw,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pub_bytes = sk.public_key().public_bytes(
            encoding=serialization.Encoding.Raw,
            format=serialization.PublicFormat.Raw,
        )
        return cls(private=priv_bytes, public=pub_bytes)


def sign(canonical_bytes: bytes, keypair: Keypair) -> SignatureBytes:
    """Sign canonical bytes with the keypair's private key.

    Parameters
    ----------
    canonical_bytes
        Output of ``canonical.to_canonical_bytes()``. Never raw input.
    keypair
        The signer's keypair.

    Returns
    -------
    bytes
        64-byte detached Ed25519 signature.
    """
    sk = Ed25519PrivateKey.from_private_bytes(keypair.private)
    return sk.sign(canonical_bytes)


def verify(
    canonical_bytes: bytes,
    signature: SignatureBytes,
    public_key: Union[PublicKeyBytes, Keypair],
) -> bool:
    """Verify a detached Ed25519 signature over canonical bytes.

    Parameters
    ----------
    canonical_bytes
        The exact bytes that were signed. Never raw user input.
    signature
        The detached signature returned by :func:`sign`.
    public_key
        Either raw 32-byte public key or a :class:`Keypair` (its public
        component will be used).

    Returns
    -------
    bool
        ``True`` if the signature is valid for these bytes under this
        public key; ``False`` otherwise. Never raises on invalid input
        — verification is a yes/no question.
    """
    pub_bytes: bytes = public_key.public if isinstance(public_key, Keypair) else public_key
    try:
        pk = Ed25519PublicKey.from_public_bytes(pub_bytes)
        pk.verify(signature, canonical_bytes)
        return True
    except (InvalidSignature, ValueError):
        return False


def verify_or_raise(
    canonical_bytes: bytes,
    signature: SignatureBytes,
    public_key: Union[PublicKeyBytes, Keypair],
) -> None:
    """Like :func:`verify` but raises ``InvalidSignature`` on failure.

    Useful for code paths where signature failure is exceptional and
    callers want a stack trace rather than a boolean.
    """
    pub_bytes: bytes = public_key.public if isinstance(public_key, Keypair) else public_key
    pk = Ed25519PublicKey.from_public_bytes(pub_bytes)
    pk.verify(signature, canonical_bytes)


# ---------------------------------------------------------------------------
# Convenience: hex/byte interop for cert envelope serialization
# ---------------------------------------------------------------------------

def public_key_hex(keypair_or_pub: Union[Keypair, PublicKeyBytes]) -> str:
    """Render the public key as 64 hex characters.

    Cert envelopes typically embed the signer's public key as hex for
    JSON-LD friendliness. Use this when serializing a cert.
    """
    pub: bytes = keypair_or_pub.public if isinstance(keypair_or_pub, Keypair) else keypair_or_pub
    return pub.hex()


def signature_hex(signature: SignatureBytes) -> str:
    """Render a 64-byte signature as 128 hex characters.

    Same purpose as :func:`public_key_hex`: JSON-LD-friendly
    serialization.
    """
    return signature.hex()


def public_key_from_hex(hex_str: str) -> PublicKeyBytes:
    """Parse a 64-hex-char public key into raw bytes.

    Raises
    ------
    ValueError
        If the hex is malformed or doesn't decode to exactly 32 bytes.
    """
    pub = bytes.fromhex(hex_str)
    if len(pub) != 32:
        raise ValueError(f"Ed25519 public key must decode to 32 bytes, got {len(pub)}")
    return pub


def signature_from_hex(hex_str: str) -> SignatureBytes:
    """Parse a 128-hex-char signature into raw bytes."""
    sig = bytes.fromhex(hex_str)
    if len(sig) != 64:
        raise ValueError(f"Ed25519 signature must decode to 64 bytes, got {len(sig)}")
    return sig

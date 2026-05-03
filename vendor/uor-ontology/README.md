# UOR Foundation Ontology — vendored snapshot

> **Source:** https://uor-foundation.github.io/UOR-Framework/
> **License:** Apache-2.0 (per the UOR-Framework repo)
> **Snapshot date:** 2026-05-03
> **Why vendored:** offline access during Consensus build sprint; avoid network dependency; pin a known-good version while spec drafting

## Files

| File | Size | Format | Use |
|---|---|---|---|
| `uor.foundation.jsonld` | 2.3 MB | JSON-LD 1.1 | Primary linked-data form. Use with `pyld` or `jsonld.js`. |
| `uor.foundation.ttl` | 1.9 MB | Turtle 1.1 | Human-readable RDF; easiest to grep. |
| `uor.foundation.nt` | 4.6 MB | N-Triples | Line-oriented; for streaming and tooling. |
| `uor.foundation.owl` | 2.5 MB | OWL 2 RDF/XML | Open in Protégé / OWL reasoners. |
| `uor.foundation.schema.json` | 284 KB | JSON Schema (Draft 2020-12) | Typed code generation in 30+ languages. |
| `uor.shapes.ttl` | 214 KB | SHACL Shapes | Validate RDF data against UOR constraints. |
| `uor.term.ebnf` | 12.7 KB | EBNF Grammar (ISO/IEC 14977) | Formal grammar for the UOR Term Language. |

## Inventory snapshot

- **34 namespaces** — Kernel (17), Bridge (14), User (3)
- **471 classes** — including `u:Element` (content-addressed), `cert:Certificate`, `op:Identity` (algebraic), `partition:*`
- **947 properties**
- **3,554 named individuals** — 635 algebraic identities across 12 verification domains, 671 proofs, etc.

## Updating

To re-sync from upstream:

```bash
cd vendor/uor-ontology/
BASE="https://uor-foundation.github.io/UOR-Framework"
for f in uor.foundation.jsonld uor.foundation.ttl uor.foundation.nt \
         uor.foundation.owl uor.foundation.schema.json \
         uor.shapes.ttl uor.term.ebnf; do
  curl -sL "$BASE/$f" -o "$f"
done
```

Then update the snapshot date above and commit with the new SHA-256s if needed.

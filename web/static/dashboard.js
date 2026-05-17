/* RoyaltAI dashboard — live polling + state-to-SVG render + animation choreography.
 *
 * Polls /api/state every POLL_INTERVAL_MS, diffs against previous state, and applies
 * CSS classes on SVG elements to drive the animation. Vanilla JS, no frameworks.
 *
 * Event handling philosophy:
 *   - Static fields (actor addresses, balances, metrics) refresh on every poll.
 *   - Choreographed beats (edge draws, cert mints, karakurenai flash) react to NEW
 *     events in the event log — keyed by `seq`. We never re-trigger an animation
 *     for an event we've already processed.
 */

(function () {
  'use strict';

  const POLL_INTERVAL_MS = 600;
  const STATE_URL = '/api/state';

  let lastSeq = 0;
  let connected = false;
  let activeCurrency = 'XRP';  // mirrors state.currency; used by event handlers for edge labels

  // Running counters that increment as events are processed in the dashboard.
  // We DON'T use state.metrics for the displayed numbers because that's the
  // server's aggregated total — would show "10 inferences" the moment the
  // dashboard loads (defeating the count-up animation). These counters reset
  // each polling response since we re-run the events and accumulate fresh.
  const runningMetrics = {
    total_inferences: 0,
    cache_misses: 0,
    cache_hits: 0,
    total_volume: 0,
    total_royalty: 0,
    anthropic_calls_made: 0,
    anthropic_calls_saved: 0,
  };

  // Estimated per-inference cost in USD when calling Anthropic Haiku directly.
  // Conservative estimate for "~500 input + 300 output tokens" at current pricing.
  const ANTHROPIC_COST_USD_PER_INFERENCE = 0.0015;

  // ---------------------------------------------------------------------------
  // Tiny DOM helpers
  // ---------------------------------------------------------------------------

  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  function setText(el, text) {
    if (!el) return;
    if (el.textContent !== text) el.textContent = text;
  }

  function shortAddr(addr, n = 6) {
    if (!addr || typeof addr !== 'string') return '—';
    if (addr.length <= n * 2 + 2) return addr;
    return addr.slice(0, n) + '…' + addr.slice(-4);
  }

  function shortUor(uor) {
    if (!uor) return '—';
    if (uor.startsWith('sha256:')) return uor.slice(0, 7) + uor.slice(7, 13) + '…';
    return uor.slice(0, 12) + '…';
  }

  function shortTxid(txid) {
    if (!txid) return '—';
    return txid.slice(0, 8) + '…' + txid.slice(-4);
  }

  function fmtTime(iso) {
    if (!iso) return '';
    try {
      const d = new Date(iso);
      return d.toISOString().slice(11, 19); // HH:MM:SS UTC
    } catch (e) { return ''; }
  }

  // ---------------------------------------------------------------------------
  // Status indicator
  // ---------------------------------------------------------------------------

  function setStatus(text, isLive) {
    setText($('#status-text'), text);
    const dot = $('#live-dot');
    if (dot) dot.classList.toggle('live', !!isLive);
  }

  // ---------------------------------------------------------------------------
  // Actor rendering (positions + balances + addresses)
  // ---------------------------------------------------------------------------

  function renderActors(actors, currency) {
    if (!actors) return;
    Object.keys(actors).forEach(role => {
      const info = actors[role];
      const node = document.querySelector(`[data-actor="${role}"]`);
      if (!node) return;

      // Address line
      const addrEl = node.querySelector('[data-field="address"]');
      if (addrEl) setText(addrEl, shortAddr(info.address));

      // Balance: pick the field matching the current settlement currency.
      // /api/state always emits both balance_xrp and balance_rlusd; we surface
      // whichever currency the server is settling in.
      const balEl = node.querySelector('[data-field="balance"]');
      if (balEl) {
        const bal = (currency === 'XRP') ? info.balance_xrp : info.balance_rlusd;
        setText(balEl, bal != null ? Number(bal).toFixed(4) : '—');
      }

      // Model NFT owner: also update model name
      const nameEl = node.querySelector('[data-field="model_name"]');
      if (nameEl && info.label) setText(nameEl, info.label);
    });
  }

  // ---------------------------------------------------------------------------
  // Cert node (the star)
  // ---------------------------------------------------------------------------

  function renderCert(certs) {
    const certNode = $('#node-cert');
    if (!certNode) return;
    if (!certs || certs.length === 0) {
      certNode.classList.add('empty');
      setText(certNode.querySelector('[data-field="cert_uor"]'), 'no cert minted');
      setText(certNode.querySelector('[data-field="hit_count"]'), '');
      return;
    }
    // Most recent cert is the star
    const latest = certs[certs.length - 1];
    certNode.classList.remove('empty');
    setText(certNode.querySelector('[data-field="cert_uor"]'), shortUor(latest.cert_uor));
    const hits = latest.hit_count || 0;
    setText(certNode.querySelector('[data-field="hit_count"]'),
            hits > 0 ? `${hits} cache hit${hits === 1 ? '' : 's'}` : 'fresh mint');

    // HCS panel — show ORIGINAL anchor's seq number (mint time) + a separate
    // cumulative access counter. The cert was anchored once; cache hits reuse
    // it. That's the cost story made visible: "1 anchor serves N reads."
    if (latest.hcs) {
      const hcsTopic = document.querySelector('#node-hcs [data-field="topic"]');
      const hcsSeq = document.querySelector('#node-hcs [data-field="latest_seq"]');
      const hcsHits = document.querySelector('#node-hcs [data-field="hits_witnessed"]');
      setText(hcsTopic, `topic ${latest.hcs.topic_id || '…'}`);
      setText(hcsSeq, latest.hcs.sequence_number != null
        ? `anchor seq ${latest.hcs.sequence_number} (mint)`
        : 'pending');
      if (hcsHits) {
        const hitCount = latest.hit_count || 0;
        setText(hcsHits, hitCount === 0
          ? '0 access events witnessed'
          : `${hitCount} access${hitCount === 1 ? '' : 'es'} witnessed`);
      }
    }
  }

  // ---------------------------------------------------------------------------
  // Metrics + standards
  // ---------------------------------------------------------------------------

  // Renders the running counters that increment as events tick through the
   // handler. Called from handleEvent (not onState) so the displayed values
  // climb in step with the visible animation.
  function renderRunningMetrics() {
    const r = runningMetrics;
    const total = r.total_inferences;
    const hitRate = total ? Math.round((r.cache_hits / total) * 100) : 0;
    setText($('[data-metric="total_inferences"]'), String(total));
    setText($('[data-metric="cache_hit_rate_pct"]'), hitRate + '%');
    setText($('[data-metric="total_rlusd_volume"]'), r.total_volume.toFixed(4));
    setText($('[data-metric="total_royalty_paid"]'), r.total_royalty.toFixed(4));
    setText($('[data-metric="anthropic_calls_saved_by_cache"]'),
            String(r.anthropic_calls_saved));
    const spent = (r.anthropic_calls_made * ANTHROPIC_COST_USD_PER_INFERENCE).toFixed(4);
    const saved = (r.anthropic_calls_saved * ANTHROPIC_COST_USD_PER_INFERENCE).toFixed(4);
    setText($('[data-metric="anthropic_spend_actual"]'), '$' + spent);
    setText($('[data-metric="anthropic_spend_saved"]'), '$' + saved);
  }

  // Sync the Anthropic node's in-graph counter from server-side metrics.
  // This handles the case where the page loaded AFTER a cert was minted —
  // primeSeqAndStart skips historical events to avoid replay animation, so
  // pulseAnthropic() never ran for that earlier mint and the node's text
  // would otherwise stay frozen at "0 calls this session". Reading the
  // canonical count from state.metrics on each poll keeps it accurate.
  function syncAnthropicCounter(metrics) {
    if (!metrics) return;
    const n = Number(metrics.anthropic_calls_made || 0);
    const ant = document.getElementById('node-anthropic');
    if (!ant) return;
    const calls = ant.querySelector('[data-field="calls"]');
    if (calls) {
      setText(calls, `${n} call${n === 1 ? '' : 's'} this session`);
    }
    // Remove the dim class once Anthropic has actually been called.
    if (n > 0) ant.classList.remove('node-dim');
    else ant.classList.add('node-dim');
  }

  function renderStandards(s) {
    if (!s) return;
    const endpoint = $('#uor-mcp-endpoint');
    if (endpoint && s.uor_mcp_endpoint) setText(endpoint, s.uor_mcp_endpoint);
  }

  function renderCurrencyLabel(state) {
    // Server reports `currency` as a top-level state field (XRP for the May 16
    // demo, RLUSD when the fallback flag is off). Fallback to "XRP" if absent
    // for any reason.
    const currency = state.currency || 'XRP';
    document.querySelectorAll('[data-currency-label]').forEach(el => {
      setText(el, currency);
    });
  }

  // ---------------------------------------------------------------------------
  // Recent events list
  // ---------------------------------------------------------------------------

  const EVENT_LABELS = {
    request_quoted: 'quoted',
    payment_validated: 'paid',
    cert_minted: 'cert minted',
    cache_hit: 'CACHE HIT',
    hcs_anchored: 'Hedera anchor',
    royalty_dispatched: 'royalty',
    uor_mcps_receipt: 'UOR receipt',
  };

  function eventDetail(ev) {
    const p = ev.payload || {};
    switch (ev.kind) {
      case 'request_quoted':
        return `${p.price} RLUSD · ${p.is_cache_hit ? 'hit' : 'miss'} · ${shortUor(ev.request_uor)}`;
      case 'payment_validated':
        return `${p.amount} RLUSD · ${shortTxid(p.txid)}`;
      case 'cert_minted':
        return `${shortUor(p.cert_uor)} · ${p.model || ''}`;
      case 'cache_hit':
        return `${shortUor(p.cert_uor)} · hits=${p.hit_count || '?'}`;
      case 'hcs_anchored':
        return `seq ${p.sequence_number} · ${p.topic_id || ''}`;
      case 'royalty_dispatched':
        return `${p.amount} RLUSD → ${shortAddr(ev.actor || p.recipient)}`;
      case 'uor_mcps_receipt':
        return `trust ${p.trust_level} · pubkey ${(p.public_key || '').slice(0, 16)}…`;
      default:
        return '';
    }
  }

  function pushEventToList(ev) {
    const list = $('#event-list');
    if (!list) return;
    const li = document.createElement('li');
    li.className = `event-${ev.kind}`;
    li.dataset.seq = ev.seq;
    li.innerHTML =
      `<span class="event-time">${fmtTime(ev.ts)}</span>` +
      `<span class="event-kind">${EVENT_LABELS[ev.kind] || ev.kind}</span>` +
      `<span class="event-detail">${eventDetail(ev)}</span>`;
    list.insertBefore(li, list.firstChild);
    // Trim to last 12 entries
    while (list.children.length > 12) list.removeChild(list.lastChild);
  }

  // ---------------------------------------------------------------------------
  // Animation choreography — driven by new events
  // ---------------------------------------------------------------------------

  function activateEdge(edgeId, labelText) {
    const edge = document.getElementById(`edge-${edgeId}`);
    if (edge) {
      // Retrigger the flash animation every time, even if the edge is already
      // active. Same-tick class toggles get debounced by the CSS engine, so
      // we remove → reflow → add to force the animation to replay.
      edge.classList.remove('flashing');
      void edge.getBoundingClientRect();
      edge.classList.add('active', 'flashing');
      setTimeout(() => edge.classList.remove('flashing'), 1000);
    }
    if (labelText) {
      const label = document.getElementById(`label-edge-${edgeId}`);
      if (label) {
        setText(label, labelText);
        label.classList.remove('flashing');
        void label.getBoundingClientRect();
        label.classList.add('visible', 'flashing');
        setTimeout(() => label.classList.remove('flashing'), 1000);
      }
    }
  }

  function flashEdgeHit(edgeId) {
    const edge = document.getElementById(`edge-${edgeId}`);
    if (!edge) return;
    edge.classList.add('hit-flash');
    setTimeout(() => edge.classList.remove('hit-flash'), 3000);
    const label = document.getElementById(`label-edge-${edgeId}`);
    if (label) {
      label.classList.add('hit');
      setTimeout(() => label.classList.remove('hit'), 3000);
    }
  }

  function flashCertHit() {
    const cert = $('#node-cert');
    if (!cert) return;
    cert.classList.add('hit-flash');
    setTimeout(() => cert.classList.remove('hit-flash'), 3000);
  }

  function pulseAnthropic() {
    const ant = $('#node-anthropic');
    if (!ant) return;
    ant.classList.remove('node-dim');
    ant.classList.add('materialize');
    setTimeout(() => ant.classList.remove('materialize'), 800);
    // Bump call counter
    const calls = ant.querySelector('[data-field="calls"]');
    if (calls) {
      const m = /^(\d+)/.exec(calls.textContent || '0');
      const n = m ? Number(m[1]) + 1 : 1;
      setText(calls, `${n} call${n === 1 ? '' : 's'} this session`);
    }
  }

  function materializeCert(certUor) {
    const cert = $('#node-cert');
    if (!cert) return;
    cert.classList.remove('empty');
    cert.classList.add('materialize');
    setTimeout(() => cert.classList.remove('materialize'), 700);
    setText(cert.querySelector('[data-field="cert_uor"]'), shortUor(certUor));
  }

  function bumpUorReceiptCounter() {
    const el = document.querySelector('#node-uor-mcp [data-field="receipts"]');
    if (!el) return;
    const m = /^(\d+)/.exec(el.textContent || '0');
    const n = m ? Number(m[1]) + 1 : 1;
    setText(el, `${n} receipt${n === 1 ? '' : 's'} L1`);
  }

  function updateRequestBanner({ prompt, request_uor, is_cache_hit, price, currency }) {
    const banner = $('#request-banner');
    const promptEl = $('#request-banner-prompt');
    const uorEl = $('#request-banner-uor');
    const tierEl = $('#request-banner-tier');
    if (!banner) return;
    if (promptEl && prompt) setText(promptEl, prompt);
    if (uorEl) setText(uorEl, shortUor(request_uor || ''));
    if (tierEl) {
      const tier = is_cache_hit ? 'CACHE HIT' : 'CACHE MISS';
      const priceLabel = price ? ` · ${price} ${currency || activeCurrency}` : '';
      setText(tierEl, tier + priceLabel);
      tierEl.classList.toggle('hit', !!is_cache_hit);
      tierEl.classList.toggle('miss', !is_cache_hit);
    }
    // Flash the banner so the audience sees it changed.
    banner.classList.remove('flash');
    void banner.getBoundingClientRect();
    banner.classList.add('flash');
    setTimeout(() => banner.classList.remove('flash'), 1300);
  }

  function applyOptimisticBalance(role, deltaAmount) {
    const node = document.querySelector(`[data-actor="${role}"]`);
    if (!node) return;
    const balEl = node.querySelector('[data-field="balance"]');
    if (!balEl) return;
    const current = parseFloat(balEl.textContent);
    if (isNaN(current)) return;
    const newVal = current - parseFloat(deltaAmount);
    setText(balEl, newVal.toFixed(4));
    // Flash the balance briefly so the change is visible.
    balEl.classList.remove('balance-pulse');
    void balEl.getBoundingClientRect();
    balEl.classList.add('balance-pulse');
    setTimeout(() => balEl.classList.remove('balance-pulse'), 1300);
  }

  function handleEvent(ev) {
    const p = ev.payload || {};
    pushEventToList(ev);
    switch (ev.kind) {
      case 'request_quoted':
        updateRequestBanner({
          prompt: p.prompt,
          request_uor: ev.request_uor,
          is_cache_hit: p.is_cache_hit,
          price: p.price,
          currency: activeCurrency,
        });
        break;
      case 'payment_validated': {
        const role = roleForActorAddress(ev.actor);
        const label = `${p.amount} ${activeCurrency}`;
        if (role === 'agent_a') activateEdge('agent-a-to-server', label);
        else if (role === 'agent_b') activateEdge('agent-b-to-server', label);
        if (role && p.amount) {
          applyOptimisticBalance(role, p.amount);
          applyOptimisticBalance('server', `-${p.amount}`);
        }
        // Running metrics: volume increments by the payment amount.
        runningMetrics.total_volume += parseFloat(p.amount || 0);
        renderRunningMetrics();
        break;
      }
      case 'cert_minted':
        activateEdge('server-to-cert');
        materializeCert(p.cert_uor);
        activateEdge('server-to-anthropic');
        pulseAnthropic();
        runningMetrics.total_inferences += 1;
        runningMetrics.cache_misses += 1;
        runningMetrics.anthropic_calls_made += 1;
        renderRunningMetrics();
        break;
      case 'cache_hit': {
        flashCertHit();
        const role = roleForActorAddress(ev.actor);
        if (role === 'agent_a') flashEdgeHit('agent-a-to-server');
        else if (role === 'agent_b') flashEdgeHit('agent-b-to-server');
        runningMetrics.total_inferences += 1;
        runningMetrics.cache_hits += 1;
        runningMetrics.anthropic_calls_saved += 1;
        renderRunningMetrics();
        break;
      }
      case 'hcs_anchored':
        activateEdge('cert-to-hcs', `seq ${p.sequence_number}`);
        break;
      case 'royalty_dispatched':
        activateEdge('server-to-owner', `${p.amount} ${activeCurrency} royalty`);
        applyOptimisticBalance('server', p.amount);
        applyOptimisticBalance('model_owner', `-${p.amount}`);
        runningMetrics.total_royalty += parseFloat(p.amount || 0);
        runningMetrics.total_volume += parseFloat(p.amount || 0);
        renderRunningMetrics();
        break;
      case 'uor_mcps_receipt':
        activateEdge('cert-to-uor');
        bumpUorReceiptCounter();
        break;
    }
  }

  // ---------------------------------------------------------------------------
  // Address → role mapping (refreshed each poll from state.actors)
  // ---------------------------------------------------------------------------

  let actorByAddress = {};

  function refreshActorAddressMap(actors) {
    actorByAddress = {};
    Object.keys(actors || {}).forEach(role => {
      const info = actors[role];
      if (info && info.address) actorByAddress[info.address] = role;
    });
  }

  function roleForActorAddress(addr) {
    return actorByAddress[addr] || null;
  }

  // ---------------------------------------------------------------------------
  // Main poll loop
  // ---------------------------------------------------------------------------

  async function pollOnce() {
    try {
      const resp = await fetch(`${STATE_URL}?since=${lastSeq}`, { cache: 'no-store' });
      if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
      const state = await resp.json();
      onState(state);
      if (!connected) {
        connected = true;
        setStatus('live', true);
      }
    } catch (err) {
      connected = false;
      setStatus('reconnecting…', false);
    }
  }

  function onState(state) {
    activeCurrency = state.currency || 'XRP';
    refreshActorAddressMap(state.actors);
    renderActors(state.actors, activeCurrency);
    renderCert(state.certs);
    renderStandards(state.standards);
    renderCurrencyLabel(state);
    syncAnthropicCounter(state.metrics);

    // Process new events strictly in order (server returns ascending seq).
    // If the dashboard loads AFTER a demo has already run, the first poll
    // returns the whole event log in one batch — staggering the animations
    // by 700ms each so the user sees the sequence play out instead of all
    // edges activating at once.
    const events = (state.events || [])
      .filter(e => e.seq > lastSeq)
      .sort((a, b) => a.seq - b.seq);
    const stagger = events.length > 1 ? 700 : 0;
    events.forEach((ev, idx) => {
      setTimeout(() => handleEvent(ev), idx * stagger);
    });
    if (events.length) {
      lastSeq = events[events.length - 1].seq;
    }

    // Bottom-right seq counter
    setText($('#seq-counter'), `seq ${state.latest_seq || 0}`);
  }

  // ---------------------------------------------------------------------------
  // Boot
  // ---------------------------------------------------------------------------

  // Demo-trigger keyboard shortcuts. Press '1' for the cache-miss batch
  // (single call) and '9' for the cache-hits batch (nine calls). No visible
  // buttons — keeps the dashboard clean for the booth. Server enforces a
  // single-batch-at-a-time lock, so a double-tap is harmless.
  function fireBatch(total, label) {
    fetch(`/demo/run?total=${total}`, { method: 'POST' })
      .then(r => r.json())
      .then(j => {
        if (j.status === 'rejected') {
          console.warn(`[demo] batch ${label} rejected: ${j.reason}`);
        } else {
          console.log(`[demo] batch ${label} (${total}) started`);
        }
      })
      .catch(err => console.error(`[demo] batch ${label} failed:`, err));
  }

  document.addEventListener('keydown', (e) => {
    // Ignore when the user is typing in a field
    if (e.target && (e.target.tagName === 'INPUT' || e.target.tagName === 'TEXTAREA')) return;
    if (e.metaKey || e.ctrlKey || e.altKey) return;
    if (e.key === '1') { e.preventDefault(); fireBatch(1, 'cache-miss'); }
    else if (e.key === '9') { e.preventDefault(); fireBatch(9, 'cache-hits'); }
  });

  // On page load, fast-forward lastSeq past any pre-existing events so a
  // refresh after demos have already run doesn't replay every cert mint and
  // payment animation back at the audience. Static state (balances, cert
  // count, metrics) still renders, only the per-event animations are skipped.
  async function primeSeqAndStart() {
    try {
      const resp = await fetch(`${STATE_URL}?since=0`, { cache: 'no-store' });
      if (resp.ok) {
        const state = await resp.json();
        lastSeq = state.latest_seq || 0;
        // Render the current snapshot once (actors, balances, certs, metrics)
        // but with lastSeq already advanced past historical events so they
        // don't animate.
        onState({ ...state, events: [] });
      }
    } catch (_) { /* fall through to normal polling */ }
    setStatus('live', true);
    setInterval(pollOnce, POLL_INTERVAL_MS);
  }

  function start() {
    setStatus('connecting…', false);
    primeSeqAndStart();
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', start);
  } else {
    start();
  }
})();

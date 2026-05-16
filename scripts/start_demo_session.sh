#!/usr/bin/env bash
# start_demo_session.sh — one-command setup for the RoyaltAI booth demo.
#
# Opens two things:
#   1. Terminal window with the FastAPI server (KEEP ALIVE through entire pitch)
#   2. Browser tab on the dashboard
#
# During the pitch you trigger batches directly from the browser:
#   - Press '1' on the dashboard → fires the cache-miss batch (1 call)
#   - Press '9' on the dashboard → fires the cache-hits batch (9 calls)
# No terminal interaction needed during the demo. Minimize the server window
# and present in fullscreen browser mode.
#
# Run this once before doors open Saturday morning. Do NOT kill the server
# window during the pitch — the cert_store is in-process memory and a restart
# would turn batch 2's cache hits back into cache misses (~$0.135 of wasted
# Anthropic spend AND the demo story collapses).
#
# Usage:
#   bash scripts/start_demo_session.sh
#
# Pre-flight verifies port 8765 is free; skips server launch if already up.

set -e

WORKTREE="/Users/mauraclark/AgentLevy-XRPL-UOR/.claude/worktrees/jolly-yonath-54b30a"
PITCH_URL="http://localhost:8765/pitch"
DASHBOARD_URL="http://localhost:8765/dashboard"
PORT=8765

# ---- 1. Server window (skip if already running) ----
if lsof -i :"$PORT" -sTCP:LISTEN > /dev/null 2>&1; then
    echo "✓ Server already running on port $PORT — skipping server startup."
else
    echo "→ Launching server in new Terminal window..."
    osascript <<EOF
tell application "Terminal"
    activate
    do script "cd '$WORKTREE' && clear && echo '======================================' && echo '  RoyaltAI SERVER' && echo '  DO NOT KILL DURING PITCH' && echo '======================================' && echo '' && uvicorn agentlevy.inference.server:create_app --factory --host 127.0.0.1 --port $PORT"
end tell
EOF
fi

# ---- 2. Wait for /health to respond ----
echo -n "→ Waiting for server /health"
SERVER_UP=0
for i in $(seq 1 30); do
    if curl -sf "http://localhost:$PORT/health" > /dev/null 2>&1; then
        SERVER_UP=1
        echo " ✓"
        break
    fi
    echo -n "."
    sleep 1
done
if [ "$SERVER_UP" -ne 1 ]; then
    echo ""
    echo "✗ Server didn't respond after 30s. Check the server window for errors."
    exit 1
fi

# ---- 3. Open the pitch deck (with the dashboard embedded as section 1) ----
echo "→ Opening pitch deck: $PITCH_URL"
open "$PITCH_URL"

echo ""
echo "✓ Demo session ready."
echo ""
echo "  Pitch deck : $PITCH_URL    ← present from this URL (deck + embedded demo)"
echo "  Dashboard  : $DASHBOARD_URL (just the dashboard, no slides)"
echo "  Server     : port $PORT (Terminal window — minimize and leave alone)"
echo ""
echo "  During the pitch, focus the browser tab and press:"
echo "    1   →  cache-miss batch (1 call, full pipeline)"
echo "    9   →  cache-hits batch (9 calls, royalty climbs)"
echo ""
echo "  Scroll down on the pitch page for the slide sections."
echo "  No terminal interaction needed during the demo."

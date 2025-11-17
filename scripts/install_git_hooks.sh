#!/usr/bin/env bash
set -euo pipefail
ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
HOOK="$ROOT/.git/hooks/pre-push"
cat > "$HOOK" <<'SH'
#!/usr/bin/env bash
set -euo pipefail
echo "[pre-push] running local CI…"
bash scripts/ci_local.sh
echo "[pre-push] passed. Pushing allowed."
SH
chmod +x "$HOOK"
echo "Installed pre-push hook at .git/hooks/pre-push"
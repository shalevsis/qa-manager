#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────
#  QA Agent Skill — Installer
#  Installs the qa-manager Claude Code skill to ~/Claude/qa-manager
#  and registers it in installed_plugins.json.
# ─────────────────────────────────────────────────────────────

set -e

SKILL_NAME="qa-manager"
PLUGIN_ID="qa-manager@community"
INSTALL_DIR="$HOME/Claude/qa-manager"
INSTALLED_JSON="$HOME/.claude/plugins/installed_plugins.json"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "  Installing QA Agent skill for Claude Code..."
echo ""

# ── 1. Copy skill files ──────────────────────────────────────
mkdir -p "$INSTALL_DIR/.claude-plugin"
cp -r "$SCRIPT_DIR/skills" "$INSTALL_DIR/"
if [ -f "$SCRIPT_DIR/.claude-plugin/plugin.json" ]; then
  cp "$SCRIPT_DIR/.claude-plugin/plugin.json" "$INSTALL_DIR/.claude-plugin/"
fi
echo "  ✓ Skill files copied to $INSTALL_DIR"

# ── 2. Make log script executable ───────────────────────────
chmod +x "$INSTALL_DIR/skills/qa-manager/scripts/log_qa_run.py" 2>/dev/null || true

# ── 3. Register in installed_plugins.json ───────────────────
mkdir -p "$HOME/.claude/plugins"

if [ ! -f "$INSTALLED_JSON" ]; then
  echo '{"plugins":[]}' > "$INSTALLED_JSON"
fi

# Remove old entry if present
python3 - <<PYEOF
import json
path = "$INSTALLED_JSON"
with open(path) as f:
    data = json.load(f)
data["plugins"] = [p for p in data.get("plugins", []) if p.get("id") != "$PLUGIN_ID"]
with open(path, "w") as f:
    json.dump(data, f, indent=2)
PYEOF

# Add fresh entry
python3 - <<PYEOF
import json
path = "$INSTALLED_JSON"
with open(path) as f:
    data = json.load(f)
data.setdefault("plugins", []).append({
  "id": "$PLUGIN_ID",
  "name": "$SKILL_NAME",
  "version": "1.0.0",
  "source": "community",
  "path": "$INSTALL_DIR",
  "enabled": True,
  "skills": ["$SKILL_NAME"]
})
with open(path, "w") as f:
    json.dump(data, f, indent=2)
print("  ✓ Registered in installed_plugins.json")
PYEOF

# ── 4. Create feedback and log directories ───────────────────
mkdir -p "$HOME/.claude/qa-feedback"
echo "  ✓ Created ~/.claude/qa-feedback/ for run feedback"

# ── 5. Done ──────────────────────────────────────────────────
echo ""
echo "  ┌─────────────────────────────────────────────────┐"
echo "  │  QA Agent installed successfully!               │"
echo "  │                                                 │"
echo "  │  Restart Claude Code, then use it with:         │"
echo "  │    /qa-manager                                    │"
echo "  │    'run QA on this project'                     │"
echo "  │    'write tests for this file'                  │"
echo "  │                                                 │"
echo "  │  Skill lives at: ~/Claude/qa-manager              │"
echo "  │  Run feedback:   ~/.claude/qa-feedback/         │"
echo "  │  Run logs:       ~/.claude/qa-runs.jsonl        │"
echo "  └─────────────────────────────────────────────────┘"
echo ""

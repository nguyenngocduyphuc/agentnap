#!/bin/bash
# AgentNap installer — symlink CLI, optionally install launchd daemon.
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
BIN="$HOME/.local/bin"
PLIST="$HOME/Library/LaunchAgents/com.agentnap.daemon.plist"

mkdir -p "$BIN"
chmod +x "$DIR/agentnap.py"
ln -sf "$DIR/agentnap.py" "$BIN/agentnap"
echo "✓ agentnap -> $BIN/agentnap"
case ":$PATH:" in *":$BIN:"*) ;; *) echo "⚠ add $BIN to your PATH";; esac

read -r -p "Install background daemon (reaps orphans on memory pressure)? [y/N] " yn
if [[ "${yn:-n}" =~ ^[Yy] ]]; then
  cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN"
  "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>com.agentnap.daemon</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/bin/python3</string>
    <string>$DIR/agentnap.py</string>
    <string>daemon</string>
  </array>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ProcessType</key><string>Background</string>
  <key>StandardOutPath</key><string>/tmp/agentnap.log</string>
  <key>StandardErrorPath</key><string>/tmp/agentnap.log</string>
</dict>
</plist>
EOF
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST"
  echo "✓ daemon loaded (log: /tmp/agentnap.log)"
fi
echo "Done. Try: agentnap status"

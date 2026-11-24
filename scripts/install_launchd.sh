#!/usr/bin/env bash
# Install a macOS launchd job that runs the daily check-in.
# Usage: scripts/install_launchd.sh [HH] [MM]     (default 09:17)
set -euo pipefail

HOUR="${1:-9}"
MINUTE="${2:-17}"
REPO="$(cd "$(dirname "$0")/.." && pwd)"
PY="$REPO/.venv/bin/python"
LABEL="com.charlie.shopee-checkin"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"

if [[ ! -x "$PY" ]]; then
  echo "找不到 $PY，請先照 README 建立 .venv" >&2
  exit 1
fi

mkdir -p "$HOME/Library/LaunchAgents" "$REPO/log"
cat > "$PLIST" <<EOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$PY</string>
    <string>$REPO/shopee_checkin.py</string>
    <string>checkin</string>
  </array>
  <key>WorkingDirectory</key><string>$REPO</string>
  <key>EnvironmentVariables</key>
  <dict>
    <key>BROWSER_CHANNEL</key><string>chrome</string>
    <key>HEADLESS</key><string>1</string>
  </dict>
  <key>StartCalendarInterval</key>
  <dict>
    <key>Hour</key><integer>$HOUR</integer>
    <key>Minute</key><integer>$MINUTE</integer>
  </dict>
  <key>StandardOutPath</key><string>$REPO/log/launchd.out.log</string>
  <key>StandardErrorPath</key><string>$REPO/log/launchd.err.log</string>
</dict>
</plist>
EOF

launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
launchctl bootstrap "gui/$(id -u)" "$PLIST"
echo "已安裝：每天 $(printf %02d:%02d "$HOUR" "$MINUTE") 執行。"
echo "立即測試：launchctl kickstart -p gui/$(id -u)/$LABEL"
echo "Telegram 通知：在 plist 的 EnvironmentVariables 加 TELEGRAM_BOT_TOKEN / TELEGRAM_CHAT_ID 後重跑本腳本"

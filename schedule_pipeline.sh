#!/bin/bash
# Install the ingestion pipeline as a scheduled job, so the architecture's
# "re-runs automatically whenever BIS publishes an amendment" is literally true
# rather than a diagram caption.
#
# The pipeline polls the BIS portal for the standards already in the register and
# reports any status or edition change. It runs in report-only mode: an amendment
# is written into the register only when someone runs `pipeline.py --apply`, so a
# scheduled job can never silently rewrite the data.
#
#   ./schedule_pipeline.sh install     # every 6 hours (macOS launchd)
#   ./schedule_pipeline.sh uninstall
#   ./schedule_pipeline.sh status

set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
LABEL="in.gov.bis.manaksetu.pipeline"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
INTERVAL=21600      # 6 hours

case "${1:-status}" in
install)
  mkdir -p "$HOME/Library/LaunchAgents" "$ROOT/logs"
  cat > "$PLIST" <<PLISTEOF
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$ROOT/backend_venv/bin/python</string>
    <string>$ROOT/pipeline.py</string>
    <string>--versions-limit</string><string>120</string>
  </array>
  <key>WorkingDirectory</key><string>$ROOT</string>
  <key>StartInterval</key><integer>$INTERVAL</integer>
  <key>RunAtLoad</key><false/>
  <key>StandardOutPath</key><string>$ROOT/logs/pipeline.log</string>
  <key>StandardErrorPath</key><string>$ROOT/logs/pipeline.err</string>
</dict></plist>
PLISTEOF
  launchctl unload "$PLIST" 2>/dev/null || true
  launchctl load "$PLIST"
  echo "installed: $LABEL runs every $((INTERVAL/3600))h"
  echo "  logs   $ROOT/logs/pipeline.log"
  echo "  runs   $ROOT/data/pipeline_runs.jsonl"
  echo "  report-only — amendments need 'pipeline.py --apply' to be written"
  ;;
uninstall)
  launchctl unload "$PLIST" 2>/dev/null || true
  rm -f "$PLIST"
  echo "removed $LABEL"
  ;;
status)
  # Captured first, not piped into grep -q: with `set -o pipefail`, grep exiting
  # early sends launchctl a SIGPIPE and the whole pipeline reports failure, which
  # made an installed job look uninstalled.
  loaded="$(launchctl list 2>/dev/null || true)"
  if printf '%s' "$loaded" | grep -qF "$LABEL"; then
    echo "scheduled every $((INTERVAL/3600))h:"
    printf '%s\n' "$loaded" | grep -F "$LABEL"
  else
    echo "not scheduled — run: ./schedule_pipeline.sh install"
  fi
  [ -f "$ROOT/data/pipeline_runs.jsonl" ] && \
    echo "last run: $(tail -1 "$ROOT/data/pipeline_runs.jsonl" | python3 -c 'import json,sys;d=json.load(sys.stdin);print(d["finished"],"changed="+str(d["changed"]))')"
  ;;
*)
  echo "usage: $0 {install|uninstall|status}"; exit 1;;
esac

# Linux equivalent, if you deploy there instead of a Mac:
#   crontab -e
#   0 */6 * * * cd /path/to/SIH && backend_venv/bin/python pipeline.py --versions-limit 120

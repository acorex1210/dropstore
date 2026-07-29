#!/bin/bash
# Abre Terminal.app visualmente y ejecuta el script enviar_agendados.sh
osascript <<'EOF'
tell application "Terminal"
    activate
    do script "/Users/dermaessenza/TRABAJO/enviar_agendados.sh"
end tell
EOF

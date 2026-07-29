#!/bin/bash
cd /Users/dermaessenza/TRABAJO || exit 1
# Esperar a que haya internet (hasta 120s: al despertar tarda mas)
for i in $(seq 1 60); do
  if ping -c 1 -W 2 8.8.8.8 &>/dev/null; then
    break
  fi
  sleep 2
done

HOY=$(date +%d/%m/%Y)
DIA_SEM=$(date +%u)
if [ "$DIA_SEM" = "6" ]; then
  MANANA=$(date -v+2d +%d/%m/%Y)
else
  MANANA=$(date -v+1d +%d/%m/%Y)
fi
/usr/bin/python3 /Users/dermaessenza/TRABAJO/capturar_enviar.py "$HOY" "$MANANA"

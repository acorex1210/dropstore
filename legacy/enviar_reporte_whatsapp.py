#!/usr/bin/env python3
import pywhatkit as kit, time, os, webbrowser

IMAGEN = "/Users/dermaessenza/TRABAJO/reporte_10julio2026.jpg"
TELEFONO = "+51913600399"

caption = "Reporte pacientes agendados 10/07/2026\n(sin retoques/eval/sesiones, sin registros vacios)\n\nGLORIA: 15\nHEBELIN: 8\nTotal: 23"

print("Paso 1: Abriendo WhatsApp Web...")
webbrowser.open("https://web.whatsapp.com")
print("Esperando 30 segundos. Escanea el QR si aparece...")
time.sleep(30)

print("Paso 2: Enviando mensaje...")
try:
    kit.sendwhats_image(TELEFONO, os.path.abspath(IMAGEN), caption, wait_time=60, tab_close=False)
    print("Comando ejecutado. Revisa tu WhatsApp.")
except Exception as e:
    print(f"Error: {e}")
    print("\nPara enviarlo manualmente:")
    print(f"1. Abre web.whatsapp.com y escanea el QR")
    print(f"2. Arrastra este archivo al chat:")
    print(f"   {IMAGEN}")

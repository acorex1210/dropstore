#!/usr/bin/env python3
import pywhatkit as kit, time, os, webbrowser

IMAGEN = "/Users/dermaessenza/TRABAJO/reporte_hoy.jpg"
TELEFONO = "+51913600399"

# Obtener datos del último reporte generado
caption = "Reporte agendados 11/07/2026"

print("Abriendo WhatsApp Web...")
webbrowser.open("https://web.whatsapp.com")
time.sleep(35)
print("Enviando imagen...")
kit.sendwhats_image(TELEFONO, os.path.abspath(IMAGEN), caption, wait_time=60, tab_close=True)
print("Enviado!")

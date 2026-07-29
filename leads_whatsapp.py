#!/usr/bin/env python3
"""
Leads WhatsApp → CONTROL DE LLAMADAS
Lee leads escaneados desde WhatsApp Web y los escribe en la hoja CONTROL.

Uso:
    python3 leads_whatsapp.py                          # Usa el JSON más reciente de Downloads
    python3 leads_whatsapp.py ~/Downloads/whatsapp_leads_2026-07-27.json
"""
import sys
import os
import json
import glob
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

from config import CONTROL_SPREADSHEET_ID, CONTROL_SHEET_NAME, LEADS_JSON_DIR, LEADS_PHONE_DESTINO
from utils import configurar_logging, conectar_gsheets

log = configurar_logging('leads_whatsapp')


def find_latest_json():
    """Busca el JSON más reciente en la carpeta de Downloads."""
    pattern = os.path.join(LEADS_JSON_DIR, 'whatsapp_leads_*.json')
    files = sorted(glob.glob(pattern), key=os.path.getmtime, reverse=True)
    if not files:
        return None
    return files[0]


def load_leads(json_path):
    """Carga leads desde un archivo JSON."""
    with open(json_path, 'r', encoding='utf-8') as f:
        leads = json.load(f)
    log.info(f'Leads cargados: {len(leads)} desde {json_path}')
    return leads


def get_existing_phones(ws):
    """Obtiene los teléfonos ya existentes en la hoja para evitar duplicados."""
    all_rows = ws.get_all_values()
    phones = set()
    for row in all_rows:
        phone = str(row[1]).strip() if len(row) > 1 else ''
        if phone:
            phones.add(phone.replace(' ', '').replace('-', ''))
    return phones


def write_to_sheet(leads):
    """Escribe leads en la hoja CONTROL de Google Sheets."""
    gc = conectar_gsheets()
    sh = gc.open_by_key(CONTROL_SPREADSHEET_ID)

    try:
        ws = sh.worksheet(CONTROL_SHEET_NAME)
    except Exception:
        ws = sh.add_worksheet(title=CONTROL_SHEET_NAME, rows=1000, cols=8)

    existing = get_existing_phones(ws)

    new_rows = []
    skipped = 0
    for lead in leads:
        phone = lead.get('number', '').strip()
        phone_clean = phone.replace(' ', '').replace('-', '')
        if phone_clean in existing:
            skipped += 1
            continue

        row = [
            lead.get('date', datetime.now().strftime('%d/%m/%Y')),
            phone,
            lead.get('campaign', ''),
        ]
        new_rows.append(row)
        existing.add(phone_clean)

    if not new_rows:
        log.info(f'Sin leads nuevos. {skipped} duplicados omitidos.')
        return 0, skipped

    ws.append_rows(new_rows, value_input_option='USER_ENTERED')
    log.info(f'{len(new_rows)} lead(s) escritos en hoja "{CONTROL_SHEET_NAME}"')
    if skipped:
        log.info(f'{skipped} duplicado(s) omitido(s)')
    return len(new_rows), skipped


def main():
    json_path = sys.argv[1] if len(sys.argv) > 1 else find_latest_json()

    if not json_path or not os.path.exists(json_path):
        log.error('No se encontró archivo JSON de leads.')
        log.info('Pasos:')
        log.info('  1. Abrí WhatsApp Web en Chrome')
        log.info('  2. Pegá scanner.js en la consola')
        log.info('  3. Escaneá y clickeá "JSON"')
        log.info(f'  4. Ejecutá: python3 {__file__} ~/Downloads/whatsapp_leads_*.json')
        sys.exit(1)

    leads = load_leads(json_path)
    if not leads:
        log.info('Sin leads en el archivo.')
        sys.exit(0)

    written, skipped = write_to_sheet(leads)
    log.info(f'Resultado: {written} nuevos, {skipped} duplicados')
    log.info('Finalizado.')


if __name__ == '__main__':
    main()

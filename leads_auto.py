#!/usr/bin/env python3
"""
WhatsApp Leads Automático
Abre WhatsApp Web en Chrome, detecte leads por keywords y los escribe en Google Sheets.

Uso:
    python3 leads_auto.py
"""
import sys
import os
import time
import json
import subprocess
import re
from datetime import datetime

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

from config import CONTROL_SPREADSHEET_ID, CONTROL_SHEET_NAME
from utils import configurar_logging, conectar_gsheets

log = configurar_logging('leads_auto')

KEYWORDS = [
    {'keyword': 'novuma', 'campaign': 'Novuma'},
    {'keyword': 'ellanse', 'campaign': 'Ellanse'},
    {'keyword': 'ellansé', 'campaign': 'Ellanse'},
    {'keyword': 'botox', 'campaign': 'Botox'},
    {'keyword': 'toxina', 'campaign': 'Botox'},
    {'keyword': 'acido hialuronico', 'campaign': 'Acido Hialuronico'},
    {'keyword': 'ácido hialurónico', 'campaign': 'Acido Hialuronico'},
    {'keyword': 'radiesse', 'campaign': 'Radiesse'},
    {'keyword': 'bichectomia', 'campaign': 'Bichectomia'},
    {'keyword': 'lipolaser', 'campaign': 'Lipolaser'},
    {'keyword': 'hilos tensores', 'campaign': 'Hilos Tensores'},
    {'keyword': 'plasma', 'campaign': 'Plasma'},
    {'keyword': 'mesoterapia', 'campaign': 'Mesoterapia'},
    {'keyword': 'jalupro', 'campaign': 'Jalupro'},
    {'keyword': 'hidrofacial', 'campaign': 'Hidrofacial'},
    {'keyword': 'bioestimulador', 'campaign': 'Bioestimuladores'},
    {'keyword': 'sculptra', 'campaign': 'Sculptra'},
    {'keyword': 'hifu', 'campaign': 'HIFU'},
]


def run_osascript(script):
    result = subprocess.run(
        ['osascript', '-e', script],
        capture_output=True, text=True, timeout=30
    )
    return result.stdout.strip(), result.stderr.strip()


def chrome_js(code):
    """Ejecuta JavaScript en Chrome via AppleScript."""
    escaped = code.replace('"', '\\"')
    script = f'tell application "Google Chrome"\nset r to execute active tab of front window javascript "{escaped}"\nreturn r\nend tell'
    stdout, stderr = run_osascript(script)
    if stderr and 'error' in stderr.lower():
        log.warning(f'JS error: {stderr[:200]}')
    return stdout


def open_whatsapp():
    log.info('Abriendo WhatsApp Web en Chrome...')
    subprocess.run(['open', '-a', 'Google Chrome', 'https://web.whatsapp.com'], check=True)
    time.sleep(8)
    run_osascript('tell application "Google Chrome" to activate')
    time.sleep(2)


def wait_for_whatsapp(timeout=30):
    log.info('Esperando WhatsApp Web...')
    for i in range(timeout):
        result = chrome_js('document.querySelectorAll("div[data-testid=cell-frame-container]").length')
        try:
            if int(result) > 3:
                log.info(f'WhatsApp Web cargado.')
                return True
        except (ValueError, TypeError):
            pass
        time.sleep(1)
    log.error('WhatsApp Web no cargó')
    return False


def get_chat_phones():
    """Obtiene teléfonos de los chats visibles."""
    js = 'var items=document.querySelectorAll("div[data-testid=cell-frame-container]");var r=[];for(var i=1;i<items.length;i++){var t=items[i].innerText;var p=t.indexOf("+51");if(p==0){var num=t.substring(0,16).trim();r.push({i:i,phone:num});}}JSON.stringify(r)'
    result = chrome_js(js)
    try:
        return json.loads(result)
    except:
        return []


def go_back_to_chat_list():
    """Vuelve a la lista de chats."""
    chrome_js('var back=document.querySelector("div[data-testid=chat-list-search-container]");if(back)back.click()')
    time.sleep(1)


def click_chat_by_phone(phone):
    """Abre un chat por número de teléfono via URL."""
    clean = phone.replace('+', '').replace(' ', '').replace('-', '')
    url = f'https://web.whatsapp.com/send?phone={clean}'
    chrome_js(f'window.location.href="{url}"')
    time.sleep(3)
    for _ in range(10):
        check = chrome_js('document.querySelector("div[data-testid=conversation-panel-messages]")?"ok":"wait"')
        if check == 'ok':
            break
        time.sleep(1)


def get_messages_text():
    """Obtiene textos de mensajes del chat abierto."""
    js = 'var msgs=document.querySelectorAll("div[data-testid=msg-container]");var r=[];for(var i=0;i<msgs.length;i++){var t=msgs[i].innerText;if(t&&t.length>5){r.push(t.substring(0,200));}}JSON.stringify(r.slice(-15))'
    result = chrome_js(js)
    try:
        return json.loads(result)
    except:
        return []


def find_keyword(text):
    text_lower = text.lower()
    for kw in KEYWORDS:
        if kw['keyword'] in text_lower:
            return kw['campaign']
    return None


def normalize_number(num):
    return re.sub(r'[\s\-\(\)]', '', num)


def scan_all_chats():
    phones = get_chat_phones()
    if not phones:
        log.error('No se encontraron chats con teléfono')
        return []

    log.info(f'Chats con teléfono: {len(phones)}')
    leads = []
    seen = set()

    for chat in phones:
        phone = chat['phone']
        phone_norm = normalize_number(phone)

        log.info(f'  Chat: {phone}')
        click_chat_by_phone(phone)

        messages = get_messages_text()
        for msg in messages:
            campaign = find_keyword(msg)
            if campaign:
                key = f'{phone_norm}_{campaign}'
                if key not in seen:
                    leads.append({
                        'number': phone,
                        'number_normalized': phone_norm,
                        'campaign': campaign,
                        'date': datetime.now().strftime('%d/%m/%Y'),
                        'snippet': msg[:80]
                    })
                    seen.add(key)
                    log.info(f'    -> LEAD: {phone} [{campaign}]')
                break

        go_back_to_chat_list()

    return leads


def get_existing_phones(ws):
    all_rows = ws.get_all_values()
    phones = set()
    for row in all_rows:
        phone = str(row[1]).strip() if len(row) > 1 else ''
        if phone:
            phones.add(normalize_number(phone))
    return phones


def write_to_sheet(leads):
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
        if lead['number_normalized'] in existing:
            skipped += 1
            continue
        new_rows.append([lead['date'], "'" + lead['number'], lead['campaign']])
        existing.add(lead['number_normalized'])

    if not new_rows:
        log.info(f'Sin leads nuevos. {skipped} duplicados omitidos.')
        return 0, skipped

    # Find first empty row in column A
    all_rows = ws.get_all_values()
    next_row = len(all_rows) + 1
    while next_row <= len(all_rows) and any(cell.strip() for cell in all_rows[next_row - 1]):
        next_row += 1

    range_str = f'A{next_row}:C{next_row + len(new_rows) - 1}'
    ws.update(range_name=range_str, values=new_rows, value_input_option='USER_ENTERED')
    log.info(f'{len(new_rows)} lead(s) escritos en hoja "{CONTROL_SHEET_NAME}" (fila {next_row})')
    if skipped:
        log.info(f'{skipped} duplicado(s) omitido(s)')
    return len(new_rows), skipped


def main():
    log.info('=== WhatsApp Leads Automático ===')
    open_whatsapp()
    if not wait_for_whatsapp():
        sys.exit(1)

    leads = scan_all_chats()
    log.info(f'Leads detectados: {len(leads)}')

    if not leads:
        log.info('Sin leads nuevos.')
        return

    for lead in leads:
        log.info(f'  {lead["number"]} -> {lead["campaign"]}')

    log.info('Escribiendo en Google Sheets...')
    written, skipped = write_to_sheet(leads)
    log.info(f'Resultado: {written} nuevos, {skipped} duplicados')
    log.info('Finalizado.')


if __name__ == '__main__':
    main()

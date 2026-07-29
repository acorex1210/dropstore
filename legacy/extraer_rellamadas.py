#!/usr/bin/env python3
"""
Extrae de WhatsApp Web los chats donde el último mensaje fue nuestro
(pacientes sin respuesta) y los guarda en la hoja RELLAMADAS.
"""

import gspread, os, re, sys, time, json
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime

SHEET_ID = '1fqC_v1IS0cynbnUa0sie1YrGgNu9jodMFgrN6oxUM30'
JSON_KEY = os.path.expanduser('~/credenciales-sheets.json')
WS_NAME = 'RELLAMADAS'
HEADER_ROW = 3
PROFILE_DIR = os.path.expanduser('~/Library/Application Support/Google/Chrome/WhatsAppProfile')

def conectar_sheets():
    gc = gspread.service_account(filename=JSON_KEY)
    sh = gc.open_by_key(SHEET_ID)
    return sh.worksheet(WS_NAME)

def leer_existentes(ws):
    raw = ws.get_all_values()
    if len(raw) <= HEADER_ROW + 1:
        return set()
    phones = set()
    for r in raw[HEADER_ROW + 1:]:
        if len(r) > 1 and r[1].strip():
            clean = re.sub(r'\D', '', r[1].strip())
            phones.add(clean)
    return phones

def normalizar_numero(texto):
    if not texto:
        return ''
    return re.sub(r'[\s\-\–\(\)\+\#]', '', texto.strip())

def ejecutar_js(driver, script):
    return driver.execute_script(script)

def extraer_rellamadas():
    ws = conectar_sheets()
    existentes = leer_existentes(ws)
    print(f'Celulares ya registrados en RELLAMADAS: {len(existentes)}')

    options = Options()
    options.add_argument(f'user-data-dir={PROFILE_DIR}')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-blink-features=AutomationControlled')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)

    try:
        driver.get('https://web.whatsapp.com')
        wait = WebDriverWait(driver, 180)

        print('\nEsperando que escanees el QR de WhatsApp Web...')
        wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, 'div[role="list"]')))
        print('Chats cargados.')
        time.sleep(3)

        chats_data = ejecutar_js(driver, """
            const items = document.querySelectorAll('div[role="list"] > div');
            const results = [];
            for (const item of items) {
                try {
                    const nameEl = item.querySelector('[role="gridcell"] span');
                    const name = nameEl ? nameEl.textContent.trim() : '';

                    const spans = item.querySelectorAll('span[dir="auto"]');
                    const lastMsg = spans.length > 0 ? spans[spans.length - 1].textContent.trim() : '';

                    const hasCheck = item.querySelector('span[data-icon]');
                    const icon = hasCheck ? hasCheck.getAttribute('data-icon') : '';

                    const timeEl = item.querySelector('[aria-label*="chronos"], time');
                    const time = timeEl ? (timeEl.getAttribute('title') || timeEl.textContent.trim()) : '';

                    results.push({name, lastMsg, icon, time});
                } catch(e) {}
            }
            return JSON.stringify(results);
        """)

        chats = json.loads(chats_data)
        print(f'Chats encontrados: {len(chats)}')

        nuevos = []
        for i, chat in enumerate(chats):
            name = chat.get('name', '')
            last_msg = chat.get('lastMsg', '')
            icon = chat.get('icon', '')
            time_raw = chat.get('time', '')

            tiene_check = any(k in icon for k in ['check', 'dblcheck', 'msg-check', 'msg-dblcheck', 'msg-time'])

            if not tiene_check:
                continue
            if not name or not last_msg:
                continue

            numero = normalizar_numero(name)
            if not numero or not numero.isdigit() or len(numero) < 9:
                continue

            if numero in existentes:
                continue

            fecha = datetime.now().strftime('%d.%m')
            campana = last_msg[:50] if last_msg else ''

            nuevos.append([fecha, numero, campana, ''])
            existentes.add(numero)
            print(f'  [{i+1}] +{numero} | {campana[:30]} | {time_raw}')

        driver.quit()

        if not nuevos:
            print('\nNo se encontraron nuevos chats para agregar.')
            return

        print(f'\nAgregando {len(nuevos)} registros a RELLAMADAS...')
        for fila in nuevos:
            ws.append_row(fila, value_input_option='USER_ENTERED')

        print('✅ Completado.')

    except Exception as e:
        print(f'ERROR: {e}')
        import traceback
        traceback.print_exc()
        driver.quit()
        sys.exit(1)

if __name__ == '__main__':
    extraer_rellamadas()

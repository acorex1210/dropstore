#!/usr/bin/env python3
"""
WhatsApp Web → Google Sheets RELLAMADAS
Extrae chats donde el paciente no ha respondido (último mensaje fue nuestro)
y guarda:
  - Número del paciente
  - Fecha del último mensaje
  - Campaña a la que pertenece (cruzando con base de datos)

Uso:
  python3 extraer_rellamadas_v2.py                        # modo normal
  python3 extraer_rellamadas_v2.py --setup                # crear perfil Chrome
  python3 extraer_rellamadas_v2.py --dry-run              # vista previa
  python3 extraer_rellamadas_v2.py --test-sheet SHEET_ID  # usar otra hoja (ej: copia de prueba)
  python3 extraer_rellamadas_v2.py --debug-whatsapp       # muestra info de todos los chats (sin filtrar)
"""

import gspread
import os
import re
import sys
import time
import json
import requests
import openpyxl
import tempfile
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from webdriver_manager.chrome import ChromeDriverManager
from datetime import datetime
from selenium.common.exceptions import TimeoutException

from config import (
    RELLAMADAS_SHEET_ID, SHEET_DATOS_ID, JSON_KEY, PROFILE_DIR,
    WS_RELLAMADAS, HEADER_ROW, COL_FECHA, COL_CELULAR, COL_CAMPAÑA,
    COL_CONTESTA, COL_CRM, COL_AGENDA, COL_RELLAMADA,
    CJ_COL_TELEFONO, CJ_COL_CAMPAÑA,
    CRMS, NO_INTERESADO, CAMPANAS_ESPECIFICAS, CAMPANAS_POR_TEXTO,
)


# ============================================================
# GOOGLE SHEETS
# ============================================================
def conectar_gsheets():
    gc = gspread.service_account(filename=JSON_KEY)
    return gc


def leer_existentes(ws):
    raw = ws.get_all_values()
    if len(raw) <= HEADER_ROW + 1:
        return set(), None
    phones = set()
    ultima_fecha_raw = ''
    ultima_fecha_num = -1
    for r in raw[HEADER_ROW + 1:]:
        if len(r) > COL_CELULAR and r[COL_CELULAR].strip():
            clean = re.sub(r'\D', '', r[COL_CELULAR].strip())
            if clean:
                phones.add(clean)
        if len(r) > COL_FECHA and r[COL_FECHA].strip():
            # Formato DD.MM
            m = re.match(r'(\d{1,2})\.(\d{1,2})', r[COL_FECHA].strip())
            if m:
                dia, mes = int(m.group(1)), int(m.group(2))
                num = mes * 100 + dia  # MM*100+DD para comparar fácil
                if num > ultima_fecha_num:
                    ultima_fecha_num = num
                    ultima_fecha_raw = r[COL_FECHA].strip()
    # Convertir a datetime
    if ultima_fecha_raw:
        m = re.match(r'(\d{1,2})\.(\d{1,2})', ultima_fecha_raw)
        if m:
            dia, mes = int(m.group(1)), int(m.group(2))
            hoy = datetime.now()
            anio = hoy.year
            # Si la fecha está en el futuro (>hoy + 31 días), asumir año anterior
            fecha = datetime(anio, mes, dia)
            diff = (fecha - hoy).days
            if diff > 31:
                fecha = datetime(anio - 1, mes, dia)
            return phones, fecha
    return phones, None


def construir_mapa_campanas(sh):
    """
    Construye un dict {teléfono: campaña} a partir de CONFIRMADOS CJ.
    """
    mapa = {}
    ws = sh.worksheet('CONFIRMADOS CJ')
    vals = ws.get_all_values()
    if len(vals) <= 4:
        return mapa
    for row in vals[4:]:
        if len(row) <= max(CJ_COL_TELEFONO, CJ_COL_CAMPAÑA):
            continue
        phone_raw = row[CJ_COL_TELEFONO].strip()
        camp = row[CJ_COL_CAMPAÑA].strip()
        if phone_raw and camp:
            phone = re.sub(r'\D', '', phone_raw)
            if phone:
                mapa[phone] = camp
    return mapa


# ============================================================
# WHATSAPP WEB (SELENIUM)
# ============================================================
def setup_chrome():
    options = Options()
    options.add_argument(f'user-data-dir={PROFILE_DIR}')
    options.add_argument('--disable-dev-shm-usage')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-blink-features=AutomationControlled')

    service = Service(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver


def esperar_chats(driver, timeout=180):
    print('  Esperando que WhatsApp Web cargue...')
    inicio = time.time()

    while time.time() - inicio < timeout:
        # Tomar screenshot periódicamente para debug
        if int(time.time() - inicio) % 30 == 0 and int(time.time() - inicio) > 0:
            driver.save_screenshot(f'/tmp/whatsapp_{int(time.time()-inicio)}s.png')

        # Verificar si hay QR (canvas)
        qr = driver.find_elements(By.CSS_SELECTOR, 'canvas')
        if qr:
            print('  📷 QR detectado - escanea el código con tu celular.')
            print('  (Cuando los chats aparezcan, se detectarán automáticamente)')

        # Verificar si ya están los chats - detectar por JS si hay elementos visibles
        hay_chats = driver.execute_script("""
            const selectores = [
                'div[role="list"]',
                'div[data-testid="chat-list"]',
                'div[aria-label="Lista de chats"]',
                'div[aria-label="Chat list"]',
            ];
            for (const sel of selectores) {
                const el = document.querySelector(sel);
                if (el && el.textContent.trim().length > 100) return el.children.length;
            }
            return 0;
        """)
        if hay_chats:
            print(f'  ✅ Chats cargados ({hay_chats} chats).')
            time.sleep(3)
            return

        time.sleep(2)

    # Timeout - preguntar al usuario si ya escaneó
    print()
    print('  ⏳ ¿Ya escaneaste el QR y ves tus chats?')
    print('  Si es así, presiona Enter para continuar.')
    print('  Si no, escanea el QR y luego presiona Enter.')
    try:
        input('  Presiona Enter cuando esté listo...')
        time.sleep(3)
        return
    except:
        pass

    # Timeout final - tomar screenshot y mostrar info de la página
    print('  ⚠ Tiempo de espera agotado.')
    driver.save_screenshot('/tmp/whatsapp_error.png')
    print('  Screenshot guardado en /tmp/whatsapp_error.png')

    info = driver.execute_script("""
        return JSON.stringify({
            url: location.href,
            title: document.title,
            bodyClasses: document.body.className,
            selectors: {
                role_list: document.querySelectorAll('div[role="list"]').length,
                testid_list: document.querySelectorAll('div[data-testid="chat-list"]').length,
                aria_list: document.querySelectorAll('div[aria-label="Lista de chats"]').length,
                canvas: document.querySelectorAll('canvas').length,
                login_button: document.querySelector('[data-testid="login"]') ? true : false,
            }
        });
    """)
    print(f'  Info página: {info}')
    raise TimeoutException('No se detectaron chats en WhatsApp Web')





def normalizar_fecha(raw_fecha):
    """
    Convierte fecha extraída de WhatsApp al formato DD.MM
    Ej: "12/06/2024 10:30" → "12.06"
        "10:30" → fecha actual
        "Ayer 15:00" → fecha de ayer
    """
    if not raw_fecha:
        return datetime.now().strftime('%d.%m')

    raw = raw_fecha.strip()

    # Intentar formato "DD/MM/YYYY" o "DD/MM/YY"
    m = re.search(r'(\d{1,2})/(\d{1,2})(?:/(\d{2,4}))?', raw)
    if m:
        dia, mes = int(m.group(1)), int(m.group(2))
        return f'{dia:02d}.{mes:02d}'

    # Si solo tiene hora, es hoy
    m = re.match(r'^\d{1,2}:\d{2}', raw)
    if m:
        return datetime.now().strftime('%d.%m')

    # "Ayer" -> ayer
    if 'ayer' in raw.lower():
        ayer = datetime.now().day - 1
        mes = datetime.now().month
        # Manejar cambio de mes
        if ayer < 1:
            from calendar import monthrange
            mes_anterior = mes - 1 if mes > 1 else 12
            ayer = monthrange(datetime.now().year, mes_anterior)[1]
            mes = mes_anterior
        return f'{ayer:02d}.{mes:02d}'

    return datetime.now().strftime('%d.%m')


# ============================================================
# MAIN
# ============================================================
def main():
    dry_run = '--dry-run' in sys.argv
    setup_only = '--setup' in sys.argv

    # Sheet override para pruebas
    sheet_id = RELLAMADAS_SHEET_ID
    if '--test-sheet' in sys.argv:
        idx = sys.argv.index('--test-sheet')
        if idx + 1 < len(sys.argv):
            sheet_id = sys.argv[idx + 1]
            dry_run = True
            print(f'🔬 MODO PRUEBA: usando sheet {sheet_id[:8]}...')

    print('=' * 50)
    print('EXTRACTOR RELLAMADAS v2')
    print('=' * 50)

    # 1. Conectar y leer datos
    print('\n[1/4] Leyendo datos...')
    gc = conectar_gsheets()

    # Intentar abrir como Google Sheet nativo; si falla, descargar como xlsx
    existentes = set()
    ultima_fecha = None
    using_xlsx = False
    try:
        sh_rellamadas = gc.open_by_key(sheet_id)
        ws_rellamadas = sh_rellamadas.worksheet(WS_RELLAMADAS)
        existentes, ultima_fecha = leer_existentes(ws_rellamadas)
    except Exception:
        using_xlsx = True
        dry_run = True
        print('  (Sheet es archivo Excel, modo lectura local)')
        url = f'https://docs.google.com/spreadsheets/d/{sheet_id}/export?format=xlsx'
        r = requests.get(url)
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix='.xlsx')
        tmp.write(r.content)
        tmp.close()
        wb = openpyxl.load_workbook(tmp.name, data_only=True)
        ws = wb[WS_RELLAMADAS]
        ultima_fecha_num = -1
        for i, row in enumerate(ws.iter_rows(min_row=HEADER_ROW + 1, values_only=True)):
            if len(row) > COL_CELULAR and row[COL_CELULAR] is not None:
                clean = re.sub(r'\D', '',
                    str(int(row[COL_CELULAR])) if isinstance(row[COL_CELULAR], float)
                    else str(row[COL_CELULAR]))
                if clean:
                    existentes.add(clean)
            if len(row) > COL_FECHA and row[COL_FECHA] is not None:
                fecha_raw = str(row[COL_FECHA]).strip()
                m = re.match(r'(\d{1,2})\.(\d{1,2})', fecha_raw)
                if m:
                    dia, mes = int(m.group(1)), int(m.group(2))
                    num = mes * 100 + dia
                    if num > ultima_fecha_num:
                        ultima_fecha_num = num
                        hoy = datetime.now()
                        anio = hoy.year
                        fecha = datetime(anio, mes, dia)
                        if (fecha - hoy).days > 31:
                            fecha = datetime(anio - 1, mes, dia)
                        ultima_fecha = fecha
        wb.close()
        os.unlink(tmp.name)

    print(f'  Registros existentes en RELLAMADAS: {len(existentes)}')
    if ultima_fecha:
        print(f'  Última fecha registrada: {ultima_fecha.strftime("%d.%m.%Y")}')

    print('  Construyendo mapa de campañas...')
    sh_datos = gc.open_by_key(SHEET_DATOS_ID)
    mapa_campanas = construir_mapa_campanas(sh_datos)
    print(f'  Teléfonos con campaña en BD: {len(mapa_campanas)}')

    # Si es modo xlsx (copia de prueba), solo mostrar stats y salir
    if using_xlsx:
        print('\n📋 Modo prueba - estadísticas:')
        print(f'   RELLAMADAS: {len(existentes)} registros')
        print(f'   Campañas disponibles: {len(mapa_campanas)}')
        print(f'   Potenciales a extraer (en BD pero no en RELLAMADAS):')
        count = 0
        for phone, camp in mapa_campanas.items():
            if phone not in existentes:
                count += 1
                if count <= 5:
                    print(f'     +{phone} | {camp}')
        print(f'     ... y {count - 5} más' if count > 5 else '')
        print('\n✅ Conexión verificada. Para extraer datos reales necesitas:')
        print('   1. Convertir la copia a Hoja de Google (Archivo > Guardar como Hoja de Google)')
        print('   2. O ejecutar sin --test-sheet para usar la hoja de producción')
        print()
        return

    # 2. Iniciar Chrome / WhatsApp Web
    print('\n[2/4] Iniciando Chrome...')
    driver = setup_chrome()
    driver.get('https://web.whatsapp.com')

    if setup_only:
        print('\nModo --setup:')
        print('1. Se abrirá Chrome con un perfil nuevo')
        print('2. Escanea el código QR de WhatsApp Web')
        print('3. Cuando veas tus chats, vuelve a esta terminal')
        print('4. Presiona Enter y el perfil quedará guardado')
        print(f'\nPerfil: {PROFILE_DIR}')
        input('\nPresiona Enter después de escanear el QR...')
        driver.quit()
        print('✅ Perfil configurado. Ya puedes usar el script sin --setup')
        return

    esperar_chats(driver)

    # Modo debug: mostrar info de todos los chats y salir
    if '--debug-whatsapp' in sys.argv:
        debug = driver.execute_script("""
            const container = document.querySelector('div[role="list"]') || document.querySelector('div[data-testid="chat-list"]');
            if (!container) return JSON.stringify({ error: 'no container' });
            let items = Array.from(container.children);
            if (items.length === 1 && items[0].children.length > 5) items = Array.from(items[0].children);
            items = items.filter(el => el.querySelector('[role="gridcell"] span'));
                return JSON.stringify(items.map((item, i) => {
                const nameEl = item.querySelector('[role="gridcell"] span');
                const name = nameEl ? nameEl.textContent.trim() : '';

                // Detectar si nuestro msg es el último
                let esMsgNuestro = false;
                let statusIcono = '';
                const statusEl = item.querySelector('[data-testid="last-msg-status"]');
                if (statusEl) {
                    const svgTitle = statusEl.querySelector('svg title');
                    if (svgTitle) {
                        statusIcono = svgTitle.textContent.trim();
                        if (statusIcono.includes('wds-ic-')) esMsgNuestro = true;
                    }
                    // Si statusEl existe pero NO tiene wds-ic-, no es nuestro mensaje
                }

                let statusHTML = statusEl ? statusEl.innerHTML.substring(0, 300) : '';
                const icons = Array.from(item.querySelectorAll('[data-icon]')).map(e => e.getAttribute('data-icon'));
                const testids = Array.from(item.querySelectorAll('[data-testid]')).map(e => e.getAttribute('data-testid'));
                const tieneLabel = icons.includes('ic-label-filled');
                // Extraer texto de etiquetas
                let labelTexts = '';
                if (tieneLabel) {
                    const labelEls = item.querySelectorAll('[data-icon="ic-label-filled"]');
                    for (const le of labelEls) {
                        const parent = le.closest('[role="gridcell"]') || le.parentElement;
                        const allSpans = parent ? parent.querySelectorAll('span') : [];
                        for (const s of allSpans) {
                            const t = (s.textContent || '').trim().toLowerCase();
                            if (t && t.length < 20 && !/^[\d\s\+]+$/.test(t) && t !== le.textContent.trim()) {
                                labelTexts += (labelTexts ? ',' : '') + t;
                            }
                        }
                    }
                }
                const dataId = item.getAttribute('data-id') || '';
                const numMatch = dataId.match(/(\d+)@c\.us/);
                const numero = numMatch ? numMatch[1] : (name.replace(/\D/g, ''));
                return { i, name, esMsgNuestro, statusIcono, statusHTML, icons, testids, tieneLabel, labelTexts, dataId, numero };
            }));
        """)
        data = json.loads(debug)
        print(f'\n🔍 DEBUG - {len(data)} chats:')
        for c in data:
            if c.get('name'):
                nuestro = '✅ NOSOTROS' if c.get('esMsgNuestro') else '❌ ELLOS'
                label_txt = c.get('labelTexts', '')
                label = f' 🏷️{label_txt}' if label_txt else (' 🏷️LABEL?' if c.get('tieneLabel') else '')
                icono = c.get('statusIcono','') or ''
                icono_str = f' [{icono}]' if icono else ''
                num_str = c.get('numero','')[:15] if c.get('numero','') else 'sin# '
                print(f'  [{c["i"]}] {nuestro}{label}{icono_str} "{c["name"]}" num={num_str}')
        # Mostrar HTML detallado de algunos chats
        print(f'\n  HTML interno de last-msg-status (primeros reales):')
        for c in data:
            name = c.get('name','')
            if name and not c.get('tieneLabel') and name not in ('default-contact-refreshed','wds-ic-disappearing-messages'):
                if '+' in name or ' ' in name.strip():
                    print(f'\n  "{name}" (Nuestro: {c.get("esMsgNuestro")}):')
                    html = c.get('statusHTML','')
                    if html:
                        print(f'    HTML: {html[:250]}')
                    else:
                        print(f'    (sin last-msg-status)')
                    print(f'    icons: {c.get("icons",[])}')
                    break  # solo 1 ejemplo
        driver.quit()
        return

    # 3. Escanear chats (con scroll para cargar todos)
    print('\n[3/4] Escaneando chats de WhatsApp...')

    # Scroll para cargar más chats (WhatsApp virtualiza la lista)
    print('    Cargando más chats (scroll)...')
    for _ in range(10):
        driver.execute_script("""
    const c = document.querySelector('div[role="list"]') || document.querySelector('div[data-testid="chat-list"]');
    if (c) c.scrollTop = c.scrollHeight;
    """)
        time.sleep(1)
    print('    Volviendo al inicio...')
    driver.execute_script("""
    const c = document.querySelector('div[role="list"]') || document.querySelector('div[data-testid="chat-list"]');
    if (c) c.scrollTop = 0;
    """)
    time.sleep(2)

    resultados = driver.execute_script("""
    const container = document.querySelector('div[role="list"]') || document.querySelector('div[data-testid="chat-list"]');
    if (!container) return JSON.stringify({ error: 'no container', chats: [] });

    let items = Array.from(container.children);
    if (items.length === 1 && items[0].children.length > 5) {
        items = Array.from(items[0].children);
    }
    items = items.filter(el => el.querySelector('[role="gridcell"] span'));

    const results = [];

    for (let i = 0; i < items.length; i++) {
        const item = items[i];
        try {
            const nameEl = item.querySelector('[role="gridcell"] span');
            const name = nameEl ? nameEl.textContent.trim() : '';

            const statusEl = item.querySelector('[data-testid="last-msg-status"]');
            const statusIcono = statusEl ? (statusEl.querySelector('svg title')?.textContent.trim() || '') : '';

            const allIconsArr = Array.from(item.querySelectorAll('[data-icon]')).map(e => e.getAttribute('data-icon'));

            // Extraer texto de todas las etiquetas/labels visibles
            const labelTexts = Array.from(item.querySelectorAll('[data-icon="ic-label-filled"]'))
                .map(el => {
                    // El texto de la etiqueta está en un span hermano o padre cercano
                    const parent = el.closest('[role="gridcell"]') || el.parentElement;
                    // Buscar spans con texto después del icono
                    const spans = parent ? parent.querySelectorAll('span[dir="auto"]') : [];
                    for (const s of spans) {
                        const t = s.textContent.trim().toLowerCase();
                        if (t.length > 0 && t.length < 20 && !t.match(/^[\d\s\+]+$/)) {
                            return t;
                        }
                    }
                    return '';
                })
                .filter(t => t.length > 0)
                .join(',');

            const timeEl = item.querySelector('time');
            const timeTitle = timeEl ? (timeEl.getAttribute('title') || timeEl.textContent.trim()) : '';

            // Solo skip si la etiqueta dice EXACTAMENTE "gloria"
            const esGloria = labelTexts.includes('gloria');

            const dataId = item.getAttribute('data-id') || '';
            const match = dataId.match(/(\\d+)@c\\.us/);
            const numeroDataId = match ? match[1] : '';

            results.push({
                index: i,
                name: name,
                statusIcono: statusIcono,
                timeTitle: timeTitle,
                labelTexts: labelTexts,
                esGloria: esGloria,
                numeroDataId: numeroDataId
            });
        } catch(e) {}
    }
    return JSON.stringify({ error: null, chats: results });
    """)

    data = json.loads(resultados)
    if data.get('error'):
        print(f'  Error: {data["error"]}')
        driver.quit()
        return

    chats = data.get('chats', [])
    print(f'  Chats encontrados: {len(chats)}')

    if chats:
        for c in chats[:5]:
            nuestro = '✅' if c.get('statusIcono', '').startswith('wds-ic-') else '❌'
            label = f' lbl:{c["labelTexts"]}' if c.get('labelTexts') else ''
            print(f'    {nuestro} "{c["name"][:25]:25s}"{label}')
        if len(chats) > 5:
            print(f'    ... y {len(chats)-5} más')

    # Filtrar chats candidatos (sin filtrar por gloria aún, se detecta al abrir)
    candidatos = []
    chats_sistema = 0

    for info in chats:
        name = info.get('name', '')
        if not name:
            continue
        if name in ['1 mensaje no leído', '1 mensaje no leido',
                     '2 mensajes no leídos', '2 mensajes no leidos',
                     'wds-ic-disappearing-messages']:
            chats_sistema += 1
            continue
        # Extraer número tentativo
        num = info.get('numeroDataId', '')
        if not num:
            solo_numeros = re.sub(r'\D', '', name)
            if solo_numeros and len(solo_numeros) >= 9:
                num = solo_numeros
        if num and not num.startswith('51'):
            continue  # No Perú, saltar
        info['numero_previo'] = num or ''
        candidatos.append(info)

    print(f'\n  Filtrado:')
    print(f'    - UI/No chat: {chats_sistema}')
    print(f'    - Candidatos: {len(candidatos)}')

    # 4. Procesar cada chat (abriéndolo con Selenium native click)
    nuevos = []
    errores = 0
    skip_gloria = 0
    saltados_no_peru = 0
    saltados_sin_numero = 0
    saltados_interes = 0
    saltados_fecha = 0
    saltados_existentes = 0

    for idx, info in enumerate(candidatos):
        name = info.get('name', '')
        time_raw = info.get('timeTitle', '')
        print(f'\n  [{idx+1}/{len(candidatos)}] {name} ({time_raw})')

        try:
            # Click nativo de Selenium en el chat
            chat_index = info.get('index', -1)
            clicked_ok = False
            try:
                chat_el = driver.find_element(By.XPATH, f"//span[text()='{name}']")
                chat_el.click()
                time.sleep(2)
                clicked_ok = True
            except Exception:
                if chat_index >= 0:
                    driver.execute_script(f"""
                const c = document.querySelector('div[role="list"]') || document.querySelector('div[data-testid="chat-list"]');
                let items = Array.from(c?.children || []);
                if (items.length === 1 && items[0].children.length > 5) items = Array.from(items[0].children);
                const target = items[{chat_index}];
                if (target) target.click();
                """)
                    time.sleep(2)
                    clicked_ok = True
            if not clicked_ok:
                print(f'    ⚠ No se pudo hacer clic')
                continue

            # Verificar si tiene etiqueta "gloria" en el header del chat abierto
            es_gloria = driver.execute_script("""
    try {
        const header = document.querySelector('header');
        if (!header) return false;
        const txt = header.textContent.toLowerCase();
        // Buscar etiqueta "gloria" en el header (es un label/pill)
        if (txt.includes('gloria')) return true;
        return false;
    } catch(e) { return false; }
    """)
            if es_gloria:
                skip_gloria += 1
                print(f'    ⏩ Etiqueta "gloria"')
                continue

            # Extraer número (desde data-id, nombre, o dentro del chat abierto)
            numero = info.get('numero_previo', '')
            if not numero or len(numero) < 9:
                # Cerrar cualquier panel previo
                driver.execute_script("document.body.style.background='';")
                driver.execute_script("""
    try {
        document.querySelector('[role="dialog"]')?.querySelector('[aria-label="Cerrar"], [aria-label="Close"]')?.click();
        // Escape para cerrar panel
        document.dispatchEvent(new KeyboardEvent('keydown', {'key': 'Escape'}));
    } catch(e) {}
    """)
                time.sleep(1)
                # Abrir panel de contacto (click en nombre)
                driver.execute_script("""
    try {
        const header = document.querySelector('header');
        if (header) {
            const nameArea = header.querySelector('div[role="button"], span[dir="auto"]');
            if (nameArea) nameArea.click();
        }
    } catch(e) {}
    """)
                time.sleep(2)
                num_from_chat = driver.execute_script("""
    try {
        // Solo buscar en panel de contacto visible
        const panel = document.querySelector('[role="dialog"]') || document.querySelector('[data-testid*="contact"]');
        if (!panel) return '';
        const text = panel.textContent;
        // Buscar perí +51 o 51 o número de 9 dígitos (peruano)
        const m = text.match(/\\+?51[ -]?(\\d{2,3}[ -]?\\d{3}[ -]?\\d{3,4})/);
        if (m) return m[0].replace(/[^\\d]/g, '');
        const m2 = text.match(/(\\d{9})(?:\\D|$)/);
        if (m2) return m2[1];
        return '';
    } catch(e) { return ''; }
    """)
                # Cerrar panel de contacto
                driver.execute_script("""
    try {
        document.querySelector('[role="dialog"]')?.querySelector('[aria-label="Cerrar"], [aria-label="Close"]')?.click();
        document.dispatchEvent(new KeyboardEvent('keydown', {'key': 'Escape'}));
    } catch(e) {}
    """)
                time.sleep(0.5)
                if num_from_chat and len(num_from_chat) >= 9:
                    numero = re.sub(r'\D', '', num_from_chat)
                else:
                    print(f'    ⚠ Sin número')
            if not numero or len(numero) < 9:
                saltados_sin_numero += 1
                print(f'    ⚠ Sin número')
                continue
            if not numero.startswith('51'):
                saltados_no_peru += 1
                print(f'    ⏩ No Perú: +{numero}')
                continue
            # Quitar prefijo 51 (guardamos solo número local, ej: 931751950)
            numero_local = numero[2:] if numero.startswith('51') else numero
            if numero in existentes or numero_local in existentes:
                saltados_existentes += 1
                print(f'    ⏩ Ya existe')
                continue
            numero = numero_local

            # Fecha
            fecha = normalizar_fecha(time_raw)

            # Filtro fecha
            if ultima_fecha:
                try:
                    m = re.match(r'(\d{1,2})/(\d{1,2})/(\d{4})', time_raw)
                    if m:
                        fc = datetime(int(m.group(3)), int(m.group(2)), int(m.group(1)))
                    elif re.match(r'^\d{1,2}:\d{2}', time_raw):
                        fc = datetime.now()
                    elif 'ayer' in time_raw.lower():
                        from datetime import timedelta
                        fc = datetime.now() - timedelta(days=1)
                    else:
                        fc = None
                    if fc and ultima_fecha:
                        if fc.date() <= ultima_fecha.date():
                            saltados_fecha += 1
                            print(f'    ⏩ Anterior a última fecha ({ultima_fecha.date()})')
                            continue
                except Exception:
                    pass

            # --- CAMPANAS: extraer primer mensaje NUESTRO del chat ---
            campana = None

            campaign_texts = driver.execute_script("""
    try {
        const selectors = ['[data-testid="conversation-panel-messages"]', '[data-testid="conversation-panel"]', 'div[aria-label*="mensajes"]', 'div[aria-label*="messages"]', 'main div[tabindex="-1"]'];
        let panel = null;
        for (const sel of selectors) {
            panel = document.querySelector(sel);
            if (panel) break;
        }
        if (!panel) return JSON.stringify({ error: 'no panel' });

        panel.scrollTop = 0;

        // Esperar a que carguen mensajes antiguos
        return new Promise(resolve => {
            setTimeout(() => {
                // Todos los mensajes con su texto y dirección
                const msgRows = panel.querySelectorAll('div[data-testid*="conv-msg"]');
                const results = [];
                for (const row of msgRows) {
                    const isOut = row.querySelector('[data-testid="tail-out"]');
                    const textEl = row.querySelector('span[data-testid="selectable-text"], span.selectable-text, span[dir="auto"]');
                    const text = textEl ? textEl.textContent.trim() : '';
                    if (text) {
                        results.push({ out: !!isOut, text: text });
                    }
                }
                resolve(JSON.stringify({ msgs: results, total: msgRows.length }));
            }, 1500);
        });
    } catch(e) { return JSON.stringify({ error: e.message }); }
    """)
            pd = json.loads(campaign_texts)
            if pd.get('error'):
                print(f'    📝 Error: {pd["error"]}')
                campana = 'CAMP. CARLOS JAVIER'
            else:
                print(f'    📝 mensajes: {pd["total"]}')
                # Buscar campaña en mensajes
                # Estrategia:
                # 1. Buscar keywords ESPECÍFICAS de campaña (TOXINA, NOVUMA, ELLANSE, etc.)
                #    en TODOS los mensajes nuestros (sin detenernos en el saludo)
                # 2. Si paciente preguntó por tratamiento, asignar esa campaña
                # 3. Si no se encontró nada específico → CAMP. CARLOS JAVIER
                no_interesado_flag = False
                for msg in pd.get('msgs', []):
                    lower = msg['text'].lower()
                    if lower.startswith('anuncio de ') or lower.startswith('anuncio en '):
                        continue
                    if not msg['out']:
                        # Detectar si paciente dice no interesado
                        for frase in NO_INTERESADO:
                            if frase in lower:
                                print(f'      🚫 NO INTERESADO: "{frase}" en "{lower[:60]}"')
                                no_interesado_flag = True
                                break
                        if no_interesado_flag:
                            break
                        # Si el paciente preguntó por tratamiento
                        for keywords, cname in CAMPANAS_POR_TEXTO:
                            if any(kw in lower for kw in keywords):
                                campana = cname
                                break
                        if campana:
                            break
                    else:
                        # Mensaje NUESTRO: buscar solo campañas ESPECÍFICAS
                        # (NO el saludo "Dr. Carlos Javier" que está en casi todos)
                        if not campana:
                            for keywords, cname in CAMPANAS_ESPECIFICAS:
                                if any(kw in lower for kw in keywords):
                                    campana = cname
                                    break
                            if campana:
                                break  # Encontramos la campaña real, ya no necesitamos más
                if no_interesado_flag:
                    campana = None

            if campana is None:
                saltados_interes += 1
                print(f'    ⏩ No interesado')
                continue
            if not campana:
                campana = mapa_campanas.get(numero, '')
            if not campana:
                campana = 'CAMP. CARLOS JAVIER'

            nuevos.append([fecha, numero, campana, '', '', '', '', ''])
            print(f'    ✅ +{numero} | {campana} | {fecha}')

        except Exception as e:
            errores += 1
            print(f'    ❌ Error: {e}')
            time.sleep(1)

    driver.quit()

    print(f'\n[4/4] Resultado:')
    print(f'  Nuevos: {len(nuevos)}')
    print(f'  Etiqueta Gloria: {skip_gloria}')
    print(f'  Sin número: {saltados_sin_numero}')
    print(f'  No Perú: {saltados_no_peru}')
    print(f'  Ya existen: {saltados_existentes}')
    print(f'  Fuera fecha: {saltados_fecha}')
    print(f'  No interesado: {saltados_interes}')
    print(f'  Errores: {errores}')

    if nuevos:
        if dry_run:
            print('\n  --- DRY RUN ---')
            for f in nuevos:
                print(f'    {f[0]} | {f[1]} | {f[2]}')
        else:
            print('\n  Guardando...')
            for f in nuevos:
                ws_rellamadas.append_row(f, value_input_option='USER_ENTERED')
            print(f'  ✅ {len(nuevos)} agregados.')
    else:
        print('  Sin registros nuevos.')

    print('\n✅ Listo.')


if __name__ == '__main__':
    main()

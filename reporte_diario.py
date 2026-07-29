#!/usr/bin/env python3
"""Reporte diario de pacientes agendados enviado por WhatsApp Web.

Descarga el Excel de AGENDADOS desde Google Drive, cuenta los pacientes
agendados para el dia de hoy agrupados por CRM, genera un grafico de barras
y lo envia por WhatsApp Web al numero configurado en PHONE_REPORTE.
"""
import os
import sys
import time
import urllib.parse
import warnings
from datetime import date
from collections import defaultdict

# Silenciar warnings ruidosos antes de importar librerias pesadas
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)
try:
    from urllib3.exceptions import NotOpenSSLWarning
    warnings.filterwarnings('ignore', category=NotOpenSSLWarning)
except Exception:
    pass

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.common.exceptions import TimeoutException, NoSuchElementException, WebDriverException

from config import PHONE_REPORTE, OUT_DIR, MESES_ESP, EXCLUIR_REPORTE
from utils import configurar_logging, descargar_excel_drive, crear_bar_chart

log = configurar_logging('reporte_diario')

OUTPUT_JPG = os.path.join(OUT_DIR, 'reporte_hoy.jpg')
CHROME_PROFILE = '/Users/dermaessenza/ChromeWhatsAppReporte'
DRIVER_PATH = '/Users/dermaessenza/.cache/selenium/chromedriver/mac-arm64/150.0.7871.115/chromedriver'

# Timeouts (segundos)
WAIT_LOAD = 180      # esperar carga inicial / escaneo de QR
WAIT_ELEMENT = 60    # esperar elementos de la interfaz

hoy = date.today()
TARGET_DAY = hoy.day
TARGET_MONTH = hoy.month
TARGET_YEAR = hoy.year

# XPaths tolerantes a idioma (usan data-* estables en lugar de title traducible)
XPATH_APP_LOADED = (
    '//div[@contenteditable="true" and @data-tab="3"] | '
    '//div[@contenteditable="true" and @data-tab="10"]'
)
XPATH_SEARCH_BOX = (
    '//div[@contenteditable="true" and @data-tab="3"]'
)
XPATH_MESSAGE_BOX = (
    '//div[@contenteditable="true" and @data-tab="10"] | '
    '//div[@contenteditable="true" and @data-tab="6"]'
)
XPATH_ATTACH = '//button[@title="Adjuntar" or @title="Attach"] | //div[@title="Adjuntar" or @title="Attach"]'
XPATH_IMAGE_INPUT = '//input[@accept="image/*,video/mp4,video/3gpp,video/quicktime"]'
XPATH_CAPTION_BOX = (
    '//div[@contenteditable="true" and @data-tab="10"] | '
    '//div[@contenteditable="true" and @aria-label]'
)
XPATH_SEND = '//span[@data-icon="send"] | //button[@aria-label="Enviar" or @aria-label="Send"]'


# ============================================================
# DATOS
# ============================================================
def _parse_mes(valor):
    """Convierte una celda de mes (numero o texto) a numero de mes."""
    if valor is None:
        return 0
    raw = str(valor).strip().upper()
    limpio = raw.replace('.', '').replace('-', '')
    if limpio.isdigit():
        try:
            return int(float(valor))
        except (ValueError, TypeError):
            pass
    return MESES_ESP.get(raw[:3], 0)


def _parse_int(valor):
    try:
        return int(valor) if valor is not None else 0
    except (ValueError, TypeError):
        return 0


def obtener_agendados_hoy():
    """Devuelve una lista [(crm, cantidad), ...] ordenada desc para hoy."""
    log.info('Descargando Excel desde Google Drive...')
    wb = descargar_excel_drive()
    if 'AGENDADOS' not in wb.sheetnames:
        raise RuntimeError("La hoja 'AGENDADOS' no existe en el Excel")
    ws = wb['AGENDADOS']

    data = defaultdict(int)
    for row in ws.iter_rows(min_row=5, values_only=True):
        if len(row) < 16:
            continue
        crm = str(row[11]).strip() if row[11] else ''
        if not crm or crm.lower() == 'none':
            continue
        nombre = str(row[5]).strip() if len(row) > 5 and row[5] else ''
        telefono = str(row[8]).strip() if len(row) > 8 and row[8] else ''
        campana = str(row[15]).strip() if row[15] else ''
        if not nombre or not telefono or not campana:
            continue
        if any(e in campana.upper() for e in EXCLUIR_REPORTE):
            continue

        dia_val = _parse_int(row[2])
        ano_val = _parse_int(row[4])
        mes_num = _parse_mes(row[3])

        if dia_val == TARGET_DAY and mes_num == TARGET_MONTH and ano_val == TARGET_YEAR:
            data[crm] += 1

    wb.close()
    return sorted(data.items(), key=lambda x: -x[1])


def construir_texto(crms_sorted):
    total = sum(v for _, v in crms_sorted)
    if not crms_sorted:
        return f'No hay pacientes agendados hoy ({hoy})'
    lineas = '\n'.join(f'{c}: {v}' for c, v in crms_sorted)
    return f'*Reporte {hoy}*\n{lineas}\n\nTotal: {total}'


# ============================================================
# WHATSAPP WEB
# ============================================================
def iniciar_driver():
    opts = Options()
    opts.add_argument(f'--user-data-dir={CHROME_PROFILE}')
    opts.add_argument('--profile-directory=Default')
    opts.add_argument('--disable-blink-features=AutomationControlled')
    opts.add_argument('--no-first-run')
    opts.add_argument('--no-default-browser-check')
    opts.add_argument('--start-maximized')
    opts.add_argument('--disable-notifications')
    opts.add_experimental_option('excludeSwitches', ['enable-automation', 'enable-logging'])
    opts.add_experimental_option('useAutomationExtension', False)

    try:
        if os.path.exists(DRIVER_PATH):
            return webdriver.Chrome(service=Service(DRIVER_PATH), options=opts)
    except WebDriverException as e:
        log.warning(f'Fallo con driver fijo, usando autodeteccion: {e}')
    return webdriver.Chrome(options=opts)


def _js_click(driver, element):
    driver.execute_script('arguments[0].click();', element)


def cerrar_novedades(driver):
    """Cierra el popup de 'Novedades en WhatsApp Web' si aparece."""
    time.sleep(2)
    cierres = [
        '//div[@role="button"][.//span[contains(text(),"Aceptar")]]',
        '//div[@role="button"][.//span[contains(text(),"OK")]]',
        '//div[@role="button"][.//span[contains(text(),"Got it")]]',
        '//div[@role="button"][.//span[contains(text(),"Continue")]]',
        '//div[@role="button"][.//span[contains(text(),"Continuar")]]',
        '//div[@role="button"][.//span[contains(text(),"Acepto")]]',
        '//span[contains(text(),"Aceptar")]',
        '//span[contains(text(),"OK")]',
        '//span[contains(text(),"Got it")]',
        '//div[@aria-label="Cerrar" or @aria-label="Close"]',
        '//span[@aria-label="Cerrar" or @aria-label="Close"]',
        '//span[@data-icon="x"]//ancestor::div[@role="button"]',
        '//div[@role="dialog"]//div[@role="button"]',
    ]
    for xpath in cierres:
        try:
            el = driver.find_element(By.XPATH, xpath)
            if el.is_displayed():
                _js_click(driver, el)
                log.info(f'Popup de novedades cerrado ({xpath})')
                time.sleep(1)
                return True
        except (NoSuchElementException, WebDriverException):
            continue
    try:
        from selenium.webdriver.common.action_chains import ActionChains
        ActionChains(driver).send_keys(Keys.ESCAPE).perform()
        time.sleep(0.5)
    except Exception:
        pass
    return False


def esperar_app_lista(driver):
    wait = WebDriverWait(driver, WAIT_LOAD)
    log.info('Esperando WhatsApp Web... (si aparece QR, escanealo con tu telefono)')
    wait.until(EC.presence_of_element_located((By.XPATH, XPATH_APP_LOADED)))
    log.info('WhatsApp Web listo!')
    cerrar_novedades(driver)


def abrir_chat(driver):
    """Abre el chat directo con el numero via deep-link (mas fiable)."""
    telefono = ''.join(ch for ch in PHONE_REPORTE if ch.isdigit())
    log.info(f'Abriendo chat con {telefono}...')
    driver.get(f'https://web.whatsapp.com/send?phone={telefono}')
    wait = WebDriverWait(driver, WAIT_LOAD)
    wait.until(EC.presence_of_element_located((By.XPATH, XPATH_MESSAGE_BOX)))
    time.sleep(2)


def enviar_imagen(driver, ruta_imagen, caption):
    wait = WebDriverWait(driver, WAIT_ELEMENT)
    attach = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_ATTACH)))
    attach.click()
    time.sleep(1)
    image_input = wait.until(EC.presence_of_element_located((By.XPATH, XPATH_IMAGE_INPUT)))
    image_input.send_keys(os.path.abspath(ruta_imagen))
    time.sleep(3)
    try:
        caption_box = wait.until(EC.presence_of_element_located((By.XPATH, XPATH_CAPTION_BOX)))
        caption_box.click()
        caption_box.send_keys(caption)
        time.sleep(1)
    except TimeoutException:
        log.warning('No se pudo escribir el caption, se envia sin texto')
    send = wait.until(EC.element_to_be_clickable((By.XPATH, XPATH_SEND)))
    send.click()
    time.sleep(5)
    log.info('Imagen enviada!')


def enviar_texto(driver, texto):
    wait = WebDriverWait(driver, WAIT_ELEMENT)
    box = wait.until(EC.presence_of_element_located((By.XPATH, XPATH_MESSAGE_BOX)))
    box.click()
    # Enviar linea por linea (Shift+Enter) para respetar saltos de linea
    lineas = texto.split('\n')
    for i, linea in enumerate(lineas):
        box.send_keys(linea)
        if i < len(lineas) - 1:
            box.send_keys(Keys.SHIFT, Keys.ENTER)
    time.sleep(1)
    box.send_keys(Keys.ENTER)
    time.sleep(4)
    log.info('Texto enviado!')


# ============================================================
# MAIN
# ============================================================
def main():
    try:
        crms_sorted = obtener_agendados_hoy()
    except Exception as e:
        log.error(f'Error obteniendo datos: {e}')
        sys.exit(1)

    total = sum(v for _, v in crms_sorted)
    log.info(f'Agendados hoy: {total} en {len(crms_sorted)} CRMs')

    hay_imagen = False
    if crms_sorted:
        log.info('Generando grafico...')
        try:
            crear_bar_chart(dict(crms_sorted), f'PACIENTES AGENDADOS - {hoy}',
                            OUTPUT_JPG.replace('.jpg', ''))
            hay_imagen = os.path.exists(OUTPUT_JPG)
        except Exception as e:
            log.error(f'Error generando imagen: {e}')

    texto = construir_texto(crms_sorted)

    log.info('Abriendo Chrome para WhatsApp Web...')
    driver = None
    try:
        driver = iniciar_driver()
        driver.get('https://web.whatsapp.com')
        esperar_app_lista(driver)
        abrir_chat(driver)

        enviado = False
        if hay_imagen:
            try:
                enviar_imagen(driver, OUTPUT_JPG, f'Reporte agendados {hoy}')
                enviado = True
            except Exception as e:
                log.error(f'Error al enviar imagen: {e}. Intentando solo texto...')

        if not enviado:
            enviar_texto(driver, texto)

        log.info('Reporte enviado correctamente!')
    except TimeoutException:
        log.error('Timeout esperando WhatsApp Web. Verifica la sesion/QR.')
        sys.exit(2)
    except Exception as e:
        log.error(f'Error inesperado: {e}')
        sys.exit(3)
    finally:
        if driver is not None:
            time.sleep(2)
            try:
                driver.quit()
            except Exception:
                pass
    log.info('Listo!')


if __name__ == '__main__':
    main()

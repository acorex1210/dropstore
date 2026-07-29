#!/usr/bin/env python3
"""Reporte diario de pacientes agendados enviado por WhatsApp via pywhatkit + pyautogui.

pywhatkit abre Safari con WhatsApp Web (sesion existente).
pyautogui presiona Enter para enviar automaticamente.
"""
import os
import sys
import time
import warnings
from datetime import date, datetime
from collections import defaultdict

warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=UserWarning)
try:
    from urllib3.exceptions import NotOpenSSLWarning
    warnings.filterwarnings('ignore', category=NotOpenSSLWarning)
except Exception:
    pass

from config import PHONE_REPORTE, OUT_DIR, MESES_ESP, EXCLUIR_REPORTE
from utils import configurar_logging, descargar_excel_drive, crear_bar_chart

log = configurar_logging('reporte_safari')

OUTPUT_JPG = os.path.join(OUT_DIR, 'reporte_hoy.jpg')

if len(sys.argv) >= 2:
    hoy = datetime.strptime(sys.argv[1], '%d/%m/%Y').date()
else:
    hoy = date.today()
TARGET_DAY = hoy.day
TARGET_MONTH = hoy.month
TARGET_YEAR = hoy.year


# ============================================================
# DATOS
# ============================================================
def _parse_mes(valor):
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


def crear_tabla_agendados(crms_sorted, ruta):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt
    from matplotlib.patches import FancyBboxPatch

    colores = ['#e94560', '#0f3460', '#533483', '#a66cff', '#ffa62e', '#7ed321', '#ff6b6b', '#4ecdc4']
    total = sum(v for _, v in crms_sorted)

    if not crms_sorted:
        fig, ax = plt.subplots(figsize=(5, 2.5))
        ax.set_facecolor('#1a1a2e')
        fig.patch.set_facecolor('#1a1a2e')
        ax.text(0.5, 0.5, f'Sin agendados hoy ({hoy})', ha='center', va='center',
                fontsize=16, color='white', fontweight='bold')
        ax.axis('off')
        fig.savefig(ruta, dpi=200, bbox_inches='tight', facecolor='#1a1a2e')
        plt.close(fig)
        return

    nrows = len(crms_sorted) + 1
    fig_h = max(3, nrows * 0.7 + 2)
    fig, ax = plt.subplots(figsize=(7, fig_h))
    ax.set_facecolor('#1a1a2e')
    fig.patch.set_facecolor('#1a1a2e')
    ax.axis('off')

    ax.text(0.5, 0.95, f'PACIENTES AGENDADOS - {hoy}', ha='center', va='top',
            fontsize=16, color='white', fontweight='bold', transform=ax.transAxes)

    y_start = 0.85
    row_h = 0.7 / max(nrows, 1)

    for i, (crm, cant) in enumerate(crms_sorted):
        y = y_start - (i + 1) * row_h
        color = colores[i % len(colores)]

        rect = FancyBboxPatch((0.05, y - row_h * 0.35), 0.9, row_h * 0.7,
                               boxstyle="round,pad=0.02", facecolor=color, alpha=0.85,
                               transform=ax.transAxes)
        ax.add_patch(rect)

        ax.text(0.12, y, crm.upper(), ha='left', va='center', fontsize=14,
                color='white', fontweight='bold', transform=ax.transAxes)
        ax.text(0.88, y, str(cant), ha='right', va='center', fontsize=18,
                color='white', fontweight='bold', transform=ax.transAxes)

    y_total = y_start - (nrows) * row_h
    rect_total = FancyBboxPatch((0.05, y_total - row_h * 0.35), 0.9, row_h * 0.7,
                                 boxstyle="round,pad=0.02", facecolor='#333333', alpha=0.9,
                                 transform=ax.transAxes)
    ax.add_patch(rect_total)
    ax.text(0.12, y_total, 'TOTAL', ha='left', va='center', fontsize=14,
            color='#ffa62e', fontweight='bold', transform=ax.transAxes)
    ax.text(0.88, y_total, str(total), ha='right', va='center', fontsize=18,
            color='#ffa62e', fontweight='bold', transform=ax.transAxes)

    plt.subplots_adjust(top=0.92, bottom=0.05, left=0.03, right=0.97)
    fig.savefig(ruta, dpi=200, bbox_inches='tight', facecolor='#1a1a2e')
    plt.close(fig)


# ============================================================
# WHATSAPP
# ============================================================
def enviar_whatsapp(ruta_imagen, caption):
    import pywhatkit as kit
    import pyautogui
    pyautogui.FAILSAFE = False

    try:
        from pywhatkit.core import log as _pwk_log
        _pwk_log.log_image = lambda *a, **k: None
        _pwk_log.log_message = lambda *a, **k: None
    except Exception:
        pass

    log.info('Abriendo WhatsApp Web en Safari...')
    kit.sendwhats_image(
        PHONE_REPORTE,
        os.path.abspath(ruta_imagen),
        caption,
        wait_time=15,
        tab_close=False,
    )

    log.info('Esperando que cargue el chat...')
    time.sleep(8)

    log.info('Enviando con Enter...')
    pyautogui.press('enter')
    time.sleep(2)
    log.info('Imagen enviada!')


def enviar_texto_whatsapp(texto):
    import matplotlib
    matplotlib.use('Agg')
    import matplotlib.pyplot as plt

    ruta_txt = os.path.join(OUT_DIR, 'reporte_texto.jpg')
    fig, ax = plt.subplots(figsize=(6, 3))
    ax.text(0.5, 0.5, texto, ha='center', va='center', fontsize=14,
            fontfamily='monospace', wrap=True, transform=ax.transAxes)
    ax.axis('off')
    fig.savefig(ruta_txt, dpi=150, bbox_inches='tight', facecolor='white')
    plt.close(fig)

    enviar_whatsapp(ruta_txt, texto)


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
        log.info('Generando tabla...')
        try:
            crear_tabla_agendados(crms_sorted, OUTPUT_JPG)
            hay_imagen = os.path.exists(OUTPUT_JPG)
        except Exception as e:
            log.error(f'Error generando imagen: {e}')

    texto = construir_texto(crms_sorted)

    try:
        if hay_imagen:
            caption = f'Reporte agendados {hoy}'
            enviar_whatsapp(OUTPUT_JPG, caption)
        else:
            enviar_texto_whatsapp(texto)
        log.info('Reporte enviado correctamente!')
    except Exception as e:
        log.error(f'Error al enviar: {e}')
        sys.exit(2)

    log.info('Listo!')


if __name__ == '__main__':
    main()

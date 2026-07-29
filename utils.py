import io
import os
import re
import time
import logging
from collections import defaultdict

import gspread
import openpyxl
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

from config import (
    JSON_KEY, CREDENTIALS_FILE, MESES_ESP,
    SPREADSHEET_ID, AGENDADOS_FILE_ID, EXCLUIR_REPORTE,
)

# ============================================================
# LOGGING
# ============================================================
def configurar_logging(nombre, logs_dir=None):
    from config import LOGS_DIR
    if logs_dir is None:
        logs_dir = LOGS_DIR
    os.makedirs(logs_dir, exist_ok=True)
    logger = logging.getLogger(nombre)
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        fh_out = logging.FileHandler(os.path.join(logs_dir, f'{nombre}_out.log'))
        fh_err = logging.FileHandler(os.path.join(logs_dir, f'{nombre}_err.log'))
        fh_err.setLevel(logging.WARNING)
        sh = logging.StreamHandler()
        fmt = logging.Formatter('%(asctime)s %(levelname)s %(message)s')
        fh_out.setFormatter(fmt)
        fh_err.setFormatter(fmt)
        sh.setFormatter(fmt)
        logger.addHandler(fh_out)
        logger.addHandler(fh_err)
        logger.addHandler(sh)
    return logger

# ============================================================
# GOOGLE SHEETS
# ============================================================
def conectar_gsheets():
    gc = gspread.service_account(filename=JSON_KEY)
    return gc

def abrir_spreadsheet(gc=None, sheet_id=None):
    if gc is None:
        gc = conectar_gsheets()
    if sheet_id is None:
        sheet_id = SPREADSHEET_ID
    return gc.open_by_key(sheet_id)

# ============================================================
# GOOGLE DRIVE
# ============================================================
def descargar_excel_drive(file_id=None, intentos=3, timeout=120):
    from googleapiclient.http import MediaIoBaseDownload
    if file_id is None:
        file_id = AGENDADOS_FILE_ID
    scope = ['https://www.googleapis.com/auth/drive.readonly']
    creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)

    ultimo_error = None
    for intento in range(1, intentos + 1):
        try:
            service = build('drive', 'v3', credentials=creds)
            request = service.files().get_media(fileId=file_id)
            fh = io.BytesIO()
            downloader = MediaIoBaseDownload(fh, request, chunksize=1024 * 1024)
            done = False
            while not done:
                _, done = downloader.next_chunk(num_retries=3)
            fh.seek(0)
            return openpyxl.load_workbook(fh, read_only=True)
        except Exception as e:
            ultimo_error = e
            if intento < intentos:
                time.sleep(5)
    raise ultimo_error

# ============================================================
# FECHAS Y HORAS
# ============================================================
def normalizar_hora(h):
    if not h or not h.strip():
        return ''
    h = h.strip().upper()
    h = re.sub(r'\bSM\b', 'PM', h)
    h = re.sub(
        r'(\d{1,2}):(\d)(\s*[AP]M)',
        lambda m: f'{m.group(1)}:0{m.group(2)}{m.group(3)}',
        h,
    )
    return h

def hora_sort_key(h):
    if not h or not h.strip():
        return '99999'
    h = normalizar_hora(h)
    m = re.match(r'(\d{1,2}):(\d{1,2})\s*(AM|PM)', h)
    if not m:
        return '99999' + h
    hour, minute, ampm = int(m.group(1)), m.group(2).zfill(2), m.group(3)
    if ampm == 'PM' and hour != 12:
        hour += 12
    elif ampm == 'AM' and hour == 12:
        hour = 0
    return f'{hour:02d}{minute}'

def fecha_a_numero(dia, mes):
    return mes * 100 + dia

# ============================================================
# LECTURA DE SHEETS
# ============================================================
def leer_sheet_a_dataframe(ws, header_row, ncols):
    raw = ws.get_all_values()
    header_idx = header_row - 1
    headers_full = raw[header_idx]
    data_rows = raw[header_idx + 1:]
    if not data_rows:
        return pd.DataFrame()
    headers = [str(headers_full[i]) for i in range(ncols)]
    rows = [[r[i] if i < len(r) else '' for i in range(ncols)] for r in data_rows]
    df = pd.DataFrame(rows, columns=headers)
    df = df.replace('', pd.NA).fillna('')
    df = df.map(lambda x: x.strip() if isinstance(x, str) else x)
    return df

def filtrar_por_fecha(df, dia_filtro, date_cols):
    dia_str = str(dia_filtro.day)
    mes_num = dia_filtro.month
    año_str = str(dia_filtro.year)
    mes_abrev = [k for k, v in MESES_ESP.items() if v == mes_num]
    if not mes_abrev:
        return pd.DataFrame()
    mes_str = mes_abrev[0]
    col_dia = df.iloc[:, date_cols[0]].astype(str).str.strip()
    col_mes = df.iloc[:, date_cols[1]].astype(str).str.strip().str.upper()
    col_año = df.iloc[:, date_cols[2]].astype(str).str.strip()
    mask = (col_dia == dia_str) & (col_mes == mes_str) & (col_año == año_str)
    return df[mask]

# ============================================================
# MENSAJES
# ============================================================
def crear_mensaje_agendados(df, label):
    col_camp = next((c for c in df.columns if 'CAMP' in c.upper()), None)
    if not col_camp:
        return ''
    camps = [str(v).strip().upper() for v in df[col_camp]]
    total = len(camps)
    evals = sum(1 for c in camps if 'EVALUACION' in c)
    retoques = sum(1 for c in camps if c == 'RETOQUE')
    sesiones = sum(1 for c in camps if 'SESION' in c or 'SESIÓN' in c)
    agendados = total - evals - retoques - sesiones
    partes = []
    if agendados:
        partes.append(f'{agendados} agendados')
    if sesiones:
        partes.append(f'{sesiones} sesiones' if sesiones != 1 else '1 sesion')
    if evals:
        partes.append(f'{evals} evaluaciones' if evals != 1 else '1 evaluacion')
    if retoques:
        partes.append(f'{retoques} retoques' if retoques != 1 else '1 retoque')
    if not partes:
        return ''
    if len(partes) == 1:
        return f'Para {label.lower()} tenemos {partes[0]}'
    return f'Para {label.lower()} tenemos ' + ', '.join(partes[:-1]) + ' y ' + partes[-1]

# ============================================================
# IMÁGENES
# ============================================================
def crear_tabla_imagen(df, titulo, ruta, highlight_camp=False):
    if df.empty:
        fig, ax = plt.subplots(figsize=(6, 2))
        ax.text(0.5, 0.5, 'Sin datos', ha='center', va='center', fontsize=14)
        ax.axis('off')
        fig.savefig(ruta, dpi=300, bbox_inches='tight', format='jpg')
        plt.close(fig)
        return
    ncols = len(df.columns)
    nrows = len(df)
    fig_w = max(14, ncols * 2.2)
    fig_h = max(4, nrows * 0.55 + 3)
    fig, ax = plt.subplots(figsize=(fig_w, fig_h))
    ax.axis('off')
    cell_text = [['' if pd.isna(v) else str(v) for v in row] for row in df.values]
    tabla = ax.table(cellText=cell_text, colLabels=list(df.columns), cellLoc='center', loc='center')
    tabla.auto_set_font_size(False)
    tabla.set_fontsize(9)
    tabla.scale(1, 1.8)
    if highlight_camp:
        col_camp = next((c for c in df.columns if 'CAMP' in c.upper()), None)
        if col_camp:
            for i, val in enumerate(df[col_camp]):
                camp = str(val).strip().upper()
                if any(k in camp for k in ('EVALUACION', 'RETOQUE', 'SESION', 'SESIÓN')):
                    for j in range(ncols):
                        tabla[(i + 1, j)].set_facecolor('#FFE066')
    for (i, j), celda in tabla.get_celld().items():
        if i == 0:
            celda.set_text_props(weight='bold')
            celda.set_facecolor('#d9d9d9')
            celda.set_height(celda.get_height() * 1.4)
        if j == 0:
            celda.set_width(celda.get_width() * 0.7)
    plt.suptitle(titulo, fontsize=15, weight='bold', y=0.97)
    plt.subplots_adjust(top=0.94, left=0.03, right=0.97)
    fig.savefig(ruta, dpi=300, bbox_inches='tight', format='jpg')
    plt.close(fig)

def crear_bar_chart(datos, titulo, ruta):
    if not datos:
        return
    crms_sorted = sorted(datos.items(), key=lambda x: -x[1])
    total = sum(v for _, v in crms_sorted)
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor('#1a1a2e')
    ax.set_facecolor('#1a1a2e')
    crms = [c[0] for c in crms_sorted]
    vals = [c[1] for c in crms_sorted]
    colors = ['#e94560', '#0f3460', '#533483', '#a66cff', '#ffa62e', '#7ed321']
    bars = ax.barh(crms, vals, color=colors[:len(crms)], height=0.6)
    for bar, val in zip(bars, vals):
        ax.text(bar.get_width() + 0.3, bar.get_height() / 2 + bar.get_y(),
                str(val), ha='left', va='center', color='white', fontweight='bold', fontsize=14)
    ax.tick_params(colors='white', labelsize=12)
    ax.set_title(titulo, fontsize=15, fontweight='bold', color='white')
    ax.set_xlabel('Pacientes agendados', color='white')
    ax.set_xlim(0, max(vals) * 1.3 + 1)
    ax.grid(True, axis='x', alpha=0.1, color='white')
    for spine in ax.spines.values():
        spine.set_color('#444')
    plt.tight_layout()
    plt.savefig(ruta + '.png', dpi=200, bbox_inches='tight', facecolor='#1a1a2e')
    Image.open(ruta + '.png').convert('RGB').save(ruta, 'JPEG', quality=95)
    plt.close()

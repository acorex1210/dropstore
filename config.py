import os

# ============================================================
# RUTAS
# ============================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
JSON_KEY = os.path.expanduser('~/credenciales-sheets.json')
CREDENTIALS_FILE = JSON_KEY
PROFILE_DIR = os.path.expanduser('~/Library/Application Support/Google/Chrome/WhatsAppProfile')
OUT_DIR = os.path.expanduser('~/TRABAJO/capturas')
LOGS_DIR = os.path.join(BASE_DIR, 'logs')
os.makedirs(OUT_DIR, exist_ok=True)
os.makedirs(LOGS_DIR, exist_ok=True)

# ============================================================
# GOOGLE SHEETS
# ============================================================
SPREADSHEET_ID = '1cdcKsfd4D3GbG1XytYRat6CsrgT-CjBXdZ3T3i1m2sM'
RELLAMADAS_SHEET_ID = '1fqC_v1IS0cynbnUa0sie1YrGgNu9jodMFgrN6oxUM30'
SHEET_DATOS_ID = SPREADSHEET_ID
AGENDADOS_FILE_ID = '1eVeMN1_f-RL2caN_Y9pq3DNEez3TeVTZ'
WS_RELLAMADAS = 'RELLAMADAS'

# ============================================================
# WHATSAPP
# ============================================================
PHONE_AGENDADOS = '+51913600399'
PHONE_REPORTE = '+51968797977'

# ============================================================
# MESES
# ============================================================
MESES_ESP = {
    'ENE': 1, 'FEB': 2, 'MAR': 3, 'ABR': 4, 'MAY': 5, 'JUN': 6,
    'JUL': 7, 'AGO': 8, 'SET': 9, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DIC': 12,
}

# ============================================================
# COLUMNAS RELLAMADAS (0-indexed)
# ============================================================
HEADER_ROW = 3
COL_FECHA = 0
COL_CELULAR = 1
COL_CAMPAÑA = 2
COL_CONTESTA = 3
COL_CRM = 4
COL_AGENDA = 5
COL_RELLAMADA = 7
CJ_COL_TELEFONO = 9
CJ_COL_CAMPAÑA = 15

# ============================================================
# FILTROS WHATSAPP
# ============================================================
CRMS = ['gloria', 'maria', 'almendra', 'hebelin', 'stefany', 'sofia', 'equipo']

NO_INTERESADO = [
    'no me interesa', 'no estoy interesado', 'no estoy interesada',
    'no gracias', 'gracias pero no', 'no quiero',
    'no me llame', 'no me llamen', 'déjame de molestar', 'dejame de molestar',
    'no me escriba', 'no me escriban', 'no me contacte', 'no me contacten',
    'no me molestes', 'ya no me interesa', 'ya no quiero',
]

CAMPANAS_ESPECIFICAS = [
    (['ellansé', 'ellanse'], 'ELLANSE'),
    (['novuma'], 'NOVUMA'),
    (['toxina botulinica', 'meditoxin', 'toxina botulínica', 'full face', 'botox'], 'TOXINA BOTULINICA'),
    (['hifu 7d', 'ultrasonido focalizado', 'hifu'], 'HIFU'),
    (['ácido hialurónico', 'ácido hialuronico', 'acido hialuronico', 'neuramis'], 'ACIDO HIALURONICO'),
]

CAMPANAS_POR_TEXTO = CAMPANAS_ESPECIFICAS + [
    (['dr. carlos javier', 'tratamientos innovadores', 'marcas de excelente calidad'], 'CAMP. CARLOS JAVIER'),
]

# ============================================================
# COLUMNAS CONFIRMADOS (para capturar_enviar.py)
# ============================================================
SHEETS_CONFIG = {
    'CONFIRMADOS CJ': {
        'header_row': 4, 'date_cols': (12, 13, 14), 'time_col': 16,
        'ncols_full': 19, 'cols_mostrar': [6, 7, 8, 9, 10, 11, 15, 16, 17, 18],
        'nombre_header': 'PACIENTE',
        'display_name': '🤖 SYSTEM CRM CONFIRMADOS',
    },
    'CONFIRMADOS BM': {
        'header_row': 4, 'date_cols': (11, 12, 13), 'time_col': 15,
        'ncols_full': 18, 'cols_mostrar': [6, 7, 8, 9, 10, 14, 15, 16, 17],
        'nombre_header': None,
    },
    'AGENDADOS': {
        'header_row': 4, 'date_cols': (10, 11, 12), 'time_col': 14,
        'ncols_full': 19, 'cols_mostrar': [5, 6, 7, 8, 9, 13, 14, 15, 16],
        'nombre_header': 'PACIENTE',
        'spreadsheet_key': '1So_1Fh744c3K9kss2oA1twjBLJpgrSxZCu2lqhWpqJM',
        'display_name': 'CONFIRMADOS DERMA ESSENZA',
    },
}

# ============================================================
# LEADS WHATSAPP (para leads_whatsapp.py)
# ============================================================
CONTROL_SPREADSHEET_ID = '1v2ue4Wfih6gTzhgdFdfpL6X4pE1beYBRHUHE0G_gEbM'
CONTROL_SHEET_NAME = 'CONTROL'
LEADS_PHONE_DESTINO = '+51913600399'
LEADS_JSON_DIR = os.path.expanduser('~/Downloads')

# ============================================================
# REPORTE DIARIO (para reporte_diario.py)
# ============================================================
EXCLUIR_REPORTE = {'RETOQUES', 'RETOQUE', 'EVALUACIONES', 'EVALUACION', 'SESION', 'SESIÓN', 'SESIONES'}

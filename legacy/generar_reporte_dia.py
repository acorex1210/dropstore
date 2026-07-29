import io, sys
from collections import defaultdict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import openpyxl
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from PIL import Image

CREDENTIALS_FILE = "/Users/dermaessenza/TRABAJO/derma-essenza-73300c21ffe8.json"
FILE_ID = "1eVeMN1_f-RL2caN_Y9pq3DNEez3TeVTZ"

months_map = {
    'ENE': 1, 'FEB': 2, 'MAR': 3, 'ABR': 4, 'MAY': 5, 'JUN': 6,
    'JUL': 7, 'AGO': 8, 'SET': 9, 'SEP': 9, 'OCT': 10, 'NOV': 11, 'DIC': 12
}

scope = ["https://www.googleapis.com/auth/drive.readonly"]
creds = Credentials.from_service_account_file(CREDENTIALS_FILE, scopes=scope)
service = build("drive", "v3", credentials=creds)

request = service.files().get_media(fileId=FILE_ID)
fh = io.BytesIO(request.execute())
wb = openpyxl.load_workbook(fh, read_only=True)
ws = wb["AGENDADOS"]

data = defaultdict(int)
total_excluidos = 0
target_year = 2026
target_month = 7
target_day = 10

excluir = {'RETOQUES', 'RETOQUE', 'EVALUACIONES', 'EVALUACION', 'SESION', 'SESIÓN', 'SESIONES'}

for row in ws.iter_rows(min_row=5, values_only=True):
    if len(row) < 16: continue
    crm = str(row[11]).strip() if row[11] else ''
    if not crm or crm == 'None': continue

    nombre = str(row[5]).strip() if len(row) > 5 and row[5] else ''
    telefono = str(row[8]).strip() if len(row) > 8 and row[8] else ''
    campana = str(row[15]).strip() if row[15] else ''

    if not nombre or not telefono or not campana:
        continue

    campana_upper = campana.upper()
    if any(e in campana_upper for e in excluir):
        continue

    try:
        dia_val = int(row[2]) if row[2] is not None else 0
    except (ValueError, TypeError):
        dia_val = 0
    try:
        ano_val = int(row[4]) if row[4] is not None else 0
    except (ValueError, TypeError):
        ano_val = 0
    mes_raw = str(row[3]).strip().upper() if row[3] else ''
    try:
        mes_num = int(float(row[3])) if row[3] is not None and str(row[3]).replace('.','').replace('-','').isdigit() else months_map.get(mes_raw[:3], 0)
    except (ValueError, TypeError):
        mes_num = months_map.get(mes_raw[:3], 0)

    if dia_val == target_day and mes_num == target_month and ano_val == target_year:
        data[crm] += 1

crms_sorted = sorted(data.items(), key=lambda x: -x[1])

fig, ax = plt.subplots(figsize=(10, 6))
fig.patch.set_facecolor('#1a1a2e')
ax.set_facecolor('#1a1a2e')

crms = [c[0] for c in crms_sorted]
vals = [c[1] for c in crms_sorted]
colors = ['#e94560', '#0f3460', '#533483', '#f5a623', '#7ed321', '#50e3c2', '#b8e986', '#4a90e2', '#16213e']

bars = ax.barh(crms, vals, color=colors[:len(crms)], height=0.6)
for bar, val in zip(bars, vals):
    ax.text(bar.get_width() + 0.3, bar.get_y() + bar.get_height()/2,
            str(val), ha='left', va='center', color='white', fontweight='bold', fontsize=14)

ax.tick_params(colors='white', labelsize=12)
ax.set_xlabel('Pacientes agendados', color='white', fontsize=12)
ax.set_title(f'PACIENTES AGENDADOS - 10 Jul 2026', fontsize=16, fontweight='bold', color='white', pad=15)
total = sum(vals)
ax.text(0.95, 0.95, f'Total: {total}', transform=ax.transAxes, ha='right', va='top',
        color='white', fontsize=14, fontweight='bold',
        bbox=dict(boxstyle='round', facecolor='#0f3460', edgecolor='white', alpha=0.8))

ax.set_xlim(0, max(vals) * 1.3 + 1 if vals else 10)
ax.grid(True, axis='x', alpha=0.1, color='white')
for spine in ax.spines.values():
    spine.set_color('#444444')

plt.tight_layout()
output_png = "/Users/dermaessenza/TRABAJO/reporte_10julio2026.png"
plt.savefig(output_png, dpi=200, bbox_inches='tight', facecolor='#1a1a2e')
Image.open(output_png).convert('RGB').save(output_png.replace('.png', '.jpg'), 'JPEG', quality=95)

print(f"Reporte: {output_png}")
for crm, cnt in crms_sorted:
    print(f"  {crm}: {cnt}")
print(f"  Total: {total}")

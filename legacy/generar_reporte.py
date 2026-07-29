import io, sys
from collections import defaultdict
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
import openpyxl
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from datetime import date

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

data = defaultdict(lambda: defaultdict(int))
all_crms = set()
excluir = {'RETOQUES', 'RETOQUE', 'EVALUACIONES', 'EVALUACION', 'SESION', 'SESIÓN', 'SESIONES'}

target_year = 2026
target_month = 7

for row in ws.iter_rows(min_row=5, values_only=True):
    if len(row) < 15:
        continue
    crm = str(row[11]).strip() if row[11] else ''
    if not crm or crm == 'None':
        continue

    campana = str(row[15]).strip().upper() if len(row) > 15 and row[15] else ''
    if any(e in campana for e in excluir):
        continue

    mes = row[3]
    ano = row[4]
    if isinstance(mes, str):
        mes_num = months_map.get(mes.upper()[:3], 0)
    else:
        mes_num = int(mes) if mes else 0
    ano_val = int(ano) if ano else 0
    dia_val = int(row[2]) if row[2] else 0

    if dia_val > 0 and mes_num == target_month and ano_val == target_year:
        data[crm][dia_val] += 1
        all_crms.add(crm)

crms_sorted = sorted(all_crms, key=lambda c: sum(data[c].values()), reverse=True)

if not crms_sorted:
    print("No data found for July 2026")
    sys.exit(1)

print(f"CRMs with data: {crms_sorted}")
for c in crms_sorted:
    print(f"  {c}: {sum(data[c].values())} total")

days = list(range(1, 32))
dates = [date(target_year, target_month, d) for d in days]

table_data = {}
for crm in crms_sorted:
    table_data[crm] = [data[crm].get(d, 0) for d in days]

fig, (ax_table, ax_chart) = plt.subplots(2, 1, figsize=(18, 10), gridspec_kw={'height_ratios': [1.2, 2]})
fig.patch.set_facecolor('#1a1a2e')

colors = ['#e94560', '#0f3460', '#16213e', '#533483', '#f5a623', '#7ed321', '#50e3c2', '#b8e986', '#4a90e2']
crm_colors = {crm: colors[i % len(colors)] for i, crm in enumerate(crms_sorted)}

col_labels = ['CRM'] + [str(d) for d in days] + ['TOTAL']
cell_data = []
for crm in crms_sorted:
    row_vals = table_data[crm]
    total = sum(row_vals)
    cell_data.append([crm] + row_vals + [total])

totals_row = ['TOTAL'] + [sum(table_data[crm][d-1] for crm in crms_sorted) for d in days] + [sum(sum(table_data[crm]) for crm in crms_sorted)]
cell_data.append(totals_row)

ncols = len(col_labels)
table = ax_table.table(
    cellText=[[str(v) for v in row] for row in cell_data],
    colLabels=col_labels,
    cellLoc='center',
    loc='center',
    colWidths=[0.07] + [0.022]*31 + [0.07]
)

table.auto_set_font_size(False)
table.set_fontsize(7)
table.scale(1, 1.3)

for j in range(ncols):
    cell = table[0, j]
    cell.set_facecolor('#16213e')
    cell.set_text_props(color='white', fontweight='bold', fontsize=6.5)

for i in range(len(cell_data)):
    is_total = (i == len(cell_data) - 1)
    for j in range(ncols):
        cell = table[i+1, j]
        if is_total:
            cell.set_facecolor('#0f3460')
            cell.set_text_props(color='white', fontweight='bold', fontsize=7)
        elif j == 0:
            cell.set_facecolor('#533483')
            cell.set_text_props(color='white', fontweight='bold', fontsize=7)
        elif isinstance(cell_data[i][j], int) and cell_data[i][j] > 0:
            cell.set_facecolor('#e94560')
            cell.set_text_props(color='white', fontweight='bold', fontsize=6.5)
        else:
            cell.set_facecolor('#2d2d44')
            cell.set_text_props(color='#888888', fontsize=6)

ax_table.axis('off')
ax_table.set_title(f'PACIENTES AGENDADOS POR CRM - Julio {target_year}',
                   fontsize=16, fontweight='bold', color='white', pad=15)

for crm in crms_sorted:
    vals = table_data[crm]
    ax_chart.plot(dates, vals, marker='o', linewidth=2, markersize=4,
                  color=crm_colors[crm], label=f'{crm} ({sum(vals)})')

ax_chart.set_facecolor('#1a1a2e')
ax_chart.tick_params(colors='white', labelsize=9)
ax_chart.set_xlabel('Día de Julio 2026', color='white', fontsize=11)
ax_chart.set_ylabel('Pacientes agendados', color='white', fontsize=11)
ax_chart.set_title('Evolución diaria de agendados por CRM', fontsize=14, fontweight='bold', color='white', pad=10)
ax_chart.xaxis.set_major_locator(mdates.DayLocator(interval=2))
ax_chart.xaxis.set_major_formatter(mdates.DateFormatter('%d'))
ax_chart.grid(True, alpha=0.15, color='white')
ax_chart.legend(loc='upper left', fontsize=8, facecolor='#1a1a2e', edgecolor='white', labelcolor='white')

for spine in ax_chart.spines.values():
    spine.set_color('#444444')

plt.tight_layout(pad=2)
output_path = "/Users/dermaessenza/TRABAJO/reporte_julio2026.png"
plt.savefig(output_path, dpi=200, bbox_inches='tight', facecolor='#1a1a2e')
print(f"\nReporte generado: {output_path}")

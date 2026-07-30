#!/usr/bin/env python3
import os,sys,time,io,logging,warnings; from datetime import date,datetime
from collections import defaultdict
warnings.filterwarnings('ignore')
import openpyxl; from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build; from googleapiclient.http import MediaIoBaseDownload

# CONFIG
PHONE='+51968797977'; OUT=os.path.expanduser('~/TRABAJO/capturas'); os.makedirs(OUT,exist_ok=True)
LOGS=os.path.expanduser('~/TRABAJO/logs'); os.makedirs(LOGS,exist_ok=True)
JSON_KEY=os.path.expanduser('~/credenciales-sheets.json')
FILE_ID='1eVeMN1_f-RL2caN_Y9pq3DNEez3TeVTZ'
MES={'ENE':1,'FEB':2,'MAR':3,'ABR':4,'MAY':5,'JUN':6,'JUL':7,'AGO':8,'SET':9,'SEP':9,'OCT':10,'NOV':11,'DIC':12}
EXCL={'RETOQUES','RETOQUE','EVALUACIONES','EVALUACION','SESION','SESIÓN','SESIONES'}
COL=['#e94560','#0f3460','#533483','#a66cff','#ffa62e','#7ed321','#ff6b6b','#4ecdc4']

hoy=datetime.strptime(sys.argv[1],'%d/%m/%Y').date()if len(sys.argv)>=2 else date.today()
TD,TN,TY=hoy.day,hoy.month,hoy.year; JPG=os.path.join(OUT,'reporte_hoy.jpg')

# LOGGING
l=logging.getLogger('rpt');l.setLevel(logging.INFO)
if not l.handlers:
 h1=logging.FileHandler(os.path.join(LOGS,'rpt_out.log'))
 h2=logging.FileHandler(os.path.join(LOGS,'rpt_err.log'));h2.setLevel(logging.WARNING)
 s=logging.StreamHandler();f=logging.Formatter('%(asctime)s %(levelname)s %(message)s')
 for x in(h1,h2,s):x.setFormatter(f);l.addHandler(x)

def descargar():
 for _ in range(3):
  try:
   c=Credentials.from_service_account_file(JSON_KEY,scopes=['https://www.googleapis.com/auth/drive.readonly'])
   b=build('drive','v3',credentials=c);r=b.files().get_media(fileId=FILE_ID);h=io.BytesIO()
   d=MediaIoBaseDownload(h,r,chunksize=1024*1024);ok=False
   while not ok:_,ok=d.next_chunk(num_retries=3)
   h.seek(0);return openpyxl.load_workbook(h,read_only=True)
  except Exception as e:time.sleep(5)
 raise e

def datos():
 l.info('Descargando...');wb=descargar();ws=wb['AGENDADOS'];d=defaultdict(int)
 for r in ws.iter_rows(min_row=5,values_only=True):
  if len(r)<16:continue
  c=str(r[11]or'').strip()
  if not c or c.lower()=='none':continue
  n=str(r[5]or'').strip();t=str(r[8]or'').strip();p=str(r[15]or'').strip()
  if not n or not t or not p:continue
  if any(e in p.upper() for e in EXCL):continue
  dv=int(r[2])if r[2]is not None else 0;av=int(r[4])if r[4]is not None else 0
  mw=str(r[3]or'').strip().upper();mn=MES.get(mw[:3],0)
  if dv==TD and mn==TN and av==TY:d[c]+=1
 wb.close();return sorted(d.items(),key=lambda x:-x[1])

def tabla(d,ruta):
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt;from matplotlib.patches import FancyBboxPatch
 t=sum(v for _,v in d)
 if not d:
  f,a=plt.subplots(figsize=(5,2.5));a.set_facecolor('#1a1a2e')
  f.patch.set_facecolor('#1a1a2e');a.text(.5,.5,f'Sin agendados hoy ({hoy})',ha='center',va='center',fontsize=16,color='white',fontweight='bold')
  a.axis('off');f.savefig(ruta,dpi=200,bbox_inches='tight',facecolor='#1a1a2e');plt.close(f);return
 n=len(d)+1;f,a=plt.subplots(figsize=(7,max(3,n*.7+2)))
 a.set_facecolor('#1a1a2e');f.patch.set_facecolor('#1a1a2e');a.axis('off')
 a.text(.5,.95,f'PACIENTES AGENDADOS - {hoy}',ha='center',va='top',fontsize=16,color='white',fontweight='bold',transform=a.transAxes)
 ys=.85;rh=.7/max(n,1)
 for i,(c,v)in enumerate(d):
  y=ys-(i+1)*rh;cl=COL[i%len(COL)]
  a.add_patch(FancyBboxPatch((.05,y-rh*.35),.9,rh*.7,boxstyle="round,pad=0.02",facecolor=cl,alpha=.85,transform=a.transAxes))
  a.text(.12,y,c.upper(),ha='left',va='center',fontsize=14,color='white',fontweight='bold',transform=a.transAxes)
  a.text(.88,y,str(v),ha='right',va='center',fontsize=18,color='white',fontweight='bold',transform=a.transAxes)
 yt=ys-n*rh;a.add_patch(FancyBboxPatch((.05,yt-rh*.35),.9,rh*.7,boxstyle="round,pad=0.02",facecolor='#333',alpha=.9,transform=a.transAxes))
 a.text(.12,yt,'TOTAL',ha='left',va='center',fontsize=14,color='#ffa62e',fontweight='bold',transform=a.transAxes)
 a.text(.88,yt,str(t),ha='right',va='center',fontsize=18,color='#ffa62e',fontweight='bold',transform=a.transAxes)
 plt.subplots_adjust(top=.92,bottom=.05,left=.03,right=.97);f.savefig(ruta,dpi=200,bbox_inches='tight',facecolor='#1a1a2e');plt.close(f)

def enviar(r,c):
 import pyautogui;pyautogui.FAILSAFE=False
 import pywhatkit as kit
 try:
  from pywhatkit.core import log as _;_.log_image=_.log_message=lambda*a,**k:None
 except:pass
 l.info('Abriendo WhatsApp...')
 kit.sendwhats_image(PHONE,os.path.abspath(r),c,wait_time=15,tab_close=False)
 l.info('Esperando...');time.sleep(8);pyautogui.press('enter');time.sleep(2);l.info('Enviado!')

try:
 d=datos();t=sum(v for _,v in d);l.info(f'{t} en {len(d)} CRMs')
 if d:
  l.info('Generando tabla...');tabla(d,JPG)
  if os.path.exists(JPG):enviar(JPG,f'🤖CRM Report_System: Agendados {hoy}')
  else:l.error('No se genero imagen')
 else:l.info('Sin datos')
except Exception as e:l.error(f'Error: {e}');sys.exit(1)
l.info('Listo!')

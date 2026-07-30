#!/usr/bin/env python3
import os,sys,time,io,logging,warnings;from datetime import date,datetime,timedelta
from collections import defaultdict
warnings.filterwarnings('ignore')
import openpyxl;from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build;from googleapiclient.http import MediaIoBaseDownload

PHONE='+51968797977';OUT=os.path.expanduser('~/TRABAJO/capturas');os.makedirs(OUT,exist_ok=True)
LOGS=os.path.expanduser('~/TRABAJO/logs');os.makedirs(LOGS,exist_ok=True)
JSON_KEY=os.path.expanduser('~/credenciales-sheets.json')
FILE_ID='1eVeMN1_f-RL2caN_Y9pq3DNEez3TeVTZ'
MES={'ENE':1,'FEB':2,'MAR':3,'ABR':4,'MAY':5,'JUN':6,'JUL':7,'AGO':8,'SET':9,'SEP':9,'OCT':10,'NOV':11,'DIC':12}
EXCL={'RETOQUES','RETOQUE','EVALUACIONES','EVALUACION','SESION','SESIÓN','SESIONES'}
COL=['#e94560','#0f3460','#533483','#a66cff','#ffa62e','#7ed321','#ff6b6b','#4ecdc4']
JPG=os.path.join(OUT,'reporte_semanal.jpg')

l=logging.getLogger('semanal');l.setLevel(logging.INFO)
if not l.handlers:
 h1=logging.FileHandler(os.path.join(LOGS,'semanal_out.log'))
 h2=logging.FileHandler(os.path.join(LOGS,'semanal_err.log'));h2.setLevel(logging.WARNING)
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
  except:time.sleep(5)
 raise Exception('Fallo descarga')

def rango():
 h=date.today()
 if len(sys.argv)>=3:
  l=datetime.strptime(sys.argv[1],'%d/%m/%Y').date()
  s=datetime.strptime(sys.argv[2],'%d/%m/%Y').date()
  return l,s
 lunes=h-timedelta(days=h.weekday())
 sabado=lunes+timedelta(days=5)
 return lunes,sabado

def datos(lunes,sabado):
 l.info(f'Semana {lunes} al {sabado}');wb=descargar();ws=wb['AGENDADOS'];d=defaultdict(int);dx=defaultdict(lambda:defaultdict(int))
 for r in ws.iter_rows(min_row=5,values_only=True):
  if len(r)<16:continue
  c=str(r[11]or'').strip()
  if not c or c.lower()=='none':continue
  n=str(r[5]or'').strip();t=str(r[8]or'').strip();p=str(r[15]or'').strip()
  if not n or not t or not p:continue
  if any(e in p.upper() for e in EXCL):continue
  dv=int(r[2])if r[2]is not None else 0;av=int(r[4])if r[4]is not None else 0
  mw=str(r[3]or'').strip().upper();mn=MES.get(mw[:3],0)
  if dv==0 or mn==0 or av==0:continue
  f=date(av,mn,dv)
  if lunes<=f<=sabado:d[c]+=1;dx[c][str(f)]+=1
 wb.close();return sorted(d.items(),key=lambda x:-x[1]),dx

def tabla(d,dx,lunes,sabado,ruta):
 import matplotlib;matplotlib.use('Agg')
 import matplotlib.pyplot as plt;from matplotlib.patches import FancyBboxPatch
 t=sum(v for _,v in d);dias=[str(lunes+timedelta(days=i))for i in range((sabado-lunes).days+1)]
 if not d:
  f,a=plt.subplots(figsize=(5,2.5));a.set_facecolor('#1a1a2e')
  f.patch.set_facecolor('#1a1a2e');a.text(.5,.5,f'Sin agendados ({lunes} al {sabado})',ha='center',va='center',fontsize=14,color='white',fontweight='bold')
  a.axis('off');f.savefig(ruta,dpi=200,bbox_inches='tight',facecolor='#1a1a2e');plt.close(f);return
 n=len(d)+2;f,a=plt.subplots(figsize=(10,max(4,n*.55+2)))
 a.set_facecolor('#1a1a2e');f.patch.set_facecolor('#1a1a2e');a.axis('off')
 a.text(.5,.96,f'AGENDADOS SEMANA {lunes} AL {sabado}',ha='center',va='top',fontsize=14,color='white',fontweight='bold',transform=a.transAxes)
 ys=.9;rh=.75/max(n,1)
 for i,(c,v)in enumerate(d):
  y=ys-(i+1)*rh;cl=COL[i%len(COL)]
  a.add_patch(FancyBboxPatch((.02,y-rh*.35),.96,rh*.7,boxstyle="round,pad=0.02",facecolor=cl,alpha=.85,transform=a.transAxes))
  a.text(.05,y,c.upper(),ha='left',va='center',fontsize=11,color='white',fontweight='bold',transform=a.transAxes)
  det=', '.join(f'{dx[c].get(d,0)}'for d in dias)
  a.text(.35,y,det,ha='left',va='center',fontsize=9,color='#ffd700',transform=a.transAxes)
  a.text(.92,y,str(v),ha='right',va='center',fontsize=14,color='white',fontweight='bold',transform=a.transAxes)
 yt=ys-(n-1)*rh;a.add_patch(FancyBboxPatch((.02,yt-rh*.35),.96,rh*.7,boxstyle="round,pad=0.02",facecolor='#333',alpha=.9,transform=a.transAxes))
 a.text(.05,yt,'TOTAL',ha='left',va='center',fontsize=12,color='#ffa62e',fontweight='bold',transform=a.transAxes)
 a.text(.92,yt,str(t),ha='right',va='center',fontsize=14,color='#ffa62e',fontweight='bold',transform=a.transAxes)
 a.text(.5,yt,f'Semanal {t}',ha='center',va='center',fontsize=10,color='#aaa',transform=a.transAxes)
 a.text(.02,.16,'L M M J V S',ha='left',va='center',fontsize=8,color='#666',transform=a.transAxes)
 plt.subplots_adjust(top=.94,bottom=.04,left=.02,right=.98);f.savefig(ruta,dpi=200,bbox_inches='tight',facecolor='#1a1a2e');plt.close(f)

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
 lunes,sabado=rango();d,dx=datos(lunes,sabado);t=sum(v for _,v in d);l.info(f'{t} en {len(d)} CRMs')
 if d:
  l.info('Generando tabla...');tabla(d,dx,lunes,sabado,JPG)
  if os.path.exists(JPG):enviar(JPG,f'🤖CRM Report_System: Semanal {lunes} al {sabado}')
  else:l.error('No se genero imagen')
 else:l.info('Sin datos')
except Exception as e:l.error(f'Error: {e}');sys.exit(1)
l.info('Listo!')

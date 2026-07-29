#!/usr/bin/env python3
import sys
import time
import os
from datetime import datetime, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)
sys.path.insert(0, BASE_DIR)

from config import PHONE_AGENDADOS, OUT_DIR, SHEETS_CONFIG
from utils import (
    configurar_logging, conectar_gsheets, abrir_spreadsheet,
    normalizar_hora, hora_sort_key, crear_mensaje_agendados,
    crear_tabla_imagen, leer_sheet_a_dataframe, filtrar_por_fecha,
)

log = configurar_logging('capturar_enviar')

if len(sys.argv) >= 3:
    HOY = datetime.strptime(sys.argv[1], '%d/%m/%Y')
    MANANA = datetime.strptime(sys.argv[2], '%d/%m/%Y')
else:
    HOY = datetime.now()
    dias = 2 if HOY.weekday() == 5 else 1
    MANANA = HOY + timedelta(days=dias)


def enviar_whatsapp(ruta_imagen, caption, primera=False):
    """
    Envía imagen + texto a WhatsApp Web usando osascript directamente.
    """
    import subprocess
    ruta_abs = os.path.abspath(ruta_imagen)
    phone = PHONE_AGENDADOS

    def run_osascript(script):
        return subprocess.run(
            ['osascript', '-e', script],
            capture_output=True, text=True, timeout=30
        )

    def copiar_imagen():
        """Copia la imagen al portapapeles."""
        run_osascript(
            f'set the clipboard to (read (POSIX file "{ruta_abs}") as JPEG picture)'
        )
        time.sleep(1)

    def pegar_tecla():
        """Pega con Cmd+V via System Events."""
        run_osascript(
            'tell application "System Events" to keystroke "v" using command down'
        )

    try:
        chat_url = f'https://web.whatsapp.com/send?phone={phone}'

        # Copiar imagen al portapapeles primero
        copiar_imagen()
        log.info('Imagen copiada al portapapeles')

        # Abrir Safari con WhatsApp Web (nueva pestaña si ya está abierto)
        subprocess.run(['open', '-a', 'Safari', chat_url], check=True)

        # Esperar a que el chat cargue
        wait = 30 if primera else 20
        log.info(f'Esperando {wait}s para que el chat cargue...')
        time.sleep(wait)

        # Traer Safari al frente
        run_osascript('tell application "Safari" to activate')
        time.sleep(1)

        # Pegar imagen (re-copiar por si el portapapeles se cambio)
        copiar_imagen()
        pegar_tecla()
        log.info('Imagen pegada')
        time.sleep(5)

        # Pegar caption (preserva espacios y saltos)
        subprocess.run(['pbcopy'], input=caption.encode('utf-8'), check=True)
        time.sleep(0.5)
        pegar_tecla()
        time.sleep(2)

        # Enviar (Enter)
        run_osascript(
            'tell application "System Events" to keystroke return'
        )
        log.info('Enviado')
        time.sleep(3)

    except Exception as e:
        log.error(f'ERROR WhatsApp: {e}')
        log.info(f'Imagen guardada en: {ruta_abs}')


def main():
    log.info('Conectando a Google Sheets...')
    try:
        gc = conectar_gsheets()
        sh_default = abrir_spreadsheet(gc)
    except Exception as e:
        log.error(f'Error de conexion: {e}')
        sys.exit(1)

    spreadsheets = {}
    primera = True
    for nombre, cfg in SHEETS_CONFIG.items():
        # Abrir el spreadsheet correcto (puede ser uno diferente)
        sp_key = cfg.get('spreadsheet_key')
        if sp_key:
            if sp_key not in spreadsheets:
                spreadsheets[sp_key] = gc.open_by_key(sp_key)
            sh = spreadsheets[sp_key]
        else:
            sh = sh_default

        for label, dia in [('HOY', HOY), ('MANANA', MANANA)]:
            log.info(f'{nombre} -- {label} ({dia.strftime("%d/%m/%Y")})')
            ws = sh.worksheet(nombre)
            raw = ws.get_all_values()
            header_idx = cfg['header_row'] - 1
            headers_full = raw[header_idx]
            data_rows = raw[header_idx + 1:]
            if not data_rows:
                log.info('Sin datos, se omite.')
                continue
            ncols = cfg['ncols_full']
            headers = [str(headers_full[i]) for i in range(ncols)]
            rows = [[r[i] if i < len(r) else '' for i in range(ncols)] for r in data_rows]
            df_tmp = __import__('pandas').DataFrame(rows, columns=headers)
            df_tmp = df_tmp.replace('', __import__('pandas').NA).fillna('')
            df_tmp = df_tmp.map(lambda x: x.strip() if isinstance(x, str) else x)

            mask_df = filtrar_por_fecha(df_tmp, dia, cfg['date_cols'])
            log.info(f'Filas: {len(mask_df)}')
            if mask_df.empty:
                log.info('Sin datos, se omite.')
                continue

            col_hora = headers[cfg['time_col']]
            filtrado = mask_df.copy()
            filtrado[col_hora] = filtrado[col_hora].apply(normalizar_hora)
            filtrado['_sort_key'] = filtrado[col_hora].apply(hora_sort_key)
            filtrado = filtrado.sort_values('_sort_key').drop(columns=['_sort_key'])
            cols_idx = cfg['cols_mostrar']
            filtrado = filtrado.iloc[:, cols_idx]
            if cfg.get('nombre_header'):
                new_cols = list(filtrado.columns)
                new_cols[0] = cfg['nombre_header']
                filtrado.columns = new_cols
            col_nombre = filtrado.columns[0]
            filtrado = filtrado[filtrado[col_nombre].astype(str).str.strip() != '']
            filtrado = filtrado.reset_index(drop=True)

            display = cfg.get('display_name', nombre)
            archivo = os.path.join(OUT_DIR, f"{display.replace(' ', '_')}_{label}.jpg")
            titulo_img = f"{display} -- {label} ({dia.strftime('%d/%m/%Y')})"
            destacar = 'CJ' in nombre
            crear_tabla_imagen(filtrado, titulo_img, archivo, highlight_camp=destacar)
            mensaje = crear_mensaje_agendados(filtrado, label)
            caption = f'{titulo_img}\n{mensaje}' if mensaje else titulo_img
            log.info(f'Mensaje: {caption}')
            if not os.path.exists(archivo):
                log.warning(f'Imagen no generada: {archivo}')
                continue
            log.info('Enviando WhatsApp...')
            enviar_whatsapp(archivo, caption, primera)
            primera = False

    log.info('Finalizado.')


if __name__ == '__main__':
    main()

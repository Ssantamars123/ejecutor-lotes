"""
Módulo común para comunicación por FIFOs y protocolo JSON.
Usado por todos los servicios del sistema Ejecutor de Lotes.
"""

import os
import sys
import json
import stat


def crear_fifo(ruta):
    """Crea un FIFO si no existe."""
    if os.path.exists(ruta):
        # Verificar que es un FIFO
        if stat.S_ISFIFO(os.stat(ruta).st_mode):
            print(f"[INFO] FIFO ya existe: {ruta}")
            return
        else:
            print(f"[ERROR] {ruta} existe pero no es un FIFO")
            sys.exit(1)
    try:
        os.mkfifo(ruta)
        print(f"[INFO] FIFO creado: {ruta}")
    except OSError as e:
        print(f"[ERROR] No se pudo crear FIFO {ruta}: {e}")
        sys.exit(1)


def eliminar_fifo(ruta):
    """Elimina un FIFO si existe."""
    if os.path.exists(ruta):
        os.unlink(ruta)
        print(f"[INFO] FIFO eliminado: {ruta}")


def enviar_mensaje(fifo_path, mensaje_dict):
    """
    Envía un mensaje JSON a través de un FIFO.
    Abre el FIFO en modo escritura, escribe el JSON + newline, y cierra.
    """
    json_str = json.dumps(mensaje_dict, ensure_ascii=False)
    print(f"[ENVIAR → {fifo_path}] {json_str}")
    with open(fifo_path, 'w') as f:
        f.write(json_str + '\n')
        f.flush()


def recibir_mensaje(fifo_path):
    """
    Recibe un mensaje JSON desde un FIFO.
    Abre el FIFO en modo lectura, lee una línea, parsea JSON, y cierra.
    Retorna el diccionario parseado o None si el FIFO se cerró.
    """
    with open(fifo_path, 'r') as f:
        linea = f.readline().strip()
        if not linea:
            return None
        print(f"[RECIBIR ← {fifo_path}] {linea}")
        try:
            return json.loads(linea)
        except json.JSONDecodeError as e:
            print(f"[ERROR] JSON inválido: {e}")
            return None


def respuesta_ok(id_peticion, datos, mensaje=""):
    """Crea un diccionario de respuesta exitosa."""
    return {
        "id": id_peticion,
        "estado": "ok",
        "datos": datos,
        "mensaje": mensaje
    }


def respuesta_error(id_peticion, mensaje):
    """Crea un diccionario de respuesta de error."""
    return {
        "id": id_peticion,
        "estado": "error",
        "datos": None,
        "mensaje": mensaje
    }


def log(servicio, mensaje):
    """Imprime un mensaje de log con el nombre del servicio."""
    print(f"[{servicio}] {mensaje}")

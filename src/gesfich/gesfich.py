#!/usr/bin/env python3
"""
gesfich - Gestor de Ficheros
Servicio CRUD para ficheros almacenados en aralmac.
"""

import os
import sys
import argparse
import shutil

# Agregar el directorio padre al path para importar common
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.protocolo import (
    crear_fifo, eliminar_fifo, enviar_mensaje, recibir_mensaje,
    respuesta_ok, respuesta_error, log
)


class GestorFicheros:
    def __init__(self, fifo_req, fifo_res, ruta_aralmac):
        self.fifo_req = fifo_req
        self.fifo_res = fifo_res
        self.ruta_aralmac = ruta_aralmac
        self.directorio_ficheros = os.path.join(ruta_aralmac, 'ficheros')
        self.archivo_contador = os.path.join(ruta_aralmac, 'estado', 'fichero_counter.txt')
        self.estado = 'corriendo'  # corriendo | suspendido | terminado

        # Crear directorios si no existen
        os.makedirs(self.directorio_ficheros, exist_ok=True)
        os.makedirs(os.path.join(ruta_aralmac, 'estado'), exist_ok=True)

    def obtener_siguiente_id(self):
        """Lee el contador, lo incrementa y retorna el nuevo id."""
        contador = 0
        if os.path.exists(self.archivo_contador):
            with open(self.archivo_contador, 'r') as f:
                contenido = f.read().strip()
                if contenido:
                    contador = int(contenido)
        contador += 1
        with open(self.archivo_contador, 'w') as f:
            f.write(str(contador))
        return f"f-{contador:04d}"

    def ruta_fichero(self, id_fichero):
        """Retorna la ruta completa de un fichero dado su id."""
        return os.path.join(self.directorio_ficheros, id_fichero)

    def fichero_existe(self, id_fichero):
        """Verifica si un fichero existe."""
        return os.path.exists(self.ruta_fichero(id_fichero))

    # ─────────────────────────────────────────
    # Operaciones CRUD
    # ─────────────────────────────────────────

    def op_crear(self, peticion):
        """Crea un fichero vacío y retorna su id."""
        id_fichero = self.obtener_siguiente_id()
        ruta = self.ruta_fichero(id_fichero)
        # Crear archivo vacío
        with open(ruta, 'w') as f:
            pass
        log("gesfich", f"Fichero creado: {id_fichero}")
        return respuesta_ok(
            peticion['id'],
            {"id_fichero": id_fichero},
            "Fichero creado"
        )

    def op_leer(self, peticion):
        """Lee un fichero por id, o lista todos si no se da id."""
        params = peticion.get('parametros', {})
        id_fichero = params.get('id_fichero')

        if id_fichero:
            # Leer un fichero específico
            if not self.fichero_existe(id_fichero):
                return respuesta_error(peticion['id'], f"El fichero {id_fichero} no existe")
            ruta = self.ruta_fichero(id_fichero)
            with open(ruta, 'r') as f:
                contenido = f.read()
            return respuesta_ok(
                peticion['id'],
                {"id_fichero": id_fichero, "contenido": contenido}
            )
        else:
            # Listar todos los ficheros
            ficheros = []
            for nombre in sorted(os.listdir(self.directorio_ficheros)):
                if nombre.startswith('f-'):
                    ruta = self.ruta_fichero(nombre)
                    tamaño = os.path.getsize(ruta)
                    ficheros.append({"id_fichero": nombre, "tamaño": tamaño})
            return respuesta_ok(
                peticion['id'],
                {"ficheros": ficheros}
            )

    def op_actualizar(self, peticion):
        """Copia contenido de un archivo externo al fichero registrado."""
        params = peticion.get('parametros', {})
        id_fichero = params.get('id_fichero')
        ruta_origen = params.get('ruta')

        if not id_fichero:
            return respuesta_error(peticion['id'], "Falta id_fichero")
        if not ruta_origen:
            return respuesta_error(peticion['id'], "Falta ruta del archivo origen")
        if not self.fichero_existe(id_fichero):
            return respuesta_error(peticion['id'], f"El fichero {id_fichero} no existe")
        if not os.path.exists(ruta_origen):
            return respuesta_error(peticion['id'], f"El archivo origen {ruta_origen} no existe")

        shutil.copy2(ruta_origen, self.ruta_fichero(id_fichero))
        log("gesfich", f"Fichero actualizado: {id_fichero} ← {ruta_origen}")
        return respuesta_ok(
            peticion['id'],
            {"id_fichero": id_fichero},
            "Fichero actualizado"
        )

    def op_borrar(self, peticion):
        """Elimina un fichero del aralmac."""
        params = peticion.get('parametros', {})
        id_fichero = params.get('id_fichero')

        if not id_fichero:
            return respuesta_error(peticion['id'], "Falta id_fichero")
        if not self.fichero_existe(id_fichero):
            return respuesta_error(peticion['id'], f"El fichero {id_fichero} no existe")

        os.remove(self.ruta_fichero(id_fichero))
        log("gesfich", f"Fichero borrado: {id_fichero}")
        return respuesta_ok(
            peticion['id'],
            {"id_fichero": id_fichero},
            "Fichero borrado"
        )

    # ─────────────────────────────────────────
    # Control de estado
    # ─────────────────────────────────────────

    def op_suspender(self, peticion):
        if self.estado != 'corriendo':
            return respuesta_error(peticion['id'], f"No se puede suspender desde estado '{self.estado}'")
        self.estado = 'suspendido'
        log("gesfich", "Servicio SUSPENDIDO")
        return respuesta_ok(peticion['id'], {"estado": self.estado}, "Servicio suspendido")

    def op_reasumir(self, peticion):
        if self.estado != 'suspendido':
            return respuesta_error(peticion['id'], f"No se puede reasumir desde estado '{self.estado}'")
        self.estado = 'corriendo'
        log("gesfich", "Servicio REASUMIDO")
        return respuesta_ok(peticion['id'], {"estado": self.estado}, "Servicio reasumido")

    def op_terminar(self, peticion):
        self.estado = 'terminado'
        log("gesfich", "Servicio TERMINADO")
        return respuesta_ok(peticion['id'], {"estado": self.estado}, "Servicio terminado")

    # ─────────────────────────────────────────
    # Despacho de operaciones
    # ─────────────────────────────────────────

    def despachar(self, peticion):
        """Dirige la petición a la operación correcta."""
        operacion = peticion.get('operacion', '').lower()

        # En estado suspendido, solo aceptar reasumir y terminar
        if self.estado == 'suspendido':
            if operacion == 'reasumir':
                return self.op_reasumir(peticion)
            elif operacion == 'terminar':
                return self.op_terminar(peticion)
            else:
                return respuesta_error(
                    peticion.get('id', ''),
                    f"Servicio suspendido. Solo se acepta 'reasumir' o 'terminar'."
                )

        # En estado corriendo, aceptar todo
        operaciones = {
            'crear': self.op_crear,
            'leer': self.op_leer,
            'actualizar': self.op_actualizar,
            'borrar': self.op_borrar,
            'suspender': self.op_suspender,
            'reasumir': self.op_reasumir,
            'terminar': self.op_terminar,
        }

        func = operaciones.get(operacion)
        if func:
            return func(peticion)
        else:
            return respuesta_error(
                peticion.get('id', ''),
                f"Operación desconocida: '{operacion}'"
            )

    # ─────────────────────────────────────────
    # Loop principal
    # ─────────────────────────────────────────

    def ejecutar(self):
        """Loop principal del servicio."""
        log("gesfich", f"Iniciando servicio...")
        log("gesfich", f"  FIFO peticiones: {self.fifo_req}")
        log("gesfich", f"  FIFO respuestas: {self.fifo_res}")
        log("gesfich", f"  Almacenamiento:  {self.ruta_aralmac}")

        # Crear FIFOs
        crear_fifo(self.fifo_req)
        crear_fifo(self.fifo_res)

        log("gesfich", "Servicio listo. Esperando peticiones...")

        while self.estado != 'terminado':
            # Leer petición
            peticion = recibir_mensaje(self.fifo_req)

            if peticion is None:
                # FIFO cerrado, reabrir y esperar
                continue

            # Procesar
            respuesta = self.despachar(peticion)

            # Enviar respuesta
            enviar_mensaje(self.fifo_res, respuesta)

        log("gesfich", "Servicio finalizado.")


def main():
    parser = argparse.ArgumentParser(description='gesfich - Gestor de Ficheros')
    parser.add_argument('-f', required=True, help='FIFO para recibir peticiones')
    parser.add_argument('-b', required=False, help='FIFO para enviar respuestas (half-duplex)')
    parser.add_argument('-x', required=True, help='Ruta del almacenamiento aralmac')

    args = parser.parse_args()

    # En Linux (half-duplex), -b es obligatorio
    fifo_res = args.b if args.b else args.f
    if not args.b:
        log("gesfich", "ADVERTENCIA: No se especificó -b. Usando mismo FIFO (full-duplex).")

    gestor = GestorFicheros(args.f, fifo_res, args.x)
    try:
        gestor.ejecutar()
    except KeyboardInterrupt:
        log("gesfich", "Interrumpido por el usuario (Ctrl+C)")
    except Exception as e:
        log("gesfich", f"Error fatal: {e}")
        raise


if __name__ == '__main__':
    main()

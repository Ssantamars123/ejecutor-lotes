#!/usr/bin/env python3
"""
gesprog - Gestor de Programas
Servicio CRUD para programas almacenados en aralmac.
"""

import os
import sys
import json
import argparse
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.protocolo import (
    crear_fifo, eliminar_fifo, enviar_mensaje, recibir_mensaje,
    respuesta_ok, respuesta_error, log
)


class GestorProgramas:
    def __init__(self, fifo_req, fifo_res, ruta_aralmac):
        self.fifo_req = fifo_req
        self.fifo_res = fifo_res
        self.ruta_aralmac = ruta_aralmac
        self.directorio_programas = os.path.join(ruta_aralmac, 'programas')
        self.archivo_contador = os.path.join(ruta_aralmac, 'estado', 'programa_counter.txt')
        self.estado = 'corriendo'

        os.makedirs(self.directorio_programas, exist_ok=True)
        os.makedirs(os.path.join(ruta_aralmac, 'estado'), exist_ok=True)

    def obtener_siguiente_id(self):
        contador = 0
        if os.path.exists(self.archivo_contador):
            with open(self.archivo_contador, 'r') as f:
                contenido = f.read().strip()
                if contenido:
                    contador = int(contenido)
        contador += 1
        with open(self.archivo_contador, 'w') as f:
            f.write(str(contador))
        return f"p-{contador:04d}"

    def ruta_metadata(self, id_programa):
        """Ruta al archivo JSON de metadata del programa."""
        return os.path.join(self.directorio_programas, f"{id_programa}.json")

    def programa_existe(self, id_programa):
        return os.path.exists(self.ruta_metadata(id_programa))

    def leer_metadata(self, id_programa):
        with open(self.ruta_metadata(id_programa), 'r') as f:
            return json.load(f)

    def guardar_metadata(self, id_programa, datos):
        with open(self.ruta_metadata(id_programa), 'w') as f:
            json.dump(datos, f, indent=2, ensure_ascii=False)

    # ─────────────────────────────────────────
    # Operaciones CRUD
    # ─────────────────────────────────────────

    def op_guardar(self, peticion):
        """Registra un nuevo programa."""
        params = peticion.get('parametros', {})
        ejecutable = params.get('ejecutable')
        argumentos = params.get('argumentos', [])
        ambiente = params.get('ambiente', {})

        if not ejecutable:
            return respuesta_error(peticion['id'], "Falta el campo 'ejecutable'")

        # Verificar que el ejecutable existe
        if not os.path.exists(ejecutable) and not shutil.which(ejecutable):
            return respuesta_error(peticion['id'], f"El ejecutable '{ejecutable}' no se encontró")

        id_programa = self.obtener_siguiente_id()
        metadata = {
            "id_programa": id_programa,
            "ejecutable": ejecutable,
            "argumentos": argumentos,
            "ambiente": ambiente
        }
        self.guardar_metadata(id_programa, metadata)
        log("gesprog", f"Programa registrado: {id_programa} → {ejecutable}")
        return respuesta_ok(
            peticion['id'],
            {"id_programa": id_programa},
            "Programa registrado"
        )

    def op_leer(self, peticion):
        """Lee info de un programa, o lista todos."""
        params = peticion.get('parametros', {})
        id_programa = params.get('id_programa')

        if id_programa:
            if not self.programa_existe(id_programa):
                return respuesta_error(peticion['id'], f"El programa {id_programa} no existe")
            metadata = self.leer_metadata(id_programa)
            return respuesta_ok(peticion['id'], metadata)
        else:
            programas = []
            for nombre in sorted(os.listdir(self.directorio_programas)):
                if nombre.endswith('.json'):
                    ruta = os.path.join(self.directorio_programas, nombre)
                    with open(ruta, 'r') as f:
                        metadata = json.load(f)
                    programas.append(metadata)
            return respuesta_ok(peticion['id'], {"programas": programas})

    def op_actualizar(self, peticion):
        """Actualiza la información de un programa existente."""
        params = peticion.get('parametros', {})
        id_programa = params.get('id_programa')

        if not id_programa:
            return respuesta_error(peticion['id'], "Falta id_programa")
        if not self.programa_existe(id_programa):
            return respuesta_error(peticion['id'], f"El programa {id_programa} no existe")

        # Leer metadata actual y actualizar campos proporcionados
        metadata = self.leer_metadata(id_programa)
        if 'ejecutable' in params:
            metadata['ejecutable'] = params['ejecutable']
        if 'argumentos' in params:
            metadata['argumentos'] = params['argumentos']
        if 'ambiente' in params:
            metadata['ambiente'] = params['ambiente']

        self.guardar_metadata(id_programa, metadata)
        log("gesprog", f"Programa actualizado: {id_programa}")
        return respuesta_ok(
            peticion['id'],
            {"id_programa": id_programa},
            "Programa actualizado"
        )

    def op_borrar(self, peticion):
        """Elimina un programa del registro."""
        params = peticion.get('parametros', {})
        id_programa = params.get('id_programa')

        if not id_programa:
            return respuesta_error(peticion['id'], "Falta id_programa")
        if not self.programa_existe(id_programa):
            return respuesta_error(peticion['id'], f"El programa {id_programa} no existe")

        os.remove(self.ruta_metadata(id_programa))
        log("gesprog", f"Programa borrado: {id_programa}")
        return respuesta_ok(
            peticion['id'],
            {"id_programa": id_programa},
            "Programa borrado"
        )

    # ─────────────────────────────────────────
    # Control de estado
    # ─────────────────────────────────────────

    def op_suspender(self, peticion):
        if self.estado != 'corriendo':
            return respuesta_error(peticion['id'], f"No se puede suspender desde '{self.estado}'")
        self.estado = 'suspendido'
        log("gesprog", "Servicio SUSPENDIDO")
        return respuesta_ok(peticion['id'], {"estado": self.estado}, "Servicio suspendido")

    def op_reasumir(self, peticion):
        if self.estado != 'suspendido':
            return respuesta_error(peticion['id'], f"No se puede reasumir desde '{self.estado}'")
        self.estado = 'corriendo'
        log("gesprog", "Servicio REASUMIDO")
        return respuesta_ok(peticion['id'], {"estado": self.estado}, "Servicio reasumido")

    def op_terminar(self, peticion):
        self.estado = 'terminado'
        log("gesprog", "Servicio TERMINADO")
        return respuesta_ok(peticion['id'], {"estado": self.estado}, "Servicio terminado")

    # ─────────────────────────────────────────
    # Despacho y loop principal
    # ─────────────────────────────────────────

    def despachar(self, peticion):
        operacion = peticion.get('operacion', '').lower()

        if self.estado == 'suspendido':
            if operacion == 'reasumir':
                return self.op_reasumir(peticion)
            elif operacion == 'terminar':
                return self.op_terminar(peticion)
            elif operacion == 'leer':
                return self.op_leer(peticion)
            else:
                return respuesta_error(
                    peticion.get('id', ''),
                    "Servicio suspendido. Solo se acepta 'leer', 'reasumir' o 'terminar'."
                )

        operaciones = {
            'guardar': self.op_guardar,
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
            return respuesta_error(peticion.get('id', ''), f"Operación desconocida: '{operacion}'")

    def ejecutar(self):
        log("gesprog", "Iniciando servicio...")
        log("gesprog", f"  FIFO peticiones: {self.fifo_req}")
        log("gesprog", f"  FIFO respuestas: {self.fifo_res}")
        log("gesprog", f"  Almacenamiento:  {self.ruta_aralmac}")

        crear_fifo(self.fifo_req)
        crear_fifo(self.fifo_res)

        log("gesprog", "Servicio listo. Esperando peticiones...")

        while self.estado != 'terminado':
            peticion = recibir_mensaje(self.fifo_req)
            if peticion is None:
                continue
            respuesta = self.despachar(peticion)
            enviar_mensaje(self.fifo_res, respuesta)

        log("gesprog", "Servicio finalizado.")


def main():
    parser = argparse.ArgumentParser(description='gesprog - Gestor de Programas')
    parser.add_argument('-p', required=True, help='FIFO para recibir peticiones')
    parser.add_argument('-c', required=False, help='FIFO para enviar respuestas (half-duplex)')
    parser.add_argument('-x', required=True, help='Ruta del almacenamiento aralmac')

    args = parser.parse_args()
    fifo_res = args.c if args.c else args.p
    if not args.c:
        log("gesprog", "ADVERTENCIA: No se especificó -c. Usando mismo FIFO (full-duplex).")

    gestor = GestorProgramas(args.p, fifo_res, args.x)
    try:
        gestor.ejecutar()
    except KeyboardInterrupt:
        log("gesprog", "Interrumpido por el usuario (Ctrl+C)")
    except Exception as e:
        log("gesprog", f"Error fatal: {e}")
        raise


if __name__ == '__main__':
    main()

#!/usr/bin/env python3
"""
ejecutor - Ejecutor de Procesos de Lotes
Ejecuta procesos a partir de programas y ficheros registrados en aralmac.
"""

import os
import sys
import json
import argparse
import signal
import subprocess

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.protocolo import (
    crear_fifo, eliminar_fifo, enviar_mensaje, recibir_mensaje,
    respuesta_ok, respuesta_error, log
)


class Ejecutor:
    def __init__(self, fifo_req, fifo_res, ruta_aralmac):
        self.fifo_req = fifo_req
        self.fifo_res = fifo_res
        self.ruta_aralmac = ruta_aralmac
        self.directorio_ficheros = os.path.join(ruta_aralmac, 'ficheros')
        self.directorio_programas = os.path.join(ruta_aralmac, 'programas')
        self.archivo_contador = os.path.join(ruta_aralmac, 'estado', 'lote_counter.txt')
        self.estado = 'ejecutar'  # ejecutar | suspendidos | parar | terminar
        self.procesos = {}  # id_lote → { pid, proceso, estado_proceso, ... }

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
        return f"j-{contador:04d}"

    def leer_programa(self, id_programa):
        """Lee la metadata de un programa registrado."""
        ruta = os.path.join(self.directorio_programas, f"{id_programa}.json")
        if not os.path.exists(ruta):
            return None
        with open(ruta, 'r') as f:
            return json.load(f)

    def ruta_fichero(self, id_fichero):
        return os.path.join(self.directorio_ficheros, id_fichero)

    def actualizar_estados_procesos(self):
        """Revisa procesos hijos y actualiza su estado."""
        for id_lote, info in self.procesos.items():
            if info['estado_proceso'] in ('corriendo', 'suspendido'):
                proc = info.get('proceso')
                if proc:
                    retcode = proc.poll()
                    if retcode is not None:
                        info['estado_proceso'] = 'terminado'
                        info['codigo_retorno'] = retcode
                        log("ejecutor", f"Proceso {id_lote} terminó (código: {retcode})")

    def contar_activos(self):
        """Cuenta procesos activos (corriendo o suspendido)."""
        self.actualizar_estados_procesos()
        return sum(1 for info in self.procesos.values()
                   if info['estado_proceso'] in ('corriendo', 'suspendido'))

    # ─────────────────────────────────────────
    # Operaciones
    # ─────────────────────────────────────────

    def op_ejecutar(self, peticion):
        """Crea y ejecuta un proceso de lotes."""
        params = peticion.get('parametros', {})
        id_programa = params.get('id_programa')
        id_fichero_entrada = params.get('id_fichero_entrada')
        id_fichero_salida = params.get('id_fichero_salida')

        if not id_programa:
            return respuesta_error(peticion['id'], "Falta id_programa")
        if not id_fichero_entrada:
            return respuesta_error(peticion['id'], "Falta id_fichero_entrada (obligatorio)")
        if not id_fichero_salida:
            return respuesta_error(peticion['id'], "Falta id_fichero_salida (obligatorio)")

        # Leer programa
        programa = self.leer_programa(id_programa)
        if not programa:
            return respuesta_error(peticion['id'], f"El programa {id_programa} no existe")

        ruta_entrada = self.ruta_fichero(id_fichero_entrada)
        if not os.path.exists(ruta_entrada):
            return respuesta_error(peticion['id'], f"El fichero de entrada {id_fichero_entrada} no existe")

        ruta_salida = self.ruta_fichero(id_fichero_salida)
        if not os.path.exists(ruta_salida):
            return respuesta_error(peticion['id'], f"El fichero de salida {id_fichero_salida} no existe")

        stdin_file = open(ruta_entrada, 'r')
        stdout_file = open(ruta_salida, 'w')

        # Construir comando
        ejecutable = programa['ejecutable']
        argumentos = programa.get('argumentos', [])
        ambiente = os.environ.copy()
        ambiente.update(programa.get('ambiente', {}))

        cmd = [ejecutable] + argumentos

        try:
            proc = subprocess.Popen(
                cmd,
                stdin=stdin_file,
                stdout=stdout_file,
                stderr=subprocess.PIPE,
                env=ambiente
            )
        except FileNotFoundError:
            return respuesta_error(peticion['id'], f"Ejecutable no encontrado: {ejecutable}")
        except PermissionError:
            return respuesta_error(peticion['id'], f"Sin permisos para ejecutar: {ejecutable}")
        finally:
            # No cerrar stdin_file/stdout_file aquí, Popen los usa
            pass

        id_lote = self.obtener_siguiente_id()
        self.procesos[id_lote] = {
            'proceso': proc,
            'pid': proc.pid,
            'estado_proceso': 'corriendo',
            'id_programa': id_programa,
            'id_fichero_entrada': id_fichero_entrada,
            'id_fichero_salida': id_fichero_salida,
            'codigo_retorno': None,
            'stdin_file': stdin_file,
            'stdout_file': stdout_file,
        }

        log("ejecutor", f"Proceso de lotes iniciado: {id_lote} (PID: {proc.pid})")
        return respuesta_ok(
            peticion['id'],
            {"id_lote": id_lote, "pid": proc.pid},
            "Proceso de lotes iniciado"
        )

    def op_estado(self, peticion):
        """Consulta el estado de un proceso o de todos."""
        params = peticion.get('parametros', {})
        id_lote = params.get('id_lote')

        self.actualizar_estados_procesos()

        if id_lote:
            if id_lote not in self.procesos:
                return respuesta_error(peticion['id'], f"Proceso {id_lote} no existe")
            info = self.procesos[id_lote]
            return respuesta_ok(peticion['id'], {
                "id_lote": id_lote,
                "pid": info['pid'],
                "estado_proceso": info['estado_proceso'],
                "id_programa": info['id_programa'],
                "codigo_retorno": info['codigo_retorno']
            })
        else:
            lista = []
            for lote_id, info in self.procesos.items():
                lista.append({
                    "id_lote": lote_id,
                    "pid": info['pid'],
                    "estado_proceso": info['estado_proceso'],
                    "codigo_retorno": info['codigo_retorno']
                })
            return respuesta_ok(peticion['id'], {"procesos": lista})

    def op_matar(self, peticion):
        """Mata un proceso de lotes."""
        params = peticion.get('parametros', {})
        id_lote = params.get('id_lote')

        if not id_lote:
            return respuesta_error(peticion['id'], "Falta id_lote")
        if id_lote not in self.procesos:
            return respuesta_error(peticion['id'], f"Proceso {id_lote} no existe")

        info = self.procesos[id_lote]
        if info['estado_proceso'] == 'terminado':
            return respuesta_error(peticion['id'], f"Proceso {id_lote} ya terminó")

        try:
            os.kill(info['pid'], signal.SIGTERM)
            info['estado_proceso'] = 'terminado'
            # Cerrar archivos abiertos
            if info.get('stdin_file'):
                info['stdin_file'].close()
            if info.get('stdout_file'):
                info['stdout_file'].close()
            log("ejecutor", f"Proceso {id_lote} (PID: {info['pid']}) MATADO")
            return respuesta_ok(peticion['id'], {"id_lote": id_lote}, "Proceso matado")
        except ProcessLookupError:
            info['estado_proceso'] = 'terminado'
            return respuesta_ok(peticion['id'], {"id_lote": id_lote}, "Proceso ya no existía")

    def op_suspender(self, peticion):
        """Suspende el servicio ejecutor y todos los procesos activos."""
        if self.estado != 'ejecutar':
            return respuesta_error(peticion['id'], f"No se puede suspender desde '{self.estado}'")

        # Enviar SIGSTOP a todos los procesos activos
        for id_lote, info in self.procesos.items():
            if info['estado_proceso'] == 'corriendo':
                try:
                    os.kill(info['pid'], signal.SIGSTOP)
                    info['estado_proceso'] = 'suspendido'
                    log("ejecutor", f"Proceso {id_lote} SUSPENDIDO")
                except ProcessLookupError:
                    info['estado_proceso'] = 'terminado'

        self.estado = 'suspendidos'
        log("ejecutor", "Servicio SUSPENDIDO")
        return respuesta_ok(peticion['id'], {"estado": self.estado}, "Servicio suspendido")

    def op_reasumir(self, peticion):
        """Reasume el servicio y todos los procesos suspendidos."""
        if self.estado != 'suspendidos':
            return respuesta_error(peticion['id'], f"No se puede reasumir desde '{self.estado}'")

        for id_lote, info in self.procesos.items():
            if info['estado_proceso'] == 'suspendido':
                try:
                    os.kill(info['pid'], signal.SIGCONT)
                    info['estado_proceso'] = 'corriendo'
                    log("ejecutor", f"Proceso {id_lote} REASUMIDO")
                except ProcessLookupError:
                    info['estado_proceso'] = 'terminado'

        self.estado = 'ejecutar'
        log("ejecutor", "Servicio REASUMIDO")
        return respuesta_ok(peticion['id'], {"estado": self.estado}, "Servicio reasumido")

    def op_parar(self, peticion):
        """Pasa a estado parar solo si no hay procesos activos."""
        activos = self.contar_activos()
        if activos > 0:
            return respuesta_error(
                peticion['id'],
                f"No se puede parar: hay {activos} proceso(s) activo(s)"
            )
        self.estado = 'parar'
        log("ejecutor", "Servicio en estado PARAR")
        return respuesta_ok(peticion['id'], {"estado": self.estado}, "Servicio en parar")

    def op_terminar(self, peticion):
        """Termina el servicio."""
        # Matar todos los procesos activos
        for id_lote, info in self.procesos.items():
            if info['estado_proceso'] in ('corriendo', 'suspendido'):
                try:
                    os.kill(info['pid'], signal.SIGTERM)
                except ProcessLookupError:
                    pass
                info['estado_proceso'] = 'terminado'

        self.estado = 'terminar'
        log("ejecutor", "Servicio TERMINADO")
        return respuesta_ok(peticion['id'], {"estado": self.estado}, "Servicio terminado")

    # ─────────────────────────────────────────
    # Despacho y loop principal
    # ─────────────────────────────────────────

    def despachar(self, peticion):
        operacion = peticion.get('operacion', '').lower()

        if self.estado == 'suspendidos':
            if operacion == 'reasumir':
                return self.op_reasumir(peticion)
            elif operacion == 'terminar':
                return self.op_terminar(peticion)
            else:
                return respuesta_error(
                    peticion.get('id', ''),
                    "Servicio suspendido. Solo se acepta 'reasumir' o 'terminar'."
                )

        if self.estado == 'parar':
            if operacion == 'terminar':
                return self.op_terminar(peticion)
            else:
                return respuesta_error(
                    peticion.get('id', ''),
                    "Servicio en parar. Solo se acepta 'terminar'."
                )

        operaciones = {
            'ejecutar': self.op_ejecutar,
            'estado': self.op_estado,
            'matar': self.op_matar,
            'suspender': self.op_suspender,
            'reasumir': self.op_reasumir,
            'parar': self.op_parar,
            'terminar': self.op_terminar,
        }

        func = operaciones.get(operacion)
        if func:
            return func(peticion)
        else:
            return respuesta_error(peticion.get('id', ''), f"Operación desconocida: '{operacion}'")

    def ejecutar_servicio(self):
        log("ejecutor", "Iniciando servicio...")
        log("ejecutor", f"  FIFO peticiones: {self.fifo_req}")
        log("ejecutor", f"  FIFO respuestas: {self.fifo_res}")
        log("ejecutor", f"  Almacenamiento:  {self.ruta_aralmac}")

        crear_fifo(self.fifo_req)
        crear_fifo(self.fifo_res)

        log("ejecutor", "Servicio listo. Esperando peticiones...")

        while self.estado != 'terminar':
            peticion = recibir_mensaje(self.fifo_req)
            if peticion is None:
                continue
            respuesta = self.despachar(peticion)
            enviar_mensaje(self.fifo_res, respuesta)

        log("ejecutor", "Servicio finalizado.")


def main():
    parser = argparse.ArgumentParser(description='ejecutor - Ejecutor de Lotes')
    parser.add_argument('-e', required=True, help='FIFO para recibir peticiones')
    parser.add_argument('-d', required=False, help='FIFO para enviar respuestas (half-duplex)')
    parser.add_argument('-x', required=True, help='Ruta del almacenamiento aralmac')

    args = parser.parse_args()
    fifo_res = args.d if args.d else args.e
    if not args.d:
        log("ejecutor", "ADVERTENCIA: No se especificó -d. Usando mismo FIFO (full-duplex).")

    ejec = Ejecutor(args.e, fifo_res, args.x)
    try:
        ejec.ejecutar_servicio()
    except KeyboardInterrupt:
        log("ejecutor", "Interrumpido por el usuario (Ctrl+C)")
    except Exception as e:
        log("ejecutor", f"Error fatal: {e}")
        raise


if __name__ == '__main__':
    main()

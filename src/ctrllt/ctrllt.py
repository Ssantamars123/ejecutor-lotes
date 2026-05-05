#!/usr/bin/env python3
"""
ctrllt - Control de Lotes
Pasarela que recibe peticiones de clientes y las redirige al servicio apropiado.
"""

import os
import sys
import argparse

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
from common.protocolo import (
    crear_fifo, eliminar_fifo, enviar_mensaje, recibir_mensaje,
    respuesta_ok, respuesta_error, log
)


class ControlLotes:
    def __init__(self, cliente_req, cliente_res,
                 gesfich_req, gesfich_res,
                 gesprog_req, gesprog_res,
                 ejecutor_req, ejecutor_res):
        # FIFOs del cliente
        self.cliente_req = cliente_req
        self.cliente_res = cliente_res
        # FIFOs de los servicios
        self.servicios = {
            'gesfich': {
                'req': gesfich_req,
                'res': gesfich_res
            },
            'gesprog': {
                'req': gesprog_req,
                'res': gesprog_res
            },
            'ejecutor': {
                'req': ejecutor_req,
                'res': ejecutor_res
            }
        }
        self.estado = 'corriendo'

    def ejecutar(self):
        log("ctrllt", "Iniciando Control de Lotes...")
        log("ctrllt", f"  Cliente REQ: {self.cliente_req}")
        log("ctrllt", f"  Cliente RES: {self.cliente_res}")
        for nombre, fifos in self.servicios.items():
            log("ctrllt", f"  {nombre} REQ: {fifos['req']}")
            log("ctrllt", f"  {nombre} RES: {fifos['res']}")

        # Crear FIFOs del cliente (los de servicios ya los crean ellos)
        crear_fifo(self.cliente_req)
        crear_fifo(self.cliente_res)

        log("ctrllt", "Pasarela lista. Esperando peticiones del cliente...")

        while self.estado != 'terminado':
            # 1. Leer petición del cliente
            peticion = recibir_mensaje(self.cliente_req)

            if peticion is None:
                continue

            # 2. Verificar si es un comando para ctrllt mismo
            servicio = peticion.get('servicio', '').lower()
            operacion = peticion.get('operacion', '').lower()

            if servicio == 'ctrllt':
                if operacion == 'terminar':
                    self.estado = 'terminado'
                    respuesta = respuesta_ok(peticion['id'], {"estado": "terminado"}, "ctrllt terminado")
                    enviar_mensaje(self.cliente_res, respuesta)
                    continue
                else:
                    respuesta = respuesta_error(peticion['id'], f"ctrllt no soporta operación '{operacion}'")
                    enviar_mensaje(self.cliente_res, respuesta)
                    continue

            # 3. Verificar servicio destino
            if servicio not in self.servicios:
                respuesta = respuesta_error(
                    peticion.get('id', ''),
                    f"Servicio desconocido: '{servicio}'. Servicios válidos: gesfich, gesprog, ejecutor"
                )
                enviar_mensaje(self.cliente_res, respuesta)
                continue

            # 4. Reenviar petición al servicio correcto
            fifos = self.servicios[servicio]
            log("ctrllt", f"Reenviando a {servicio}...")

            enviar_mensaje(fifos['req'], peticion)

            # 5. Esperar respuesta del servicio
            respuesta = recibir_mensaje(fifos['res'])

            if respuesta is None:
                respuesta = respuesta_error(
                    peticion.get('id', ''),
                    f"No se recibió respuesta del servicio {servicio}"
                )

            # 6. Reenviar respuesta al cliente
            enviar_mensaje(self.cliente_res, respuesta)

        log("ctrllt", "Control de Lotes finalizado.")


def main():
    parser = argparse.ArgumentParser(description='ctrllt - Control de Lotes')
    parser.add_argument('-c', required=True, help='FIFO cliente peticiones')
    parser.add_argument('-a', required=False, help='FIFO cliente respuestas')
    parser.add_argument('-f', required=True, help='FIFO gesfich peticiones')
    parser.add_argument('-b', required=False, help='FIFO gesfich respuestas')
    parser.add_argument('-p', required=True, help='FIFO gesprog peticiones')
    parser.add_argument('-q', required=False, help='FIFO gesprog respuestas')
    parser.add_argument('-e', required=True, help='FIFO ejecutor peticiones')
    parser.add_argument('-d', required=False, help='FIFO ejecutor respuestas')

    args = parser.parse_args()

    ctrl = ControlLotes(
        cliente_req=args.c,
        cliente_res=args.a if args.a else args.c,
        gesfich_req=args.f,
        gesfich_res=args.b if args.b else args.f,
        gesprog_req=args.p,
        gesprog_res=args.q if args.q else args.p,
        ejecutor_req=args.e,
        ejecutor_res=args.d if args.d else args.e,
    )

    try:
        ctrl.ejecutar()
    except KeyboardInterrupt:
        log("ctrllt", "Interrumpido por el usuario (Ctrl+C)")
    except Exception as e:
        log("ctrllt", f"Error fatal: {e}")
        raise


if __name__ == '__main__':
    main()

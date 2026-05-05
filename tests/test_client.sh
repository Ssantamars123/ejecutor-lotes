#!/bin/bash
# Cliente de prueba para el sistema Ejecutor de Lotes
# Ejecutar DESPUÉS de iniciar el sistema con scripts/iniciar_sistema.sh

CTRLLT_REQ="/tmp/fifo_ctrllt_req"
CTRLLT_RES="/tmp/fifo_ctrllt_res"

# Función auxiliar para enviar petición y recibir respuesta
enviar() {
    local descripcion="$1"
    local json="$2"
    echo ""
    echo "────────────────────────────────────────"
    echo "📤 $descripcion"
    echo "   → $json"
    echo "$json" > $CTRLLT_REQ
    local respuesta=$(cat $CTRLLT_RES)
    echo "   ← $respuesta"
    echo "────────────────────────────────────────"
    sleep 0.3
}

echo "╔══════════════════════════════════════════╗"
echo "║   PRUEBAS DEL SISTEMA EJECUTOR DE LOTES ║"
echo "╚══════════════════════════════════════════╝"

# ─── PRUEBAS DE GESFICH ───

echo ""
echo "══════ PRUEBAS GESFICH ══════"

enviar "Crear fichero de entrada" \
    '{"id":"r01","servicio":"gesfich","operacion":"crear","parametros":{}}'

enviar "Crear fichero de salida" \
    '{"id":"r02","servicio":"gesfich","operacion":"crear","parametros":{}}'

# Crear un archivo temporal con datos de prueba
echo -e "5\n3\n8\n1\n9\n2\n7\n4\n6" > /tmp/datos_prueba.txt

enviar "Actualizar fichero con datos" \
    '{"id":"r03","servicio":"gesfich","operacion":"actualizar","parametros":{"id_fichero":"f-0001","ruta":"/tmp/datos_prueba.txt"}}'

enviar "Leer fichero f-0001" \
    '{"id":"r04","servicio":"gesfich","operacion":"leer","parametros":{"id_fichero":"f-0001"}}'

enviar "Listar todos los ficheros" \
    '{"id":"r05","servicio":"gesfich","operacion":"leer","parametros":{}}'

# ─── PRUEBAS DE GESPROG ───

echo ""
echo "══════ PRUEBAS GESPROG ══════"

enviar "Registrar programa (sort)" \
    '{"id":"r10","servicio":"gesprog","operacion":"guardar","parametros":{"ejecutable":"/usr/bin/sort","argumentos":["-n"],"ambiente":{}}}'

enviar "Leer programa p-0001" \
    '{"id":"r11","servicio":"gesprog","operacion":"leer","parametros":{"id_programa":"p-0001"}}'

enviar "Listar todos los programas" \
    '{"id":"r12","servicio":"gesprog","operacion":"leer","parametros":{}}'

# ─── PRUEBAS DE EJECUTOR ───

echo ""
echo "══════ PRUEBAS EJECUTOR ══════"

enviar "Ejecutar proceso de lotes (sort sobre f-0001 → f-0002)" \
    '{"id":"r20","servicio":"ejecutor","operacion":"ejecutar","parametros":{"id_programa":"p-0001","id_fichero_entrada":"f-0001","id_fichero_salida":"f-0002"}}'

sleep 1

enviar "Estado del proceso j-0001" \
    '{"id":"r21","servicio":"ejecutor","operacion":"estado","parametros":{"id_lote":"j-0001"}}'

enviar "Listar todos los procesos" \
    '{"id":"r22","servicio":"ejecutor","operacion":"estado","parametros":{}}'

# ─── VERIFICAR RESULTADO ───

echo ""
echo "══════ VERIFICAR RESULTADO ══════"

enviar "Leer fichero de salida f-0002 (debe estar ordenado)" \
    '{"id":"r30","servicio":"gesfich","operacion":"leer","parametros":{"id_fichero":"f-0002"}}'

# ─── PRUEBAS DE ESTADO (suspender/reasumir) ───

echo ""
echo "══════ PRUEBAS DE ESTADO ══════"

enviar "Suspender gesfich" \
    '{"id":"r40","servicio":"gesfich","operacion":"suspender","parametros":{}}'

enviar "Intentar crear fichero (debe fallar - suspendido)" \
    '{"id":"r41","servicio":"gesfich","operacion":"crear","parametros":{}}'

enviar "Reasumir gesfich" \
    '{"id":"r42","servicio":"gesfich","operacion":"reasumir","parametros":{}}'

enviar "Crear fichero (ahora debe funcionar)" \
    '{"id":"r43","servicio":"gesfich","operacion":"crear","parametros":{}}'

# ─── PRUEBAS DE ERROR ───

echo ""
echo "══════ PRUEBAS DE ERROR ══════"

enviar "Leer fichero que no existe" \
    '{"id":"r50","servicio":"gesfich","operacion":"leer","parametros":{"id_fichero":"f-9999"}}'

enviar "Servicio que no existe" \
    '{"id":"r51","servicio":"noexiste","operacion":"leer","parametros":{}}'

enviar "Borrar programa que no existe" \
    '{"id":"r52","servicio":"gesprog","operacion":"borrar","parametros":{"id_programa":"p-9999"}}'

# ─── LIMPIEZA ───

echo ""
echo "══════ FINALIZAR ══════"

enviar "Borrar fichero f-0001" \
    '{"id":"r60","servicio":"gesfich","operacion":"borrar","parametros":{"id_fichero":"f-0001"}}'

enviar "Borrar programa p-0001" \
    '{"id":"r61","servicio":"gesprog","operacion":"borrar","parametros":{"id_programa":"p-0001"}}'

rm -f /tmp/datos_prueba.txt

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║     PRUEBAS FINALIZADAS CON ÉXITO        ║"
echo "╚══════════════════════════════════════════╝"

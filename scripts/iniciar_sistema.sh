#!/bin/bash
# Iniciar todo el sistema Ejecutor de Lotes
# Ejecutar desde la raíz del proyecto: bash scripts/iniciar_sistema.sh

PROYECTO_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROYECTO_DIR"

echo "========================================="
echo "  EJECUTOR DE LOTES - Iniciando sistema"
echo "========================================="

# Preparar directorios
mkdir -p aralmac/ficheros aralmac/programas aralmac/estado

# Limpiar FIFOs previos
bash scripts/limpiar.sh

# Definir nombres de FIFOs
CTRLLT_REQ="/tmp/fifo_ctrllt_req"
CTRLLT_RES="/tmp/fifo_ctrllt_res"
GESFICH_REQ="/tmp/fifo_gesfich_req"
GESFICH_RES="/tmp/fifo_gesfich_res"
GESPROG_REQ="/tmp/fifo_gesprog_req"
GESPROG_RES="/tmp/fifo_gesprog_res"
EJECUTOR_REQ="/tmp/fifo_ejecutor_req"
EJECUTOR_RES="/tmp/fifo_ejecutor_res"
ARALMAC="./aralmac"

echo ""
echo "[1/4] Iniciando gesfich..."
python3 src/gesfich/gesfich.py -f $GESFICH_REQ -b $GESFICH_RES -x $ARALMAC &
PID_GESFICH=$!
sleep 0.5

echo "[2/4] Iniciando gesprog..."
python3 src/gesprog/gesprog.py -p $GESPROG_REQ -c $GESPROG_RES -x $ARALMAC &
PID_GESPROG=$!
sleep 0.5

echo "[3/4] Iniciando ejecutor..."
python3 src/ejecutor/ejecutor.py -e $EJECUTOR_REQ -d $EJECUTOR_RES -x $ARALMAC &
PID_EJECUTOR=$!
sleep 0.5

echo "[4/4] Iniciando ctrllt..."
python3 src/ctrllt/ctrllt.py \
    -c $CTRLLT_REQ -a $CTRLLT_RES \
    -f $GESFICH_REQ -b $GESFICH_RES \
    -p $GESPROG_REQ -q $GESPROG_RES \
    -e $EJECUTOR_REQ -d $EJECUTOR_RES &
PID_CTRLLT=$!
sleep 0.5

echo ""
echo "========================================="
echo "  Sistema iniciado correctamente"
echo "========================================="
echo "  PIDs:"
echo "    gesfich:  $PID_GESFICH"
echo "    gesprog:  $PID_GESPROG"
echo "    ejecutor: $PID_EJECUTOR"
echo "    ctrllt:   $PID_CTRLLT"
echo ""
echo "  FIFO del cliente: $CTRLLT_REQ / $CTRLLT_RES"
echo ""
echo "  Para probar: bash tests/test_client.sh"
echo "  Para detener: kill $PID_CTRLLT $PID_GESFICH $PID_GESPROG $PID_EJECUTOR"
echo "========================================="

# Esperar a que todos terminen
wait

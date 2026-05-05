# Ejecutor de Lotes

Sistema de ejecución de procesos por lotes usando tuberías nombradas (FIFOs).

## Requisitos
- Linux (o WSL)
- Python 3.8+

## Ejecución rápida

```bash
# 1. Preparar almacenamiento
mkdir -p aralmac/ficheros aralmac/programas aralmac/estado

# 2. Iniciar servicios (cada uno en una terminal diferente)
python3 src/gesfich/gesfich.py -f /tmp/fifo_gesfich_req -b /tmp/fifo_gesfich_res -x ./aralmac
python3 src/gesprog/gesprog.py -p /tmp/fifo_gesprog_req -c /tmp/fifo_gesprog_res -x ./aralmac
python3 src/ejecutor/ejecutor.py -e /tmp/fifo_ejecutor_req -d /tmp/fifo_ejecutor_res -x ./aralmac
python3 src/ctrllt/ctrllt.py -c /tmp/fifo_ctrllt_req -a /tmp/fifo_ctrllt_res \
  -f /tmp/fifo_gesfich_req -b /tmp/fifo_gesfich_res \
  -p /tmp/fifo_gesprog_req -q /tmp/fifo_gesprog_res \
  -e /tmp/fifo_ejecutor_req -d /tmp/fifo_ejecutor_res

# 3. Ejecutar pruebas
bash tests/test_client.sh
```

## Estructura
ejecutor-lotes/
├── docs/Diseño.md
├── src/
│   ├── common/protocolo.py
│   ├── ctrllt/ctrllt.py
│   ├── gesfich/gesfich.py
│   ├── gesprog/gesprog.py
│   └── ejecutor/ejecutor.py
├── tests/test_client.sh
└── aralmac/

## Autor Samuel Santamaria

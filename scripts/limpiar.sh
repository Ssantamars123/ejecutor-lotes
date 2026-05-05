#!/bin/bash
echo "Limpiando FIFOs..."
rm -f /tmp/fifo_ctrllt_req /tmp/fifo_ctrllt_res
rm -f /tmp/fifo_gesfich_req /tmp/fifo_gesfich_res
rm -f /tmp/fifo_gesprog_req /tmp/fifo_gesprog_res
rm -f /tmp/fifo_ejecutor_req /tmp/fifo_ejecutor_res
echo "Limpiando aralmac..."
rm -rf aralmac/ficheros/* aralmac/programas/* aralmac/estado/*
echo "Listo."

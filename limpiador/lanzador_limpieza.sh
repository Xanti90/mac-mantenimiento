#!/bin/bash
# Lanzador inteligente del limpiador de Mac
# Se ejecuta al arrancar y cada domingo a las 10:00 AM
# En modo --auto solo limpia si hay más de 2 GB de basura

SCRIPT="/Users/santiagojimeneztellez/Projects/sistema/mac-mantenimiento/limpiador/limpiar_mac.py"
MARCA="/tmp/limpiar_mac_ultima_vez.txt"
HOY=$(date +%Y-%m-%d)

# Evitar doble ejecución en el mismo día
if [ -f "$MARCA" ] && [ "$(cat $MARCA)" = "$HOY" ]; then
    exit 0
fi

/usr/bin/python3 "$SCRIPT" --auto
echo "$HOY" > "$MARCA"

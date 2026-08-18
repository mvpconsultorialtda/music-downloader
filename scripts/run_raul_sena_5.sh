#!/bin/bash
# Script: run_raul_sena_5.sh
# Objetivo: Baixar 20 novos videos do Raul Sena (Investidor Sardinha) com temas diferentes - 2025
# Data: 29/04/2026

cd "$(dirname "$0")/.." || exit 1

echo "=== Download Raul Sena - Batch 5 - 20 novos temas ==="
echo "Output: output/raul_sena_2025_new/"
echo "Filtro: ano 2025, canal Investidor Sardinha l Raul Sena"
echo ""

py -u download_music.py 2>&1 | tee scripts/output_raul_sena_5.log

echo ""
echo "=== Download concluido. Verificando novos arquivos ==="
ls -1 output/raul_sena_2025_new/ | tail -30

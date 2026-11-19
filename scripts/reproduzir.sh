#!/usr/bin/env bash
# Reproduz toda a análise a partir das saídas dos modelos já gravadas em resultados/.
# Uso, na raiz do repositório:   bash scripts/reproduzir.sh
# Requer o uv (https://docs.astral.sh/uv/). Na primeira execução o tiktoken baixa o tokenizador.
set -euo pipefail
cd "$(dirname "$0")/.."

PY="uv run --with tiktoken --with matplotlib --with python-docx python"
MODELO="Anexo I - MODELO ARTIGO FORMATADO - ABRIR EM WORD 2013 OU MAIS ATUALIZADO.docx"

echo "== 1. Métricas com o gabarito original e com o revisado"
$PY scripts/calcular_metricas_v2.py --saida resultados/v2_pre
$PY scripts/calcular_metricas_v2.py --base datasets/dataset_erros_gramaticais_revisado.csv --saida resultados/v2_pos
$PY scripts/comparar_pre_pos.py

echo "== 2. Análise dos falsos positivos (usa a anotação em datasets/revisao/fp_amostra.csv)"
$PY scripts/amostra_falsos_positivos.py calcular

echo "== 3. Figuras"
$PY scripts/gerar_fluxo_metodologico.py
$PY scripts/gerar_figuras_v2.py resultados/v2_pre figuras pre
$PY scripts/gerar_figuras_v2.py resultados/v2_pos figuras pos

echo "== 4. Artigo"
$PY scripts/gerar_rascunho_artigo.py "$MODELO" TCC_artigo.docx
echo "Pronto: TCC_artigo.docx"

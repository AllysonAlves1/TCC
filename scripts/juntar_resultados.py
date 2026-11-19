#!/usr/bin/env python3
"""Junta os CSVs de resultado de um modelo (um por lote) em um unico arquivo.

Convencao esperada:
    resultados/<modelo>/lote_001.csv
    resultados/<modelo>/lote_002.csv
    ...
Saida:
    resultados/dataset_erros_gramaticais_<modelo>.csv

Os arquivos de lote usam ';' como delimitador (sem cabecalho).
O arquivo final tambem usa ';'.

Uso:
    python scripts/juntar_resultados.py gpt-4o
    python scripts/juntar_resultados.py claude-sonnet --origem caminho/para/lotes
"""
import argparse
import csv
import glob
import os
import re


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("modelo", help="Nome do modelo (ex.: gpt-4o, claude-sonnet)")
    ap.add_argument("--origem", default=None,
                    help="Pasta com os CSVs de resultado do modelo "
                         "(default: resultados/<modelo>/)")
    ap.add_argument("--destino", default="resultados")
    ap.add_argument("--padrao", default="lote_*.csv")
    args = ap.parse_args()

    origem = args.origem or os.path.join(args.destino, args.modelo)
    os.makedirs(args.destino, exist_ok=True)

    files = glob.glob(os.path.join(origem, args.padrao))
    if not files:
        raise SystemExit(f"Nenhum arquivo encontrado em '{origem}' (padrao: {args.padrao})")

    def sort_key(p):
        m = re.search(r"lote_(\d+)", os.path.basename(p))
        return int(m.group(1)) if m else 0

    files.sort(key=sort_key)

    all_rows = []
    for fp in files:
        with open(fp, newline="", encoding="utf-8") as f:
            reader = csv.reader(f, delimiter=";")
            for row in reader:
                if not row:
                    continue
                # pula linhas que sejam cabecalho repetido
                if row and row[0].strip().lower() == "id":
                    continue
                all_rows.append(row)

    if not all_rows:
        raise SystemExit("Nenhum dado encontrado nos arquivos.")

    out = os.path.join(args.destino, f"dataset_erros_gramaticais_{args.modelo}.csv")
    with open(out, "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, delimiter=";", quoting=csv.QUOTE_MINIMAL)
        w.writerows(all_rows)

    print(f"Juntados {len(files)} lotes ({len(all_rows)} linhas) -> {out}")


if __name__ == "__main__":
    main()

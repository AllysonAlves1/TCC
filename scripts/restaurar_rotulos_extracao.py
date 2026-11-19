#!/usr/bin/env python3
"""Restaura categoria_extracao e subcategoria_extracao com os rótulos originais do LanguageTool.

Algumas frases do dataset ficaram com essas colunas sobrescritas por uma classificação
manual antiga (ex.: "Morfologia / Verbo (tempos, ...)"). Este script procura cada uma
na extração bruta (pelo par frase incorreta + frase correta e, se não achar, só pela
frase incorreta) e grava um NOVO arquivo; o original e as colunas do revisor não mudam.

Uso (na raiz do TCC):
    python scripts/restaurar_rotulos_extracao.py datasets/dataset_erros_gramaticais.csv \
        datasets/extracao_bruta_2026-11-18.csv datasets/dataset_erros_gramaticais_rotulos_lt.csv
"""
import csv
import re
import sys

base, bruto, saida = sys.argv[1:4]
limpar_cat = lambda c: re.sub(r"^[^\wÀ-ÿ]+", "", c).strip()  # remove emoji do início ("❓ Confusão...")

b = list(csv.DictReader(open(bruto, encoding="utf-8"), delimiter=";"))
ids_lt = {x["subcategoria_extracao"] for x in b}
por_par = {(x["Frase incorreta"], x["Frase correta"]): x for x in b}
por_frase = {}
for x in b:
    por_frase.setdefault(x["Frase incorreta"], x)

linhas = list(csv.DictReader(open(base, encoding="utf-8"), delimiter=";"))
restauradas, nao_achadas = 0, []
for i, r in enumerate(linhas, 1):
    if r["subcategoria_extracao"] in ids_lt:
        continue  # já tem o rótulo original
    achado = por_par.get((r["Frase incorreta"], r["Frase correta"])) or por_frase.get(r["Frase incorreta"])
    if achado:
        r["categoria_extracao"] = limpar_cat(achado["categoria_extracao"])
        r["subcategoria_extracao"] = achado["subcategoria_extracao"]
        restauradas += 1
    else:
        nao_achadas.append((i, r["Frase incorreta"], r["subcategoria_extracao"]))

with open(saida, "w", newline="", encoding="utf-8") as f:
    w = csv.DictWriter(f, fieldnames=list(linhas[0].keys()), delimiter=";")
    w.writeheader()
    w.writerows(linhas)
print(f"{restauradas} linhas restauradas; {len(nao_achadas)} não encontradas na extração bruta -> {saida}")
for i, frase, rot in nao_achadas:
    print(f"  id {i}: {frase} | rótulo atual: {rot}")

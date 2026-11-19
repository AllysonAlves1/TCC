#!/usr/bin/env python3
"""Compara a classificação antes e depois da revisão do gabarito.

Além da acurácia pré e pós, calcula a acurácia nas frases que a revisão NÃO tocou
(fora da planilha de revisão). Como a revisão foi feita justamente onde os modelos
discordavam do gabarito, esse subconjunto dá uma estimativa sem o efeito da revisão.

Uso (na raiz do TCC):
    python scripts/comparar_pre_pos.py
"""
import csv
import glob
import os
import sys

sys.path.insert(0, os.path.dirname(__file__))
import calcular_metricas_v2 as cm  # noqa: E402

PRE = "datasets/dataset_erros_gramaticais.csv"
POS = "datasets/dataset_erros_gramaticais_revisado.csv"
PLANILHA = "datasets/revisao/revisao_frases.csv"
SAIDA = "resultados/comparacao_pre_pos.csv"

with open(cm.ARQUIVO_EXCLUIDOS, newline="", encoding="utf-8-sig") as f:
    fora = set(cm.EXCLUIR_IDS_PADRAO) | {int(r["id"]) for r in csv.DictReader(f, delimiter=";")}
with open(PLANILHA, newline="", encoding="utf-8-sig") as f:
    revisadas = {int(r["id"]) for r in csv.DictReader(f, delimiter=";")}

pre = [b for b in cm.ler_base(PRE) if b.id not in fora]
pos = [b for b in cm.ler_base(POS) if b.id not in fora]
linhas = []
for arq in sorted(glob.glob("resultados/" + cm.PREFIXO + "*.csv")):
    m = cm.nome_modelo(arq)
    if m in cm.EXCLUIR_PADRAO:
        continue
    saida = cm.ler_modelo(arq)
    fpre = [cm.avaliar_frase(b, saida.get(b.id)) for b in pre]
    fpos = [cm.avaliar_frase(b, saida.get(b.id)) for b in pos]
    nr = [x for x in fpos if x.id not in revisadas]
    acc = lambda fr, k: sum(getattr(x, k) for x in fr) / len(fr)
    linhas.append({"modelo": m,
                   "acc_cat_pre": acc(fpre, "cat_ok"), "acc_cat_pos": acc(fpos, "cat_ok"),
                   "acc_sub_pre": acc(fpre, "sub_ok"), "acc_sub_pos": acc(fpos, "sub_ok"),
                   "acc_cat_nao_revisadas": acc(nr, "cat_ok"), "acc_sub_nao_revisadas": acc(nr, "sub_ok"),
                   "n_nao_revisadas": len(nr)})
linhas.sort(key=lambda r: -r["acc_sub_nao_revisadas"])
cm.salvar_csv(SAIDA, linhas)
for r in linhas:
    print(f"{r['modelo']:20s} sub pre {r['acc_sub_pre']:.3f} pos {r['acc_sub_pos']:.3f} "
          f"nao-revisadas {r['acc_sub_nao_revisadas']:.3f} (n={r['n_nao_revisadas']}) "
          f"| cat nao-revisadas {r['acc_cat_nao_revisadas']:.3f}")
print("->", SAIDA)

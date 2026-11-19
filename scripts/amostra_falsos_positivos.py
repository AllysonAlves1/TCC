#!/usr/bin/env python3
"""Analise de falsos positivos (FP): separa correcoes indevidas de alternativas validas.

Um FP e uma edicao do modelo que nao esta na referencia. Como ha uma unica referencia
por frase, parte dos FP pode ser correta. Este script tem duas etapas:

  gerar    sorteia uma amostra estratificada de FP por modelo e grava uma planilha CEGA
           (sem o nome do modelo) para anotacao manual, mais uma chave separada.
  calcular le a planilha anotada e calcula, por modelo, a proporcao de cada rotulo
           (IC de Wilson 95%) e a precisao ajustada.

Rotulos (coluna 'rotulo'):
  INDEVIDA        a edicao introduz erro, muda o sentido ou altera algo correto sem necessidade
  ALTERNATIVA     corrige o mesmo erro da referencia de outra forma, tambem correta
  ADICIONAL       corrige outro erro real da frase que a referencia nao marcou
  NEUTRA          mudanca opcional/estilistica, nem erro nem correcao (ex.: virgula facultativa)
  REF_ERRADA      a referencia e que esta errada; o modelo acertou

Uso:
  python scripts/amostra_falsos_positivos.py gerar --por-modelo 12
  (anotar datasets/revisao/fp_amostra.csv)
  python scripts/amostra_falsos_positivos.py calcular
"""
import argparse
import csv
import glob
import math
import os
import random
import sys
from collections import Counter, defaultdict

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from calcular_metricas_v2 import (EXCLUIR_IDS_PADRAO, EXCLUIR_PADRAO, ARQUIVO_EXCLUIDOS, PREFIXO,  # noqa: E402
                                  edicoes, ler_base, ler_modelo, nome_modelo, tokens)

ROTULOS = ["INDEVIDA", "ALTERNATIVA", "ADICIONAL", "NEUTRA", "REF_ERRADA"]
VALIDOS = {"ALTERNATIVA", "ADICIONAL", "REF_ERRADA"}  # contam como acerto na precisao ajustada
SEMENTE = 42
PASTA = "datasets/revisao"
AMOSTRA = os.path.join(PASTA, "fp_amostra.csv")
CHAVE = os.path.join(PASTA, "fp_chave.csv")


def ids_excluidos() -> set[int]:
    ids = set(EXCLUIR_IDS_PADRAO)
    if os.path.exists(ARQUIVO_EXCLUIDOS):
        with open(ARQUIVO_EXCLUIDOS, newline="", encoding="utf-8-sig") as f:
            ids |= {int(r["id"]) for r in csv.DictReader(f, delimiter=";") if r.get("id", "").strip()}
    return ids


def trecho(toks: list[str], i1: int, i2: int) -> str:
    return " ".join(toks[i1:i2]) or "∅"


def descrever(origem: list[str], e: tuple) -> str:
    i1, i2, novo = e
    antes, depois = trecho(origem, i1, i2), " ".join(novo) or "∅"
    ctx_esq = " ".join(origem[max(0, i1 - 3):i1])
    ctx_dir = " ".join(origem[i2:i2 + 3])
    return f"…{ctx_esq} [{antes} → {depois}] {ctx_dir}…".replace("  ", " ")


def gerar(args) -> None:
    if os.path.exists(AMOSTRA) and not args.forcar:
        with open(AMOSTRA, newline="", encoding="utf-8-sig") as f:
            feitos = sum(1 for r in csv.DictReader(f, delimiter=";") if r.get("rotulo", "").strip())
        if feitos:
            raise SystemExit(f"{AMOSTRA} ja tem {feitos} itens anotados; nao vou sobrescrever. "
                             "Use --forcar para gerar de novo (perde a anotacao).")
    fora = ids_excluidos()
    base = {b.id: b for b in ler_base(args.base) if b.id not in fora}
    arquivos = sorted(glob.glob(os.path.join("resultados", PREFIXO + "*.csv")))
    arquivos = [a for a in arquivos if nome_modelo(a) not in set(EXCLUIR_PADRAO)]
    rng = random.Random(SEMENTE)
    itens, totais = [], []
    for arq in arquivos:
        m = nome_modelo(arq)
        saida = ler_modelo(arq)
        fps = []
        for i, b in base.items():
            r = saida.get(i)
            if not r or len(r) < 3:
                continue
            origem = tokens(b.incorreta)
            g = edicoes(origem, tokens(b.correta))
            for e in sorted(edicoes(origem, tokens(r[2])) - g):
                fps.append((i, e, r[2]))
        totais.append({"modelo": m, "fp_total": len(fps)})
        for i, e, saida_txt in rng.sample(fps, min(args.por_modelo, len(fps))):
            b = base[i]
            itens.append({"modelo": m, "id": i, "frase_incorreta": b.incorreta,
                          "frase_referencia": b.correta, "saida_modelo": saida_txt,
                          "edicao_modelo": descrever(tokens(b.incorreta), e),
                          "subcategoria_ref": b.subcategoria})
    rng.shuffle(itens)  # mistura os modelos: a anotacao fica cega
    os.makedirs(PASTA, exist_ok=True)
    with open(AMOSTRA, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["item", "id", "frase_incorreta", "frase_referencia", "saida_modelo", "edicao_modelo",
                    "subcategoria_ref", "rotulo", "justificativa", "fonte_gramatica"])
        for n, it in enumerate(itens, 1):
            w.writerow([n, it["id"], it["frase_incorreta"], it["frase_referencia"], it["saida_modelo"],
                        it["edicao_modelo"], it["subcategoria_ref"], "", "", ""])
    with open(CHAVE, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["item", "modelo"])
        for n, it in enumerate(itens, 1):
            w.writerow([n, it["modelo"]])
    with open(os.path.join(PASTA, "fp_totais.csv"), "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=["modelo", "fp_total"], delimiter=";")
        w.writeheader()
        w.writerows(totais)
    print(f"{len(itens)} edicoes sorteadas de {len(arquivos)} modelos -> {AMOSTRA}")
    print(f"Chave (nao abrir durante a anotacao) -> {CHAVE}")
    print("Rotulos validos: " + ", ".join(ROTULOS))


def wilson(k: int, n: int, z: float = 1.96) -> tuple[float, float, float]:
    if n == 0:
        return 0.0, 0.0, 0.0
    p = k / n
    den = 1 + z * z / n
    centro = (p + z * z / (2 * n)) / den
    meia = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, max(0.0, centro - meia), min(1.0, centro + meia)


def br(x: float, c: int = 3) -> str:
    return f"{x:.{c}f}".replace(".", ",")


def calcular(args) -> None:
    with open(CHAVE, newline="", encoding="utf-8-sig") as f:
        chave = {int(r["item"]): r["modelo"] for r in csv.DictReader(f, delimiter=";")}
    with open(AMOSTRA, newline="", encoding="utf-8-sig") as f:
        linhas = list(csv.DictReader(f, delimiter=";"))
    erros = [r["item"] for r in linhas if r["rotulo"].strip().upper() not in ROTULOS]
    if erros:
        raise SystemExit(f"Itens sem rotulo valido ({len(erros)}): {', '.join(erros[:20])} ...")
    por_modelo: dict[str, Counter] = defaultdict(Counter)
    for r in linhas:
        por_modelo[chave[int(r["item"])]][r["rotulo"].strip().upper()] += 1
    # TP/FP de cada modelo vem das metricas oficiais.
    import json
    met = json.load(open(args.metricas, encoding="utf-8"))
    tpfp = {r["modelo"]: (r["TP"], r["FP"], r["P"]) for r in met["resumo"]}

    saida = []
    geral = Counter()
    for m, cont in sorted(por_modelo.items()):
        geral.update(cont)
        n = sum(cont.values())
        k_val = sum(cont[x] for x in VALIDOS)
        p_val, lo, hi = wilson(k_val, n)
        tp, fp, p = tpfp[m]
        p_aj = (tp + fp * p_val) / (tp + fp) if tp + fp else p
        linha = {"modelo": m, "n_amostra": n, **{x: cont[x] for x in ROTULOS},
                 "prop_validas": br(p_val), "ic_inf": br(lo), "ic_sup": br(hi),
                 "P_original": br(p), "P_ajustada": br(p_aj),
                 "P_ajustada_inf": br((tp + fp * lo) / (tp + fp)), "P_ajustada_sup": br((tp + fp * hi) / (tp + fp))}
        saida.append(linha)
    n = sum(geral.values())
    os.makedirs(args.saida, exist_ok=True)
    arq = os.path.join(args.saida, "falsos_positivos.csv")
    with open(arq, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(saida[0]), delimiter=";")
        w.writeheader()
        w.writerows(saida)
    print(f"Total anotado: {n}")
    for x in ROTULOS:
        p, lo, hi = wilson(geral[x], n)
        print(f"  {x:12s} {geral[x]:4d}  {br(p * 100, 1)}%  (IC95% {br(lo * 100, 1)}–{br(hi * 100, 1)}%)")
    print(f"Por modelo -> {arq}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    sub = ap.add_subparsers(dest="etapa")
    g = sub.add_parser("gerar")
    g.add_argument("--base", default="datasets/dataset_erros_gramaticais_revisado.csv")
    g.add_argument("--por-modelo", type=int, default=12)
    g.add_argument("--forcar", action="store_true", help="sobrescreve uma amostra ja anotada")
    c = sub.add_parser("calcular")
    c.add_argument("--metricas", default="resultados/v2_pos/metricas.json")
    c.add_argument("--saida", default="resultados/v2_pos")
    args = ap.parse_args()
    if not args.etapa:
        print(__doc__)
        if os.path.exists(AMOSTRA):
            with open(AMOSTRA, newline="", encoding="utf-8-sig") as f:
                linhas = list(csv.DictReader(f, delimiter=";"))
            feitos = sum(1 for r in linhas if r.get("rotulo", "").strip())
            print(f"Situacao: {AMOSTRA} tem {feitos} de {len(linhas)} itens anotados.")
            print("Proximo passo: " + ("anotar a planilha." if feitos < len(linhas) else
                                       "python scripts/amostra_falsos_positivos.py calcular"))
        else:
            print("Situacao: amostra ainda nao gerada. Rode: python scripts/amostra_falsos_positivos.py gerar")
        return
    gerar(args) if args.etapa == "gerar" else calcular(args)


if __name__ == "__main__":
    main()

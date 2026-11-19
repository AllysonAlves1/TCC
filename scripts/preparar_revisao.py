#!/usr/bin/env python3
"""Kit de revisao do gabarito (categoria/subcategoria) com registro auditavel.

Etapas (rodar a partir da raiz do projeto TCC):

  1) gerar      -> cria datasets/revisao/revisao_frases.csv com as frases em que
                   pelo menos 80% dos modelos concordam entre si numa subcategoria
                   diferente da do gabarito. Voce preenche as colunas de decisao.
  2) aplicar    -> le a planilha preenchida (decisao = MANTER, ALTERAR ou EXCLUIR),
                   valida contra a taxonomia, gera
                   datasets/dataset_erros_gramaticais_revisado.csv,
                   datasets/revisao/log_alteracoes.csv e
                   datasets/revisao/ids_excluidos.csv (frases que saem da avaliacao;
                   elas continuam no gabarito para nao mudar a numeracao dos ids).
  3) amostra    -> sorteia 50 frases ALTERADAS e cria a planilha cega do colega
                   (sem o seu rotulo e sem o dos modelos).
  4) concordancia -> compara a planilha do colega com os seus novos rotulos
                   (percentual de concordancia e kappa de Cohen).

Uso:
    python scripts/preparar_revisao.py gerar
    python scripts/preparar_revisao.py aplicar
    python scripts/preparar_revisao.py amostra
    python scripts/preparar_revisao.py concordancia
"""
from __future__ import annotations

import argparse
import collections
import csv
import glob
import os
import random
import sys

BASE = "datasets/dataset_erros_gramaticais.csv"
REVISADO = "datasets/dataset_erros_gramaticais_revisado.csv"
PASTA = "datasets/revisao"
PLANILHA = os.path.join(PASTA, "revisao_frases.csv")
LOG = os.path.join(PASTA, "log_alteracoes.csv")
EXCLUIDOS = os.path.join(PASTA, "ids_excluidos.csv")
AMOSTRA_COLEGA = os.path.join(PASTA, "amostra_colega_PREENCHER.csv")
CHAVE_AMOSTRA = os.path.join(PASTA, "amostra_colega_chave_NAO_ENVIAR.csv")
EXCLUIR = {"deepseek-v4-pro"}
IDS_EXCLUIDOS = {961, 982}  # frases corrompidas (fora da avaliacao)
LIMIAR = 0.8
TAMANHO_AMOSTRA = 50
SEMENTE = 2026

TAXONOMIA = {
    "Fonologia": ["Acentuação gráfica", "Ortografia", "Emprego do hífen", "Maiúsculas e minúsculas"],
    "Morfologia": ["Substantivo", "Verbo", "Adjetivo", "Locução adjetiva", "Pronome", "Artigo",
                   "Numeral", "Preposição", "Conjunção", "Locução conjuntiva", "Advérbio",
                   "Locução adverbial", "Classe de palavras", "Contração"],
    "Sintaxe": ["Concordância verbal", "Concordância nominal", "Regência verbal", "Regência nominal",
                "Colocação pronominal", "Pontuação", "Uso da crase", "Seleção Lexical", "Redundância"],
    "Semântica": ["Parônimo", "Homônimo", "Propriedade Vocabular"],
}


def norm(s: str | None) -> str:
    return " ".join(str(s or "").strip().lower().split())


CANON_CAT = {norm(c): c for c in TAXONOMIA}
CANON_SUB = {norm(s): (c, s) for c, subs in TAXONOMIA.items() for s in subs}


def ler_csv(path: str) -> list[dict]:
    with open(path, newline="", encoding="utf-8-sig") as f:
        return list(csv.DictReader(f, delimiter=";"))


def gravar_csv(path: str, linhas: list[dict], colunas: list[str]) -> None:
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    # utf-8-sig: abre com acentos corretos no Excel e no LibreOffice.
    with open(path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=colunas, delimiter=";", extrasaction="ignore")
        w.writeheader()
        w.writerows(linhas)


def ler_saidas_modelos() -> dict[str, dict[int, list[str]]]:
    saidas = {}
    for arq in sorted(glob.glob("resultados/dataset_erros_gramaticais_*.csv")):
        nome = os.path.basename(arq)[len("dataset_erros_gramaticais_"):-4]
        if nome in EXCLUIR:
            continue
        linhas: dict[int, list[str]] = {}
        with open(arq, newline="", encoding="utf-8") as f:
            for r in csv.reader(f, delimiter=";"):
                if r and r[0].strip().isdigit():
                    linhas.setdefault(int(r[0]), (r + [""] * 7)[:7])
        saidas[nome] = linhas
    return saidas


def gerar(_args) -> None:
    base = ler_csv(BASE)
    saidas = ler_saidas_modelos()
    n_modelos = len(saidas)
    linhas = []
    for i, b in enumerate(base, 1):
        if i in IDS_EXCLUIDOS:
            continue
        votos_sub = collections.Counter(norm(s[i][6]) for s in saidas.values() if i in s)
        votos_cat = collections.Counter(norm(s[i][5]) for s in saidas.values() if i in s)
        sub_top, n_top = votos_sub.most_common(1)[0]
        if n_top / n_modelos >= LIMIAR and sub_top != norm(b["subcategoria_revisor"]):
            cat_top, n_cat = votos_cat.most_common(1)[0]
            cat_sug = CANON_CAT.get(cat_top, cat_top)
            sub_sug = CANON_SUB.get(sub_top, (None, sub_top))[1]
            linhas.append({
                "id": i,
                "frase_incorreta": b["Frase incorreta"],
                "frase_correta": b["Frase correta"],
                "tokens_incorretos": b["lista_tokens_incorretos"],
                "tokens_corrigidos": b["lista_tokens_corrigidos"],
                "categoria_atual": b["categoria_revisor"],
                "subcategoria_atual": b["subcategoria_revisor"],
                "categoria_modelos": cat_sug,
                "votos_categoria": f"{n_cat}/{n_modelos}",
                "subcategoria_modelos": sub_sug,
                "votos_subcategoria": f"{n_top}/{n_modelos}",
                "decisao": "",
                "categoria_nova": "",
                "subcategoria_nova": "",
                "justificativa": "",
                "fonte_gramatica": "",
            })
    if os.path.exists(PLANILHA):  # preserva o que já foi preenchido
        anteriores = {r["id"]: r for r in ler_csv(PLANILHA)}
        for l in linhas:
            antigo = anteriores.get(str(l["id"]), {})
            for c in ("decisao", "categoria_nova", "subcategoria_nova", "justificativa", "fonte_gramatica"):
                if antigo.get(c):
                    l[c] = antigo[c]
    colunas = list(linhas[0].keys()) if linhas else []
    gravar_csv(PLANILHA, linhas, colunas)
    print(f"{len(linhas)} frases para revisar em {PLANILHA}")
    print("Preencha 'decisao' com MANTER ou ALTERAR. Em ALTERAR, preencha categoria_nova, "
          "subcategoria_nova, justificativa e fonte_gramatica.")
    print("Decisões já preenchidas numa planilha anterior foram mantidas.")


def aplicar(_args) -> None:
    base = ler_csv(BASE)
    plan = ler_csv(PLANILHA)
    erros, log, excluidos = [], [], []
    por_id = {}
    for r in plan:
        dec = norm(r.get("decisao"))
        if dec not in {"manter", "alterar", "excluir"}:
            erros.append(f"id {r['id']}: decisao vazia ou invalida ({r.get('decisao')!r}); "
                         "use MANTER, ALTERAR ou EXCLUIR")
            continue
        if dec == "manter":
            continue
        if dec == "excluir":
            if not r.get("justificativa", "").strip():
                erros.append(f"id {r['id']}: EXCLUIR exige justificativa (por que a frase sai do teste)")
                continue
            excluidos.append({"id": r["id"], "frase_incorreta": r["frase_incorreta"],
                              "frase_correta": r["frase_correta"], "justificativa": r["justificativa"],
                              "fonte_gramatica": r.get("fonte_gramatica", "")})
            continue
        sub = CANON_SUB.get(norm(r.get("subcategoria_nova")))
        if not sub:
            erros.append(f"id {r['id']}: subcategoria_nova fora da taxonomia ({r.get('subcategoria_nova')!r})")
            continue
        if norm(r.get("categoria_nova")) and CANON_CAT.get(norm(r["categoria_nova"])) != sub[0]:
            erros.append(f"id {r['id']}: categoria_nova nao corresponde a subcategoria ({sub[0]} esperado)")
            continue
        if not r.get("justificativa", "").strip() or not r.get("fonte_gramatica", "").strip():
            erros.append(f"id {r['id']}: ALTERAR exige justificativa e fonte_gramatica")
            continue
        por_id[int(r["id"])] = (sub, r)
    if erros:
        print("Corrija a planilha antes de aplicar:", *erros, sep="\n  ", file=sys.stderr)
        raise SystemExit(1)

    saida = []
    padronizadas = 0
    for i, b in enumerate(base, 1):
        b = dict(b)
        atual = CANON_SUB.get(norm(b["subcategoria_revisor"]))
        if atual and (b["categoria_revisor"], b["subcategoria_revisor"]) != atual:
            b["categoria_revisor"], b["subcategoria_revisor"] = atual  # so padroniza a grafia
            padronizadas += 1
        if i in por_id:
            (cat, sub), r = por_id[i]
            log.append({"id": i, "frase_incorreta": b["Frase incorreta"],
                        "categoria_antiga": r["categoria_atual"], "subcategoria_antiga": r["subcategoria_atual"],
                        "categoria_nova": cat, "subcategoria_nova": sub,
                        "justificativa": r["justificativa"], "fonte_gramatica": r["fonte_gramatica"]})
            b["categoria_revisor"], b["subcategoria_revisor"] = cat, sub
        saida.append(b)

    gravar_csv(REVISADO, saida, list(base[0].keys()))
    gravar_csv(LOG, log, ["id", "frase_incorreta", "categoria_antiga", "subcategoria_antiga",
                          "categoria_nova", "subcategoria_nova", "justificativa", "fonte_gramatica"])
    gravar_csv(EXCLUIDOS, excluidos, ["id", "frase_incorreta", "frase_correta", "justificativa", "fonte_gramatica"])
    print(f"{len(excluidos)} frases marcadas para EXCLUIR -> {EXCLUIDOS} "
          "(continuam no gabarito, mas o calcular_metricas_v2.py as tira da avaliacao)")
    print(f"{len(log)} rotulos alterados; {padronizadas} grafias padronizadas (ex.: 'Uso da Crase' -> 'Uso da crase').")
    print(f"Gabarito revisado: {REVISADO}\nLog: {LOG}")


def amostra(_args) -> None:
    log = ler_csv(LOG)
    if not log:
        raise SystemExit("Nenhuma alteracao no log; rode 'aplicar' primeiro.")
    base = ler_csv(BASE)
    rng = random.Random(SEMENTE)
    sorteio = rng.sample(log, min(TAMANHO_AMOSTRA, len(log)))
    rng.shuffle(sorteio)
    cega, chave = [], []
    for n, r in enumerate(sorteio, 1):
        b = base[int(r["id"]) - 1]
        cega.append({"item": n, "frase_incorreta": b["Frase incorreta"], "frase_correta": b["Frase correta"],
                     "tokens_incorretos": b["lista_tokens_incorretos"],
                     "tokens_corrigidos": b["lista_tokens_corrigidos"],
                     "categoria": "", "subcategoria": "", "comentario": ""})
        chave.append({"item": n, "id": r["id"], "subcategoria_antiga": r["subcategoria_antiga"],
                      "subcategoria_nova": r["subcategoria_nova"]})
    gravar_csv(AMOSTRA_COLEGA, cega, list(cega[0].keys()))
    gravar_csv(CHAVE_AMOSTRA, chave, list(chave[0].keys()))
    print(f"Envie ao colega apenas: {AMOSTRA_COLEGA} (+ a taxonomia).")
    print(f"Guarde sem enviar: {CHAVE_AMOSTRA}")


def kappa(a: list[str], b: list[str]) -> float:
    n = len(a)
    po = sum(x == y for x, y in zip(a, b)) / n
    ca, cb = collections.Counter(a), collections.Counter(b)
    pe = sum(ca[k] * cb.get(k, 0) for k in ca) / (n * n)
    return (po - pe) / (1 - pe) if pe < 1 else 1.0


def concordancia(_args) -> None:
    colega = {r["item"]: r for r in ler_csv(AMOSTRA_COLEGA)}
    chave = ler_csv(CHAVE_AMOSTRA)
    pares = [(norm(colega[c["item"]]["subcategoria"]), norm(c["subcategoria_nova"]), norm(c["subcategoria_antiga"]))
             for c in chave if norm(colega.get(c["item"], {}).get("subcategoria"))]
    if not pares:
        raise SystemExit("Planilha do colega ainda sem subcategorias preenchidas.")
    col, nova, antiga = zip(*pares)
    n = len(pares)
    print(f"Itens avaliados pelo colega: {n}")
    print(f"Colega concorda com o rotulo NOVO:   {sum(a == b for a, b in zip(col, nova)) / n:.1%}")
    print(f"Colega concorda com o rotulo ANTIGO: {sum(a == b for a, b in zip(col, antiga)) / n:.1%}")
    print(f"Kappa de Cohen (colega x rotulo novo): {kappa(list(col), list(nova)):.3f}")


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("etapa", choices=["gerar", "aplicar", "amostra", "concordancia"])
    args = ap.parse_args()
    {"gerar": gerar, "aplicar": aplicar, "amostra": amostra, "concordancia": concordancia}[args.etapa](args)


if __name__ == "__main__":
    main()

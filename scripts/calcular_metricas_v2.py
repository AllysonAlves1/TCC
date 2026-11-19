#!/usr/bin/env python3
"""Calcula as metricas da versao 2 do TCC (correcao gramatical em PT-BR).

Diferencas em relacao ao calcular_metricas.py:
- F0.5 por edicao (precisao, cobertura e F0.5), no estilo do M2 Scorer
  (Dahlmeier; Ng, 2012), com edicoes extraidas por alinhamento de tokens
  entre a frase incorreta e a frase corrigida.
- Acerto exato da frase corrigida.
- Classificacao: acuracia e F1-macro de categoria e de subcategoria.
- Intervalos de confianca de 95% por bootstrap (reamostragem de frases).
- Teste de McNemar (exato) entre os modelos de topo, com correcao de Holm.
- Desempenho por subcategoria (para o mapa de calor).
- Teste de integridade: percentual de linhas identicas ao gabarito.
- Estimativa de custo (opcional), se existir um arquivo de precos.
- Modelos excluidos por padrao: deepseek-v4-pro (saida identica ao gabarito).
- Frases excluidas por padrao: ids 961 e 982 (corrompidas no dataset; ver --excluir-ids)
  e as marcadas como EXCLUIR na revisao (datasets/revisao/ids_excluidos.csv).

Os CSVs saem com ';' como separador e ',' como decimal, para abrir
corretamente no LibreOffice/Excel em portugues. O JSON guarda os numeros
com ponto decimal e e a fonte de verdade para as tabelas do artigo.

Uso (a partir da raiz do projeto TCC):
    python scripts/calcular_metricas_v2.py
    python scripts/calcular_metricas_v2.py --base datasets/dataset_erros_gramaticais_revisado.csv --saida resultados/v2_pos
    python scripts/calcular_metricas_v2.py --precos scripts/precos.csv

Formato do arquivo de precos (opcional, ';' como separador, '.' decimal):
    modelo;entrada_usd_1M;saida_usd_1M;fonte;data_consulta
    beam;0.25;1.00;https://...;2026-11-18
"""
from __future__ import annotations

import argparse
import csv
import difflib
import glob
import json
import math
import os
import random
import re
import sys
from dataclasses import dataclass

PREFIXO = "dataset_erros_gramaticais_"
EXCLUIR_PADRAO = ["deepseek-v4-pro"]
# Frases corrompidas no dataset (ponto e vírgula sem aspas): os modelos receberam só
# "O relatório foi entregue". Ids = posição da linha no dataset (1 = primeira frase).
EXCLUIR_IDS_PADRAO = [961, 982]
# Frases que a revisao do gabarito marcou como EXCLUIR (gerado por preparar_revisao.py aplicar).
ARQUIVO_EXCLUIDOS = "datasets/revisao/ids_excluidos.csv"
BETA = 0.5
N_BOOTSTRAP = 1000
SEMENTE = 42
PALAVRAS_LIVRO = 80_000
MULTIPLICADORES_SAIDA = [1, 3, 10]
TOP_MCNEMAR = 6

TOKEN_RE = re.compile(r"\w+|[^\w\s]", re.UNICODE)


# ---------------------------------------------------------------------------
# Texto
# ---------------------------------------------------------------------------

def tokens(s: str | None) -> list[str]:
    """Tokeniza preservando maiusculas e pontuacao (ambas sao tipos de erro)."""
    return TOKEN_RE.findall(s or "")


def norm(s: str | None) -> str:
    return " ".join(str(s or "").strip().lower().split())


def edicoes(origem: list[str], destino: list[str]) -> set[tuple]:
    """Conjunto de edicoes (inicio, fim, substituicao) que levam origem a destino."""
    sm = difflib.SequenceMatcher(a=origem, b=destino, autojunk=False)
    return {(i1, i2, tuple(destino[j1:j2]))
            for op, i1, i2, j1, j2 in sm.get_opcodes() if op != "equal"}


def f_beta(tp: int, fp: int, fn: int, beta: float = BETA) -> tuple[float, float, float]:
    p = tp / (tp + fp) if tp + fp else 1.0
    r = tp / (tp + fn) if tp + fn else 1.0
    b2 = beta * beta
    f = (1 + b2) * p * r / (b2 * p + r) if (b2 * p + r) else 0.0
    return p, r, f


# ---------------------------------------------------------------------------
# Leitura
# ---------------------------------------------------------------------------

@dataclass
class Base:
    id: int
    incorreta: str
    correta: str
    categoria: str
    subcategoria: str
    token_incorreto: str
    token_correto: str


def delimitador(path: str) -> str:
    with open(path, encoding="utf-8-sig") as f:
        return ";" if ";" in f.readline() else ","


def campo(row: dict, *nomes: str) -> str:
    for n in nomes:
        if row.get(n):
            return row[n]
    return ""


def ler_base(path: str) -> list[Base]:
    # utf-8-sig: aceita arquivos com BOM (o gabarito revisado e gravado assim para abrir no Excel).
    with open(path, newline="", encoding="utf-8-sig") as f:
        rd = csv.DictReader(f, delimiter=delimitador(path))
        return [Base(i,
                     campo(r, "Frase incorreta", "frase incorreta"),
                     campo(r, "Frase correta", "frase correta"),
                     campo(r, "categoria_revisor", "categoria"),
                     campo(r, "subcategoria_revisor", "subcategoria"),
                     campo(r, "lista_tokens_incorretos", "token incorreto"),
                     campo(r, "lista_tokens_corrigidos", "token correto"))
                for i, r in enumerate(rd, 1)]


def ler_modelo(path: str) -> dict[int, list[str]]:
    saida: dict[int, list[str]] = {}
    with open(path, newline="", encoding="utf-8") as f:
        for r in csv.reader(f, delimiter=delimitador(path)):
            if not r or not r[0].strip().isdigit():
                continue
            i = int(r[0])
            if i not in saida:
                saida[i] = r
    return saida


def nome_modelo(path: str) -> str:
    return os.path.basename(path).replace(PREFIXO, "").replace(".csv", "")


# ---------------------------------------------------------------------------
# Avaliacao por frase
# ---------------------------------------------------------------------------

@dataclass
class Frase:
    id: int
    presente: bool
    formato_ok: bool
    tp: int
    fp: int
    fn: int
    exata: int
    cat_ok: int
    sub_ok: int
    linha_identica: int
    cat_pred: str
    sub_pred: str
    texto_saida: str


def avaliar_frase(b: Base, r: list[str] | None) -> Frase:
    origem, ouro = tokens(b.incorreta), tokens(b.correta)
    g = edicoes(origem, ouro)
    if r is None:
        return Frase(b.id, False, False, 0, 0, len(g), 0, 0, 0, 0, "", "", "")
    r7 = (r + [""] * 7)[:7]
    hip = tokens(r7[2])
    h = edicoes(origem, hip)
    tp = len(h & g)
    identica = int([x.strip() for x in r7[1:7]] ==
                   [b.incorreta.strip(), b.correta.strip(), b.token_incorreto.strip(),
                    b.token_correto.strip(), b.categoria.strip(), b.subcategoria.strip()])
    return Frase(
        id=b.id, presente=True, formato_ok=len(r) == 7,
        tp=tp, fp=len(h - g), fn=len(g - h),
        exata=int(hip == ouro),
        cat_ok=int(norm(r7[5]) == norm(b.categoria)),
        sub_ok=int(norm(r7[6]) == norm(b.subcategoria)),
        linha_identica=identica,
        cat_pred=norm(r7[5]), sub_pred=norm(r7[6]),
        texto_saida=r7[2] + " " + r7[3] + " " + r7[4] + " " + r7[5] + " " + r7[6],
    )


# ---------------------------------------------------------------------------
# Agregacao
# ---------------------------------------------------------------------------

def f1_macro(ouro: list[str], pred: list[str]) -> float:
    classes = sorted(set(ouro))
    f1s = []
    for c in classes:
        tp = sum(1 for o, p in zip(ouro, pred) if o == c and p == c)
        fp = sum(1 for o, p in zip(ouro, pred) if o != c and p == c)
        fn = sum(1 for o, p in zip(ouro, pred) if o == c and p != c)
        prec = tp / (tp + fp) if tp + fp else 0.0
        rec = tp / (tp + fn) if tp + fn else 0.0
        f1s.append(2 * prec * rec / (prec + rec) if prec + rec else 0.0)
    return sum(f1s) / len(f1s) if f1s else 0.0


def agregar(fr: list[Frase]) -> dict:
    tp = sum(x.tp for x in fr)
    fp = sum(x.fp for x in fr)
    fn = sum(x.fn for x in fr)
    p, r, f = f_beta(tp, fp, fn)
    n = len(fr)
    return {"P": p, "R": r, "F05": f,
            "Exata": sum(x.exata for x in fr) / n,
            "Acc_cat": sum(x.cat_ok for x in fr) / n,
            "Acc_sub": sum(x.sub_ok for x in fr) / n}


def bootstrap(fr: list[Frase], rng: random.Random, n: int = N_BOOTSTRAP) -> dict:
    chaves = ["F05", "Exata", "Acc_cat", "Acc_sub"]
    amostras = {k: [] for k in chaves}
    tam = len(fr)
    for _ in range(n):
        reamostra = [fr[rng.randrange(tam)] for _ in range(tam)]
        a = agregar(reamostra)
        for k in chaves:
            amostras[k].append(a[k])
    ic = {}
    for k, vals in amostras.items():
        vals.sort()
        ic[k + "_IC_inf"] = vals[int(0.025 * n)]
        ic[k + "_IC_sup"] = vals[int(0.975 * n) - 1]
    return ic


def mcnemar_exato(a: list[int], b: list[int]) -> tuple[int, int, float]:
    """Teste exato de McNemar (binomial bicaudal) sobre acertos por frase."""
    b01 = sum(1 for x, y in zip(a, b) if x == 1 and y == 0)
    b10 = sum(1 for x, y in zip(a, b) if x == 0 and y == 1)
    n = b01 + b10
    if n == 0:
        return b01, b10, 1.0
    k = min(b01, b10)
    p = 2 * sum(math.comb(n, i) for i in range(k + 1)) / 2 ** n
    return b01, b10, min(1.0, p)


def holm(pvals: list[float]) -> list[float]:
    ordem = sorted(range(len(pvals)), key=lambda i: pvals[i])
    ajust = [0.0] * len(pvals)
    acum = 0.0
    m = len(pvals)
    for pos, i in enumerate(ordem):
        acum = max(acum, min(1.0, (m - pos) * pvals[i]))
        ajust[i] = acum
    return ajust


# ---------------------------------------------------------------------------
# Custo
# ---------------------------------------------------------------------------

def contador_tokens():
    try:
        import tiktoken  # type: ignore
        enc = tiktoken.get_encoding("o200k_base")
        return (lambda s: len(enc.encode(s))), "tiktoken o200k_base"
    except Exception:
        return (lambda s: max(1, round(len(s) / 4))), "aproximacao 4 caracteres/token"


def ler_precos(path: str | None) -> dict[str, dict]:
    if not path or not os.path.exists(path):
        return {}
    with open(path, newline="", encoding="utf-8") as f:
        return {r["modelo"]: r for r in csv.DictReader(f, delimiter=";")}


def estimar_custo(base: list[Base], fr: list[Frase], prompt: str, preco: dict,
                  contar, tamanho_lote: int = 50) -> dict:
    """Custo de chamada direta a API: prompt uma vez por lote + frases; saida = linhas geradas."""
    n_lotes = math.ceil(len(base) / tamanho_lote)
    t_in = n_lotes * contar(prompt) + sum(contar(f"{b.id};{b.incorreta}") for b in base)
    t_out = sum(contar(x.texto_saida) for x in fr if x.presente)
    palavras = sum(len(b.incorreta.split()) for b in base)
    pin, pout = float(preco["entrada_usd_1M"]), float(preco["saida_usd_1M"])
    res = {"tokens_entrada": t_in, "tokens_saida": t_out,
           "fonte_preco": preco.get("fonte", ""), "data_preco": preco.get("data_consulta", "")}
    for mult in MULTIPLICADORES_SAIDA:
        custo = (t_in * pin + t_out * mult * pout) / 1e6
        res[f"custo_dataset_usd_x{mult}"] = custo
        res[f"custo_livro_usd_x{mult}"] = custo / palavras * PALAVRAS_LIVRO
    return res


# ---------------------------------------------------------------------------
# Saida
# ---------------------------------------------------------------------------

def fmt(v):
    if isinstance(v, float):
        return f"{v:.4f}".replace(".", ",")
    return v


def salvar_csv(path: str, linhas: list[dict]) -> None:
    if not linhas:
        return
    os.makedirs(os.path.dirname(path) or ".", exist_ok=True)
    colunas = list(dict.fromkeys(k for l in linhas for k in l))
    with open(path, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=colunas, delimiter=";", restval="")
        w.writeheader()
        for l in linhas:
            w.writerow({k: fmt(v) for k, v in l.items()})


def arred(d: dict) -> dict:
    return {k: (round(v, 4) if isinstance(v, float) else v) for k, v in d.items()}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("--base", default="datasets/dataset_erros_gramaticais.csv")
    ap.add_argument("--modelos", nargs="*", default=None)
    ap.add_argument("--excluir", nargs="*", default=EXCLUIR_PADRAO)
    ap.add_argument("--excluir-ids", nargs="*", type=int, default=EXCLUIR_IDS_PADRAO,
                    help="ids de frases a excluir da avaliacao (padrao: 961 982)")
    ap.add_argument("--arquivo-excluidos", default=ARQUIVO_EXCLUIDOS,
                    help="CSV com coluna id de frases excluidas na revisao (somado a --excluir-ids)")
    ap.add_argument("--saida", default="resultados/v2_pre")
    ap.add_argument("--prompt", default="scripts/prompt_padrao.txt")
    ap.add_argument("--precos", default="scripts/precos.csv")
    ap.add_argument("--bootstrap", type=int, default=N_BOOTSTRAP)
    args = ap.parse_args()

    ids_fora = set(args.excluir_ids)
    if args.arquivo_excluidos and os.path.exists(args.arquivo_excluidos):
        with open(args.arquivo_excluidos, newline="", encoding="utf-8-sig") as f:
            ids_fora |= {int(r["id"]) for r in csv.DictReader(f, delimiter=";") if r.get("id", "").strip()}
    args.excluir_ids = sorted(ids_fora)
    base = [b for b in ler_base(args.base) if b.id not in ids_fora]
    if not all(b.incorreta and b.correta for b in base):
        raise SystemExit("Colunas 'Frase incorreta'/'Frase correta' vazias: confira o cabecalho do --base.")
    print(f"Frases avaliadas: {len(base)} (excluidas: {', '.join(map(str, args.excluir_ids)) or 'nenhuma'})")
    padroes = args.modelos or [os.path.join("resultados", PREFIXO + "*.csv")]
    arquivos = sorted({p for pd in padroes for p in glob.glob(pd)})
    arquivos = [a for a in arquivos if nome_modelo(a) not in set(args.excluir)]
    if not arquivos:
        raise SystemExit("Nenhum arquivo de modelo encontrado.")

    rng = random.Random(SEMENTE)
    contar, tokenizador = contador_tokens()
    print(f"Contagem de tokens para o custo: {tokenizador}")
    prompt = open(args.prompt, encoding="utf-8").read() if os.path.exists(args.prompt) else ""
    precos = ler_precos(args.precos)

    resumos, por_sub, integridade, custos = [], [], [], []
    acertos_exatos: dict[str, list[int]] = {}
    # Agrupa subcategorias sem diferenciar maiusculas ("Uso da crase" == "Uso da Crase").
    nome_sub: dict[str, str] = {}
    for b in base:
        nome_sub.setdefault(norm(b.subcategoria), b.subcategoria.strip())
    subcats = sorted(nome_sub)

    for arq in arquivos:
        m = nome_modelo(arq)
        saida = ler_modelo(arq)
        fr = [avaliar_frase(b, saida.get(b.id)) for b in base]
        ag = agregar(fr)
        res = {"modelo": m,
               "cobertura": sum(x.presente for x in fr) / len(base),
               "taxa_formato": sum(x.formato_ok for x in fr) / len(base),
               "TP": sum(x.tp for x in fr), "FP": sum(x.fp for x in fr), "FN": sum(x.fn for x in fr),
               **ag,
               "F1macro_cat": f1_macro([norm(b.categoria) for b in base], [x.cat_pred for x in fr]),
               "F1macro_sub": f1_macro([norm(b.subcategoria) for b in base], [x.sub_pred for x in fr]),
               **bootstrap(fr, rng, args.bootstrap)}
        resumos.append(res)
        acertos_exatos[m] = [x.exata for x in fr]

        integridade.append({"modelo": m,
                            "linhas_identicas_gabarito": sum(x.linha_identica for x in fr) / len(base)})

        for s in subcats:
            sub_fr = [x for x, b in zip(fr, base) if norm(b.subcategoria) == s]
            a = agregar(sub_fr)
            por_sub.append({"modelo": m, "subcategoria": nome_sub[s], "n": len(sub_fr),
                            "F05": a["F05"], "Exata": a["Exata"], "Acc_sub": a["Acc_sub"]})

        if m in precos:
            custos.append({"modelo": m, **estimar_custo(base, fr, prompt, precos[m], contar)})

        print(f"{m:22s} F0.5={ag['F05']:.4f} P={ag['P']:.4f} R={ag['R']:.4f} "
              f"Exata={ag['Exata']:.4f} AccCat={ag['Acc_cat']:.4f} AccSub={ag['Acc_sub']:.4f}")

    resumos.sort(key=lambda r: r["F05"], reverse=True)

    topo = [r["modelo"] for r in resumos[:TOP_MCNEMAR]]
    pares = [(a, b) for i, a in enumerate(topo) for b in topo[i + 1:]]
    testes = [mcnemar_exato(acertos_exatos[a], acertos_exatos[b]) for a, b in pares]
    p_holm = holm([t[2] for t in testes])
    mcnemar = [{"modelo_A": a, "modelo_B": b, "so_A_acerta": t[0], "so_B_acerta": t[1],
                "p_valor": t[2], "p_holm": ph, "diferenca_significativa_5pct": ph < 0.05}
               for (a, b), t, ph in zip(pares, testes, p_holm)]

    os.makedirs(args.saida, exist_ok=True)
    salvar_csv(os.path.join(args.saida, "metricas.csv"), resumos)
    salvar_csv(os.path.join(args.saida, "por_subcategoria.csv"), por_sub)
    salvar_csv(os.path.join(args.saida, "mcnemar_topo.csv"), mcnemar)
    salvar_csv(os.path.join(args.saida, "integridade.csv"), integridade)
    salvar_csv(os.path.join(args.saida, "custo.csv"), custos)
    with open(os.path.join(args.saida, "metricas.json"), "w", encoding="utf-8") as f:
        json.dump({"base": args.base, "excluidos": args.excluir, "ids_excluidos": args.excluir_ids,
                   "n_frases": len(base), "bootstrap": args.bootstrap,
                   "semente": SEMENTE, "tokenizador_custo": tokenizador,
                   "palavras_livro": PALAVRAS_LIVRO,
                   "resumo": [arred(r) for r in resumos],
                   "por_subcategoria": [arred(r) for r in por_sub],
                   "mcnemar_topo": [arred(r) for r in mcnemar],
                   "integridade": [arred(r) for r in integridade],
                   "custo": [arred(r) for r in custos]}, f, ensure_ascii=False, indent=2)

    suspeitos = [i for i in integridade if i["linhas_identicas_gabarito"] > 0.6]
    for s in suspeitos:
        print(f"[ALERTA] {s['modelo']}: {s['linhas_identicas_gabarito']:.1%} das linhas "
              f"identicas ao gabarito (possivel vazamento)", file=sys.stderr)
    if not precos:
        print(f"[info] sem {args.precos}: custo nao calculado.", file=sys.stderr)
    print(f"\nArquivos gravados em {args.saida}/")


if __name__ == "__main__":
    main()

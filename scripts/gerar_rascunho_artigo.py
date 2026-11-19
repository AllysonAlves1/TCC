#!/usr/bin/env python3
"""Gera o rascunho do artigo no modelo do IFPE (Anexo I) a partir de resultados/v2_pos/metricas.json
(gabarito revisado), de resultados/v2_pre/metricas.json e de resultados/comparacao_pre_pos.csv."""
import copy
import json
import sys

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH, WD_COLOR_INDEX, WD_TAB_ALIGNMENT
from docx.oxml.ns import qn
from docx.oxml import OxmlElement
from docx.shared import Pt, Cm

MODELO = sys.argv[1]
SAIDA = sys.argv[2]
METRICAS = sys.argv[3] if len(sys.argv) > 3 else "resultados/v2_pos/metricas.json"
METRICAS_PRE = "resultados/v2_pre/metricas.json"
COMPARACAO = "resultados/comparacao_pre_pos.csv"
FIG = "figuras"

d = json.load(open(METRICAS, encoding="utf-8"))
RES = {r["modelo"]: r for r in d["resumo"]}
CUSTO = {c["modelo"]: c for c in d["custo"]}
PRE = {r["modelo"]: r for r in json.load(open(METRICAS_PRE, encoding="utf-8"))["resumo"]}
import csv as _csv
import math as _math
COMP = {r["modelo"]: {k: (float(v.replace(",", ".")) if k != "modelo" else v) for k, v in r.items()}
        for r in _csv.DictReader(open(COMPARACAO, encoding="utf-8"), delimiter=";")}
media = lambda vals: sum(vals) / len(vals)
_ROT = ["INDEVIDA", "ALTERNATIVA", "ADICIONAL", "NEUTRA", "REF_ERRADA"]
FP = {r["modelo"]: r for r in _csv.DictReader(open("resultados/v2_pos/falsos_positivos.csv", encoding="utf-8-sig"),
                                                delimiter=";")}
FP_N = sum(int(r["n_amostra"]) for r in FP.values())
FP_ROT = {k: sum(int(r[k]) for r in FP.values()) for k in _ROT}
_val = FP_ROT["ALTERNATIVA"] + FP_ROT["ADICIONAL"] + FP_ROT["REF_ERRADA"]
def _wilson(k, n, z=1.96):
    p = k / n; den = 1 + z * z / n
    c = (p + z * z / (2 * n)) / den; m = z * _math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / den
    return p, c - m, c + m
with open("datasets/revisao/fp_amostra.csv", encoding="utf-8-sig", newline="") as _f:
    _am = list(_csv.DictReader(_f, delimiter=";"))
FP_IDS = len({r["id"] for r in _am})
FP_IDS_REF = len({r["id"] for r in _am if r["rotulo"].strip().upper() == "REF_ERRADA"})
FP_INDEV_SENTIDO = sum(1 for r in _am if r["rotulo"].strip().upper() == "INDEVIDA"
                       and "sentido" in r["justificativa"].lower())
FP_NEUTRA_MAIUSC = sum(1 for r in _am if r["rotulo"].strip().upper() == "NEUTRA"
                       and "maiúscula" in r["justificativa"].lower())
N_AVAL = d["n_frases"]
_cx = lambda m, k="custo_livro_usd_x1": CUSTO[m][k]
C_MIN, C_MAX = min(c["custo_livro_usd_x1"] for c in CUSTO.values()), max(c["custo_livro_usd_x1"] for c in CUSTO.values())
LIMITE_MAX = _math.ceil(C_MAX)  # "menos de US$ N" com qualquer modelo
LIMITE_MIMO = _math.ceil(_cx("MiMo-V2.6-Pro"))
RAZAO_SONNET_MIMO = _cx("claude-sonnet-5.5") / _cx("MiMo-V2.6-Pro")
usd_en = lambda v: f"{v:.2f}"
extenso = {1: "um dólar", 2: "dois dólares", 3: "três dólares", 4: "quatro dólares", 5: "cinco dólares"}
extenso_en = {1: "one dollar", 2: "two dollars", 3: "three dollars", 4: "four dollars", 5: "five dollars"}


def br(x, c=3):
    return f"{x:.{c}f}".replace(".", ",")


def pct(x, c=1):
    return f"{100 * x:.{c}f}".replace(".", ",") + "%"


doc = Document(MODELO)
P = doc.paragraphs
T_BODY, T_H1, T_H2, T_H3 = P[23], P[22], P[44], P[46]
T_CAP, T_FONTE, T_REF = P[36], P[38], P[74]
T_CENTER = P[37]
pPr = lambda p: copy.deepcopy(p._p.pPr) if p._p.pPr is not None else None
MOLDES = {k: pPr(v) for k, v in dict(body=T_BODY, h1=T_H1, h2=T_H2, h3=T_H3, cap=T_CAP,
                                     fonte=T_FONTE, ref=T_REF, center=T_CENTER).items()}


def set_text(p, text, bold=None, size=None):
    for r in p.runs[1:]:
        r._r.getparent().remove(r._r)
    if p.runs:
        p.runs[0].text = text
        if bold is not None:
            p.runs[0].bold = bold
        if size:
            p.runs[0].font.size = Pt(size)
    else:
        r = p.add_run(text)
        r.bold = bold
        if size:
            r.font.size = Pt(size)


# ---- Cabecalho (paragrafos 0-21 do modelo) ----
set_text(P[1], "MODELOS DE LINGUAGEM DE GRANDE ESCALA NA REVISÃO GRAMATICAL DO PORTUGUÊS BRASILEIRO: "
         "uma avaliação comparativa de qualidade e custo", True, 16)
set_text(P[2], "LARGE LANGUAGE MODELS FOR GRAMMATICAL REVISION OF BRAZILIAN PORTUGUESE: "
         "a comparative evaluation of quality and cost", None, 14)
set_text(P[3], "[Nome completo do autor]", True)
set_text(P[4], "[e-mail do autor]")
set_text(P[5], "", True)
set_text(P[6], "")
set_text(P[7], "[Nome do orientador]", True)
set_text(P[8], "[e-mail do orientador]")
for i in (3, 4, 7, 8):
    for r in P[i].runs:
        r.font.highlight_color = WD_COLOR_INDEX.YELLOW

RESUMO = (
    "A revisão gramatical de textos longos, como livros, é uma etapa cara do processo editorial e, em "
    "português brasileiro, ainda pouco estudada com modelos de linguagem de grande escala (LLMs). Este "
    "trabalho avalia 21 LLMs comerciais e de pesos abertos na correção de erros gramaticais do português "
    "brasileiro e na classificação do tipo de erro, e estima o custo de revisar um livro com cada um deles. "
    "Construiu-se um conjunto de 1.206 frases com erro a partir dos exemplos das regras do LanguageTool, "
    "anotadas manualmente em uma taxonomia de 4 categorias e 30 subcategorias, das quais 1.203 foram usadas na avaliação. Todos os modelos receberam "
    "o mesmo prompt, em 25 lotes, executados por agentes de programação. A correção foi medida por F0,5 em "
    "nível de edição e por acerto exato da frase, com intervalos de confiança por bootstrap e teste de "
    "McNemar; o custo foi estimado a partir dos preços oficiais das APIs. Os seis melhores modelos "
    f"alcançaram F0,5 entre {br(RES['gemini-3.8-flash']['F05'])} e {br(RES['claude-sonnet-5.5']['F05'])}, "
    "sem diferença estatisticamente significativa entre a maioria deles, enquanto a classificação da "
    f"subcategoria do erro, após a revisão do gabarito, ficou entre {pct(RES['MiniMax-M3']['Acc_sub'])} e "
    f"{pct(RES['gemini-4-argon']['Acc_sub'])} de acurácia. O custo estimado para revisar um livro de "
    f"80 mil palavras variou de US$ {br(C_MIN, 2)} a "
    f"US$ {br(C_MAX, 2)}, e um modelo de pesos abertos "
    f"(MiMo-V2.6-Pro) obteve qualidade equivalente à dos melhores por menos de {extenso.get(LIMITE_MIMO, f'US$ {LIMITE_MIMO}')}. Conclui-se que a "
    "correção automática de frases já é tecnicamente e economicamente viável, mas a explicação do tipo "
    "de erro ainda exige revisão humana. A análise de uma amostra de falsos positivos mostrou que "
    f"{pct(_val / FP_N)} das edições não previstas pela referência eram válidas, muitas delas corrigindo erros "
    "que permaneciam na própria referência.")
set_text(P[12], RESUMO)
set_text(P[14], "Palavras-chave: correção gramatical automática. modelos de linguagem de grande escala. "
                "português brasileiro. avaliação de modelos. custo de inferência.")
ABSTRACT = (
    "Grammatical revision of long texts, such as books, is a costly step of the publishing process and "
    "remains little studied for Brazilian Portuguese with large language models (LLMs). This work evaluates "
    "21 commercial and open-weight LLMs on correcting Brazilian Portuguese grammatical errors and on "
    "classifying the error type, and estimates the cost of revising a book with each of them. A set of 1,206 "
    "erroneous sentences (1,203 evaluated) was built from the examples of LanguageTool rules and manually annotated with a "
    "taxonomy of 4 categories and 30 subcategories. All models received the same prompt, in 25 batches, run "
    "through coding agents. Correction was measured with edit-level F0.5 and sentence exact match, with "
    "bootstrap confidence intervals and McNemar tests; cost was estimated from official API prices. The six "
    "best models reached F0.5 between 0.822 and 0.834, mostly without statistically significant differences, "
    "while subcategory classification accuracy, after the gold-standard review, ranged from 41.5% to 76.8%. The estimated cost of revising an "
    f"80,000-word book ranged from US$ {usd_en(C_MIN)} to US$ {usd_en(C_MAX)}, and an open-weight model (MiMo-V2.6-Pro) matched "
    f"the best models for less than {extenso_en.get(LIMITE_MIMO, f'US$ {LIMITE_MIMO}')}. Sentence-level automatic correction is already technically "
    "and economically viable, but explaining the error type still requires human review. A manual analysis of a "
    f"sample of false positives showed that {round(100 * _val / FP_N)}% of the edits not in the reference were "
    "valid, many of them fixing errors left in the reference itself.")
set_text(P[17], ABSTRACT)
set_text(P[19], "Keywords: grammatical error correction. large language models. Brazilian Portuguese. "
                "model evaluation. inference cost.")

# ---- Remove o corpo-modelo (paragrafo 22 em diante) ----
body = doc.element.body
for p in P[22:]:
    body.remove(p._p)
for t in list(doc.tables):
    body.remove(t._tbl)


def par(texto, molde="body", bold=None, size=None, italic=None, pend=False, align=None):
    p = doc.add_paragraph()
    if MOLDES[molde] is not None:
        if p._p.pPr is not None:
            p._p.remove(p._p.pPr)
        p._p.insert(0, copy.deepcopy(MOLDES[molde]))
    partes = texto.split("[[") if "[[" in texto else [texto]
    for i, parte in enumerate(partes):
        if i > 0 and "]]" in parte:
            pend_txt, resto = parte.split("]]", 1)
            r = p.add_run("[" + pend_txt + "]")
            r.font.highlight_color = WD_COLOR_INDEX.YELLOW
            parte = resto
        if parte:
            r = p.add_run(parte)
            r.bold, r.italic = bold, italic
            if size:
                r.font.size = Pt(size)
            if pend:
                r.font.highlight_color = WD_COLOR_INDEX.YELLOW
    if align is not None:
        p.alignment = align
    return p


h1 = lambda t: par(t, "h1")
h2 = lambda t: par(t, "h2")
h3 = lambda t: par(t, "h3")


def figura(n, titulo, arquivo, fonte, largura=15):
    par(f"Figura {n} – {titulo}", "cap", size=10).paragraph_format.keep_with_next = True
    p = par("", "center", align=WD_ALIGN_PARAGRAPH.CENTER)
    p.paragraph_format.keep_with_next = True
    p.paragraph_format.first_line_indent = Cm(0)
    p.add_run().add_picture(f"{FIG}/{arquivo}", width=Cm(largura))
    par(f"Fonte: {fonte}", "fonte", size=10)


def borda(cell, lado, val="single", sz=8):
    tcPr = cell._tc.get_or_add_tcPr()
    b = tcPr.find(qn("w:tcBorders"))
    if b is None:
        b = OxmlElement("w:tcBorders")
        tcPr.append(b)
    e = OxmlElement(f"w:{lado}")
    e.set(qn("w:val"), val)
    e.set(qn("w:sz"), str(sz))
    e.set(qn("w:color"), "000000")
    b.append(e)


def quadro(n, titulo, linhas, fonte, tamanho=8.5):
    par(f"Quadro {n} – {titulo}", "cap", size=10).paragraph_format.keep_with_next = True
    t = doc.add_table(rows=1, cols=1)
    c = t.rows[0].cells[0]
    for lado in ("top", "bottom", "left", "right"):
        borda(c, lado)
    c.paragraphs[0].text = ""
    for i, lin in enumerate(linhas):
        q = c.paragraphs[0] if i == 0 else c.add_paragraph()
        pf = q.paragraph_format
        pf.first_line_indent = Cm(0)
        pf.space_before = pf.space_after = Pt(0)
        pf.line_spacing = 1.0
        pf.keep_with_next = True
        q.alignment = WD_ALIGN_PARAGRAPH.LEFT
        r = q.add_run(lin)
        r.font.name = "Courier New"
        r._element.rPr.rFonts.set(qn("w:eastAsia"), "Courier New")
        r.font.size = Pt(tamanho)
    par(f"Fonte: {fonte}", "fonte", size=10)


def tabela(n, titulo, cab, linhas, fonte, larguras=None, nota=None):
    par(f"Tabela {n} – {titulo}", "cap", size=10).paragraph_format.keep_with_next = True
    t = doc.add_table(rows=1 + len(linhas), cols=len(cab))
    t.alignment = 1
    for j, h in enumerate(cab):
        c = t.rows[0].cells[j]
        c.text = ""
        r = c.paragraphs[0].add_run(h)
        r.bold, r.font.size = True, Pt(9)
        borda(c, "top")
        borda(c, "bottom")
    for i, lin in enumerate(linhas, 1):
        for j, v in enumerate(lin):
            c = t.rows[i].cells[j]
            c.text = ""
            r = c.paragraphs[0].add_run(str(v))
            r.font.size = Pt(9)
            if i == len(linhas):
                borda(c, "bottom")
    for row in t.rows:
        for j, c in enumerate(row.cells):
            pf = c.paragraphs[0].paragraph_format
            pf.first_line_indent = Cm(0)
            pf.space_before = pf.space_after = Pt(1)
            c.paragraphs[0].alignment = WD_ALIGN_PARAGRAPH.LEFT if j == 0 else WD_ALIGN_PARAGRAPH.CENTER
            if larguras:
                c.width = Cm(larguras[j])
    if larguras:
        t.autofit = False
        grid = t._tbl.tblGrid
        for gc, w in zip(grid.findall(qn("w:gridCol")), larguras):
            gc.set(qn("w:w"), str(int(w * 567)))
        tblPr = t._tbl.tblPr
        tw = tblPr.find(qn("w:tblW"))
        if tw is None:
            tw = OxmlElement("w:tblW"); tblPr.append(tw)
        tw.set(qn("w:w"), str(int(sum(larguras) * 567))); tw.set(qn("w:type"), "dxa")
        lay = OxmlElement("w:tblLayout"); lay.set(qn("w:type"), "fixed"); tblPr.append(lay)
    if nota:
        par(nota, "fonte", size=10)
    par(f"Fonte: {fonte}", "fonte", size=10)


# =====================================================================
# 1 INTRODUCAO
# =====================================================================
h1("1 INTRODUÇÃO")
par("A revisão gramatical é uma etapa obrigatória na produção de livros, artigos e documentos "
    "institucionais. Feita por revisores humanos, ela é lenta e cara, o que a torna proporcionalmente mais "
    "pesada para autores independentes, editoras pequenas e instituições públicas. Ferramentas automáticas "
    "existem há décadas: corretores baseados em regras, como o LanguageTool (NABER, 2003), detectam bem erros "
    "previsíveis, mas dependem de regras escritas à mão e têm dificuldade com erros que exigem compreensão "
    "do contexto da frase.")
par("Os modelos de linguagem de grande escala (do inglês large language models, LLMs) mudaram esse "
    "cenário. Construídos sobre a arquitetura Transformer (VASWANI et al., 2017) e treinados em grandes "
    "volumes de texto, eles passaram a resolver tarefas novas apenas a partir de instruções em linguagem "
    "natural (BROWN et al., 2020; OUYANG et al., 2022), inclusive a correção gramatical (FANG et al., 2023). "
    "Ao mesmo tempo, o preço da inferência caiu rapidamente: para um mesmo nível de desempenho, a queda "
    "estimada é de 5 a 10 vezes por ano nos modelos de fronteira (GUNDLACH et al., 2025).")
par("Para o português brasileiro, porém, as evidências ainda são escassas. O trabalho mais próximo avaliou "
    "apenas o GPT-3.5 e o GPT-4 e observou que os LLMs tendem a corrigir mais do que o necessário, com "
    "precisão menor que a de ferramentas tradicionais (PENTEADO; PEREZ, 2023). Desde então, dezenas de "
    "modelos foram lançados por desenvolvedores dos Estados Unidos, da China e de outros países, com preços "
    "que diferem em mais de uma ordem de grandeza, e não há uma comparação sistemática entre eles para a "
    "revisão de textos em português.")
par("Este trabalho busca responder à seguinte pergunta: em que medida os LLMs atuais corrigem e classificam "
    "erros gramaticais do português brasileiro, e qual o custo estimado de revisar uma obra completa com "
    "eles? O objetivo geral é avaliar comparativamente a qualidade e o custo de 21 LLMs nessa tarefa. Os "
    "objetivos específicos são: (i) construir e anotar um conjunto de frases com erros do português "
    "brasileiro a partir das regras do LanguageTool; (ii) medir a qualidade da correção e da classificação "
    "do tipo de erro de cada modelo, com testes de significância; (iii) identificar os tipos de erro em que "
    "os modelos mais falham; e (iv) estimar o custo de revisar um livro com cada modelo.")
par("O restante do artigo está organizado da seguinte forma: a Seção 2 apresenta a evolução dos modelos de "
    "linguagem e da correção gramatical automática; a Seção 3 descreve o conjunto de dados, os modelos, o "
    "protocolo e as métricas; a Seção 4 apresenta e discute os resultados; e a Seção 5 traz as "
    "considerações finais, as limitações e os trabalhos futuros.")

# =====================================================================
# 2 FUNDAMENTACAO
# =====================================================================
h1("2 FUNDAMENTAÇÃO TEÓRICA E TRABALHOS RELACIONADOS")
par("Esta seção percorre a evolução técnica que tornou possível revisar textos com LLMs a baixo custo: dos "
    "modelos estatísticos ao Transformer, o pré-treinamento em escala, o alinhamento a instruções, as "
    "arquiteturas esparsas de mistura de especialistas e a queda do preço de inferência. Em seguida, "
    "apresenta a tarefa de correção gramatical automática e os trabalhos sobre o português.")

h2("2.1 Dos modelos estatísticos ao Transformer")
par("Um modelo de linguagem estima a probabilidade de uma sequência de palavras. Os primeiros modelos "
    "práticos eram estatísticos, baseados na contagem de n-gramas, e sofriam com a esparsidade: sequências "
    "nunca vistas no treinamento recebiam probabilidade nula ou quase nula. Bengio et al. (2003) propuseram "
    "um modelo neural que representa cada palavra como um vetor contínuo, permitindo generalizar para "
    "sequências novas a partir de palavras semelhantes. Mikolov et al. (2013) tornaram o aprendizado dessas "
    "representações eficiente em grande escala, popularizando os word embeddings.")
par("Redes recorrentes processavam o texto palavra por palavra, o que dificultava capturar dependências "
    "longas e paralelizar o treinamento. Vaswani et al. (2017) introduziram o Transformer, que substitui a "
    "recorrência pelo mecanismo de autoatenção: cada palavra é representada em função de todas as outras da "
    "sequência, em paralelo. Para a revisão gramatical, essa propriedade é central, pois a concordância, a "
    "regência e a colocação pronominal dependem de relações entre palavras distantes na frase.")

h2("2.2 Pré-treinamento, escala e alinhamento")
par("Sobre o Transformer surgiram duas linhas de pré-treinamento. O BERT (DEVLIN et al., 2019) usa apenas o "
    "codificador e aprende a prever palavras mascaradas, gerando representações úteis para classificação. "
    "A família GPT usa apenas o decodificador e aprende a prever a próxima palavra (RADFORD et al., 2018, "
    "2019), o que a torna naturalmente capaz de gerar texto, inclusive a versão corrigida de uma frase.")
par("Brown et al. (2020) mostraram com o GPT-3 que, a partir de certa escala, o modelo resolve tarefas novas "
    "apenas com instruções e poucos exemplos no prompt, sem ajuste de parâmetros. Kaplan et al. (2020) "
    "descreveram leis de escala segundo as quais o erro do modelo cai de forma previsível com o aumento de "
    "parâmetros, dados e computação. Por fim, Ouyang et al. (2022) alinharam esses modelos a instruções "
    "humanas com aprendizado por reforço a partir de preferências (RLHF), o que tornou possível pedir "
    "diretamente \"corrija esta frase\" e receber uma resposta no formato desejado. É esse comportamento que "
    "o presente trabalho explora: nenhum modelo foi ajustado para a tarefa; todos receberam apenas um prompt.")

h2("2.3 Mistura de especialistas e eficiência")
par("Aumentar o número de parâmetros melhora o desempenho, mas encarece cada consulta. A arquitetura de "
    "mistura de especialistas (mixture of experts, MoE) contorna esse problema dividindo as camadas do "
    "modelo em várias sub-redes, os especialistas, e ativando apenas algumas delas para cada token "
    "(SHAZEER et al., 2017; FEDUS; ZOPH; SHAZEER, 2022). O modelo pode ter centenas de bilhões de "
    "parâmetros no total, mas o custo de inferência é proporcional apenas aos parâmetros ativos.")
par("A consulta à documentação técnica dos 21 modelos avaliados (model cards e relatórios dos "
    "desenvolvedores) mostrou que a arquitetura MoE é declarada em todos os modelos de pesos abertos da "
    "amostra: MiMo-V2.6-Pro (1,02 trilhão de parâmetros no total e 42 bilhões ativos por token), "
    "MiMo-V2.6-Flash (309 bilhões / 15 bilhões), MiniMax-M3 e MiniMax-M3.1-Flash (cerca de 428 bilhões / "
    "23 bilhões), DeepSeek-V4.1-Flash (552 bilhões / 16 bilhões), GLM-5.3-Flash (320 bilhões / 18 bilhões), "
    "Kimi K3.1 Pro (2,8 trilhões / 104 bilhões), Qwen3.8-Max (2,4 trilhões / 95 bilhões), Qwen3.8-Flash "
    "(125 bilhões / 6 bilhões) e Beam 1.0 (501 bilhões / 23 bilhões). Entre os modelos proprietários, o "
    "Google declara que o Gemini 4 Argon é uma mistura esparsa de especialistas, sem informar o número de "
    "parâmetros, e o Gemini 4 Hydrogen deriva da mesma família. Anthropic, OpenAI, xAI e Meta não divulgam a "
    "arquitetura nem o tamanho dos modelos avaliados (Claude 5.5, GPT-6.1 e GPT-6, Grok 4.7 e Muse Spark "
    "1.3), assim como o Google no caso do Gemini 3.8 Flash. A Tabela 2, na Seção 3.3, resume essas "
    "informações. Nos modelos abertos, a razão entre parâmetros ativos e totais fica entre 2% e 5%, ou seja, "
    "cada token aciona uma pequena fração do modelo, o que ajuda a explicar os preços baixos desses modelos "
    "observados na Seção 4.4.")
par("Na correção gramatical, Qorib, Aji e Ng (2024) aplicaram a mesma ideia de forma explícita. Eles "
    "observaram que modelos diferentes têm forças complementares em tipos de erro diferentes, mas que "
    "combinar vários modelos é caro, porque exige executar todos eles. A proposta, chamada MoECE, é um único "
    "modelo com especialistas por tipo de erro, que alcança o desempenho de um modelo três vezes maior em "
    "parâmetros efetivos e ainda identifica o tipo do erro corrigido. Esse trabalho fundamenta duas escolhas "
    "do presente estudo: analisar o desempenho por tipo de erro e tratar a eficiência computacional como "
    "parte da avaliação.")

h2("2.4 Correção gramatical automática")
par("A correção gramatical automática (grammatical error correction, GEC) consiste em receber um texto com "
    "erros e devolver sua versão corrigida (BRYANT et al., 2023). Os primeiros sistemas eram baseados em "
    "regras: o LanguageTool, por exemplo, descreve cada erro como um padrão de tokens e etiquetas "
    "morfossintáticas, associado a uma mensagem e a uma sugestão de correção (NABER, 2003). Essa abordagem "
    "é precisa e explicável, mas cobre apenas os erros previstos pelas regras.")
par("A área consolidou-se com tarefas compartilhadas como a CoNLL-2014 (NG et al., 2014), que fixaram a "
    "avaliação por edição: o sistema é comparado à referência em termos das alterações que propõe, e não do "
    "texto final. A métrica padrão é o F0,5, que pondera a precisão duas vezes mais que a cobertura, porque "
    "uma correção indevida prejudica mais o usuário do que um erro não detectado (DAHLMEIER; NG, 2012). O "
    "ERRANT (BRYANT; FELICE; BRISCOE, 2017) automatizou a extração e a classificação das edições, mas apenas "
    "para o inglês. Com os LLMs, a correção passou a ser feita por instrução. Fang et al. (2023) mostraram "
    "que o ChatGPT produz correções fluentes, mas tende a reescrever trechos corretos, o que reduz a precisão "
    "medida pelas métricas tradicionais.")

h2("2.5 Correção gramatical em português")
par("O português dispõe de modelos pré-treinados específicos, como o BERTimbau (SOUZA; NOGUEIRA; LOTUFO, "
    "2020) e a família Sabiá (PIRES et al., 2023), mas de poucos recursos para avaliação de correção "
    "gramatical. Penteado e Perez (2023) criaram um conjunto de frases em português brasileiro com quatro "
    "categorias (gramática, ortografia, linguagem de internet e erros de digitação) e compararam o GPT-3.5 e "
    "o GPT-4 com o Microsoft Word e o Google Docs. O GPT-4 obteve a maior cobertura, mas os LLMs "
    "apresentaram precisão menor por excesso de correções. O presente trabalho amplia essa comparação para "
    "21 modelos atuais, usa uma taxonomia gramatical mais detalhada, mede a significância estatística das "
    "diferenças e incorpora o custo como dimensão de análise.")

h2("2.6 Custo de inferência")
par("O custo de uso de um LLM por API é cobrado por milhão de tokens, com preços distintos para tokens de "
    "entrada e de saída. Levantamentos da Epoch AI (2025) indicam que o preço para atingir um mesmo "
    "desempenho caiu entre 9 e 900 vezes por ano, conforme a tarefa. Gundlach et al. (2025) estimam uma "
    "queda de 5 a 10 vezes por ano para modelos de fronteira e atribuem cerca de 3 vezes por ano apenas a "
    "ganhos de eficiência algorítmica, como as arquiteturas MoE. Esses autores recomendam que avaliações de "
    "modelos passem a reportar também o preço, o que este trabalho faz na Seção 4.4.")

# =====================================================================
# 3 METODOLOGIA
# =====================================================================
h1("3 METODOLOGIA")
par("A pesquisa é quantitativa e experimental. A Figura 1 resume as etapas: construção do conjunto de "
    "dados, anotação, execução dos modelos, verificação de integridade, cálculo das métricas e estimativa "
    "de custo. O conjunto de dados, as saídas de todos os modelos e os scripts usados em cada etapa estão "
    "disponíveis no repositório do trabalho (https://github.com/AllysonAlves1/TCC), o que permite reproduzir "
    "todos os resultados apresentados.")
figura(1, "Fluxo metodológico da pesquisa", "fig_fluxo_metodologico.png", "Elaborado pelo autor (2026).", 15)

h2("3.1 Construção do conjunto de dados")
par("O conjunto de dados foi extraído do arquivo grammar.xml do módulo de português do LanguageTool, "
    "disponível no repositório público do projeto, no caminho languagetool-language-modules/pt/src/main/"
    "resources/org/languagetool/rules/pt/grammar.xml (LANGUAGETOOL, 2026). Nesse arquivo, cada regra gramatical é descrita em XML e organizada em três níveis: a "
    "categoria (elemento category, com um nome como \"Gramática Geral\"), o grupo de regras (rulegroup, com um "
    "identificador único) e as regras propriamente ditas (rule). Cada regra contém o padrão de tokens que "
    "detecta o erro (pattern), a mensagem mostrada ao usuário (message) e exemplos de uso (example).")
par("Ao analisar o arquivo, observou-se um padrão nos exemplos: os exemplos de frases erradas trazem o "
    "atributo correction, com a forma correta, e marcam o trecho errado com o elemento marker, enquanto os "
    "exemplos de frases corretas não têm esse atributo. O Quadro 1 mostra a regra A_TRAVES_ATRAVÉS_CONFUSAO, "
    "que tem dois exemplos de frases erradas.")
quadro(1, "Trecho do grammar.xml do LanguageTool (regra A_TRAVES_ATRAVÉS_CONFUSAO)", [
    '<rulegroup id="A_TRAVES_ATRAVÉS_CONFUSAO"',
    '           name="Confusão entre \'a traves\' e \'através\'">',
    '  <rule>',
    '    <pattern>',
    '      <marker><token>a</token><token>traves</token></marker>',
    '      <token postag_regexp="yes" postag="SP.+"/>',
    '    </pattern>',
    '    <message>Possível erro de digitação. Talvez queria utilizar',
    '      a preposição <suggestion>através</suggestion>?</message>',
    '    <example correction="Através"><marker>A traves</marker> de várias',
    '      entrevistas...</example>',
    '    <example correction="através">Correram <marker>a traves</marker>',
    '      do túnel.</example>',
    '  </rule>',
    '</rulegroup>'], "LanguageTool, arquivo grammar.xml do módulo de português.")
par("Com base nesse padrão, um script em Python (Apêndice A) percorre todas as categorias, grupos e regras "
    "e transforma cada exemplo com o atributo correction em uma linha do conjunto de dados, segundo estas "
    "regras de transformação:")
for item in [
        "a) frase incorreta: o texto completo do exemplo, como está no XML;",
        "b) tokens incorretos: o texto dentro do elemento marker;",
        "c) tokens corrigidos: o valor do atributo correction;",
        "d) frase correta: o texto antes do marker, seguido da correção e do texto depois do marker;",
        "e) categoria de extração: o nome da categoria que contém a regra;",
        "f) subcategoria de extração: o identificador do grupo de regras (ou da regra, quando ela não "
        "pertence a um grupo)."]:
    q = par(item)
    q.paragraph_format.first_line_indent = Cm(0)
    q.paragraph_format.left_indent = Cm(1.25)
par("Alguns casos exigiram tratamento específico. Quando o atributo correction traz várias sugestões "
    "separadas por barra vertical, adotou-se a primeira. Uma correção vazia indica que o trecho deve ser "
    "apagado, e a frase correta é montada sem ele. Exemplos sem marker foram descartados, porque não permitem "
    "localizar o erro, assim como os exemplos de antipadrões (antipattern), que descrevem frases corretas, e "
    "as frases repetidas. O Quadro 2 mostra a linha gerada a partir do primeiro exemplo do Quadro 1. As "
    "colunas de categoria e subcategoria do revisor ficam vazias nessa etapa e são preenchidas na anotação "
    "manual descrita na Seção 3.2.")
quadro(2, "Linha do conjunto de dados gerada a partir do primeiro exemplo do Quadro 1", [
    "Frase incorreta ........... A traves de várias entrevistas...",
    "Frase correta ............. Através de várias entrevistas...",
    "lista_tokens_incorretos ... A traves",
    "lista_tokens_corrigidos ... Através",
    "categoria_revisor ......... (preenchida na anotação)",
    "subcategoria_revisor ...... (preenchida na anotação)",
    "categoria_extracao ........ Gramática Geral",
    "subcategoria_extracao ..... A_TRAVES_ATRAVÉS_CONFUSAO"], "Elaborado pelo autor (2026).")
par("O conjunto final tem 1.206 frases, provenientes de 303 regras distintas, com média de 6,3 palavras por "
    "frase. Para documentar o ponto de partida, o script foi executado sobre a versão do arquivo de "
    "18/11/2026 (commit 09aa9f4): ele encontra 3.728 exemplos com correção e, depois de descartar 13 exemplos "
    "cuja correção não altera a frase e 57 repetidos, gera 3.658 frases de 500 regras. Das 1.206 frases do "
    "conjunto final, 1.199 continuam presentes nessa versão; as demais vieram de exemplos que foram alterados "
    "no repositório depois da extração original. As 1.206 frases (cerca de um terço do total) foram "
    "selecionadas manualmente pelo autor entre as extraídas, mantendo-se apenas as consideradas válidas para "
    "o teste. Foram descartadas: (i) correções de estilo ou de preferência, que não constituem erro "
    "gramatical; (ii) exemplos cuja correção era ambígua ou discutível; (iii) frases incompletas, "
    "malformadas ou repetidas; e (iv) correções de nomes próprios e marcas, que não eram objeto do teste. "
    "Os arquivos .ent do repositório são necessários para ler o grammar.xml, porque ele declara entidades "
    "em arquivos externos. Cada frase contém um único erro principal; apenas duas têm mais de um trecho corrigido. Como as "
    "frases vêm de exemplos de documentação, elas são curtas e descontextualizadas, o que favorece a avaliação "
    "controlada, mas não reproduz as condições de um texto corrido.")

h2("3.2 Taxonomia e anotação")
par("As categorias originais do LanguageTool (\"Gramática Geral\", \"Confusão de Palavras\", \"Sem Categoria "
    "Definida\" etc.) misturam critérios e não seguem a gramática normativa. Por isso, cada frase foi "
    "reclassificada manualmente pelo autor, em conjunto com um especialista em Letras [[nome e formação]], em "
    "uma taxonomia de 4 categorias e 30 subcategorias (28 delas "
    "presentes no conjunto), baseada nos "
    "níveis de análise linguística: Fonologia (incluindo ortografia e acentuação), Morfologia (classes de "
    "palavras), Sintaxe (concordância, regência, colocação, pontuação e crase) e Semântica (parônimos, "
    "homônimos e propriedade vocabular). A Tabela 1 mostra a distribuição resultante.")
tabela(1, "Distribuição das frases por categoria e principais subcategorias, após a revisão do gabarito",
       ["Categoria", "Frases", "Principais subcategorias (n)"],
       [["Sintaxe", "526", "Concordância nominal (161), Pontuação (95), Colocação pronominal (81)"],
        ["Fonologia", "377", "Ortografia (217), Acentuação gráfica (129), Emprego do hífen (22)"],
        ["Morfologia", "259", "Verbo (131), Pronome (33), Adjetivo (22)"],
        ["Semântica", "44", "Homônimo (24), Parônimo (15), Propriedade vocabular (5)"],
        ["Total", "1.206", "28 subcategorias presentes"]],
       "Elaborado pelo autor (2026).", [3, 2, 11])
par("Depois da execução dos modelos, as 193 frases em que pelo menos 80% deles concordaram entre si numa "
    "subcategoria diferente da anotada foram revisadas novamente pelo autor e pelo especialista, com base em "
    "gramática de referência. Os rótulos só foram alterados quando havia erro demonstrável de classificação, "
    "e nunca apenas porque os modelos discordavam; cada alteração foi registrada com o rótulo antigo, o novo, "
    "a justificativa e a fonte consultada. Também foi possível excluir frases que se mostrassem inadequadas "
    "ao teste. Das 193 frases, 41 mantiveram o rótulo, 151 tiveram o rótulo alterado (137 delas também na "
    "categoria) e 1 foi excluída, porque a própria correção de referência do LanguageTool estava errada: "
    "\"Ontem eu sai de casa.\" era corrigida para \"Ontem eu saio de casa.\", o que muda o tempo verbal, "
    "quando a forma correta seria \"saí\". As alterações mais frequentes foram de Pronome para Colocação "
    "pronominal (55), de Verbo para Concordância verbal (38) e de Preposição para Regência verbal (18). Em 150 "
    "das 151 alterações, o novo rótulo coincidiu com o escolhido pela maioria dos modelos. Como isso tende a "
    "favorecer os modelos, a Seção 4.2 apresenta a acurácia de classificação antes e depois da revisão e "
    "também nas frases que a revisão não tocou. A gramática de referência para todas as decisões foi a Nova "
    "gramática do português contemporâneo (CUNHA; CINTRA, 2017), registrada como fonte em cada linha do "
    "registro de alterações. A Tabela 1 mostra a distribuição após a revisão.")

h2("3.3 Modelos avaliados")
par("Foram avaliados 21 modelos de 12 desenvolvedores, escolhidos para cobrir os principais fornecedores "
    "comerciais e de pesos abertos disponíveis em novembro de 2026 e, dentro de cada família, versões de "
    "topo e versões leves. A Tabela 2 lista os modelos, o agente usado para executá-los, o preço oficial "
    "de API e a arquitetura declarada na documentação (Seção 2.3). Um 22º modelo, o deepseek-v4-pro, foi executado mas excluído da análise, conforme explicado na "
    "Seção 3.5.")
modelos = [
    ("claude-opus-5.5", "Anthropic", "Claude Code", "4,00 / 20,00", "não divulgada"),
    ("claude-sonnet-5.5", "Anthropic", "Claude Code", "2,00 / 10,00", "não divulgada"),
    ("claude-haiku-5.5", "Anthropic", "OpenCode", "0,10 / 0,50", "não divulgada"),
    ("gemini-4-argon", "Google", "Antigravity", "2,00 / 10,00 *", "MoE (n.d.)"),
    ("gemini-4-hydrogen", "Google", "Antigravity", "1,50 / 7,50", "MoE¹ (n.d.)"),
    ("gemini-3.8-flash", "Google", "Antigravity", "0,75 / 3,75 *", "não divulgada"),
    ("gpt-6.1-sol", "OpenAI", "Codex", "2,00 / 10,00", "não divulgada"),
    ("gpt-6.1-terra", "OpenAI", "Codex", "1,00 / 5,00", "não divulgada"),
    ("gpt-6-luna", "OpenAI", "OpenCode", "0,10 / 0,50", "não divulgada"),
    ("grok-4.7", "xAI", "Cursor", "2,00 / 6,00", "não divulgada²"),
    ("kimi-k3.1-pro", "Moonshot AI", "OpenCode", "2,00 / 10,00", "MoE 2,8 T / 104 B"),
    ("qwen3.8-max", "Alibaba", "OpenCode", "2,00 / 6,00", "MoE 2,4 T / 95 B"),
    ("qwen3.8-flash", "Alibaba", "OpenCode", "0,15 / 0,47", "MoE 125 B / 6 B"),
    ("musespark-1.3", "Meta", "OpenCode", "1,25 / 4,25", "não divulgada"),
    ("deepseek-v4.1-flash", "DeepSeek", "OpenCode", "0,30 / 1,20 **", "MoE 552 B / 16 B"),
    ("MiMo-V2.6-Pro", "Xiaomi", "OpenCode", "0,435 / 0,87", "MoE 1,02 T / 42 B"),
    ("MiMo-V2.6-Flash", "Xiaomi", "OpenCode", "0,14 / 0,28", "MoE 309 B / 15 B"),
    ("MiniMax-M3", "MiniMax", "OpenCode", "0,30 / 1,20", "MoE 428 B / 23 B"),
    ("minimax-m3.1-flash", "MiniMax", "OpenCode", "0,15 / 0,60", "MoE 428 B / 23 B"),
    ("GLM-5.3-Flash", "Z.ai", "OpenCode", "0,15 / 0,50", "MoE 320 B / 18 B"),
    ("beam (Beam 1.0)", "Reflection AI", "OpenCode", "0,25 / 1,00 ***", "MoE 501 B / 23 B"),
]
tabela(2, "Modelos avaliados, agente de execução, preço de API (US$ por milhão de tokens, entrada / saída) "
       "e arquitetura (parâmetros totais / ativos)",
       ["Modelo", "Desenvolvedor", "Agente", "Preço (US$/1M)", "Arquitetura"], [list(m) for m in modelos],
       "Páginas oficiais de preços e documentação técnica (model cards) dos desenvolvedores, consultadas em "
       "18/11/2026.", [3.6, 2.7, 2.5, 3.4, 3.8],
       nota="* Preço introdutório; o Gemini 4 Argon passa a US$ 4/20 em 01/12/2026 e o Gemini 3.8 Flash a "
            "US$ 1,50/7,50 em 01/01/2027. ** Tarifa de horário de pico (fora de pico: US$ 0,15/0,60). "
            "*** A Reflection AI não publica tabela própria; usou-se o preço do provedor OpenRouter. O modelo "
            "foi acessado gratuitamente no OpenCode, como Beam Free. Arquitetura: T = trilhões e B = bilhões de "
            "parâmetros; n.d. = número não divulgado. ¹ Inferido da linhagem: o Hydrogen deriva da família do "
            "Gemini 4 Argon. ² A xAI menciona 2,1 trilhões de parâmetros, sem documentar a arquitetura.")

h2("3.4 Evolução do protocolo de execução")
par("O protocolo usado para submeter as frases aos modelos não foi definido de uma vez. Ele passou por "
    "três abordagens, e as limitações de cada uma motivaram a seguinte. Registrar essa evolução justifica as "
    "escolhas da versão final e serve de orientação para quem precise avaliar muitos modelos com recursos "
    "limitados.")

h3("3.4.1 Primeira abordagem: interfaces web de chat")
par("Os primeiros testes foram feitos nas interfaces web de chat das próprias plataformas dos modelos "
    "avaliados. Em cada uma, o procedimento consistia em colar um prompt inicial com as instruções da tarefa "
    "e, em seguida, enviar as frases divididas em 10 lotes, na mesma conversa. A abordagem não exige "
    "programação, mas não escala: com mais de vinte modelos, seriam mais de 200 envios manuais, e cada "
    "resposta precisava ser copiada da tela para uma planilha antes de ser avaliada. Além disso, como os 10 "
    "lotes eram enviados na mesma conversa, o histórico se acumulava e podia influenciar as respostas dos "
    "lotes seguintes, e a interface não registra de forma reprodutível as condições de cada execução.")

h3("3.4.2 Segunda abordagem: o framework LangChain")
par("Para automatizar o envio, passou-se ao LangChain (CHASE, 2022), um framework que oferece uma interface "
    "comum para chamar modelos de diferentes provedores por código. Com ele, um script enviava os lotes, "
    "recebia as respostas e gravava os resultados, eliminando o trabalho manual. A abordagem, porém, exige uma "
    "chave de API em cada provedor, com cobrança por token. Para mais de vinte modelos, esse custo, somado ao "
    "trabalho de configurar e manter uma integração por provedor, com particularidades de parâmetros, limites "
    "de requisições e tratamento de erros, foi o principal motivo para abandonar a abordagem.")

h3("3.4.3 Versão final: agentes de programação")
par("A versão final usou agentes de programação: Claude Code, Codex, OpenCode, Antigravity e Cursor. Nesse "
    "tipo de ferramenta, o modelo de linguagem é envolvido por um software, chamado harness, que lhe dá "
    "ferramentas para ler e gravar arquivos e executar comandos, e que repete o ciclo de raciocinar, agir e "
    "observar o resultado até concluir a tarefa. Em vez de o pesquisador enviar cada lote e tratar a "
    "resposta, o próprio agente lê o arquivo do lote, processa as frases e grava o resultado em CSV.")
par("Essa abordagem trouxe três vantagens. Primeiro, a mesma instrução, em texto, serve para qualquer "
    "agente e qualquer modelo, sem código de integração por provedor. Segundo, a execução pode ser retomada: "
    "se for interrompida, o agente verifica o último identificador gravado e continua dali. Terceiro, os "
    "agentes foram usados por planos de assinatura, com custo mensal fixo, e não por cobrança por token: "
    "Claude Code, Antigravity, OpenCode e Codex em planos pagos, e Cursor no plano gratuito. Além do custo, "
    "pesou a praticidade de executar todos os modelos com a mesma instrução. Em contrapartida, o agente passa a ser uma variável do "
    "experimento, já que agentes diferentes podem conduzir o mesmo modelo de formas diferentes, e o acesso ao "
    "sistema de arquivos cria o risco de leitura do gabarito, tratado na Seção 3.5.")

h3("3.4.4 Construção do prompt")
par("A instrução foi dividida em dois arquivos de texto. O primeiro, prompt_padrao.txt, é o prompt "
    "propriamente dito e contém: o papel do modelo (especialista em revisão ortográfica, sintática e "
    "gramatical do português brasileiro); a estrutura de pastas do projeto; as regras de operação; o formato "
    "de saída e a definição de cada coluna; a taxonomia completa de categorias e subcategorias, em JSON; um "
    "exemplo de linha de saída; e a proibição de qualquer texto além dos dados. O segundo, "
    "comando_processar.txt, é a instrução curta digitada em todos os agentes: processar os 25 lotes um por "
    "vez, lendo, processando e gravando cada um antes de passar ao seguinte, e retomar do último "
    "identificador gravado caso o arquivo de saída já exista.")
par("Cada parte do prompt responde a um problema prático. A taxonomia fechada, em JSON, restringe a "
    "classificação a rótulos válidos e permite compará-la automaticamente com a anotação. O exemplo único de "
    "linha fixa o formato sem induzir respostas, já que trata de um erro de crase, e a crase representa "
    "apenas 4% do conjunto. A divisão em lotes de até 50 frases, processadas em blocos de 15 a 20, limita o "
    "contexto acumulado e o tamanho de cada resposta. A gravação sem cabeçalho e em modo de acréscimo "
    "permite retomar a execução sem duplicar linhas. Por fim, o prompt não menciona o LanguageTool nem "
    "apresenta as correções esperadas, para que o modelo resolva a tarefa sem pistas. O Quadro 3 reproduz o "
    "formato de saída exigido.")
quadro(3, "Formato de saída exigido no prompt e exemplo de linha", [
    "id;frase incorreta;frase correta;token incorreto;token correto;categoria;subcategoria",
    "1;Ele vai a escola todo dia.;Ele vai à escola todos os dias.;a;à;Sintaxe;Uso da crase"],
    "Arquivo prompt_padrao.txt, elaborado pelo autor (2026).")

h3("3.4.5 Escolha do formato CSV")
par("A entrada e a saída foram definidas em CSV (valores separados por delimitador), por cinco razões. "
    "A primeira é a correspondência direta com a tarefa: cada frase é um registro com os mesmos sete campos, "
    "e uma tabela representa isso sem estrutura adicional. A segunda é a economia de tokens. Formatos como "
    "JSON e XML repetem o nome de cada campo em todos os registros. Para medir o efeito, o resultado completo "
    "de um dos modelos (1.206 linhas) foi convertido para outros formatos: ele ocupa 141.742 caracteres em "
    "CSV, 297.292 em JSON (2,1 vezes mais) e 382.896 em XML (2,7 vezes mais). Como os tokens de saída são os "
    "mais caros, conforme a Tabela 2, e respostas longas correm mais risco de interrupção, o CSV reduz o custo "
    "e o risco de truncamento pela metade em relação ao JSON.")
par("A terceira razão é a tolerância a falhas. Em CSV, cada linha é independente: uma linha malformada "
    "compromete apenas aquela frase, enquanto um único erro de sintaxe em JSON pode invalidar o arquivo "
    "inteiro. No experimento, cinco modelos produziram linhas fora do formato (Seção 4.5), e todas as demais "
    "linhas puderam ser aproveitadas. A quarta é a praticidade: o arquivo abre em qualquer editor de "
    "planilhas, o que facilitou a anotação e a revisão manual, e é lido por scripts com a biblioteca padrão "
    "do Python. A quinta diz respeito ao delimitador: escolheu-se o ponto e vírgula porque 160 das 1.206 "
    "frases contêm vírgula, que é justamente um dos tipos de erro avaliados, enquanto o ponto e vírgula é "
    "raro nos exemplos.")
par("O CSV tem a desvantagem de não ter esquema nem tipos de dados: nada impede o modelo de gravar campos a "
    "mais ou a menos. Por isso, o prompt exige que campos com aspas ou ponto e vírgula sejam envolvidos por "
    "aspas duplas, e o script de avaliação mede a proporção de linhas com exatamente sete campos. O próprio "
    "conjunto de dados mostra esse risco: duas frases originais do LanguageTool continham ponto e vírgula "
    "(\"O relatório foi entregue; por quê não houve mudanças?\") e, gravadas sem aspas, foram partidas em "
    "duas colunas, de modo que os modelos receberam apenas \"O relatório foi entregue\". Essas duas frases foram excluídas da "
    "avaliação.")

h2("3.5 Verificação de integridade")
par("Como os agentes têm acesso ao sistema de arquivos, existe o risco de um modelo ler o arquivo de "
    "gabarito em vez de resolver a tarefa. Para cada modelo, calculou-se a proporção de linhas idênticas ao "
    "gabarito em todos os campos, inclusive categoria e subcategoria. O deepseek-v4-pro apresentou 100% de "
    "linhas idênticas, o que só é possível com acesso ao gabarito, e foi excluído. Nos demais modelos, essa "
    "proporção, medida com o gabarito anterior à revisão, ficou entre 9,1% e 23,5%, faixa compatível com acertos legítimos. Esse episódio mostra que "
    "avaliações executadas por agentes devem isolar o gabarito do ambiente de execução.")

h2("3.6 Métricas")
par("A qualidade da correção foi medida em nível de edição, seguindo Dahlmeier e Ng (2012). A frase "
    "incorreta, a frase de referência e a frase do modelo são divididas em tokens (palavras e sinais de "
    "pontuação, preservando maiúsculas). Por alinhamento de sequências, extraem-se as edições que levam a "
    "frase incorreta à de referência (G) e à do modelo (H). Uma edição do modelo é verdadeira positiva se "
    "coincidir com uma edição da referência. A precisão, a cobertura e o F0,5 são calculados sobre o "
    "corpus inteiro:")
for eq, n in (("P = TP / (TP + FP)", 1), ("R = TP / (TP + FN)", 2), ("F0,5 = (1,25 × P × R) / (0,25 × P + R)", 3)):
    q = par(f"{eq}\t({n})", align=WD_ALIGN_PARAGRAPH.LEFT)
    q.paragraph_format.first_line_indent = Cm(0)
    q.paragraph_format.left_indent = Cm(4)
    q.paragraph_format.tab_stops.add_tab_stop(Cm(15.5), WD_TAB_ALIGNMENT.RIGHT)
par("Também se mediu o acerto exato, isto é, a proporção de frases em que a correção do modelo é idêntica "
    "à referência. A classificação foi avaliada pela acurácia e pelo F1-macro da categoria e da subcategoria. "
    "Para cada métrica, calcularam-se intervalos de confiança de 95% por bootstrap com 1.000 reamostragens "
    "das frases (EFRON; TIBSHIRANI, 1993). A diferença entre os seis melhores modelos foi testada com o teste "
    "exato de McNemar (MCNEMAR, 1947) sobre o acerto exato, com correção de Holm (1979) para comparações "
    "múltiplas. Métricas de sobreposição de n-gramas, como BLEU (PAPINENI et al., 2002) e ROUGE-L (LIN, "
    "2004), foram calculadas, mas não são usadas na análise: como a frase corrigida difere da original em "
    "poucas palavras, elas ficam próximas de 1 mesmo quando o modelo não corrige nada.")

h2("3.7 Estimativa de custo")
par("O custo foi estimado como se cada modelo fosse chamado diretamente por API: o prompt enviado uma vez "
    "por lote, mais as frases, como tokens de entrada; e as linhas efetivamente geradas pelo modelo como "
    "tokens de saída. O custo do conjunto foi convertido em custo por palavra revisada e extrapolado para um "
    "livro de referência de 80 mil palavras. Como os modelos usaram raciocínio, cujos tokens são cobrados "
    "como saída mas não aparecem no resultado, o valor obtido é um limite inferior; por isso, apresenta-se "
    "também um cenário com a saída multiplicada por 10. " + (
    "Os tokens foram contados com o tokenizador o200k_base da biblioteca tiktoken, usado como aproximação "
    "comum a todos os modelos, já que cada desenvolvedor usa um tokenizador próprio."
    if "tiktoken" in d.get("tokenizador_custo", "") else
    "Os tokens foram contados com aproximação de 4 caracteres por token [[recalcular com o tokenizador "
    "tiktoken na máquina do autor]]."))

# =====================================================================
# 4 RESULTADOS
# =====================================================================
FP_TOTAL = sum(int(r["FP"]) for r in d["resumo"])
with open("datasets/dataset_erros_gramaticais_revisado.csv", encoding="utf-8-sig", newline="") as _f:
    _txt = " ".join(r["Frase correta"] for r in _csv.DictReader(_f, delimiter=";"))
CHARS_PALAVRA = len(_txt) / len(_txt.split())
LAUDAS = round(80_000 * CHARS_PALAVRA / 1400)
REV_SIMPLES, REV_COMPLETA = LAUDAS * 166.70, LAUDAS * 243.49
CAMBIO = 5.51
h1("4 RESULTADOS E ANÁLISE")
par(f"Os resultados a seguir consideram {N_AVAL:,}".replace(",", ".") + " frases: foram excluídas as duas "
    "frases corrompidas descritas na Seção 3.4.5 e a frase excluída na revisão do gabarito (Seção 3.2). "
    "Todos os números usam o gabarito revisado. As métricas de correção não dependem da revisão, que alterou "
    "apenas rótulos de classificação, e por isso são idênticas nas duas versões do gabarito; a classificação "
    "é comparada antes e depois da revisão na Seção 4.2.")

h2("4.1 Qualidade da correção")
par("A Tabela 3 apresenta as métricas de correção e classificação dos 21 modelos, ordenados por F0,5. A "
    "Figura 2 mostra os mesmos valores de F0,5 com os intervalos de confiança.")
linhas = []
for r in sorted(d["resumo"], key=lambda r: -r["F05"]):
    linhas.append([r["modelo"], br(r["P"]), br(r["R"]), br(r["F05"]),
                   f"{br(r['F05_IC_inf'])}–{br(r['F05_IC_sup'])}", br(r["Exata"]),
                   br(r["Acc_cat"]), br(r["Acc_sub"])])
tabela(3, "Qualidade da correção e da classificação por modelo (gabarito revisado)",
       ["Modelo", "P", "R", "F0,5", "IC 95% F0,5", "Exata", "Acc. cat.", "Acc. subcat."], linhas,
       "Elaborado pelo autor (2026).", [3.6, 1.3, 1.3, 1.3, 2.6, 1.3, 1.5, 1.6])
figura(2, "F0,5 por edição e intervalo de confiança de 95% de cada modelo", "fig_f05_ic_pos.png",
       "Elaborado pelo autor (2026).", 14)
s = RES["claude-sonnet-5.5"]
par(f"O claude-sonnet-5.5 obteve o maior F0,5 ({br(s['F05'])}), seguido de perto por musespark-1.3, "
    f"qwen3.8-max, MiMo-V2.6-Pro, gemini-4-argon e gemini-3.8-flash, todos com F0,5 de 0,82 ou mais. Os intervalos de "
    "confiança desses seis modelos se sobrepõem, e o teste de McNemar sobre o acerto exato, com correção de "
    "Holm, não encontrou diferença significativa em 14 dos 15 pares; a única exceção foi o qwen3.8-max, que "
    "acertou exatamente menos frases que o gemini-3.8-flash (p ajustado = 0,018). Na prática, portanto, não "
    "há um único melhor modelo, mas um grupo de modelos equivalentes.")
par("Dois resultados contrariam a expectativa de que modelos maiores e mais caros corrigem melhor. O "
    f"claude-opus-5.5, o mais caro da amostra, ficou em nono lugar (F0,5 = {br(RES['claude-opus-5.5']['F05'])}), "
    "abaixo do claude-sonnet-5.5 da mesma família. E o gemini-3.8-flash, versão leve, superou o "
    "gemini-4-hydrogen e empatou com o gemini-4-argon. Na base inferior ficaram os dois modelos da MiniMax "
    f"e o beam, com F0,5 entre {br(RES['MiniMax-M3']['F05'])} e {br(RES['beam']['F05'])}.")
par("Em 16 dos 21 modelos, a cobertura (R) superou a precisão (P), o que "
    "indica uma tendência a propor mais edições do que a referência, na mesma direção da sobrecorreção "
    "observada por Fang et al. (2023) e por Penteado e Perez (2023). Parte dessas edições extras pode ser "
    "legítima, já que o conjunto tem uma única referência por frase.")
par(f"Para estimar essa parcela, os {FP_TOTAL:,}".replace(",", ".") + " falsos positivos dos 21 modelos "
    "foram amostrados de forma estratificada: 12 edições por modelo, sorteadas com semente fixa, num total "
    "de 252. As edições foram embaralhadas e apresentadas sem o nome do modelo, com a frase original, a "
    "referência e a saída completa, e classificadas pelo autor e pelo especialista em Letras, com base em "
    "Cunha e Cintra (2017), em cinco rótulos: indevida (introduz erro ou altera trecho correto sem "
    "necessidade), alternativa válida (corrige o mesmo erro de outra forma), correção adicional (corrige "
    "outro erro real que a referência não marcou), neutra (mudança opcional, como uma vírgula facultativa) "
    "e referência errada. Com a proporção p de edições válidas (alternativas, adicionais e referência "
    "errada) de cada modelo, calculou-se a precisão ajustada, (TP + p·FP) / (TP + FP), com intervalo de "
    "confiança de Wilson para p.")
_pc = lambda k: pct(FP_ROT[k] / FP_N)
_ic = lambda k: "IC 95%: " + "–".join(pct(x) for x in _wilson(FP_ROT[k], FP_N)[1:])
_paj = sorted(FP.values(), key=lambda r: -float(r["P_ajustada"].replace(",", ".")))
par(f"O resultado mais relevante da anotação é que a maior parte dos falsos positivos não era erro do modelo. "
    f"Das {FP_N} edições, {FP_ROT['REF_ERRADA']} ({_pc('REF_ERRADA')}; {_ic('REF_ERRADA')}) corrigiam um erro "
    f"que permanecia na própria frase de referência, {FP_ROT['ALTERNATIVA']} ({_pc('ALTERNATIVA')}) eram "
    f"alternativas válidas à correção da referência e {FP_ROT['ADICIONAL']} ({_pc('ADICIONAL')}) corrigiam "
    f"outro erro real da frase. Somadas, as edições válidas foram {_val} ({pct(_val / FP_N)}). As indevidas "
    f"foram {FP_ROT['INDEVIDA']} ({_pc('INDEVIDA')}; {_ic('INDEVIDA')}), das quais {FP_INDEV_SENTIDO} alteravam o "
    f"sentido da frase, e as neutras, {FP_ROT['NEUTRA']} ({_pc('NEUTRA')}), quase todas a troca da inicial "
    f"minúscula por maiúscula ({FP_NEUTRA_MAIUSC} casos).")
par(f"A alta proporção de referências erradas tem uma causa identificável: os exemplos do LanguageTool foram "
    f"escritos para ilustrar uma regra, e a frase corrigida conserta apenas o erro dessa regra, deixando os "
    f"demais. É o caso da frase \"As parceiras com a ABC e a DEF foi um experiência positiva.\", cuja "
    f"referência corrige apenas \"parceiras\" para \"parcerias\" e mantém \"foi\" e \"um experiência\". Das {FP_IDS} frases distintas "
    f"que apareceram na amostra, {FP_IDS_REF} tinham ao menos uma edição rotulada como referência errada. "
    f"Esse número não estima a proporção de referências com erro em todo o conjunto, porque a amostra parte "
    f"das frases em que os modelos divergiram da referência, mas mostra que a precisão da Tabela 3 é "
    f"subestimada para todos os modelos.")
par(f"A Tabela 4 apresenta a precisão ajustada. Com ela, a precisão passa a ficar entre "
    f"{_paj[-1]['P_ajustada']} ({_paj[-1]['modelo']}) e {_paj[0]['P_ajustada']} ({_paj[0]['modelo']} e "
    f"{_paj[1]['modelo']}), e a tendência de sobrecorreção observada acima praticamente desaparece. Como a "
    f"amostra tem apenas 12 edições por modelo, os intervalos são largos e se sobrepõem, e a ordenação "
    f"entre modelos não deve ser interpretada; a conclusão segura é agregada: cerca de três em cada quatro "
    f"edições não previstas pela referência são legítimas, e menos de uma em cada cinco é uma correção "
    f"indevida.")
tabela(4, "Classificação manual de uma amostra de falsos positivos e precisão ajustada por modelo",
       ["Modelo", "Indev.", "Alt.", "Adic.", "Neutra", "Ref. err.", "P", "P ajust. (IC 95%)"],
       [[r["modelo"], r["INDEVIDA"], r["ALTERNATIVA"], r["ADICIONAL"], r["NEUTRA"], r["REF_ERRADA"],
         r["P_original"], f"{r['P_ajustada']} ({r['P_ajustada_inf']}–{r['P_ajustada_sup']})"] for r in _paj],
       "Elaborado pelo autor (2026).", [3.6, 1.3, 1.2, 1.3, 1.4, 1.6, 1.4, 3.4],
       nota="Amostra de 12 falsos positivos por modelo. Precisão ajustada: (TP + p·FP) / (TP + FP), em que p "
            "é a proporção de edições válidas (alternativas, adicionais e referência errada) na amostra do "
            "modelo; o intervalo usa o IC de Wilson de p.")

h2("4.2 Classificação do tipo de erro")
mc_pre, ms_pre = media([r["Acc_cat"] for r in PRE.values()]), media([r["Acc_sub"] for r in PRE.values()])
mc_pos, ms_pos = media([r["Acc_cat"] for r in RES.values()]), media([r["Acc_sub"] for r in RES.values()])
mc_nr, ms_nr = media([r["acc_cat_nao_revisadas"] for r in COMP.values()]), media([r["acc_sub_nao_revisadas"] for r in COMP.values()])
n_nr = int(next(iter(COMP.values()))["n_nao_revisadas"])
par(f"A classificação foi bem mais difícil que a correção. Com o gabarito revisado, a acurácia média foi de "
    f"{pct(mc_pos)} na categoria e de {pct(ms_pos)} na subcategoria. O melhor modelo, gemini-4-argon, acertou "
    f"{pct(RES['gemini-4-argon']['Acc_cat'])} das categorias e {pct(RES['gemini-4-argon']['Acc_sub'])} das "
    f"subcategorias; o pior, MiniMax-M3, {pct(RES['MiniMax-M3']['Acc_cat'])} e {pct(RES['MiniMax-M3']['Acc_sub'])}. "
    "O ranking também muda em relação à correção: o claude-sonnet-5.5, primeiro em F0,5, é apenas o 11º em "
    "acurácia de subcategoria, e o musespark-1.3 e o qwen3.8-max, segundo e terceiro em correção, ficam na "
    "metade inferior. Corrigir e explicar o erro são, portanto, competências distintas.")
n_nr_txt = f"{n_nr:,}".replace(",", ".")
par("Como a revisão do gabarito ocorreu justamente nas frases em que os modelos discordavam da anotação, e "
    "quase sempre adotou o rótulo escolhido por eles, a acurácia pós-revisão poderia estar inflada. A Tabela 5 "
    f"separa esse efeito. Antes da revisão, a acurácia média era de {pct(mc_pre)} na categoria e "
    f"{pct(ms_pre)} na subcategoria. Nas {n_nr_txt} frases que a revisão não tocou, cujo rótulo é o mesmo nas "
    f"duas versões, a acurácia média é de {pct(mc_nr)} e {pct(ms_nr)}, muito próxima dos valores pós-revisão. "
    "Isso indica que o ganho não decorre apenas de a revisão ter adotado os rótulos dos modelos: a anotação "
    "original tinha erros concentrados nas frases revisadas, como classificar como \"Pronome\" erros de "
    "colocação pronominal e como \"Verbo\" erros de concordância verbal.")
ordem = sorted(COMP.values(), key=lambda r: -r["acc_sub_nao_revisadas"])
tabela(5, "Acurácia de classificação antes e depois da revisão do gabarito e nas frases não revisadas",
       ["Modelo", "Cat. pré", "Cat. pós", "Cat. não rev.", "Subcat. pré", "Subcat. pós", "Subcat. não rev."],
       [[r["modelo"], pct(r["acc_cat_pre"]), pct(r["acc_cat_pos"]), pct(r["acc_cat_nao_revisadas"]),
         pct(r["acc_sub_pre"]), pct(r["acc_sub_pos"]), pct(r["acc_sub_nao_revisadas"])] for r in ordem],
       "Elaborado pelo autor (2026).", [3.8, 1.8, 1.8, 2.0, 2.0, 2.0, 2.2],
       nota=f"Frases não revisadas: as {n_nr_txt} frases avaliadas que não entraram na revisão do gabarito.")

h2("4.3 Desempenho por subcategoria")
par("A Figura 3 mostra o acerto exato de cada modelo nas subcategorias com pelo menos 15 frases, ordenadas "
    "da mais fácil para a mais difícil.")
figura(3, "Acerto exato da frase por subcategoria e modelo (%)", "fig_subcategorias_pos.png",
       "Elaborado pelo autor (2026).", 16)
par("Os erros mais fáceis foram os de crase, concordância verbal, ortografia e acentuação, com acerto "
    "médio de 83% a 85%. Os mais difíceis foram o adjetivo (51% em média), a pontuação (62%), o parônimo "
    "(64%), o pronome (65%) e a concordância nominal (70%). A variação entre modelos também é grande: no "
    "homônimo, o acerto vai de 38% (MiniMax-M3) a 96% (gemini-3.8-flash), e na colocação pronominal, de 49% "
    "(MiniMax-M3) a 94% (musespark-1.3). Antes da revisão, a colocação pronominal parecia a subcategoria mais "
    "difícil, mas o resultado decorria de frases rotuladas como \"Pronome\"; com os rótulos corrigidos, ela "
    "passa a ter acerto médio de 77%. Esse padrão, em que cada modelo tem pontos fortes em tipos de erro "
    "diferentes, é o mesmo que motivou a proposta de especialistas por tipo de erro de Qorib, Aji e Ng "
    "(2024), e sugere que combinar modelos poderia melhorar o resultado.")

h2("4.4 Custo e viabilidade econômica")
par("A Figura 4 relaciona o F0,5 de cada modelo ao custo estimado para revisar um livro de 80 mil palavras. "
    "A linha azul liga os modelos da fronteira de Pareto, isto é, aqueles para os quais nenhum outro modelo "
    "é ao mesmo tempo mais barato e melhor.")
figura(4, "Qualidade da correção versus custo estimado para revisar um livro de 80 mil palavras",
       "fig_qualidade_custo_pos.png", "Elaborado pelo autor (2026).", 15)
c = lambda m, k="custo_livro_usd_x1": br(CUSTO[m][k], 2)
_pts = sorted((CUSTO[m]["custo_livro_usd_x1"], RES[m]["F05"], m) for m in CUSTO if m in RES)
FRONTEIRA, _melhor = [], -1.0
for _c, _f, _m in _pts:
    if _f > _melhor:
        FRONTEIRA.append(_m)
        _melhor = _f
M_MIN = min(CUSTO, key=lambda m: CUSTO[m]["custo_livro_usd_x1"])
M_MAX = max(CUSTO, key=lambda m: CUSTO[m]["custo_livro_usd_x1"])
_num = {2: "dois", 3: "três", 4: "quatro", 5: "cinco", 6: "seis", 7: "sete"}
_lista = lambda xs: ", ".join(xs[:-1]) + " e " + xs[-1] if len(xs) > 1 else xs[0]
par(f"O custo estimado variou de US$ {c(M_MIN)} ({M_MIN}) a US$ {c(M_MAX)} ({M_MAX}) por livro. Mesmo no "
    "cenário pessimista, com a saída multiplicada por 10 para representar os tokens de raciocínio, o modelo "
    f"mais caro ficaria em US$ {c(M_MAX, 'custo_livro_usd_x10')}. A fronteira de Pareto é formada por apenas "
    f"{_num.get(len(FRONTEIRA), len(FRONTEIRA))} modelos: {_lista(FRONTEIRA)}. " + (
    "O destaque é o MiMo-V2.6-Pro, um modelo de pesos abertos que pertence ao grupo estatisticamente "
    f"equivalente ao melhor e custaria US$ {c('MiMo-V2.6-Pro')} por livro, cerca de "
    f"{br(RAZAO_SONNET_MIMO, 1)} vezes menos que o claude-sonnet-5.5."
    if "MiMo-V2.6-Pro" in FRONTEIRA else
    "[[Revisar o destaque: o MiMo-V2.6-Pro saiu da fronteira com a nova contagem de tokens.]]"))
par(f"Para comparação, a tabela de referência do Sindicato dos Jornalistas Profissionais do Ceará "
    f"(SINDJORCE, 2026) fixa R$ 166,70 por lauda para a revisão simples e R$ 243,49 para a revisão completa, "
    f"considerando lauda de 1.400 caracteres. Com a média de {br(CHARS_PALAVRA, 2)} caracteres por palavra "
    f"(incluindo espaços) observada nas frases do conjunto, um livro de 80 mil palavras tem cerca de "
    f"{LAUDAS} laudas, o que resulta em R$ {br(REV_SIMPLES / 1000, 1)} mil pela revisão simples e "
    f"R$ {br(REV_COMPLETA / 1000, 1)} mil pela revisão completa. "
    f"Ao câmbio de R$ {br(CAMBIO, 2)} por dólar (PTAX de 09/11/2026, conforme BRASIL 61, 2026), o modelo "
    f"mais caro custaria R$ {br(CUSTO[M_MAX]['custo_livro_usd_x1'] * CAMBIO, 2)} por livro, ou "
    f"R$ {br(CUSTO[M_MAX]['custo_livro_usd_x10'] * CAMBIO, 2)} no cenário pessimista. Mesmo considerando que a revisão automática "
    "não dispensa a leitura humana final, a diferença de custo é de várias ordens de grandeza, o que "
    "confirma a viabilidade econômica do uso de LLMs como primeira etapa de revisão.")

h2("4.5 Conformidade com o formato")
par("Todos os modelos devolveram as 1.206 frases. A proporção de linhas no formato exigido (sete campos "
    "separados por ponto e vírgula) foi de 100% em 16 modelos; os demais ficaram entre 92,7% (beam) e 99,8% "
    "(GLM-5.3-Flash). Linhas fora do formato foram avaliadas mesmo assim, desde que fosse possível "
    "identificar a frase corrigida, e por isso pesam pouco nos resultados, mas indicam que, numa aplicação "
    "real, a saída dos modelos precisa ser validada automaticamente.")

# =====================================================================
# 5 CONSIDERACOES FINAIS
# =====================================================================
h1("5 CONSIDERAÇÕES FINAIS")
par("Este trabalho avaliou 21 LLMs na correção e na classificação de erros gramaticais do português "
    "brasileiro, com um conjunto de 1.206 frases construído a partir das regras do LanguageTool, das quais "
    "1.203 foram avaliadas. Em resposta "
    "à pergunta de pesquisa, os resultados indicam que: (i) os melhores modelos corrigem cerca de 80% das "
    "frases exatamente como a referência, e um grupo de seis modelos de cinco desenvolvedores diferentes é "
    "estatisticamente equivalente; (ii) a classificação do tipo de erro é bem mais fraca, com acurácia "
    "de 42% a 77% na subcategoria, mesmo após a revisão do gabarito; (iii) adjetivo, pontuação, parônimo, "
    "pronome e concordância nominal concentram as falhas; e (iv) revisar um livro de 80 mil palavras custaria "
    f"menos de US$ {LIMITE_MAX} com qualquer modelo, e menos de US$ {LIMITE_MIMO} com um modelo de pesos abertos "
    "de qualidade equivalente à dos melhores. A análise dos falsos positivos acrescenta que a maior parte "
    f"das edições não previstas pela referência era legítima ({pct(_val / FP_N)} da amostra), o que torna a "
    "precisão medida um limite inferior da qualidade real dos modelos.")
par("O trabalho tem limitações. As frases são curtas e isoladas, e cada uma tem uma única correção de "
    "referência. A análise dos falsos positivos mostrou que essa referência, herdada dos exemplos do "
    "LanguageTool, nem sempre está totalmente correta, porque corrige apenas o erro da regra de origem; com "
    "isso, as métricas de correção penalizam modelos que corrigem a frase inteira. O conjunto não inclui frases corretas, "
    "de modo que não é possível medir com quantas frases sem erro os modelos interferem. A anotação foi feita "
    "por consenso entre o autor e um especialista, sem medida de concordância entre anotadores independentes, "
    "e a seleção das frases foi feita pelo autor segundo o seu julgamento do que se enquadrava nas "
    "categorias e subcategorias do teste, o que pode introduzir viés na composição do conjunto; além disso, a "
    "revisão do gabarito foi motivada pelas divergências com os modelos, o que "
    "foi mitigado pelo registro justificado de cada alteração e pela apresentação dos resultados antes e "
    "depois da revisão. Os modelos foram "
    "executados por agentes diferentes, o que mistura o efeito do modelo com o do agente; o caso mais claro "
    "é a família Claude, em que o Haiku rodou no OpenCode e os demais no Claude Code. Por fim, o custo é "
    "uma estimativa de chamada direta à API, e os preços mudam com frequência.")
par("Como trabalhos futuros, sugere-se: avaliar textos corridos e longos, como capítulos de livros; incluir "
    "frases sem erro para medir a sobrecorreção; revisar integralmente as frases de referência e usar várias "
    "referências por frase; combinar modelos com "
    "pontos fortes diferentes; e comparar os resultados com revisores humanos em tempo e custo.")

# =====================================================================
# REFERENCIAS
# =====================================================================
h1("REFERÊNCIAS")
REFS = [
    "ALIBABA CLOUD. Model Studio: model pricing. Disponível em: https://www.alibabacloud.com/help/en/model-studio/model-pricing. Acesso em: 18 nov. 2026.",
    "ANTHROPIC. Pricing. Disponível em: https://platform.claude.com/docs/en/about-claude/pricing. Acesso em: 18 nov. 2026.",
    "BENGIO, Y. et al. A neural probabilistic language model. Journal of Machine Learning Research, v. 3, p. 1137-1155, 2003.",
    "BRASIL 61. Dólar hoje fecha em leve alta a R$ 5,51 após oscilar entre queda e valorização. Brasil 61, 9 nov. 2026. Disponível em: https://brasil61.com/n/dolar-hoje-fecha-em-leve-alta-a-r-5-51-apos-oscilar-entre-queda-e-valorizacao-bras2617447. Acesso em: 18 nov. 2026.",
    "BROWN, T. B. et al. Language models are few-shot learners. In: ADVANCES IN NEURAL INFORMATION PROCESSING SYSTEMS, 33., 2020. Proceedings [...]. 2020. p. 1877-1901.",
    "BRYANT, C.; FELICE, M.; BRISCOE, T. Automatic annotation and evaluation of error types for grammatical error correction. In: ANNUAL MEETING OF THE ASSOCIATION FOR COMPUTATIONAL LINGUISTICS, 55., 2017, Vancouver. Proceedings [...]. Vancouver: ACL, 2017. p. 793-805.",
    "BRYANT, C. et al. Grammatical error correction: a survey of the state of the art. Computational Linguistics, v. 49, n. 3, p. 643-701, 2023.",
    "CHASE, H. LangChain. 2022. Repositório GitHub. Disponível em: https://github.com/langchain-ai/langchain. Acesso em: 18 nov. 2026.",
    "CUNHA, C.; CINTRA, L. Nova gramática do português contemporâneo. 7. ed. Rio de Janeiro: Lexikon, 2017.",
    "DAHLMEIER, D.; NG, H. T. Better evaluation for grammatical error correction. In: CONFERENCE OF THE NORTH AMERICAN CHAPTER OF THE ASSOCIATION FOR COMPUTATIONAL LINGUISTICS, 2012, Montréal. Proceedings [...]. Montréal: ACL, 2012. p. 568-572.",
    "DEEPSEEK. Models & pricing. Disponível em: https://api-docs.deepseek.com/quick_start/pricing. Acesso em: 18 nov. 2026.",
    "DEVLIN, J. et al. BERT: pre-training of deep bidirectional transformers for language understanding. In: CONFERENCE OF THE NORTH AMERICAN CHAPTER OF THE ASSOCIATION FOR COMPUTATIONAL LINGUISTICS, 2019, Minneapolis. Proceedings [...]. Minneapolis: ACL, 2019. p. 4171-4186.",
    "EFRON, B.; TIBSHIRANI, R. J. An introduction to the bootstrap. New York: Chapman & Hall, 1993.",
    "EPOCH AI. LLM inference price trends. 2025. Disponível em: https://epoch.ai/data-insights/llm-inference-price-trends. Acesso em: 18 nov. 2026.",
    "FANG, T. et al. Is ChatGPT a highly fluent grammatical error correction system? A comprehensive evaluation. arXiv:2304.01746, 2023.",
    "FEDUS, W.; ZOPH, B.; SHAZEER, N. Switch transformers: scaling to trillion parameter models with simple and efficient sparsity. Journal of Machine Learning Research, v. 23, n. 120, p. 1-39, 2022.",
    "GOOGLE. Gemini API pricing. Disponível em: https://ai.google.dev/gemini-api/docs/pricing. Acesso em: 18 nov. 2026.",
    "GUNDLACH, H. et al. The price of progress: algorithmic efficiency and the falling cost of AI inference. arXiv:2511.23455, 2025.",
    "HOLM, S. A simple sequentially rejective multiple test procedure. Scandinavian Journal of Statistics, v. 6, n. 2, p. 65-70, 1979.",
    "KAPLAN, J. et al. Scaling laws for neural language models. arXiv:2001.08361, 2020.",
    "LANGUAGETOOL. LanguageTool: style and grammar checker for 25+ languages. Repositório GitHub. Disponível em: https://github.com/languagetool-org/languagetool. Acesso em: 18 nov. 2026. Commit 09aa9f4.",
    "LIN, C.-Y. ROUGE: a package for automatic evaluation of summaries. In: TEXT SUMMARIZATION BRANCHES OUT, 2004, Barcelona. Proceedings [...]. Barcelona: ACL, 2004. p. 74-81.",
    "MCNEMAR, Q. Note on the sampling error of the difference between correlated proportions or percentages. Psychometrika, v. 12, n. 2, p. 153-157, 1947.",
    "META. Meta Model API: pricing and rate limits. Disponível em: https://dev.meta.ai/docs/pricing-rate-limits/. Acesso em: 18 nov. 2026.",
    "MIKOLOV, T. et al. Efficient estimation of word representations in vector space. arXiv:1301.3781, 2013.",
    "MINIMAX. Pricing overview. Disponível em: https://platform.minimax.io/docs/guides/pricing-paygo. Acesso em: 18 nov. 2026.",
    "MOONSHOT AI. Kimi API model inference pricing. Disponível em: https://platform.kimi.ai/docs/pricing/chat. Acesso em: 18 nov. 2026.",
    "NABER, D. A rule-based style and grammar checker. 2003. Dissertação (Diplomarbeit) – Universität Bielefeld, Bielefeld, 2003.",
    "NG, H. T. et al. The CoNLL-2014 shared task on grammatical error correction. In: CONFERENCE ON COMPUTATIONAL NATURAL LANGUAGE LEARNING: SHARED TASK, 18., 2014, Baltimore. Proceedings [...]. Baltimore: ACL, 2014. p. 1-14.",
    "OPENAI. API pricing. Disponível em: https://developers.openai.com/api/docs/pricing. Acesso em: 18 nov. 2026.",
    "OPENROUTER. Reflection: Beam 1.0. Disponível em: https://openrouter.ai. Acesso em: 18 nov. 2026.",
    "OUYANG, L. et al. Training language models to follow instructions with human feedback. In: ADVANCES IN NEURAL INFORMATION PROCESSING SYSTEMS, 35., 2022. Proceedings [...]. 2022. p. 27730-27744.",
    "PAPINENI, K. et al. BLEU: a method for automatic evaluation of machine translation. In: ANNUAL MEETING OF THE ASSOCIATION FOR COMPUTATIONAL LINGUISTICS, 40., 2002, Philadelphia. Proceedings [...]. Philadelphia: ACL, 2002. p. 311-318.",
    "PENTEADO, M. C.; PEREZ, F. Evaluating GPT-3.5 and GPT-4 on grammatical error correction for Brazilian Portuguese. arXiv:2306.15788, 2023.",
    "PIRES, R. et al. Sabiá: Portuguese large language models. In: BRAZILIAN CONFERENCE ON INTELLIGENT SYSTEMS, 12., 2023, Belo Horizonte. Proceedings [...]. Cham: Springer, 2023.",
    "QORIB, M. R.; AJI, A. F.; NG, H. T. Efficient and interpretable grammatical error correction with mixture of experts. In: FINDINGS OF THE ASSOCIATION FOR COMPUTATIONAL LINGUISTICS: EMNLP 2024, Miami. Proceedings [...]. Miami: ACL, 2024.",
    "RADFORD, A. et al. Improving language understanding by generative pre-training. San Francisco: OpenAI, 2018.",
    "RADFORD, A. et al. Language models are unsupervised multitask learners. San Francisco: OpenAI, 2019.",
    "SHAZEER, N. et al. Outrageously large neural networks: the sparsely-gated mixture-of-experts layer. In: INTERNATIONAL CONFERENCE ON LEARNING REPRESENTATIONS, 5., 2017, Toulon. Proceedings [...]. 2017.",
    "SINDICATO DOS JORNALISTAS PROFISSIONAIS DO CEARÁ (SINDJORCE). Pisos e tabelas: tabela de serviços avulsos. Fortaleza, 2026. Disponível em: https://www.sindjorce.org.br/pisos-e-tabelas/pisos-salariais/. Acesso em: 18 nov. 2026.",
    "SOUZA, F.; NOGUEIRA, R.; LOTUFO, R. BERTimbau: pretrained BERT models for Brazilian Portuguese. In: BRAZILIAN CONFERENCE ON INTELLIGENT SYSTEMS, 9., 2020, Rio Grande. Proceedings [...]. Cham: Springer, 2020. p. 403-417.",
    "VASWANI, A. et al. Attention is all you need. In: ADVANCES IN NEURAL INFORMATION PROCESSING SYSTEMS, 30., 2017, Long Beach. Proceedings [...]. 2017. p. 5998-6008.",
    "XAI. Models and pricing. Disponível em: https://docs.x.ai/docs/models. Acesso em: 18 nov. 2026.",
    "XIAOMI. MiMo API platform. Disponível em: https://mimo.mi.com. Acesso em: 18 nov. 2026.",
    "Z.AI. Pricing. Disponível em: https://docs.z.ai/guides/overview/pricing. Acesso em: 18 nov. 2026.",
]
for ref in REFS:
    par(ref, "ref")

h1("APÊNDICE A – NÚCLEO DO SCRIPT DE EXTRAÇÃO DO CONJUNTO DE DADOS")
par("O trecho abaixo é a função central do script extrair_grammar_xml.py, que transforma um exemplo do "
    "grammar.xml em uma linha do conjunto de dados. O script completo, que também percorre as categorias e "
    "regras, remove repetições e grava o CSV, está disponível em https://github.com/AllysonAlves1/TCC, junto com os dados, as saídas dos modelos e os scripts de análise.")
quadro("A.1", "Função de extração de um exemplo (Python)", [
    "def extrair_exemplo(example):",
    "    correction = example.get('correction')",
    "    if correction is None:          # exemplo de frase correta",
    "        return None",
    "    marker = example.find('marker')",
    "    if marker is None:              # sem trecho marcado",
    "        return None",
    "    antes = example.text or ''",
    "    errado = ''.join(marker.itertext())",
    "    depois = marker.tail or ''",
    "    corrigido = correction.split('|')[0]   # primeira sugestão",
    "    frase_incorreta = limpar(antes + errado + depois)",
    "    frase_correta = limpar(antes + corrigido + depois)",
    "    return frase_incorreta, frase_correta, limpar(errado), limpar(corrigido)"],
    "Elaborado pelo autor (2026).")

doc.save(SAIDA)
print("Rascunho salvo em", SAIDA)

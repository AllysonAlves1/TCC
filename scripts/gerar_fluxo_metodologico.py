#!/usr/bin/env python3
"""Gera a Figura 1 (fluxo metodológico) em figuras/fig_fluxo_metodologico.png."""
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

AZUL_FUNDO, AZUL_BORDA, TINTA, TINTA2 = "#e3eefb", "#2a78d6", "#0b0b0b", "#52514e"
ETAPAS = [
    ("1. Extração", "grammar.xml do LanguageTool\nscript Python (Apêndice A)\n3.658 frases de 500 regras"),
    ("2. Curadoria", "seleção manual pelo autor\n(estilo, ambiguidade, nomes próprios,\nmalformadas) → 1.206 frases"),
    ("3. Anotação", "autor + especialista em Letras\ntaxonomia: 4 categorias,\n30 subcategorias"),
    ("4. Preparação", "25 lotes CSV (até 50 frases)\nprompt padrão + taxonomia\nem JSON"),
    ("5. Execução", "22 modelos por agentes:\nClaude Code, Codex, OpenCode,\nAntigravity e Cursor"),
    ("6. Integridade", "linhas idênticas ao gabarito\ndeepseek-v4-pro excluído\n(100%) → 21 modelos"),
    ("7. Revisão do gabarito", "193 frases divergentes\nCunha & Cintra: 151 alteradas,\n1 excluída (+2 corrompidas)"),
    ("8. Avaliação", "1.203 frases · F0,5 por edição,\nacerto exato, classificação\nbootstrap e McNemar"),
    ("9. Custo", "tokens × preço oficial da API\ncusto por livro de\n80 mil palavras"),
]

fig, ax = plt.subplots(figsize=(7.2, 5.6))
ax.set_xlim(0, 3); ax.set_ylim(0, 3); ax.axis("off")
W, H = 0.86, 0.74
pos = {}
for i, (tit, txt) in enumerate(ETAPAS):
    lin, col = divmod(i, 3)
    if lin == 1:
        col = 2 - col  # zigue-zague: a segunda linha corre da direita para a esquerda
    x, y = col + 0.07, 2.13 - lin * 1.0
    pos[i] = (x, y)
    ax.add_patch(FancyBboxPatch((x, y), W, H, boxstyle="round,pad=0.012,rounding_size=0.04",
                                fc=AZUL_FUNDO, ec=AZUL_BORDA, lw=1.4))
    ax.text(x + W / 2, y + H - 0.11, tit, ha="center", va="center", fontsize=9, weight="bold", color=TINTA)
    ax.text(x + W / 2, y + H / 2 - 0.09, txt, ha="center", va="center", fontsize=7.2, color=TINTA2, linespacing=1.35)

def seta(a, b):
    (xa, ya), (xb, yb) = pos[a], pos[b]
    if abs(ya - yb) < 1e-6:  # mesma linha
        if xb > xa:
            p1, p2 = (xa + W + 0.012, ya + H / 2), (xb - 0.012, yb + H / 2)
        else:
            p1, p2 = (xa - 0.012, ya + H / 2), (xb + W + 0.012, yb + H / 2)
    else:  # desce para a linha seguinte
        p1, p2 = (xa + W / 2, ya - 0.012), (xb + W / 2, yb + H + 0.012)
    ax.add_patch(FancyArrowPatch(p1, p2, arrowstyle="-|>", mutation_scale=12, lw=1.4, color=AZUL_BORDA))

for i in range(len(ETAPAS) - 1):
    seta(i, i + 1)
fig.tight_layout()
fig.savefig("figuras/fig_fluxo_metodologico.png", dpi=300)
print("figuras/fig_fluxo_metodologico.png")

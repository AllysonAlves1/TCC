#!/usr/bin/env python3
"""Gera as figuras do artigo a partir de resultados/<pasta>/metricas.json.

Uso: python scripts/gerar_figuras_v2.py [resultados/v2_pre] [figuras] [sufixo]
"""
import json, os, sys
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import LinearSegmentedColormap

pasta = sys.argv[1] if len(sys.argv) > 1 else "resultados/v2_pre"
saida = sys.argv[2] if len(sys.argv) > 2 else "figuras"
suf = sys.argv[3] if len(sys.argv) > 3 else "pre"
os.makedirs(saida, exist_ok=True)
d = json.load(open(os.path.join(pasta, "metricas.json"), encoding="utf-8"))

AZUL, CINZA, TINTA, TINTA2, GRADE = "#2a78d6", "#a3a29c", "#0b0b0b", "#52514e", "#e6e5e1"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9, "axes.edgecolor": TINTA2,
                     "axes.labelcolor": TINTA, "xtick.color": TINTA2, "ytick.color": TINTA2,
                     "axes.spines.top": False, "axes.spines.right": False})

def br(x, casas=2):
    return f"{x:.{casas}f}".replace(".", ",")

# Figura 1: F0.5 com IC 95%
res = sorted(d["resumo"], key=lambda r: r["F05"])
fig, ax = plt.subplots(figsize=(6.3, 5.6))
y = range(len(res))
for i, r in enumerate(res):
    ax.plot([r["F05_IC_inf"], r["F05_IC_sup"]], [i, i], color=AZUL, lw=2, solid_capstyle="round", alpha=0.45)
    ax.plot(r["F05"], i, "o", color=AZUL, ms=6, mec="white", mew=1.2)
    ax.text(r["F05_IC_sup"] + 0.004, i, br(r["F05"], 3), va="center", fontsize=7.5, color=TINTA2)
ax.set_yticks(list(y)); ax.set_yticklabels([r["modelo"] for r in res], color=TINTA)
ax.set_xlabel("F0,5 por edição (ponto) e intervalo de confiança de 95% (barra)")
ax.grid(axis="x", color=GRADE, lw=0.8); ax.set_axisbelow(True)
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: br(v)))
fig.tight_layout(); fig.savefig(os.path.join(saida, f"fig_f05_ic_{suf}.png"), dpi=300); plt.close(fig)

# Figura 2: qualidade x custo (fronteira de Pareto)
custo = {c["modelo"]: c for c in d["custo"]}
pts = [(custo[r["modelo"]]["custo_livro_usd_x1"], r["F05"], r["modelo"]) for r in d["resumo"] if r["modelo"] in custo]
pts.sort()
fronteira, melhor = [], -1
for c, f, m in pts:
    if f > melhor:
        fronteira.append((c, f, m)); melhor = f
fset = {m for _, _, m in fronteira}
ROTULOS = {"MiMo-V2.6-Flash": (6, 6), "MiMo-V2.6-Pro": (-6, 7), "musespark-1.3": (-6, 7),
           "claude-sonnet-5.5": (-6, 8), "claude-opus-5.5": (-6, 7), "deepseek-v4.1-flash": (6, -10),
           "gemini-3.8-flash": (-6, 2), "MiniMax-M3": (6, -3), "beam": (6, -3)}
fig, ax = plt.subplots(figsize=(6.3, 4.4))
ax.plot([c for c, _, _ in fronteira], [f for _, f, _ in fronteira], color=AZUL, lw=2, zorder=2,
        label="Fronteira de Pareto (melhor F0,5 até aquele custo)")
for c, f, m in pts:
    na = m in fset
    ax.plot(c, f, "o", ms=8 if na else 7, color=AZUL if na else CINZA, mec="white", mew=1.5, zorder=3)
    if m in ROTULOS or na:
        dx, dy = ROTULOS.get(m, (6, 5))
        ax.annotate(m, (c, f), xytext=(dx, dy), textcoords="offset points", fontsize=7,
                    color=TINTA if na else TINTA2, ha="right" if dx < 0 else "left")
ax.plot([], [], "o", color=CINZA, ms=7, label="Demais modelos")
ax.set_xscale("log")
ax.set_xlabel("Custo estimado para revisar um livro de 80 mil palavras (US$, escala log)")
ax.set_ylabel("F0,5 por edição")
ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: br(v)))
ax.yaxis.set_major_locator(matplotlib.ticker.MultipleLocator(0.05))
ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: br(v)))
ax.grid(color=GRADE, lw=0.8); ax.set_axisbelow(True)
ax.legend(loc="center right", bbox_to_anchor=(1.0, 0.33), frameon=False, fontsize=7.5)
fig.tight_layout(); fig.savefig(os.path.join(saida, f"fig_qualidade_custo_{suf}.png"), dpi=300); plt.close(fig)

# Figura 3: acerto exato por subcategoria (n >= 15)
ordem_mod = [r["modelo"] for r in sorted(d["resumo"], key=lambda r: -r["F05"])]
subs = {}
for r in d["por_subcategoria"]:
    subs.setdefault(r["subcategoria"], {"n": r["n"]})[r["modelo"]] = r["Exata"]
linhas = sorted([s for s, v in subs.items() if v["n"] >= 15],
                key=lambda s: -sum(subs[s][m] for m in ordem_mod) / len(ordem_mod))
M = [[subs[s][m] for m in ordem_mod] for s in linhas]
cmap = LinearSegmentedColormap.from_list("azul", ["#cde2fb", "#86b6ef", "#3987e5", "#1c5cab", "#0d366b"])
fig, ax = plt.subplots(figsize=(7.2, 5.0))
im = ax.imshow(M, cmap=cmap, vmin=0.3, vmax=1.0, aspect="auto")
for i, row in enumerate(M):
    for j, v in enumerate(row):
        ax.text(j, i, f"{round(v*100)}", ha="center", va="center", fontsize=5.6,
                color="white" if v > 0.72 else TINTA)
ax.set_xticks(range(len(ordem_mod))); ax.set_xticklabels(ordem_mod, rotation=60, ha="right", fontsize=6.8)
ax.set_yticks(range(len(linhas))); ax.set_yticklabels([f"{s} (n={subs[s]['n']})" for s in linhas], fontsize=7.5)
ax.tick_params(length=0)
for s in ax.spines.values(): s.set_visible(False)
cb = fig.colorbar(im, ax=ax, fraction=0.03, pad=0.02)
cb.set_label("Acerto exato da frase (%)", fontsize=7.5)
cb.ax.yaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda v, _: f"{round(v*100)}"))
cb.outline.set_visible(False)
fig.tight_layout(); fig.savefig(os.path.join(saida, f"fig_subcategorias_{suf}.png"), dpi=300); plt.close(fig)
print("Figuras gravadas em", saida, "| fronteira:", [m for _, _, m in fronteira])

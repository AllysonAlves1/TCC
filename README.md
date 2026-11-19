# Modelos de linguagem na revisão gramatical do português brasileiro

Código, dados e resultados do Trabalho de Conclusão de Curso **"Modelos de linguagem de grande escala na revisão gramatical do português brasileiro: uma avaliação comparativa de qualidade e custo"** (IFPE, 2026).

O trabalho avalia 21 LLMs comerciais e de pesos abertos em duas tarefas:

- corrigir frases do português brasileiro com erro gramatical;
- classificar o tipo de erro.

Ele também estima quanto custaria revisar um livro de 80 mil palavras com cada modelo.

## Estrutura

```
datasets/
  grammar.xml, entities/*.ent           regras do LanguageTool (fonte das frases)
  extracao_bruta_2026-11-18.csv         saída do extrator (3.658 frases)
  dataset_erros_gramaticais.csv         conjunto anotado original (1.206 frases)
  dataset_erros_gramaticais_revisado.csv  conjunto após a revisão do gabarito
  dataset_erros_gramaticais_frases_incorretas.csv  entrada enviada aos modelos (id; frase)
  dataset_erros_gramaticais_rotulos_lt.csv  rótulos originais do LanguageTool recuperados
  revisao/                              revisão do gabarito e análise de falsos positivos
lotes/lote_001..025.csv                 as frases divididas em 25 lotes
resultados/
  <modelo>/lote_XXX.csv                 saída bruta de cada modelo, por lote
  dataset_erros_gramaticais_<modelo>.csv  saída de cada modelo, consolidada
  v2_pre/, v2_pos/                      métricas com o gabarito original e o revisado
  comparacao_pre_pos.csv                acurácia de classificação antes/depois da revisão
figuras/                                figuras do artigo
scripts/                                todo o código (ver abaixo)
```

## Etapas e scripts

| Etapa | Script | Saída |
|---|---|---|
| 1. Extração das frases do `grammar.xml` | `extrair_grammar_xml.py` | `datasets/extracao_bruta_*.csv` |
| 2. Recuperação dos rótulos do LanguageTool | `restaurar_rotulos_extracao.py` | `datasets/dataset_erros_gramaticais_rotulos_lt.csv` |
| 3. Execução dos modelos (via agentes) | `prompt_padrao.txt` + `comando_processar.txt` | `resultados/<modelo>/lote_XXX.csv` |
| 4. Consolidação dos lotes | `juntar_resultados.py <modelo>` | `resultados/dataset_erros_gramaticais_<modelo>.csv` |
| 5. Revisão do gabarito | `preparar_revisao.py gerar` / `aplicar` | `datasets/revisao/`, `dataset_..._revisado.csv` |
| 6. Métricas e custo | `calcular_metricas_v2.py` | `resultados/v2_pre/`, `resultados/v2_pos/` |
| 7. Comparação antes/depois da revisão | `comparar_pre_pos.py` | `resultados/comparacao_pre_pos.csv` |
| 8. Análise de falsos positivos | `amostra_falsos_positivos.py gerar` / `calcular` | `datasets/revisao/fp_*.csv`, `resultados/v2_pos/falsos_positivos.csv` |
| 9. Figuras | `gerar_fluxo_metodologico.py`, `gerar_figuras_v2.py` | `figuras/` |
| 10. Artigo (modelo do IFPE) | `gerar_rascunho_artigo.py` | `.docx` |

Os preços de API usados no custo estão em `scripts/precos.csv`. Foram consultados nas páginas oficiais em 18/11/2026.

## Como reproduzir

As saídas dos modelos já estão em `resultados/`. Para recalcular tudo a partir delas, com o [uv](https://docs.astral.sh/uv/) instalado:

```bash
bash scripts/reproduzir.sh
```

Esse script recalcula as métricas, a análise de falsos positivos, as figuras e o artigo (`TCC_artigo.docx`).

Sem o uv, instale as dependências e rode os scripts da tabela acima com `python`:

```bash
pip install -r requirements.txt
```

Para extrair as frases de novo a partir do LanguageTool:

```bash
python scripts/extrair_grammar_xml.py datasets/grammar.xml datasets/extracao_bruta.csv --entidades datasets/entities
```

### Métricas

- **Correção:** precisão, cobertura e F0,5 por edição (alinhamento por tokens) e acerto exato da frase. Os intervalos de confiança de 95% vêm de bootstrap com 1.000 reamostragens e semente 42. As diferenças entre os seis melhores modelos foram testadas com McNemar exato e correção de Holm.
- **Classificação:** acurácia e F1-macro da categoria e da subcategoria.
- **Custo:** tokens contados com o `tiktoken` (`o200k_base`) e multiplicados pelo preço oficial, extrapolados para um livro de 80 mil palavras. São reportados os cenários ×1, ×3 e ×10 para a saída, que representam os tokens de raciocínio.

### Exclusões

- **`deepseek-v4-pro`:** removido da análise porque 100% das linhas eram idênticas ao gabarito, o que indica vazamento.
- **Frases 961 e 982:** removidas porque ficaram corrompidas por um `;` sem aspas.
- **Frase 223:** excluída na revisão do gabarito. O motivo está em `datasets/revisao/ids_excluidos.csv`.

## Licenças e créditos

- `datasets/grammar.xml` e `datasets/entities/` vêm do [LanguageTool](https://github.com/languagetool-org/languagetool) (LGPL 2.1).
- A revisão dos rótulos e a análise de falsos positivos usaram como referência a *Nova gramática do português contemporâneo* (Cunha & Cintra).

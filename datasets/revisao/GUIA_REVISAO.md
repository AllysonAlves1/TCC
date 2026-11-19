# Guia da revisão do gabarito

O objetivo é corrigir rótulos de categoria e subcategoria que estejam errados, deixando um registro que a banca possa auditar. A revisão é feita pelo autor junto com o especialista em Letras que participou da anotação. Todos os comandos rodam a partir da pasta `TCC/`.

## 1. Planilha de revisão (já gerada)

`datasets/revisao/revisao_frases.csv` reúne **193 frases**. Em todas elas, pelo menos 80% dos 21 modelos concordam entre si numa subcategoria diferente da que está no gabarito.

As frases 961 e 982 ficaram de fora porque estão corrompidas no dataset e foram excluídas da avaliação. A conta inicial de 283 frases comparava os rótulos diferenciando maiúsculas e minúsculas; as frases a mais diferiam só nisso ("Concordância Nominal" e "Concordância nominal", por exemplo). Elas não precisam de revisão manual, porque o passo 3 padroniza essa grafia automaticamente.

Para regerar a planilha: `python scripts/preparar_revisao.py gerar`

## 2. Como preencher

Para cada linha:

1. Leia a frase incorreta, a frase correta e os tokens alterados.
2. Decida, junto com o especialista, **antes de olhar** as colunas `categoria_modelos` e `subcategoria_modelos`. O voto dos modelos não é argumento. Argumento é o que diz a gramática.
3. Preencha a coluna `decisao` com `MANTER`, `ALTERAR` ou `EXCLUIR`.
   - Use `EXCLUIR` quando a frase não serve para o teste, por exemplo quando a frase correta do LanguageTool está errada. Preencha só a `justificativa`. A frase continua no gabarito, para a numeração dos ids não mudar, mas sai da avaliação.
4. Se a decisão for `ALTERAR`, preencha também:
   - `subcategoria_nova`: precisa ser exatamente um nome da taxonomia do `prompt_padrao.txt`.
   - `categoria_nova`: opcional, porque o script deduz a categoria a partir da subcategoria.
   - `justificativa`: uma frase. Exemplo: "o erro é de concordância do adjetivo com o substantivo, não de flexão verbal".
   - `fonte_gramatica`: obra e seção. Exemplo: "BECHARA, Moderna Gramática Portuguesa, cap. Concordância".

Use uma gramática de referência e mantenha a mesma em toda a revisão: Bechara, Cunha & Cintra ou Rocha Lima.

## 3. Aplicar a revisão

    python scripts/preparar_revisao.py aplicar

O comando valida a planilha e recusa os casos abaixo, mostrando a lista de problemas:
- decisão vazia;
- subcategoria fora da taxonomia;
- `ALTERAR` sem justificativa ou sem fonte.

Se tudo estiver certo, ele gera:
- `datasets/dataset_erros_gramaticais_revisado.csv`: o gabarito revisado. O original não é alterado.
- `datasets/revisao/log_alteracoes.csv`: o registro de cada alteração. Ele vai para o apêndice do artigo.
- `datasets/revisao/ids_excluidos.csv`: as frases marcadas com `EXCLUIR`, com a justificativa.

O número de rótulos alterados, informado na saída do comando, entra na Seção 3.2 do artigo.

## 4. Recalcular as métricas com o gabarito revisado

Rode as duas versões, pré e pós, para que ambas avaliem exatamente as mesmas frases. O script lê o `ids_excluidos.csv` automaticamente e mostra quantas frases avaliou.

    python scripts/calcular_metricas_v2.py --saida resultados/v2_pre
    python scripts/gerar_figuras_v2.py resultados/v2_pre figuras pre

    python scripts/calcular_metricas_v2.py --base datasets/dataset_erros_gramaticais_revisado.csv --saida resultados/v2_pos
    python scripts/gerar_figuras_v2.py resultados/v2_pos figuras pos

O artigo reporta as duas versões, pré (`resultados/v2_pre`) e pós (`resultados/v2_pos`), lado a lado.

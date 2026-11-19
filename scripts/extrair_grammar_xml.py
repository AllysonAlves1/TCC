#!/usr/bin/env python3
"""Extrai frases com erro dos exemplos do grammar.xml do LanguageTool (portugues).

Padrao observado no XML
-----------------------
Cada regra do LanguageTool traz exemplos de uso. Os exemplos de frases
ERRADAS tem o atributo ``correction`` e marcam o trecho errado com <marker>:

    <category id="..." name="Gramática Geral">
      <rulegroup id="A_TRAVES_ATRAVÉS_CONFUSAO" name="...">
        <rule>
          ...
          <example correction="Através"><marker>A traves</marker> de várias entrevistas...</example>
          <example correction="através">Correram <marker>a traves</marker> do túnel.</example>
        </rule>
      </rulegroup>
    </category>

Daí saem todas as colunas:
- Frase incorreta         = texto do <example>, como está
- lista_tokens_incorretos = texto dentro de <marker>
- lista_tokens_corrigidos = valor do atributo correction
- Frase correta           = texto antes do marker + correction + texto depois do marker
- categoria_extracao      = atributo name da <category> que contém a regra
- subcategoria_extracao   = id do <rulegroup> (ou da <rule>, quando ela está fora de um grupo)

Exemplos sem ``correction`` são frases corretas (ou exemplos de antipadrões)
e são ignorados. Quando ``correction`` traz várias sugestões separadas por
"|", usa-se a primeira. Uma correção vazia significa "apagar o trecho".

As colunas categoria_revisor e subcategoria_revisor saem vazias: são
preenchidas depois, na revisão manual.

Entidades externas
------------------
O grammar.xml real declara entidades (&hifen;, &expressoes_de_tempo; ...) em
arquivos .ent separados, que ficam no repositório do LanguageTool em
languagetool-language-modules/pt/src/main/resources/org/languagetool/resource/pt/entities/.
O parser padrão do Python não carrega esses arquivos. Por isso o script lê os
.ent e substitui as entidades antes de interpretar o XML. Se os .ent não forem
encontrados, as entidades de caracteres (&deg;, &ordm; ...) são resolvidas pela
tabela do HTML e as demais viram um marcador; exemplos que contenham esse
marcador são descartados e contados no resumo final.

Uso (a partir da raiz do projeto TCC):
    python scripts/extrair_grammar_xml.py datasets/grammar.xml datasets/bruto.csv --entidades datasets/entities
    python scripts/extrair_grammar_xml.py datasets/grammar.xml datasets/bruto.csv --sem-desativadas
"""
from __future__ import annotations

import argparse
import csv
import html.entities
import os
import re
import sys
import xml.etree.ElementTree as ET

PREDEFINIDAS = {"amp", "lt", "gt", "quot", "apos"}
NAO_RESOLVIDA = "\u27e6{}\u27e7"  # ⟦nome⟧
RE_DOCTYPE = re.compile(r"<!DOCTYPE\s+\w+\s*\[(.*?)\]\s*>", re.S)
RE_SYSTEM = re.compile(r'<!ENTITY\s+%\s+\w+\s+SYSTEM\s+"([^"]+)"\s*>')
RE_ENTIDADE = re.compile(r"""<!ENTITY\s+([\w.-]+)\s+(?:"([^"]*)"|'([^']*)')\s*>""", re.S)
RE_REF = re.compile(r"&([A-Za-z_][\w.-]*);")

COLUNAS = ["Frase incorreta", "Frase correta", "lista_tokens_incorretos", "lista_tokens_corrigidos",
           "categoria_revisor", "subcategoria_revisor", "categoria_extracao", "subcategoria_extracao"]


def limpar(texto: str) -> str:
    """Junta espaços repetidos e remove espaço antes de pontuação (sobra de correções vazias)."""
    texto = re.sub(r"\s+", " ", texto).strip()
    return re.sub(r"\s+([,.;:!?…])", r"\1", texto)


def extrair_exemplo(example: ET.Element) -> tuple[str, str, str, str] | None:
    """Devolve (frase incorreta, frase correta, token incorreto, token corrigido) ou None."""
    correction = example.get("correction")
    if correction is None:
        return None  # exemplo de frase correta
    marker = example.find("marker")
    if marker is None:
        return None  # exemplo sem trecho marcado: não dá para montar a frase correta
    antes = example.text or ""
    errado = "".join(marker.itertext())
    depois = marker.tail or ""
    corrigido = correction.split("|")[0]
    frase_incorreta = limpar(antes + errado + depois)
    frase_correta = limpar(antes + corrigido + depois)
    return frase_incorreta, frase_correta, limpar(errado), limpar(corrigido)


def regras(raiz: ET.Element, incluir_desativadas: bool):
    """Percorre categoria -> (rulegroup ->) rule, devolvendo (categoria, identificador, rule)."""
    for categoria in raiz.iter("category"):
        nome_cat = categoria.get("name", "")
        if not incluir_desativadas and categoria.get("default") == "off":
            continue
        for filho in categoria:
            if not incluir_desativadas and filho.get("default") in {"off", "temp_off"}:
                continue
            if filho.tag == "rulegroup":
                for rule in filho.findall("rule"):
                    yield nome_cat, filho.get("id", ""), rule
            elif filho.tag == "rule":
                yield nome_cat, filho.get("id", ""), filho


def ler_entidades(texto_dtd: str) -> dict[str, str]:
    return {m.group(1): m.group(2) if m.group(2) is not None else m.group(3)
            for m in RE_ENTIDADE.finditer(re.sub(r"<!--.*?-->", "", texto_dtd, flags=re.S))}


def carregar_xml(caminho_xml: str, dir_entidades: str | None) -> tuple[ET.Element, list[str]]:
    """Lê o grammar.xml resolvendo as entidades declaradas nos arquivos .ent externos."""
    texto = open(caminho_xml, encoding="utf-8").read()
    entidades: dict[str, str] = {}
    faltando: list[str] = []
    doctype = RE_DOCTYPE.search(texto)
    if doctype:
        base = os.path.dirname(os.path.abspath(caminho_xml))
        for rel in RE_SYSTEM.findall(doctype.group(1)):
            candidatos = [os.path.normpath(os.path.join(base, rel))]
            if dir_entidades:
                candidatos.insert(0, os.path.join(dir_entidades, os.path.basename(rel)))
            achado = next((c for c in candidatos if os.path.exists(c)), None)
            if achado:
                entidades.update(ler_entidades(open(achado, encoding="utf-8").read()))
            else:
                faltando.append(os.path.basename(rel))
        entidades.update(ler_entidades(doctype.group(1)))  # entidades internas, se houver
        texto = texto[:doctype.start()] + texto[doctype.end():]

    def trocar(m: re.Match) -> str:
        nome = m.group(1)
        if nome in PREDEFINIDAS:
            return m.group(0)
        if nome in entidades:
            return entidades[nome]
        if nome in html.entities.name2codepoint:
            return chr(html.entities.name2codepoint[nome])
        return NAO_RESOLVIDA.format(nome)

    for _ in range(10):  # entidades podem conter outras entidades
        novo = RE_REF.sub(trocar, texto)
        if novo == texto:
            break
        texto = novo
    return ET.fromstring(texto), faltando


def extrair(caminho_xml: str, incluir_desativadas: bool = True,
            dir_entidades: str | None = None) -> tuple[list[dict], dict]:
    raiz, faltando = carregar_xml(caminho_xml, dir_entidades)
    resumo = {"ent_faltando": faltando, "exemplos_incorretos": 0, "sem_marker": 0,
              "entidade_nao_resolvida": 0, "sem_mudanca": 0, "repetidas": 0}
    linhas, vistos = [], set()
    for nome_cat, id_regra, rule in regras(raiz, incluir_desativadas):
        # findall("example") pega só os exemplos da regra, não os de <antipattern>.
        for example in rule.findall("example"):
            if example.get("correction") is None:
                continue  # exemplo de frase correta
            resumo["exemplos_incorretos"] += 1
            res = extrair_exemplo(example)
            if res is None:
                resumo["sem_marker"] += 1
                continue
            incorreta, correta, tok_errado, tok_certo = res
            if "\u27e6" in incorreta + correta:
                resumo["entidade_nao_resolvida"] += 1
                continue
            if incorreta == correta:
                resumo["sem_mudanca"] += 1
                continue
            if (incorreta, correta) in vistos:
                resumo["repetidas"] += 1
                continue
            vistos.add((incorreta, correta))
            linhas.append({
                "Frase incorreta": incorreta,
                "Frase correta": correta,
                "lista_tokens_incorretos": tok_errado,
                "lista_tokens_corrigidos": tok_certo,
                "categoria_revisor": "",
                "subcategoria_revisor": "",
                "categoria_extracao": nome_cat,
                "subcategoria_extracao": id_regra,
            })
    return linhas, resumo


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.split("\n")[0])
    ap.add_argument("xml", help="caminho do grammar.xml (languagetool-language-modules/pt/.../grammar.xml)")
    ap.add_argument("saida", help="CSV de saída (delimitador ';')")
    ap.add_argument("--entidades", help="pasta com os arquivos .ent do LanguageTool (messages.ent, misc.ent ...)")
    ap.add_argument("--sem-desativadas", action="store_true",
                    help="ignora regras e categorias com default=\"off\" ou \"temp_off\"")
    args = ap.parse_args()

    linhas, resumo = extrair(args.xml, not args.sem_desativadas, args.entidades)
    with open(args.saida, "w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=COLUNAS, delimiter=";")
        w.writeheader()
        w.writerows(linhas)
    regras_distintas = len({l["subcategoria_extracao"] for l in linhas})
    if resumo["ent_faltando"]:
        print("[aviso] arquivos .ent não encontrados: " + ", ".join(resumo["ent_faltando"])
              + " (use --entidades)", file=sys.stderr)
    print(f"Exemplos com correção no XML: {resumo['exemplos_incorretos']}", file=sys.stderr)
    print(f"  descartados sem <marker>: {resumo['sem_marker']}", file=sys.stderr)
    print(f"  descartados com entidade não resolvida: {resumo['entidade_nao_resolvida']}", file=sys.stderr)
    print(f"  descartados sem mudança: {resumo['sem_mudanca']} | repetidos: {resumo['repetidas']}", file=sys.stderr)
    print(f"{len(linhas)} frases extraídas de {regras_distintas} regras -> {args.saida}", file=sys.stderr)


if __name__ == "__main__":
    main()

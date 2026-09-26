# -*- coding: utf-8 -*-
"""
=============================================================================
Projeto : AuditAI Senado: Transparência e Análise Parlamentar com IA
Disciplina: Inteligência Artificial - 7º semestre - Ciência da Computação
Instituição: Universidade Presbiteriana Mackenzie - Faculdade de Computação
             e Informática (FCI)
Professor : Prof. Dr. Ivan Carlos Alcântara de Oliveira

Integrantes (nome - RA - e-mail):
  - Andrey Bezerra Virgínio dos Santos - 10420696 - 10420696@mackenzista.com.br
  - Igor Silva Araujo                  - 10428505 - 10428505@mackenzista.com.br
  - Julia Vitória Bomfim do Nascimento - 10425604 - 10425604@mackenzista.com.br
  - William Saran dos Santos Junior    - 10420128 - 10420128@mackenzista.com.br

Arquivo : src/carregamento.py
Síntese : Leitura do dataset "Brazilian Senate Speeches" (Kaggle, versão
          LITE - arquivo fsdb_lite.json). O arquivo tem ~935 MB, por isso é
          lido em streaming com a biblioteca ijson (um discurso por vez),
          evitando carregar o JSON inteiro na memória. Cada discurso é
          convertido em uma linha de um pandas.DataFrame com metadados
          (data, autor, partido, URL) e com o texto separado por papel
          (Autoral, Apartes, Presidencial e Externos).
=============================================================================
"""
from __future__ import annotations

import gzip
import json
from pathlib import Path
from typing import Iterator

import ijson
import pandas as pd

# Papéis de fala presentes em "Texto" (ver documentação do dataset no Kaggle)
PAPEIS = ("Autoral", "Apartes", "Presidencial", "Externos")


def _abrir(caminho: str | Path):
    """Abre o arquivo em modo binário, aceitando .json ou .json.gz."""
    caminho = Path(caminho)
    f = gzip.open(caminho, "rb") if caminho.suffix == ".gz" else open(caminho, "rb")
    # Os arquivos do dataset começam com BOM UTF-8 (EF BB BF), que o parser
    # JSON não aceita; se existir, é descartado.
    if f.read(3) != b"\xef\xbb\xbf":
        f.seek(0)
    return f


def iterar_discursos(caminho: str | Path) -> Iterator[tuple[str, dict]]:
    """Percorre o JSON de nível superior {CODIGO: registro} sem carregá-lo inteiro."""
    with _abrir(caminho) as f:
        # use_float=True evita objetos Decimal; kvitems('') itera o dicionário raiz
        for codigo, registro in ijson.kvitems(f, "", use_float=True):
            yield codigo, registro


def _contar_palavras(paragrafos: list[str]) -> int:
    return sum(len(p.split()) for p in paragrafos)


def registro_para_linha(codigo: str, reg: dict) -> dict:
    """Achata um registro do JSON em um dicionário (uma linha do DataFrame)."""
    autor = reg.get("Autor") or {}
    texto = reg.get("Texto") or {}
    nome = (autor.get("NomeSimples") or "").strip()

    linha = {
        "codigo": str(codigo),
        "url": reg.get("URL"),
        "data": reg.get("Data"),
        "autor_codigo": autor.get("Codigo"),
        "autor_nome": nome,
        "partido": autor.get("Partido"),
    }

    # Texto autoral: prioriza a chave do próprio autor; registra se há outras
    autoral: dict = texto.get("Autoral") or {}
    linha["autoral_n_chaves"] = len(autoral)
    linha["autor_em_autoral"] = nome in autoral
    paragrafos_autor = autoral.get(nome, [])
    if not paragrafos_autor and len(autoral) == 1:
        # caso a grafia da chave difira do NomeSimples, usa a única chave existente
        paragrafos_autor = next(iter(autoral.values()))
    linha["texto_autoral"] = "\n".join(p.strip() for p in paragrafos_autor if p and p.strip())
    linha["autoral_n_paragrafos"] = len(paragrafos_autor)
    linha["autoral_palavras"] = _contar_palavras(paragrafos_autor)

    # Demais papéis: apenas estatísticas (quantidade de oradores e de palavras)
    for papel in PAPEIS[1:]:
        falas: dict = texto.get(papel) or {}
        chave = papel.lower()
        linha[f"{chave}_n_oradores"] = len(falas)
        linha[f"{chave}_palavras"] = sum(_contar_palavras(v) for v in falas.values())
    return linha


def carregar_discursos(caminho: str | Path, limite: int | None = None,
                       tamanho_lote: int = 5000) -> pd.DataFrame:
    """Lê o fsdb_lite.json e devolve um DataFrame com um discurso por linha.

    Os registros são convertidos em lotes de `tamanho_lote` linhas: cada lote
    vira um DataFrame (texto armazenado em formato Arrow, mais compacto que
    strings Python) e só então o próximo é lido - isso mantém o pico de
    memória baixo mesmo com ~100 mil discursos.

    Parâmetros
    ----------
    caminho : caminho para fsdb_lite.json ou fsdb_lite.json.gz
    limite  : se informado, lê apenas os N primeiros discursos (útil para testes)
    """
    lotes, linhas = [], []
    for i, (codigo, reg) in enumerate(iterar_discursos(caminho)):
        if limite is not None and i >= limite:
            break
        linhas.append(registro_para_linha(codigo, reg))
        if len(linhas) == tamanho_lote:
            lotes.append(pd.DataFrame(linhas))
            linhas = []
    if linhas:
        lotes.append(pd.DataFrame(linhas))
    df = pd.concat(lotes, ignore_index=True)
    del lotes, linhas
    df["data"] = pd.to_datetime(df["data"], errors="coerce")
    df["ano"] = df["data"].dt.year.astype("Int64")
    return df


def carregar_lista_json(caminho: str | Path) -> list:
    """Lê os arquivos auxiliares pequenos (externos.json, partidos.json)."""
    with open(caminho, encoding="utf-8-sig") as f:  # utf-8-sig remove o BOM
        return json.load(f)

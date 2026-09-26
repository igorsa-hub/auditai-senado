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

Arquivo : src/preparacao.py
Síntese : Funções de preparação dos discursos para a futura etapa de busca
          semântica (RAG): normalização de texto, remoção de anotações
          taquigráficas entre parênteses, normalização para busca léxica
          (minúsculas e sem acentos), filtros de qualidade e segmentação do
          texto autoral em trechos ("chunks") com sobreposição, preservando
          os metadados necessários para agrupar resultados por parlamentar e
          citar a evidência (código do discurso, data, autor, partido, URL).
=============================================================================
"""
from __future__ import annotations

import hashlib
import re
import unicodedata

import pandas as pd

# ---------------------------------------------------------------------------
# Limpeza de texto
# ---------------------------------------------------------------------------
# Anotações da taquigrafia que não fazem parte do conteúdo do discurso,
# p.ex. "(Palmas.)", "(Pausa.)", "(Soa a campainha.)", "(Muito bem!)".
_ANOTACOES = re.compile(
    r"\((?:\s*)(?:palmas|pausa|soa a campainha|muito bem|risos|manifesta[cç][aã]o"
    r"|interven[cç][aã]o fora do microfone|fora do microfone|apoiad[oa]s?|n[aã]o apoiad[oa]"
    r"|tumulto|vaias?|o sr\.? presidente faz soar a campainha)[^()]{0,80}\)",
    flags=re.IGNORECASE,
)
_ESPACOS = re.compile(r"[ \t ]+")


# Rótulo do orador no início do parágrafo, resquício da página HTML, p.ex.
# "O SR. JEAN PAUL PRATES (PT - RN. Pela ordem.) – Voto sim..."
_ROTULO_ORADOR = re.compile(
    r"^(?:O|A)\s+SR[A]?\.\s+[A-ZÁÉÍÓÚÂÊÔÃÕÇÜ][A-ZÁÉÍÓÚÂÊÔÃÕÇÜ.\s'-]{1,60}?"
    r"(?:\s*\([^()]{0,120}\))?\s*[–—-]\s*",
    flags=re.MULTILINE,
)
# Metadados de cabeçalho entre parênteses, p.ex. "(PMDB - RO. Pela ordem.
# Sem revisão do orador.)" ou "(Sem apanhamento taquigráfico.)"
_CABECALHO = re.compile(
    r"\([^()]{0,120}(?:revis[aã]o do orador|apanhamento taquigr[aá]fico)[^()]{0,40}\)",
    flags=re.IGNORECASE,
)


def limpar_texto(texto: str) -> str:
    """Normaliza Unicode (NFC), remove rótulos de orador, cabeçalhos,
    anotações taquigráficas e espaços extras."""
    if not isinstance(texto, str):
        return ""
    t = unicodedata.normalize("NFC", texto)
    t = _ROTULO_ORADOR.sub("", t)
    t = _CABECALHO.sub(" ", t)
    t = _ANOTACOES.sub(" ", t)
    t = _ESPACOS.sub(" ", t)
    t = "\n".join(linha.strip() for linha in t.split("\n") if linha.strip())
    return t.strip()


def normalizar_busca(texto: str) -> str:
    """Minúsculas e sem acentos - usado apenas para busca léxica/contagens."""
    t = unicodedata.normalize("NFKD", texto.lower())
    return "".join(c for c in t if not unicodedata.combining(c))


def normalizar_partido(sigla: str) -> str:
    """Corrige apenas variações de grafia da mesma sigla (espaços, caixa,
    'PC DO B' x 'PCdoB', 'PODE' x 'PODEMOS', 'S/Partido' x 'S/PARTIDO').
    Mudanças históricas de nome (PMDB->MDB, PFL->DEM->UNIÃO etc.) são
    mantidas, pois o campo representa o partido na data do discurso."""
    if not isinstance(sigla, str) or not sigla.strip():
        return "N/D"
    s = " ".join(sigla.split()).upper()
    return {"PC DO B": "PCdoB", "PCDOB": "PCdoB", "PODE": "PODEMOS"}.get(s, s)


# ---------------------------------------------------------------------------
# Filtros de qualidade
# ---------------------------------------------------------------------------
def hash_textos(textos: pd.Series) -> pd.Series:
    """MD5 de cada texto - permite achar duplicatas sem comparar/copiar os
    textos inteiros (bem mais leve em memória que drop_duplicates no texto)."""
    return pd.Series([hashlib.md5(t.encode("utf-8")).hexdigest() for t in textos],
                     index=textos.index, dtype="str")


def aplicar_filtros(df: pd.DataFrame, min_palavras: int) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Aplica os filtros em sequência e devolve (df_filtrado, relatório).

    1) texto autoral vazio (após a limpeza);
    2) texto autoral duplicado (mesmo conteúdo com códigos diferentes);
    3) discurso autoral curto demais (< min_palavras), em geral procedimental
       (orientação de voto, "pela ordem" etc.).

    Observação: a lista externos.json NÃO é usada para excluir autores, pois
    a análise exploratória mostrou que ela contém suplentes que exerceram o
    mandato (ver notebook, seção 3.5).
    """
    etapas = []
    atual = df
    etapas.append(("Registros originais", len(atual)))

    atual = atual[atual["texto_limpo"].str.len() > 0]
    etapas.append(("Remove texto autoral vazio", len(atual)))

    atual = atual.loc[~hash_textos(atual["texto_limpo"]).duplicated(keep="first")]
    etapas.append(("Remove textos autorais duplicados", len(atual)))

    atual = atual[atual["palavras_limpo"] >= min_palavras]
    etapas.append((f"Remove discursos com menos de {min_palavras} palavras", len(atual)))

    rel = pd.DataFrame(etapas, columns=["etapa", "discursos_restantes"])
    rel["removidos"] = (-rel["discursos_restantes"].diff()).fillna(0).astype(int)
    return atual.copy(), rel


# ---------------------------------------------------------------------------
# Segmentação em trechos (chunks)
# ---------------------------------------------------------------------------
# Divide em sentenças: ponto/exclamação/interrogação seguido de espaço e
# letra maiúscula (ou aspas). Evita cortar em "Sr. Presidente" e "art. 5º".
_ABREVIACOES = ["Sr", "Sra", "Srs", "Sras", "Dr", "Dra", "art", "Art", "arts", "inciso",
                "Exª", "Exª", "Sª", "Prof", "Profª", "Gen", "Cel", "Dep", "Sen", "nº", "n"]
_ABREV = "".join(rf"(?<!\b{re.escape(a)}\.)" for a in _ABREVIACOES)
_SENTENCA = re.compile(r"(?<=[.!?])" + _ABREV + r"(?<!\b[A-Z]\.)\s+(?=[\"“A-ZÁÉÍÓÚÂÊÔÃÕÀÇ0-9])")


def dividir_sentencas(texto: str) -> list[str]:
    sentencas = []
    for paragrafo in texto.split("\n"):
        sentencas.extend(s.strip() for s in _SENTENCA.split(paragrafo) if s.strip())
    return sentencas


def segmentar(texto: str, max_palavras: int = 250, sobreposicao: int = 50) -> list[str]:
    """Agrupa sentenças consecutivas em trechos de até `max_palavras` palavras.

    Cada novo trecho recomeça com as últimas sentenças do anterior que somem
    até `sobreposicao` palavras, para não perder contexto na fronteira.
    Sentenças maiores que `max_palavras` são quebradas por janelas de palavras.
    """
    unidades: list[str] = []
    for s in dividir_sentencas(texto):
        palavras = s.split()
        if len(palavras) <= max_palavras:
            unidades.append(s)
        else:  # sentença gigante (raro): quebra em janelas
            passo = max_palavras - sobreposicao
            for i in range(0, len(palavras), passo):
                unidades.append(" ".join(palavras[i:i + max_palavras]))
                if i + max_palavras >= len(palavras):
                    break

    trechos: list[str] = []
    atual: list[str] = []
    n_atual = 0
    for u in unidades:
        n_u = len(u.split())
        if atual and n_atual + n_u > max_palavras:
            trechos.append(" ".join(atual))
            # sobreposição: mantém sentenças finais até `sobreposicao` palavras
            manter, n_manter = [], 0
            for s in reversed(atual):
                n_s = len(s.split())
                if n_manter + n_s > sobreposicao:
                    break
                manter.insert(0, s)
                n_manter += n_s
            # garante o limite: se sobreposição + nova sentença passar de
            # max_palavras, descarta sentenças da sobreposição
            while manter and n_manter + n_u > max_palavras:
                n_manter -= len(manter.pop(0).split())
            atual, n_atual = manter, n_manter
        atual.append(u)
        n_atual += n_u
    if atual:
        trechos.append(" ".join(atual))
    return trechos


def construir_trechos(df: pd.DataFrame, max_palavras: int = 250, sobreposicao: int = 50,
                      tamanho_lote: int = 5000) -> pd.DataFrame:
    """Gera a base de trechos com os metadados de cada discurso (em lotes,
    para limitar o uso de memória)."""
    partes = []
    for ini in range(0, len(df), tamanho_lote):
        cols = {k: [] for k in ("trecho_id", "codigo", "ordem", "data", "ano", "autor_nome",
                                "partido", "url", "texto", "n_palavras")}
        for linha in df.iloc[ini:ini + tamanho_lote].itertuples(index=False):
            for ordem, trecho in enumerate(segmentar(linha.texto_limpo, max_palavras, sobreposicao)):
                cols["trecho_id"].append(f"{linha.codigo}_{ordem:03d}")
                cols["codigo"].append(linha.codigo)
                cols["ordem"].append(ordem)
                cols["data"].append(linha.data)
                cols["ano"].append(linha.ano)
                cols["autor_nome"].append(linha.autor_nome)
                cols["partido"].append(linha.partido)
                cols["url"].append(linha.url)
                cols["texto"].append(trecho)
                cols["n_palavras"].append(len(trecho.split()))
        partes.append(pd.DataFrame(cols))
    return pd.concat(partes, ignore_index=True)

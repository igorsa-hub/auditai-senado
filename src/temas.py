# -*- coding: utf-8 -*-
"""
=============================================================================
Projeto : AuditAI Senado: Transparência e Análise Parlamentar com IA
Disciplina: Inteligência Artificial - 7º semestre - Ciência da Computação
Instituição: Universidade Presbiteriana Mackenzie - FCI
Professor : Prof. Dr. Ivan Carlos Alcântara de Oliveira

Integrantes (nome - RA):
  - Julia Vitória Bomfim do Nascimento - 10425604
  - William Saran dos Santos Junior    - 10420128

Arquivo : src/temas.py
Síntese : Temas-exemplo do projeto (os mesmos da sondagem léxica da N1),
          rótulos fracos por termos e mascaramento dos termos do tema.
          O mascaramento remove do texto de entrada as palavras que geraram
          o rótulo, para que os modelos não aprendam apenas a "achar a
          palavra" e sejam testados no que importa para a busca semântica:
          reconhecer o tema pelo contexto (deriva e descasamento de
          vocabulário).
Histórico de alterações (data - autor - descrição):
  - 20/11/2026 - William Saran dos Santos Junior - Criação do módulo (N2).
=============================================================================
"""
from __future__ import annotations

import re

import numpy as np
import pandas as pd

from preparacao import normalizar_busca

# Termos relacionados por tema, em minúsculas e sem acentos (idênticos aos da N1).
TEMAS: dict[str, list[str]] = {
    "Violência contra a mulher": [
        "violencia contra a mulher", "violencia contra as mulheres", "violencia domestica",
        "feminicidio", "feminicidios", "maria da penha", "medida protetiva",
        "medidas protetivas", "violencia de genero"],
    "Meio ambiente": [
        "meio ambiente", "desmatamento", "mudanca climatica", "mudancas climaticas",
        "aquecimento global", "queimadas", "desenvolvimento sustentavel", "efeito estufa"],
}

# Perguntas em linguagem natural usadas como consulta na etapa de recuperação.
CONSULTAS: dict[str, str] = {
    "Violência contra a mulher": "violência contra a mulher",
    "Meio ambiente": "meio ambiente e mudanças climáticas",
}


def padrao_tema(tema: str) -> re.Pattern:
    """Expressão regular (sobre texto normalizado) com todos os termos do tema."""
    termos = sorted(TEMAS[tema], key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(re.escape(t) for t in termos) + r")\b")


def normalizar_serie(textos: pd.Series) -> pd.Series:
    """Minúsculas e sem acentos (mesma normalização da busca léxica da N1)."""
    return pd.Series([normalizar_busca(t) for t in textos], index=textos.index, dtype="str")


def rotular(textos_norm: pd.Series, tema: str) -> np.ndarray:
    """Rótulo fraco: 1 se o texto contém algum termo relacionado ao tema."""
    p = padrao_tema(tema)
    return np.fromiter((p.search(t) is not None for t in textos_norm), dtype=bool,
                       count=len(textos_norm)).astype(int)


def mascarar(textos_norm: pd.Series, tema: str) -> pd.Series:
    """Remove (substitui por espaço) os termos do tema do texto normalizado."""
    p = padrao_tema(tema)
    return pd.Series([p.sub(" ", t) for t in textos_norm], index=textos_norm.index, dtype="str")


# Classes de caracteres para casar termos sem acento com o texto acentuado original.
_ACENTOS = {"a": "[aáàâãä]", "e": "[eéèêë]", "i": "[iíìîï]", "o": "[oóòôõö]", "u": "[uúùûü]", "c": "[cç]", "n": "[nñ]"}


def padrao_tema_original(tema: str) -> re.Pattern:
    """Como `padrao_tema`, mas aplicável ao texto ORIGINAL (com acentos e maiúsculas)."""
    def conv(t: str) -> str:
        return "".join(_ACENTOS.get(ch, re.escape(ch)) for ch in t)
    termos = sorted(TEMAS[tema], key=len, reverse=True)
    return re.compile(r"\b(?:" + "|".join(conv(t) for t in termos) + r")\b", flags=re.IGNORECASE)


def mascarar_original(textos: pd.Series, tema: str) -> pd.Series:
    """Remove os termos do tema preservando acentos e o restante do texto (entrada dos embeddings)."""
    p = padrao_tema_original(tema)
    return pd.Series([re.sub(r"[ \t]{2,}", " ", p.sub(" ", t)) for t in textos], index=textos.index, dtype="str")

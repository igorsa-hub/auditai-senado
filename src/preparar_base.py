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

Arquivo : src/preparar_base.py
Síntese : Reproduz, em script, as etapas E1-E3 do notebook 01 (leitura em
          streaming, limpeza, normalização de partidos e filtros de
          qualidade) e grava a base de discursos preparada em
          data/processed/discursos.parquet, usada nos experimentos N2.
Histórico de alterações (data - autor - descrição):
  - 20/11/2026 - William Saran dos Santos Junior - Criação do script (N2).
=============================================================================
"""
from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

RAIZ = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ / "src"))

from carregamento import carregar_discursos  # noqa: E402
from preparacao import aplicar_filtros, limpar_texto, normalizar_partido  # noqa: E402

MIN_PALAVRAS = 30


def main() -> None:
    arq = RAIZ / "data" / "raw" / "fsdb_lite.json"
    saida = RAIZ / "data" / "processed" / "discursos.parquet"
    saida.parent.mkdir(parents=True, exist_ok=True)

    t0 = time.time()
    df = carregar_discursos(arq)
    print(f"{len(df):,} registros lidos em {time.time() - t0:.0f} s", flush=True)

    df["partido_norm"] = df["partido"].map(normalizar_partido)
    df["texto_limpo"] = pd.Series(
        [limpar_texto(t) for t in df["texto_autoral"]], index=df.index, dtype="str")
    df["palavras_limpo"] = df["texto_limpo"].str.count(r"\S+").fillna(0).astype(int)

    dfp, rel = aplicar_filtros(df, min_palavras=MIN_PALAVRAS)
    print(rel.to_string(index=False), flush=True)
    dfp = dfp[["codigo", "url", "data", "ano", "autor_codigo", "autor_nome",
               "partido_norm", "texto_limpo", "palavras_limpo"]]
    dfp.to_parquet(saida, index=False)
    print(f"{len(dfp):,} discursos gravados em {saida} ({time.time() - t0:.0f} s)", flush=True)


if __name__ == "__main__":
    main()

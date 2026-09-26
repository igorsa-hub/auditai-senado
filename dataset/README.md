# Dataset — Brazilian Senate Speeches (versão LITE)

## Descrição breve

Conjunto público de **pronunciamentos (discursos) de parlamentares no plenário do Senado Federal**, coletado do portal oficial do Senado pelo autor LicoLabres e publicado no Kaggle. Cada registro traz a URL oficial, a data, o autor (código, nome e partido na data) e o texto do discurso **separado por papel de fala**: Autoral (o autor do pronunciamento), Apartes (outros senadores), Presidencial (quem preside a sessão) e Externos (não-senadores).

| Item | Valor |
|---|---|
| Fonte | LicoLabres (2024). *Brazilian Senate Speeches*. Kaggle. <https://www.kaggle.com/datasets/licolabres/brazilian-senate-speeches-lite> |
| Licença | CC BY-NC-SA 4.0 (atribuição, uso não comercial, compartilhamento pela mesma licença) |
| Versão usada | 5 (atualizada em 20/10/2024), arquivo `fsdb_lite.json` |
| Tamanho | 934.928.493 bytes (~935 MB) |
| Registros | 100.667 discursos de 486 parlamentares |
| Período efetivo | 03/01/1994 a 07/03/2024 (há 1 registro de 1980 e 1 de 1988 com datas atípicas; a descrição do Kaggle cita 1988–2024) |
| Palavras (texto autoral) | ~107 milhões |

## Arquivos

| Arquivo | Onde está | Conteúdo |
|---|---|---|
| `fsdb_lite.json` | **não versionado** (tamanho) — baixar do Kaggle para `data/raw/` | `{CODIGO: {URL, Data, Autor{Codigo, Partido, NomeSimples}, Texto{Autoral, Apartes, Presidencial, Externos}}}` |
| `partidos.json` | `data/raw/partidos.json` | dicionário `{nome do senador: partido}` (656 nomes) |
| `externos.json` | `data/raw/externos.json` | lista de 1.292 nomes de oradores não-senadores |
| `amostra/amostra_discursos.csv` | esta pasta | 300 discursos já preparados (amostra aleatória, semente 42) |
| `amostra/amostra_trechos.csv` | esta pasta | 2.000 trechos (*chunks*) já preparados (amostra aleatória, semente 42) |

Os arquivos originais começam com BOM UTF-8; o módulo `src/carregamento.py` trata isso.

## Como obter o arquivo principal

1. Entrar (com login) em <https://www.kaggle.com/datasets/licolabres/brazilian-senate-speeches-lite>.
2. Baixar **apenas** `fsdb_lite.json` (a versão LARGE, `fsdb_large.json`, não é usada).
3. Salvar em `data/raw/fsdb_lite.json` (também é aceita uma cópia compactada `data/raw/fsdb_lite.json.gz`).
4. Executar `notebooks/01_analise_exploratoria_preparacao.ipynb`, que gera as bases preparadas em `data/processed/`.

## Bases geradas pela preparação (não versionadas; regeneradas pelo notebook)

| Arquivo | Linhas | Colunas |
|---|---|---|
| `data/processed/discursos_preparados.parquet` | 89.017 | `codigo, url, data, ano, autor_codigo, autor_nome, partido, texto_limpo, palavras_limpo` |
| `data/processed/trechos.parquet` | 558.569 | `trecho_id, codigo, ordem, data, ano, autor_nome, partido, url, texto, n_palavras` |

As amostras em `amostra/` têm exatamente essas colunas.

## Observações de qualidade (detalhes no notebook e no artigo)

- 9.979 registros (9,9%) não têm texto autoral — em 2/3 deles o parlamentar presidia a sessão.
- ~18% das palavras de um registro são de outros oradores; **somente o texto Autoral** é usado.
- `externos.json` contém suplentes que exerceram mandato; por isso **não** é usado como filtro de autores.
- 61 rótulos de partido brutos → 42 após corrigir apenas grafia; renomeações históricas foram mantidas.
- Transcrições antigas têm erros de digitação e, às vezes, ausência de acentos.

## Anonimização

Não foi aplicada: os dados são públicos e referem-se a atos oficiais de agentes públicos no exercício do mandato (Lei 12.527/2011). Por minimização, as falas de terceiros (papel *Externos*) não entram na base de busca.

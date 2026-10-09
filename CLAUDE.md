# Comparador de gastos federais (2019–2026)

Contexto para o Claude Code continuar o projeto. Escrito em 09/10/2026, a partir de uma sessão de planejamento.

## Objetivo

Site-dashboard para a reta final do 2º turno de 2026 (eleição em 25/10/2026; confirmar a data). Deve permitir que o eleitor
verifique e compare **para onde foi o dinheiro federal** em cada governo, **onde houve aumento e onde houve corte**, por área
de política pública. O site mostra dados e contexto; **não recomenda voto** nem faz pedido de voto.

- Período: **2019–2022 (Bolsonaro)** contra **2023–2026 (Lula)**. 2026 vai só até o último bimestre publicado.
- Fora do MVP: estados, municípios, parlamentares, salários e presença. Ficam para depois da eleição.
- Prazo: cerca de 2 semanas, contadas a partir de 09/10.

## Princípios (não negociáveis)

1. **Neutralidade:** as mesmas métricas, o mesmo layout e os mesmos critérios para os dois governos. Sem adjetivos de juízo.
2. **Verificabilidade:** todo número tem link para a fonte, data de coleta e a conta explicada na página "Método".
3. **Contexto junto do número:** os cartões de contexto aparecem ao lado do gráfico, não escondidos numa página à parte.
4. Checar as regras do TSE sobre conteúdo eleitoral na internet e deixar claro quem mantém o site.

## Dados (já testados)

| Dado | Fonte | Acesso |
|---|---|---|
| Despesa da União por função e subfunção, bimestral | Tesouro / SICONFI, RREO **Anexo 02**, `id_ente=1` | `https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo?an_exercicio=AAAA&nr_periodo=P&co_tipo_demonstrativo=RREO&no_anexo=RREO-Anexo%2002&id_ente=1`. Aberta, JSON, cerca de 3 mil itens por chamada, sem chave. |
| IPCA mensal | Banco Central, SGS 433 | `https://api.bcb.gov.br/dados/serie/bcdata.sgs.433/dados?formato=json&dataInicial=01/01/2019&dataFinal=DD/MM/AAAA`. Uma `dataFinal` no futuro dá erro, então usar a data de hoje. |

Achados sobre a API do SICONFI:
- Os campos são: exercicio, periodo, rotulo, coluna, cod_conta, conta, valor (entre outros).
- Usar `rotulo == "Total das Despesas Exceto Intra-Orçamentárias"`.
- A coluna `conta` mistura funções, subfunções e as linhas "FUxx - ...". Filtrar pela lista fixa das 28 funções (está em `etl/funcoes.py`). Os nomes podem vir com espaço no fim, então aplicar `strip()`.
- Colunas úteis: "DOTAÇÃO ATUALIZADA (a)", "DESPESAS EMPENHADAS ATÉ O BIMESTRE (b)", "DESPESAS LIQUIDADAS ATÉ O BIMESTRE (d)".
- Em 09/10/2026, 2019–2025 estavam completos (bimestre 6) e 2026 ia até o bimestre 4 (janeiro a agosto).

Observação: o ambiente de nuvem não alcançava sites do governo, então a coleta foi feita pelo navegador. Na máquina local o script deve funcionar direto.

## Método (implementado em `etl/funcoes.py`)

- **Ano fechado:** despesa empenhada até o 6º bimestre (igual a liquidada mais restos a pagar não processados).
- **Mesmo período (janeiro a agosto) em todos os anos:** despesa liquidada até o 4º bimestre. O empenho no começo do ano reserva o valor anual das despesas obrigatórias, então o liquidado compara melhor no meio do ano.
- **Inflação:** IPCA, a preços do último mês publicado (era 2026-09). O ano fechado usa o índice médio do ano; o período janeiro a agosto usa o índice médio desses meses.
- **"Encargos Especiais" separado:** reúne juros, amortização e rolagem da dívida, além de transferências constitucionais. Ele é maior que todas as outras funções somadas e saltou em 2022 por causa da rolagem da dívida.
- **Médias por governo:** Bolsonaro usa 2019–2022; Lula usa 2023–2025 para ano fechado e 2023–2026 para janeiro a agosto.
- **Conferência feita:** o IPCA anual calculado bate com o oficial (2021: 10,06%; 2022: 5,78%, contra 5,79% oficial). O script também foi testado com respostas simuladas (paginação, filtro e deflator).

## Primeiros resultados (R$ bi a preços de set/2026, despesa empenhada, média por ano)

| Função | 2019–22 | 2023–25 | Var. | Jan–ago 19–22 | Jan–ago 23–26 | Var. |
|---|---|---|---|---|---|---|
| Previdência Social | 1079,0 | 1150,3 | +6,6% | 734,3 | 795,5 | +8,3% |
| Assistência Social | 302,4 | 310,5 | +2,7% | 199,3 | 204,6 | +2,6% |
| Saúde | 210,0 | 235,2 | +12,0% | 122,7 | 136,0 | +10,9% |
| Educação | 140,6 | 171,8 | +22,2% | 76,3 | 98,7 | +29,3% |
| Defesa Nacional | 115,1 | 104,0 | −9,7% | 63,5 | 59,0 | −7,0% |
| Trabalho | 106,3 | 121,8 | +14,5% | 72,5 | 88,0 | +21,4% |
| Agricultura | 31,4 | 40,6 | +29,4% | 12,5 | 15,6 | +24,7% |
| Administração | 33,8 | 31,4 | −7,1% | 19,2 | 17,8 | −6,9% |
| Ciência e Tecnologia | 9,7 | 24,0 | +147,6% | 3,8 | 8,1 | +110% |
| Gestão Ambiental | 5,9 | 20,1 | +242% | 2,2 | 15,7 | +607% |
| Transporte | 15,7 | 20,6 | +30,6% | 5,6 | 7,8 | +39,5% |
| Segurança Pública | 16,1 | 18,8 | +16,9% | 7,6 | 9,2 | +20,4% |

Total anual sem Encargos Especiais (R$ bi): 2019: 2004; 2020: 2521; 2021: 2065; 2022: 2084; 2023: 2260; 2024: 2368; 2025: 2438.

## Pendências de verificação antes de publicar

- [ ] **Ciência e Tecnologia (2025) e Gestão Ambiental (2024 em diante):** os saltos parecem vir de operações financeiras de fundos (FNDCT, Fundo Clima), ou seja, empréstimos, e não de gasto direto. Abrir as subfunções e, se preciso, separar por grupo de natureza da despesa (GND 5, inversões financeiras).
- [ ] **Habitação quase zero:** o Minha Casa Minha Vida é classificado em outras funções ou passa por fundos. Explicar no site ou buscar por programa.
- [ ] **2020 (pandemia):** o auxílio emergencial levou a Assistência Social a cerca de R$ 606 bi. Oferecer uma visão "sem créditos extraordinários" ou destacar o ano.
- [ ] **Atribuição de orçamento:** a proposta de 2019 foi enviada pelo governo Temer; a de 2023, pelo governo Bolsonaro, alterada pela PEC da Transição. Mostrar isso no site.
- [ ] **Regras fiscais:** teto de gastos (até 2023), arcabouço (2024 em diante) e pisos de Saúde e Educação. Fazer cartões de contexto.
- [ ] Conferir alguns totais contra o Relatório Resumido de Execução Orçamentária em PDF ou contra o Siga Brasil.

## Próximos passos

1. Rodar `python etl/funcoes.py` (gera `data/funcoes.json`) e conferir os números da tabela acima.
2. Coletar subfunções e programas para a tela "para onde foi o dinheiro" e para resolver as pendências.
3. Construir o front-end:
   - Comparador por função: barras lado a lado, alternando entre ano fechado e janeiro a agosto, e entre valor real e nominal.
   - Série anual de 2019 a 2026.
   - Lista "onde aumentou e onde cortou", ordenada por variação em R$ e em %.
   - Cartões de contexto.
   - Página "Método e fontes".
4. Publicar como site estático em CDN e agendar a coleta (o próximo bimestre sai no fim de novembro, depois da eleição).

## Arquitetura sugerida (inspirada em seuimposto.com, analisado em 09/10)

O site de referência ("Apuração 2026") usa:
- Preact com `htm` (JSX sem build), num `app.js` de cerca de 300 KB.
- Dados em JSONs estáticos e compactos em `/feed/*.json` (vetores por município) e um `POST /api/vivo` para a atualização ao vivo.
- Mapa em TopoJSON embutido, desenhado com SVG e canvas (sem Leaflet ou Mapbox).
- Dados de apoio em `.js` gerados por scripts Python a partir das fontes do TSE.
- Fontes Faustina e Geist, tema escuro, Cloudflare na frente e assets com hash no nome.

Para este projeto: ETL em Python gerando JSON, front estático (Preact com htm, ou React com Vite), gráficos com D3 ou uma biblioteca leve, e hospedagem no Cloudflare Pages.

## Estrutura

```
etl/funcoes.py   coleta SICONFI + IPCA → data/funcoes.json (só biblioteca padrão)
data/            saída do ETL (gerada)
```

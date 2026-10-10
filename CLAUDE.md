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

- [x] **Ciência e Tecnologia e Gestão Ambiental:** confirmado com a MSC (função × GND). Em 2025, 23,4 dos 35,0 bi de C&T e 26,5 dos 32,1 bi de Gestão Ambiental (nominais) são GND 5, inversões financeiras. O mesmo vale para Trabalho (28,9 bi, FAT/BNDES), Agricultura (19,7 bi) e Educação (7,8 bi, Fies). O site tem a opção "sem inversões financeiras", aplicada igualmente aos dois períodos, e marca as funções em que o GND 5 passa de 5%.
- [~] **Habitação quase zero:** há um cartão de contexto explicando. Falta confirmar onde a União classifica os aportes do MCMV/FAR (indício: Encargos Especiais, subfunção 846). Isso exige dados por ação (Portal da Transparência, arquivos "despesas-execucao", ou Siga Brasil).
- [x] **2020 (pandemia):** destacado no gráfico. A opção "excluir anos de calamidade" retira **2020 e 2024** (calamidade reconhecida pelo Congresso: DL 6/2020 e DL 36/2024), com a mesma regra para os dois governos.
- [x] **Atribuição de orçamento:** cartão "Quem elaborou o orçamento de cada ano".
- [x] **Regras fiscais:** cartões sobre teto/arcabouço, pisos de Saúde e Educação e precatórios.
- [~] **Conferência:** a MSC confere com o RREO centavo por centavo na maioria das funções e anos. As divergências aparecem na página "Método" (tabela `conferencia` em `painel.json`). Falta conferir alguns totais contra o RREO em PDF ou o Siga Brasil.
- [ ] **Cartões com `revisar: true` em `site/contexto.js`:** uma pessoa precisa conferir cada fato na fonte primária antes de publicar (pisos, DL 6/2020, DL 36/2024, MCMV, precatórios).
- [ ] **Quem mantém o site:** preencher `MANTENEDOR` em `site/app.js` e conferir as regras do TSE.

## Achados da sessão de 09/10 (tarde)

- **MSC orçamentária** (`/tt/msc_orcamentaria`, `id_ente=1`, `classe_conta=6`, `id_tv=ending_balance`) traz função, subfunção e natureza da despesa por linha. São cerca de 175 mil linhas por mês e cerca de 3 minutos por matriz. Contas de execução: 6.2.2.1.3.01 a .07 (as .05 a .07 são o empenhado inscrito em restos a pagar no fim do ano). Empenhado = soma das sete contas; liquidado = .03, .04 e .07. Natureza da despesa no formato "CGMMEE00" (o GND é o 2º dígito). Excluir a modalidade 91 (intra) para bater com o RREO.
- Na MSC, Encargos Especiais inclui o refinanciamento da dívida (subfunções 841 e 842), que o RREO não traz.
- **As subfunções do RREO não são estáveis:** o modelo do Anexo 02 muda (em 2025 o Bolsa Família foi para "Demais Subfunções"). As subfunções do site vêm da MSC, com código. A Portaria SOF/MPO 169/2024 criou a 245 (Serviços Socioassistenciais) e a 246 (Segurança de Renda) a partir de 2025; a 244 deixou de ser usada.

## Próximos passos

1. [x] Rodar `python etl/funcoes.py` e conferir os números da tabela acima (conferido em 09/10: bate).
2. [~] Subfunções coletadas (MSC, com código). Programas e ações ainda não (necessário para o MCMV).
3. [x] Front-end (primeira versão, `site/`):
   - Comparador por função com barras lado a lado, ano fechado ou jan–ago, real ou nominal, sem inversões financeiras e sem anos de calamidade.
   - Ordenação por tamanho, variação em R$ e em % (a lista "onde aumentou e onde cortou").
   - Página por função com série anual, médias por período, inversões hachuradas, subfunções e cartões.
   - Cartões de contexto ao lado do gráfico (`site/contexto.js`).
   - Página "Método e fontes", com a tabela de conferência MSC × RREO.
4. [ ] Revisão humana dos cartões `revisar: true`, preencher `MANTENEDOR`, revisar a neutralidade dos textos.
5. [ ] Publicar no Cloudflare Pages (pasta `site/`). Antes, considerar copiar o `htm/preact/standalone.module.js` para dentro de `site/` (hoje vem do unpkg).
6. [ ] Agendar a coleta (o próximo bimestre sai no fim de novembro, depois da eleição).

## Arquitetura sugerida (inspirada em seuimposto.com, analisado em 09/10)

O site de referência ("Apuração 2026") usa:
- Preact com `htm` (JSX sem build), num `app.js` de cerca de 300 KB.
- Dados em JSONs estáticos e compactos em `/feed/*.json` (vetores por município) e um `POST /api/vivo` para a atualização ao vivo.
- Mapa em TopoJSON embutido, desenhado com SVG e canvas (sem Leaflet ou Mapbox).
- Dados de apoio em `.js` gerados por scripts Python a partir das fontes do TSE.
- Fontes Faustina e Geist, tema escuro, Cloudflare na frente e assets com hash no nome.

Para este projeto: ETL em Python gerando JSON, front estático (Preact com htm, ou React com Vite), gráficos com D3 ou uma biblioteca leve, e hospedagem no Cloudflare Pages.

## Mapa de transferências por estado (09/10, noite)

- **Investimento por estado foi descartado:** no Portal da Transparência ("despesas-execucao"), só de 12% (dez/2022) a 25% (dez/2025) do GND 4 tem UF; o resto é "Nacional" ou região. A cobertura muda entre os períodos (provavelmente por causa das emendas), o que distorceria a comparação.
- **Mapa de transferências adotado:** arquivos mensais "transferencias" do Portal da Transparência, com UF do favorecido em 98–99% do valor, cobertura parecida nos dois períodos. Categorias: constitucionais (por fórmula), legais e voluntárias, e só investimento (GND 4). Valores por habitante usam o Censo 2022 para todos os anos.
- **Conferência:** o FPE por UF do Portal bate centavo por centavo com o arquivo mensal do Tesouro (CKAN, "Transferências Constitucionais Para Estados") em dez/2022 e dez/2025. O ETL repete essa conferência a cada execução (`conferencia_fpe` em `mapa.json`).
- **Atenção:** o servidor de downloads da CGU bloqueia temporariamente (HTTP 405) depois de cerca de 28 downloads seguidos. O ETL espera 20 s entre arquivos e tenta de novo com espera crescente. O cache mensal agregado fica em `data/raw/transf/`.

## Cores (decisão da usuária, 09/10)

2019–2022 (Bolsonaro) em azul e 2023–2026 (Lula) em vermelho, as cores dos partidos, em todo o site (`--gov-a` e `--gov-b` em `styles.css`). Aumento e corte continuam marcados por ▲/▼, não por cor.

## Aba Parlamentares (09/10, noite)

- Escopo escolhido pela usuária: deputados federais e senadores das legislaturas 56 e 57, com partido, UF, cargo, subsídio do cargo, cota parlamentar e presença no plenário.
- **Subsídio:** igual para todos, conferido no texto dos decretos: R$ 33.763,00 (DL 276/2014, desde fev/2015); pelo DL 172/2022, R$ 39.293,32 (jan/2023), R$ 41.650,92 (abr/2023), R$ 44.008,52 (fev/2024) e R$ 46.366,19 (fev/2025).
- **Presença na Câmara (Plenário):** frequência oficial pelo serviço legado `SitCamaraWS/sessoesreunioes.asmx/ListarPresencasParlamentar` (dia a dia: "Presença", "Ausência justificada" com motivo, "Ausência"). É o registro usado para o desconto de faltas. **A carteira da cota não serve** (às vezes é a de outra legislatura). O ETL consulta as carteiras 1 a 700 de cada legislatura, uma vez para a legislatura inteira, e associa ao deputado pelo nome devolvido, usando todos os nomes do histórico e a UF (`casar_carteira`). Conferido em 09/10: todos os que ficaram o ano inteiro no cargo têm frequência, e ninguém passa do total de dias com sessão do ano. São no máximo 3 consultas simultâneas (com 8, o servidor derruba as conexões), e um 404 significa "sem registro" (não repetir). Cerca de 35 min sem cache. **2020:** a frequência só foi registrada em 13 dias (fevereiro e março); nas sessões remotas, não. O site avisa.
- **Presença em comissões (Câmara):** reuniões formais encerradas fora do Plenário com presença no arquivo de presença em eventos (tipos em `TIPOS_COMISSAO`). É uma contagem, sem denominador.
- Deputados e senadores não batem ponto: não existe registro de dias trabalhados, e o site diz isso.
- **Presença no Senado:** dias com votação nominal (`/dadosabertos/votacao`), com códigos de ausência: NCom = não justificada; AP, MIS, LS, LP, LG, MERC… = justificadas. São só cerca de 36 a 40 dias por ano (conferido: a consulta anual e a soma das mensais dão o mesmo total). O código "NA" (64 ocorrências) está classificado como justificado; conferir o significado.
- **Cota:** Câmara pelo `ideCadastro`; Senado (CEAPS) só pelo nome, casado por palavras com um candidato único. Os nomes sem par ficam em `ceaps_sem_par` (2019: senadores da legislatura anterior, despesas de janeiro).

## Estrutura

```
etl/funcoes.py   RREO Anexo 02 + IPCA → data/funcoes.json (funções, subfunções do RREO, deflatores)
etl/gnd.py       MSC orçamentária → data/gnd.json (função × subfunção × GND), cerca de 45 min sem cache
etl/painel.py    junta tudo → site/data/painel.json (dados do comparador) e confere MSC × RREO
etl/transferencias.py  Portal da Transparência + IBGE + Tesouro → site/data/mapa.json (cerca de 30 min sem cache)
etl/malha.py     malha das UFs do IBGE → site/data/ufs.json (caminhos SVG já projetados)
etl/parlamentares.py   Câmara + Senado → site/data/parlamentares.json (cerca de 10 min sem cache)
data/raw/        cache das respostas das APIs (fora do git)
site/            front estático: index.html, app.js (Preact + htm via unpkg, sem build), mapa.js, util.js, contexto.js, styles.css
```

Ordem para atualizar: `python etl/funcoes.py && python etl/gnd.py && python etl/painel.py && python etl/transferencias.py` (`etl/malha.py` só uma vez).
Para ver localmente: `python -m http.server 8765 --directory site`.

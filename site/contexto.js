// Cartões de contexto exibidos ao lado dos gráficos.
// `funcoes`: nomes das funções em que o cartão aparece; "*" = em todas as telas.
// `revisar: true` = fato ainda não conferido na fonte primária por uma pessoa (ver CLAUDE.md).
// Regra de redação: descrever o que aconteceu, sem adjetivos de juízo, igual para os dois governos.

const PLANALTO = "https://www.planalto.gov.br/ccivil_03";

export const CONTEXTO = [
  {
    id: "autoria-orcamento",
    titulo: "Quem elaborou o orçamento de cada ano",
    funcoes: ["*"],
    texto:
      "O orçamento de um ano é proposto pelo Executivo em agosto do ano anterior e votado pelo Congresso. " +
      "O de 2019 foi enviado pelo governo Temer; os de 2020 a 2022, pelo governo Bolsonaro; o de 2023 também " +
      "foi enviado pelo governo Bolsonaro e alterado pela Emenda Constitucional 126/2022 (PEC da Transição), " +
      "que ampliou o limite de gastos daquele ano; os de 2024 a 2026, pelo governo Lula. " +
      "Neste site, cada ano é atribuído a quem governou durante a execução.",
    fontes: [{ nome: "EC 126/2022", url: `${PLANALTO}/constituicao/emendas/emc/emc126.htm` }],
  },
  {
    id: "regras-fiscais",
    titulo: "Regras fiscais em cada período",
    funcoes: ["*"],
    texto:
      "De 2017 a 2023 vigorou o teto de gastos (EC 95/2016): a despesa primária de cada ano era limitada " +
      "à do ano anterior corrigida pela inflação. A partir de 2024 vale o regime fiscal da Lei Complementar 200/2023 " +
      "(arcabouço fiscal): o limite cresce 70% do crescimento real da receita, com piso de 0,6% e teto de 2,5% acima da inflação.",
    fontes: [
      { nome: "EC 95/2016", url: `${PLANALTO}/constituicao/emendas/emc/emc95.htm` },
      { nome: "LC 200/2023", url: `${PLANALTO}/leis/lcp/lcp200.htm` },
    ],
  },
  {
    id: "pisos",
    titulo: "Pisos constitucionais de Saúde e Educação",
    funcoes: ["Saúde", "Educação"],
    texto:
      "Durante o teto de gastos (EC 95/2016), os pisos federais de Saúde e Educação foram corrigidos só pela inflação, a partir do valor " +
      "de 2017. A EC 126/2022 revogou essa regra, com o fim do teto pela LC 200/2023, e o TCU decidiu que os pisos calculados pela receita " +
      "voltam a valer a partir de 2024 (Acórdão 2338/2023): 15% da receita corrente líquida para Saúde (art. 198 da Constituição) e 18% da " +
      "receita de impostos, descontadas as transferências a estados e municípios, para Educação (art. 212). A regra de cálculo do piso " +
      "muda entre os dois períodos comparados.",
    fontes: [
      { nome: "EC 95/2016", url: `${PLANALTO}/constituicao/emendas/emc/emc95.htm` },
      { nome: "EC 126/2022", url: `${PLANALTO}/constituicao/emendas/emc/emc126.htm` },
      { nome: "LC 200/2023", url: `${PLANALTO}/leis/lcp/lcp200.htm` },
      { nome: "Constituição, arts. 198 e 212", url: `${PLANALTO}/constituicao/constituicao.htm` },
      { nome: "TCU, Acórdão 2338/2023", url: "https://portal.tcu.gov.br/imprensa/noticias/tcu-conclui-avaliacao-sobre-regras-fiscais-para-orcamento-da-saude-e-educacao" },
    ],
  },
  {
    id: "pandemia-2020",
    titulo: "2020: pandemia e créditos extraordinários",
    funcoes: ["*", "Assistência Social", "Saúde"],
    texto:
      "Em 2020 o Congresso reconheceu estado de calamidade pública (Decreto Legislativo 6/2020) e aprovou a EC 106/2020, " +
      "que permitiu gastos fora das regras fiscais por créditos extraordinários. O auxílio emergencial foi registrado " +
      "principalmente na função Assistência Social, o que explica o pico daquele ano. Use a opção “excluir anos de calamidade” " +
      "para ver as médias sem 2020 e 2024.",
    fontes: [
      { nome: "Decreto Legislativo 6/2020", url: `${PLANALTO}/portaria/dlg6-2020.htm` },
      { nome: "EC 106/2020", url: `${PLANALTO}/constituicao/emendas/emc/emc106.htm` },
    ],
  },
  {
    id: "rs-2024",
    titulo: "2024: calamidade no Rio Grande do Sul",
    funcoes: ["*"],
    texto:
      "Em 2024 o Congresso reconheceu calamidade pública em parte do Rio Grande do Sul (Decreto Legislativo 36/2024), " +
      "o que permitiu despesas federais por créditos extraordinários fora do limite do arcabouço. " +
      "Como em 2020, a opção “excluir anos de calamidade” retira esse ano das médias.",
    fontes: [{ nome: "Decreto Legislativo 36/2024", url: "https://www2.camara.leg.br/legin/fed/decleg/2024/decretolegislativo-36-7-maio-2024-795574-publicacaooriginal-171706-pl.html" }],
  },
  {
    id: "inversoes",
    titulo: "Empréstimos não são gasto direto",
    funcoes: ["*", "Ciência e Tecnologia", "Gestão Ambiental", "Trabalho", "Agricultura", "Educação", "Comércio e Serviços", "Comunicações", "Cultura", "Organização Agrária"],
    texto:
      "Parte da despesa de algumas funções é “inversão financeira” (grupo de natureza 5): dinheiro que o governo empresta " +
      "ou aplica e que, em geral, volta com juros. Exemplos: financiamentos do FNDCT (Ciência e Tecnologia), do Fundo Clima " +
      "(Gestão Ambiental), repasses do FAT ao BNDES (Trabalho), crédito rural (Agricultura) e Fies (Educação). " +
      "A opção “sem inversões financeiras” retira essa parte nos dois governos, com a mesma regra.",
    fontes: [{ nome: "SICONFI, MSC orçamentária (GND por função)", url: "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/msc_orcamentaria" }],
  },
  {
    id: "habitacao",
    titulo: "Por que Habitação aparece quase zerada",
    funcoes: ["Habitação", "Urbanismo", "Encargos Especiais"],
    texto:
      "O Minha Casa, Minha Vida quase não aparece na função Habitação. Parte do subsídio das faixas com financiamento é paga com recursos " +
      "do FGTS, que não faz parte do orçamento da União. Já os principais aportes da União ao programa são classificados em Encargos " +
      "Especiais: a integralização de cotas ao Fundo de Arrendamento Residencial (ação 00AF, uma inversão financeira) e as subvenções ao " +
      "financiamento habitacional (ação 00CW). Na função Habitação fica sobretudo o apoio à produção habitacional (ação 00TI), que cresceu " +
      "a partir de 2024. Acompanhar o programa por inteiro exige dados por ação, que este painel ainda não traz.",
    fontes: [
      { nome: "Portal da Transparência, execução da despesa", url: "https://portaldatransparencia.gov.br/download-de-dados/despesas-execucao" },
      { nome: "Portaria MCID 114/2023 (FAR)", url: "https://www.gov.br/cidades/pt-br/acesso-a-informacao/institucional/base-juridica/portarias/20231220_Portaria_MCID_114_MCMV_FAR_compilada.pdf" },
    ],
  },
  {
    id: "subfuncoes-2025",
    titulo: "Mudança de classificação em 2025",
    funcoes: ["Assistência Social"],
    texto:
      "A partir de 2025 a Portaria SOF/MPO 169/2024 criou as subfunções 245 (Serviços Socioassistenciais) e 246 (Segurança de Renda) " +
      "e renomeou a 241 e a 242. Transferências de renda que antes eram registradas em 244 (Assistência Comunitária) passaram para a 246. " +
      "O total da função não muda; só a divisão interna. Compare subfunções antes e depois de 2025 com cuidado.",
    fontes: [{ nome: "Nota TCE-PR sobre a Portaria SOF/MPO 169/2024", url: "https://tce.pr.gov.br/data/files/2E/60/15/5A/901D491059F9A8496D1819A8/Nota%20n%20009-2024%20-%20SIMAM%20-%20PORTARIA%20SOF%20MPO%20N%20169_%20DE%2012%20DE%20JUNHO%20DE%202024.pdf" }],
  },
  {
    id: "encargos",
    titulo: "Por que Encargos Especiais fica separado",
    funcoes: ["Encargos Especiais"],
    texto:
      "Encargos Especiais reúne juros e amortização da dívida pública e transferências constitucionais a estados e municípios. " +
      "É maior que todas as outras funções somadas e varia com a gestão da dívida, não com escolhas de política pública. " +
      "Por isso fica fora dos totais e aparece numa seção própria. O refinanciamento da dívida (rolagem) não entra nos valores.",
    fontes: [{ nome: "RREO Anexo 02 (SICONFI)", url: "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/rreo" }],
  },
  {
    id: "precatorios",
    titulo: "Precatórios adiados e pagos depois",
    funcoes: ["*", "Encargos Especiais"],
    texto:
      "A EC 114/2021 limitou o pagamento anual de precatórios (dívidas da União reconhecidas pela Justiça) de 2022 a 2026. Em 30/11/2023 o " +
      "STF declarou o limite inconstitucional, e a MP 1.200/2023 abriu R$ 93,1 bilhões para quitar os atrasados de 2022 e 2023 e antecipar " +
      "parte de 2024. Os precatórios são registrados quase todos na função Encargos Especiais, que fica fora dos totais do comparador: lá, " +
      "as sentenças judiciais pagas passaram de cerca de R$ 60 bilhões em 2022 para R$ 153 bilhões em 2023. A EC 136/2025 retirou os " +
      "precatórios da União do limite de despesas a partir de 2026.",
    fontes: [
      { nome: "EC 114/2021", url: `${PLANALTO}/constituicao/emendas/emc/emc114.htm` },
      { nome: "MP 1.200/2023 (Agência Senado)", url: "https://www12.senado.leg.br/noticias/materias/2023/12/27/medida-provisoria-possibilita-pagamento-de-r-93-1-bilhoes-em-precatorios" },
      { nome: "EC 136/2025", url: `${PLANALTO}/constituicao/emendas/emc/emc136.htm` },
      { nome: "SICONFI, MSC orçamentária", url: "https://apidatalake.tesouro.gov.br/ords/siconfi/tt/msc_orcamentaria" },
    ],
  },

  // ---------- parlamentares ----------
  {
    id: "parl-subsidio",
    titulo: "O subsídio é igual para todos",
    funcoes: ["Parlamentares"],
    texto:
      "Deputados e senadores recebem o mesmo subsídio mensal, fixado por decreto legislativo: R$ 33.763,00 de 2015 a 2022 " +
      "e, pelo Decreto Legislativo 172/2022, quatro reajustes entre janeiro de 2023 e fevereiro de 2025, até R$ 46.366,19. " +
      "O valor é bruto (antes de imposto de renda e contribuição previdenciária). No início e no fim do mandato há ainda uma ajuda de custo igual a um subsídio.",
    fontes: [{ nome: "Decreto Legislativo 172/2022", url: "https://www2.camara.leg.br/legin/fed/decleg/2022/decretolegislativo-172-21-dezembro-2022-793529-republicacao-166629-pl.html" }],
  },
  {
    id: "parl-presenca",
    titulo: "O que a presença mede",
    funcoes: ["Parlamentares"],
    texto:
      "Deputados e senadores não batem ponto, e não existe registro oficial de “dias trabalhados”. Na Câmara, a presença é a " +
      "frequência oficial nos dias com sessão deliberativa no Plenário, o registro usado para descontar do subsídio as faltas sem " +
      "justificativa; à parte, mostramos as reuniões de comissão com presença registrada. No Senado, são os dias com votação nominal. " +
      "Trabalho no gabinete e viagens ao estado não aparecem. Quem assumiu ou deixou o mandato no meio do ano é avaliado " +
      "só pelo período em que estava em exercício.",
    fontes: [
      { nome: "Câmara, Dados Abertos", url: "https://dadosabertos.camara.leg.br" },
      { nome: "Senado, votações nominais", url: "https://legis.senado.leg.br/dadosabertos/votacao" },
    ],
  },
  {
    id: "parl-cota",
    titulo: "Cota parlamentar não é salário",
    funcoes: ["Parlamentares"],
    texto:
      "A cota para o exercício da atividade parlamentar reembolsa despesas do mandato, como passagens, aluguel de escritório no estado, " +
      "combustível e divulgação, mediante nota fiscal. O limite mensal varia por estado, porque inclui passagens até Brasília. " +
      "Os valores são os reembolsos publicados por cada Casa no ano.",
    fontes: [
      { nome: "Câmara, gastos parlamentares", url: "https://www.camara.leg.br/transparencia/gastos-parlamentares" },
      { nome: "Senado, CEAPS", url: "https://www12.senado.leg.br/transparencia/dados-abertos-transparencia/dados-abertos-ceaps" },
    ],
  },

  // ---------- mapa de transferências ----------
  {
    id: "mapa-o-que-e",
    titulo: "O que o mapa mostra (e o que não mostra)",
    funcoes: ["Mapa"],
    texto:
      "O mapa soma as transferências da União a governos estaduais e municipais (incluindo seus fundos, como os de saúde). " +
      "Não entram os gastos diretos da União no estado, como obras federais, salários de servidores federais e benefícios " +
      "pagos diretamente às pessoas (aposentadorias do INSS, Bolsa Família, BPC). Repasses a entidades privadas, empresas e " +
      "organismos internacionais também ficam fora, porque a sede de quem recebe não indica o estado beneficiado " +
      "(por exemplo, a Conta de Desenvolvimento Energético, de alcance nacional, é gerida em São Paulo). Os valores fora do mapa aparecem ao lado dele.",
    fontes: [{ nome: "Portal da Transparência, Transferências", url: "https://portaldatransparencia.gov.br/download-de-dados/transferencias" }],
  },
  {
    id: "repasses-sem-uf",
    titulo: "Repasses extraordinários sem estado no Portal",
    funcoes: ["Mapa"],
    texto:
      "Alguns repasses extraordinários a estados e municípios aparecem no Portal da Transparência como um pagamento único à " +
      "tesouraria do Tesouro Nacional, sem a divisão por estado: a partilha da cessão onerosa do pré-sal (dez/2019, cerca de R$ 11 bi), " +
      "o auxílio financeiro da pandemia (2020, cerca de R$ 60 bi, LC 173/2020) e as transferências temporárias de compensação " +
      "de ICMS e de recomposição do FPE e do FPM (nov–dez/2023, cerca de R$ 16 bi), em valores nominais. Esses valores ficam fora do mapa nos dois períodos, " +
      "o que reduz mais os totais estaduais de 2019–2022. A opção “excluir anos de calamidade” retira 2020.",
    fontes: [
      { nome: "Portal da Transparência, Transferências", url: "https://portaldatransparencia.gov.br/download-de-dados/transferencias" },
      { nome: "LC 173/2020", url: `${PLANALTO}/leis/lcp/lcp173.htm` },
    ],
  },
  {
    id: "mapa-formula",
    titulo: "A maior parte segue fórmula legal",
    funcoes: ["Mapa"],
    texto:
      "As transferências constitucionais (Fundo de Participação dos Estados e dos Municípios, Fundeb, royalties) são divididas " +
      "por critérios fixados na Constituição e em lei, com coeficientes calculados pelo TCU, e acompanham a arrecadação de impostos. " +
      "O governo não escolhe quanto cada estado recebe nessa parte. Use o filtro “Tipo” para separá-las das transferências legais e voluntárias.",
    fontes: [{ nome: "Constituição, art. 159", url: `${PLANALTO}/constituicao/constituicao.htm` }],
  },
  {
    id: "mapa-emendas",
    titulo: "Emendas parlamentares também viram repasse",
    funcoes: ["Mapa"],
    texto:
      "Parte das transferências legais e voluntárias vem de emendas parlamentares, cuja execução passou a ser obrigatória " +
      "(EC 86/2015 para emendas individuais e EC 100/2019 para emendas de bancada). A EC 105/2019 criou as transferências especiais, " +
      "repassadas sem convênio. Por isso, a distribuição entre estados nessa parte também depende de decisões do Congresso.",
    fontes: [
      { nome: "EC 86/2015", url: `${PLANALTO}/constituicao/emendas/emc/emc86.htm` },
      { nome: "EC 100/2019", url: `${PLANALTO}/constituicao/emendas/emc/emc100.htm` },
      { nome: "EC 105/2019", url: `${PLANALTO}/constituicao/emendas/emc/emc105.htm` },
    ],
  },
  {
    id: "mapa-populacao",
    titulo: "Como é feita a conta por habitante",
    funcoes: ["Mapa"],
    texto:
      "Os valores por habitante usam a população do Censo 2022 do IBGE para todos os anos, nos dois períodos. " +
      "Com o mesmo denominador, a variação percentual de cada estado é a mesma em “por habitante” e em “total”. " +
      "Os valores são corrigidos pelo IPCA mês a mês.",
    fontes: [{ nome: "IBGE, Censo 2022", url: "https://servicodados.ibge.gov.br/api/v3/agregados/4709/periodos/2022/variaveis/93?localidades=N3[all]" }],
  },
];

// Na tela de uma função: primeiro os cartões específicos dela, depois os gerais.
// No mapa: só os cartões marcados com "Mapa".
export const cartoesPara = (funcao) => {
  const gerais = CONTEXTO.filter((c) => c.funcoes.includes("*"));
  if (!funcao) return gerais;
  const especificos = CONTEXTO.filter((c) => c.funcoes.includes(funcao));
  if (funcao === "Mapa") return especificos;
  return [...especificos, ...gerais.filter((c) => !especificos.includes(c))];
};

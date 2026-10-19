# Brief de decisão — Case Medway SalesOps

**Corte:** CSV B2C fornecido, com vendas registradas de 01/01/2025 a 31/07/2026; API B2B consultada em 18/10/2026, sem `updated_at` ou histórico de status. **Unidades:** B2C = valor pago registrado no período; B2B = valor mensal **contratado** dos contratos atualmente ativos. Não somar em uma suposta receita mensal total.

## 1. O crescimento B2C comparável é sobretudo de volume

| Jan–jul | Linhas | Valor pago | Valor médio/linha |
|---|---:|---:|---:|
| 2025 | 745 | R$ 6.679.396,85 | R$ 8.965,63 |
| 2026 | 1.760 | R$ 16.028.534,95 | R$ 9.107,12 |
| Variação | +136,24% | +139,97% | +1,58% |

**Leitura:** o aumento de valor acompanha principalmente o aumento de registros, não uma mudança grande do valor médio. Isso descreve a base, mas **não prova** novos clientes, maior conversão, aumento de preço ou melhora de margem: faltam IDs, leads, despesas e custos.

**Decisão possível:** preparar capacidade de atendimento e operação para o volume; investigar se o crescimento foi eficiente por canal/produto antes de ampliar orçamento. **Perguntar à gestão:** metas, taxa de conversão, CAC, margem, reembolso e capacidade de onboarding suportam esse ritmo?

## 2. O pico de setembro é disseminado e requer auditoria do evento

Setembro/2025: **650 linhas, R$ 6.028.639,25**. Em **30/09/2025**: **327 linhas, R$ 3.127.917,19**, ou **50,31%** das linhas e **51,88%** do valor mensal. O dia contém vendas nas **quatro origens**: Orgânico 122, Evento Presencial 80, Indicação Direta 70 e Embaixador 55. A participação de Orgânico no volume do dia foi 37,3%, contra 35,3% no restante do mês; Evento Presencial, 24,5% contra 23,5%. A concentração **não está restrita a uma única origem**.

**Interpretação responsável:** pode refletir campanha ampla, fechamento concentrado, lote retroativo ou escolha artificial da data, mas nenhuma dessas causas é demonstrada no CSV. **Decisão possível:** não usar o pico como tendência recorrente ou meta até cruzar timestamp de pagamento, ID de pedido, data de carga, calendário promocional, CRM e financeiro. Uma comparação com e sem 30/09 mostra a sensibilidade do resultado.

## 3. Mix B2C: contribuição não é eficiência

No histórico integral, **4.435 linhas e R$ 40.165.219,74** em valor pago, com o lançamento negativo preservado. Origem Orgânico: **1.742 linhas e R$ 16.183.886,45 (40,29% do valor)**; Evento Presencial: **983 e R$ 8.768.028,19**; Indicação Direta: **924 e R$ 8.578.961,13**; Embaixador: **786 e R$ 6.634.343,97**. Produto Extensivo R1: **1.295 e R$ 14.524.735,27 (36,16%)**. Curso Avulso: **767 e R$ 935.650,54**, mostrando que volume de linhas e valor podem apontar prioridades diferentes.

**Decisão possível:** cruzar origem × produto × ICP e comparar valor/linha, margem, CAC e atribuição. Não usar valor bruto por canal como ROI nem cupom como prova do canal causador.

## 4. B2B: concentração de carteira e ambiguidade contratual

A API retornou **28 IDs únicos**: **26 ativos, R$ 180.944/mês e 1.846 licenças**. Há **1 pausado (R$ 4.740/mês nominal)** e **1 churn (R$ 1.365/mês nominal)**, excluídos do valor mensal ativo. O plano Institucional Enterprise tem **6 contratos ativos e R$ 102.065/mês (56,41%)**; SP responde por **R$ 92.172/mês (50,94%)**. Plano e região se sobrepõem; esses percentuais **não são parcelas aditivas**.

A fotografia contém **12 contratos com início em 2025 ainda ativos (R$ 80.205/mês)** e **14 com início em 2026 ativos (R$ 100.739/mês)**. As 14 denominações de 2026 correspondem a instituições presentes em 2025, com sufixos como “Turma” ou “Renovação”. Isso **não demonstra dupla cobrança** nem novo cliente; contratos para turmas/licenças distintas podem coexistir.

**Decisão possível:** monitorar concentração Enterprise/SP e vigências; pedir ID canônico de instituição, vínculo contrato/turma, data fim, eventos de status, cobrança e uso de licenças. Só depois calcular churn, expansão, NRR ou receita realizada.

## 5. Qualidade e régua de confiança

- 746 datas B2C no formato `dd/mm/aaaa`; demais ISO. `quarter` foi consistente com as datas.
- 116 valores monetários têm ponto decimal; normalização errada inflaria drasticamente o total.
- Um lançamento negativo e um de valor zero ficaram na soma; a natureza do negativo não foi confirmada.
- Três linhas extras são idênticas a outras, mas **sem ID transacional** não é defensável excluir.
- B2C é exportação **estática** recebida; sem acesso à planilha viva, automação apenas reprocessa novas versões quando fornecidas.
- B2B é snapshot de status atual; datas de início não geram histórico mensal de MRR.
- A API do case usa HTTP; HTTPS testado falhou na validação do certificado. Token nunca deve ser enviado ao navegador; para operação real, exigir transporte seguro e rotação da credencial.

## Métricas que deliberadamente não apresentamos

**Receita total da área**, MRR histórico, ARR realizado, churn rate, NRR, CAC, ROI por origem, compradores únicos e “campanha causadora do pico” não são sustentados pelas fontes disponíveis. O dashboard separa fatos verificáveis de perguntas para a próxima camada de dados.

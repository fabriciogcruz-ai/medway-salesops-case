# Medway SalesOps — arquitetura implementada

**Objetivo:** pipeline reprodutível, dashboard público de três visões, leitura gerencial, slides editáveis e roteiro para vídeo narrado pelo candidato.

## Fontes e fluxo

1. `input/b2c-original.csv` é o arquivo entregue, preservado localmente e **excluído do repositório público**. `pipeline.py` valida esquema e trimestre, aceita datas ISO/BR e moedas com vírgula ou ponto decimal, sinaliza exceções, preserva linhas idênticas sem ID transacional e gera agregados em `public/data/b2c.json`.
2. `GET /contratos` usa token Bearer apenas no processo de coleta. Paginação, contagem declarada, IDs únicos e campos essenciais são validados. `pipeline.py --b2b-only` produz `public/data/b2b-snapshot.json` (sem nomes/IDs de instituições) com status, planos, regiões, coortes de início e cruzamento plano × região.
3. `.github/workflows/refresh-b2b.yml` consulta a API a cada hora com secret do GitHub, testa os agregados, commita o snapshot público e publica `public/` no GitHub Pages **na mesma execução**. O commit gerado pelo `GITHUB_TOKEN` não dispara outro workflow de push; por isso o deploy está no job de atualização. `.github/workflows/publish-pages.yml` publica mudanças de frontend por push.
4. `public/` é o dashboard sem build: três visões, filtro B2C, comparação jan–jul 2025/2026, ponte matemática volume × valor médio, anomalia diária por origem, matriz origem × produto, carteira B2B e matriz plano × região. No GitHub Pages lê snapshot B2B com carimbo, não chama a API em tempo real. Revalida o JSON a cada 15 minutos enquanto a aba está aberta.
5. `api/b2b.js` é uma **alternativa serverless para Vercel/local**: consulta a API na abertura com segredo no servidor e retorna apenas agregados. Não está em uso no link GitHub Pages; não misturar esses modos ao apresentar.

## Critérios de aceite

- B2C: 4.435 linhas e R$ 40.165.219,74 após normalização; comparativo jan–jul com +139,97% em valor, +136,24% em registros, +1,58% no valor médio por linha.
- B2B: 28 IDs distintos, 26 ativos, R$ 180.944/mês contratados, 1.846 licenças; sem fabricar histórico de MRR.
- Segurança: token não está em git/JSON/HTML/JS; CSV bruto e PDF com token não são publicados. Endpoint HTTP do case é limitação de transporte, não corrigida por manter segredo server-side.
- Testes: `python3 -m unittest discover -s tests -v`, `node --test tests/test_api.cjs`, `node --check public/app.js`; invariantes conciliam agregados de todas as dimensões.
- Visual: logo SVG extraído de `medway.com.br`, azul `#00205B`, verde-água `#01CFB5`, Montserrat; navegador desktop/móvel e PPTX renderizado conferidos.
- Entrega externa: link GitHub Pages acessível em janela anônima; rotina agendada executada ao menos uma vez e logs/verificação do snapshot lidos antes de afirmar automação ativa.

## Limites de fonte

Sem link da planilha viva, não existe atualização automática de **novas vendas B2C na origem**. Substituir o CSV e rodar o pipeline atualiza os agregados. A API B2B não traz eventos históricos de status nem data fim; o valor mensal contratado atual não equivale a receita recebida. O consolidado separa unidades, não soma grandezas incompatíveis.

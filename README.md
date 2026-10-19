# Case Técnico SalesOps — Medway

**Candidato:** Fabrício Cruz  
**Entregáveis:** pipeline reproduzível, dashboard de três visões, apresentação e roteiro de vídeo.  
**Documentos analíticos:** [`docs/decision-brief.md`](docs/decision-brief.md) (evidências → decisão), [`INSIGHTS_RESEARCH.md`](INSIGHTS_RESEARCH.md) (exploração independente), [`docs/brand-medway.md`](docs/brand-medway.md) (marca extraída do site oficial) e [`docs/ui-easyui-review.md`](docs/ui-easyui-review.md) (padrões de interação adaptados, sem troca de identidade).

## Resumo executivo

A análise separa **valor pago por venda B2C** de **valor mensal contratado ativo B2B**. A visão executiva coloca ambas as linhas lado a lado, sem somar grandezas incompatíveis. O B2C é um CSV estático entregue no processo seletivo; o B2B vem de uma API com token. Na publicação principal via GitHub Pages, uma GitHub Action agendada coleta e publica somente o agregado B2B; o navegador relê o snapshot periodicamente. O carimbo de coleta fica visível. A função serverless Vercel é uma implementação alternativa para consulta B2B na abertura, mas **não é usada no link GitHub Pages**.

### Métricas auditadas no recebimento

| Indicador | Valor | Definição |
|---|---:|---|
| B2C · registros | 4.435 | Linhas do CSV, não compradores únicos |
| B2C · valor pago | R$ 40.165.219,74 | Soma de `valor_pago` normalizado, incluindo ajuste negativo e zero |
| B2C · cobertura | 01/01/2025 a 31/07/2026 | `data_venda`, dias BR/ISO normalizados |
| B2B · contratos | 28 | IDs únicos na API, snapshot |
| B2B · ativos | 26 | `status=ativo` no snapshot |
| B2B · valor mensal ativo | R$ 180.944,00 | Soma de `valor_mensal` somente ativos; **não é caixa nem receita histórica** |

## Arquitetura

```text
input/b2c-original.csv ─┐
                        ├─ pipeline.py ─ validação/reconciliação ─ public/data/*.json
API B2B /contratos ──────┘                                  │
                                                             ▼
                                                     dashboard public/
API B2B /contratos ── api/b2b.js (token no servidor) ────────┘
```

- `pipeline.py` conserva o CSV original localmente, trata formatos monetários/datas sem perda e gera apenas **agregados necessários à interface** para o browser. O JSON público exclui cortes diários por cupom e embaixador e mantém somente a anomalia agregada de 30/09 para evitar células de venda única.
- `api/b2b.js` é função serverless Vercel. Retorna apenas agregados; não expõe token, nomes de instituições ou contratos individuais.
- `.github/workflows/refresh-b2b.yml` agenda uma atualização **a cada hora** do **snapshot agregado B2B** como fonte da publicação GitHub Pages; depende do secret `MEDWAY_B2B_TOKEN` e de Actions habilitadas. A configuração está ativa: execução manual e primeira execução natural `schedule` validadas em 18/10/2026 (coleta em 19/10/2026 00:13 UTC, 28 contratos/26 ativos), com readback do JSON público. GitHub Actions pode atrasar ou descartar ticks; o carimbo e o aviso de defasagem são parte do controle, não um SLA garantido.
- `.github/workflows/publish-pages.yml` executa testes Python/Node e valida JavaScript **antes** de publicar `public/` no GitHub Pages; o workflow B2B aplica os mesmos testes após atualizar o snapshot e antes de commit/deploy. Os testes que exigem o CSV bruto são pulados no runner público (o CSV não está no repositório); localmente rodam com o arquivo recebido.
- O dashboard tem filtros de período B2C, três visões e legenda de fonte/atualização. KPIs, série, rankings, matriz, alertas de qualidade e destaque do pico respeitam o filtro. O comparativo anual usa **somente meses de 2026 selecionados**, contra os mesmos meses de 2025 como referência explicitamente rotulada; quando não há meses de 2026, não exibe comparação. A fotografia B2B não é filtrada pelo período B2C. Na falha da API agendada, mantém o último snapshot **com carimbo de data que expõe defasagem**.
- A página [`public/insights.html`](public/insights.html) é um **brief de decisão** separado do filtro do dashboard: compara jan–jul/2025 com jan–jul/2026, deriva contribuições por origem e produto dos agregados públicos e lê a foto B2B atual. Propõe teste controlado de Ads para Extensivo R1/R+, preservação de Orgânico/Indicação, validação de upsell do Curso Avulso e acompanhamento Enterprise × SP. **Não declara Google/Meta vencedores, ROI, CAC, margem nem verba ótima:** faltam custos, funil, IDs de cliente/pedido e incrementalidade. Os números B2B atualizam com o mesmo snapshot agendado.
- A API fornecida usa HTTP. HTTPS foi testado, mas a cadeia do certificado falhou na validação. O token permanece server-side; para produção, exigir TLS válido e rotação de credencial. Não desabilitar validação TLS.

## Rodar localmente

**Requisitos:** Python 3.9+ e Node.js 20+ (testes da função serverless). Não há dependências Python de runtime.

```bash
cd /caminho/medway-salesops
# O CSV recebido já está em input/b2c-original.csv
python3 pipeline.py --b2c-only
# Para atualizar B2B, definir MEDWAY_B2B_TOKEN em variável de ambiente,
# nunca no código, no terminal histórico ou no repositório:
python3 pipeline.py
# Prévia estática (B2B usa snapshot rotulado):
python3 -m http.server 8776 --directory public
# Prévia completa com /api/b2b (requer MEDWAY_B2B_TOKEN):
python3 dev_server.py
```

Abra `http://127.0.0.1:8777/` para testar a função local que consulta a API B2B. **No link público GitHub Pages, a atualização vem do snapshot horário gerado pelo GitHub Actions; não há função serverless chamada a cada visita.**

**Atualizar B2C:** substituir `input/b2c-original.csv` por nova exportação com o mesmo esquema e executar `python3 pipeline.py --b2c-only` no build/deploy (ou gatilho de CI). **A origem não atualiza sozinha:** nenhum acesso à planilha viva foi fornecido. Não apresentar o CSV fixo como sincronização automática do Google Sheets.

## Apresentação e vídeo

- **Versão V2 para apresentação:** `deliverables/Medway_SalesOps_Fabricio_Cruz_V2.pptx` e `.pdf`, com **8 slides principais + 3 apêndices fora do vídeo**; 4 gráficos nativos editáveis. A versão anterior foi preservada apenas como histórico.
- `deliverables/Roteiro_Video_12min_V2.md`: narrativa de decisão, perguntas de defesa e uso de IA/ferramentas; alvo de 11–12 minutos com a voz do candidato. **Nenhum vídeo foi gravado automaticamente.**
- O gerador `make_deck.py` usa `python-pptx` e `cairosvg`; no macOS, Cairo pode precisar estar instalado via Homebrew. Os arquivos Montserrat e licença OFL estão em `assets/fonts/`. O gerador lê os JSONs auditados e falha se as métricas-chave divergirem. Exemplo: `python3 make_deck.py` após instalar essas dependências.
- A cópia em PDF foi exportada do PPTX via Keynote; não é gerada por `make_deck.py`. **`deliverables/` não é publicado no repositório: anexar PPTX/PDF e vídeo separadamente na submissão.**

## Testes

```bash
python3 -m unittest discover -s tests -v
node --test tests/test_api.cjs
node --test tests/test_filter.cjs
node --test tests/test_insights.cjs
node --check public/app.js
node --check public/insights.js
```

## Publicação

**Caminho principal — GitHub Pages:**

1. Criar repositório público `fabriciogcruz-ai/medway-salesops-case` com somente código, `public/data/` e workflows. `.gitignore` protege `input/`, PDF, PPTX e `.env`.
2. Configurar `MEDWAY_B2B_TOKEN` como secret do repositório via stdin (nunca no comando, código, browser ou URL).
3. Ativar GitHub Pages com origem `GitHub Actions`; a rotina `publish-pages.yml` publica `public/`.
4. Disparar `refresh-b2b.yml` manualmente uma vez e verificar que a coleta passou, agregados foram commitados e o Pages foi republicado. A agenda **horária** usa cron UTC (minuto 17); execuções podem atrasar, por isso o carimbo de coleta é indispensável.
5. Abrir o link público em janela anônima e testar três visões e filtros. **No Pages, o B2B é snapshot agendado, não consulta em tempo real.** A página revalida o JSON a cada 15 minutos se permanecer aberta.

**Alternativa Vercel:** `vercel.json` publica `public/` e `api/b2b.js` atende `/api/b2b`. Requer conta/segredo `MEDWAY_B2B_TOKEN` no ambiente de preview; no Vercel, a função server-side consulta a API ao abrir. Sem segredo, só o snapshot funciona e deve ficar rotulado.

Nunca publicar o CSV bruto, o PDF que contém o token ou `input/` inadvertidamente. O site público expõe apenas agregados.

## Dicionário e limites

- `valor_pago`: campo informado na exportação B2C; não assumir reconhecimento contábil, margem ou preço de tabela.
- `count B2C`: linhas. Sem ID do pedido/cliente, não contar compradores únicos nem retirar linhas idênticas por suposição.
- `valor_mensal B2B`: valor de contrato; não é faturamento confirmado, recebimento ou MRR histórico.
- `num_licencas B2B`: licenças do contrato; não mede uso/ativação.
- Status B2B reflete **agora**; `data_inicio` mede início de contrato, sem eventos de pausa/churn ou data fim.
- CSV entregue termina em 31/07/2026. Um dashboard acessado depois dessa data precisa mostrar explicitamente que o B2C está congelado.
- Os valores negativos/zero são preservados; a classificação de estorno é hipótese, não fato confirmado.
- A métrica consolidada legítima é um **painel de desempenho dos dois motores**, não uma soma artificial de bases distintas.

## Uso de IA — declaração para a apresentação

A IA ajudou a estruturar hipóteses, gerar código inicial, documentação e propostas de visualização. As métricas foram calculadas de novo via scripts e reconciliadas por soma independente, testes automatizados e inspeção visual. A IA não criou registros, não inferiu causas sem evidência, não converteu snapshot de status em série temporal histórica, nem substituiu a validação do candidato. No vídeo, Fabrício deve descrever com honestidade seu processo real de revisão e as decisões que de fato tomou.

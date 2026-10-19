# UI review — EasyUI aplicado ao case Medway

**Referência consultada:** https://easyui.site/ e páginas [Interactive Area Chart](https://easyui.site/components/interactive-area-chart), [Pill Navigation](https://easyui.site/components/pill-navigation) e [UnfoldAccordion](https://easyui.site/components/unfold-accordion). Revisão em 18/10/2026. O site apresenta componentes React; este projeto usa HTML/CSS/JS sem build, portanto adaptamos padrões de interação, não copiamos implementação.

## Aplicado

1. **Navegação segmentada:** abas executiva/B2C/B2B em uma única peça visual, com estado ativo inequívoco em azul Medway, foco de teclado e alvo móvel adequado. Mantém três visões do case.
2. **Divulgação progressiva:** metodologia em `<details>/<summary>` nativos. A tese, evidências e decisões ficam antes da explicação de fonte/limites; o detalhamento continua acessível a quem precisa auditar.
3. **Carregamento com forma estável:** esqueleto que antecipa dois indicadores e um gráfico enquanto JSON é carregado, sem animação decorativa. Erro de carga continua explícito.
4. **Feedback de frescor:** se o snapshot B2B ultrapassar três horas sem coleta validada, texto e indicador visual mudam para “coleta atrasada”; a hora exibida é da coleta, não da última alteração na API.
5. **Acessibilidade de leitura:** verde-água escurecido para texto (`#007F73`, contraste calculado 4,90:1 contra branco), mantendo a cor oficial no logo e nos acentos não textuais. Eixos usam cinza com contraste 5,03:1. Fonte de notas ampliada no celular. O comparativo B2C tem tabela recolhível com valores exatos para leitura sem hover.
6. **Manutenibilidade:** HTML, CSS e JavaScript formatados com Prettier; a interface continua sem dependência de runtime React ou EasyUI.

## Rejeitado de propósito

- **Gooey Menu / Neon Edge Button / Liquid Toggle:** efeito ornamental não ajuda uma decisão de SalesOps e desviaria da marca Medway.
- **Troca para gráfico de área animado:** o gráfico mensal em barras é mais direto para comparar períodos discretos; mantém rótulo acessível e tooltip de valor exato por mouse/teclado.
- **Copiar a tipografia Geist/Inter do EasyUI:** Montserrat e o SVG do logo da Medway prevalecem sobre a vitrine externa.

## Verificação local

- Viewports de 320, 360, 390, 768, 1024 e 1440 px sem overflow de documento; tabelas longas mantêm rolagem interna.
- Troca de abas, filtro B2C e abertura do disclosure conferidos no navegador.
- Simulação de snapshot quatro horas antigo exibiu “B2B · coleta atrasada” e aviso contextual, sem alterar as métricas.
- **Pendente antes de declarar publicação:** rodar testes após os ajustes, publicar no GitHub Pages e reler o URL público exato. O botão de consulta imediata da API pertence ao branch local `wip/refresh-button` e não deve ser apresentado como ativo no Pages.

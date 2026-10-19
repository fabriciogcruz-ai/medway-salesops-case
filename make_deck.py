#!/usr/bin/env python3
"""Decision-led Medway case deck V2: nine video slides + three appendix slides.

Visual rhythm: navy decision slides, white evidence slides, ice methodology slides.
"""
from pathlib import Path
from io import BytesIO
import json
import datetime as dt
from zoneinfo import ZoneInfo
import ctypes.util
_cairo = Path('/opt/homebrew/opt/cairo/lib/libcairo.2.dylib')
if _cairo.exists():
    _find_library = ctypes.util.find_library
    ctypes.util.find_library = lambda name: str(_cairo) if name in ('cairo','cairo-2') else _find_library(name)
import cairosvg
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.enum.shapes import MSO_SHAPE
from pptx.chart.data import CategoryChartData
from pptx.enum.chart import XL_CHART_TYPE, XL_TICK_MARK

ROOT=Path(__file__).resolve().parent
B=json.loads((ROOT/'public/data/b2c.json').read_text())
C=json.loads((ROOT/'public/data/b2b-snapshot.json').read_text())
snapshot_at=dt.datetime.fromisoformat(C['fetched_at']).astimezone(ZoneInfo('America/Sao_Paulo')).strftime('%d/%m/%Y %H:%M')
OUT=ROOT/'deliverables/Medway_SalesOps_Fabricio_Cruz_V2.pptx'
OUT.parent.mkdir(exist_ok=True)
prs=Presentation();prs.slide_width=Inches(13.333);prs.slide_height=Inches(7.5)
NAVY=RGBColor(0,32,91);BLUE=RGBColor(16,60,120);AQUA=RGBColor(1,207,181);WHITE=RGBColor(255,255,255)
ICE=RGBColor(235,244,249);PALE=RGBColor(224,241,242);MUTED=RGBColor(79,99,118)
GRID=RGBColor(220,230,237)
logo=BytesIO(cairosvg.svg2png(url=str(ROOT/'public/medway-logo.svg'),output_width=550))

def fmt(n,dec=0):return f'{n:,.{dec}f}'.replace(',','X').replace('.',',').replace('X','.')
def money(c,dec=2):return 'R$ '+fmt(c/100,dec)
def pct(f):return fmt(f*100,2)+'%'
def rect(s,x,y,w,h,color):
    sh=s.shapes.add_shape(MSO_SHAPE.RECTANGLE,Inches(x),Inches(y),Inches(w),Inches(h))
    sh.fill.solid();sh.fill.fore_color.rgb=color;sh.line.fill.background();return sh
def txt(s,value,x,y,w,h,size=17,color=NAVY,bold=False,align=None):
    sh=s.shapes.add_textbox(Inches(x),Inches(y),Inches(w),Inches(h));tf=sh.text_frame
    tf.clear();tf.word_wrap=True;tf.margin_left=tf.margin_right=tf.margin_top=tf.margin_bottom=0
    for i,line in enumerate(str(value).split('\n')):
        p=tf.paragraphs[0] if i==0 else tf.add_paragraph();p.text=line
        p.font.name='Montserrat';p.font.size=Pt(size);p.font.bold=bold;p.font.color.rgb=color
        if align:p.alignment=align
    return sh
def base(n,section,title,dark=False,source=None,shade=False):
    s=prs.slides.add_slide(prs.slide_layouts[6]);s.background.fill.solid();s.background.fill.fore_color.rgb=NAVY if dark else ICE if shade else WHITE
    if dark:rect(s,.48,.27,1.76,.5,WHITE)
    s.shapes.add_picture(logo,Inches(.60 if dark else .55),Inches(.34),width=Inches(1.52))
    txt(s,'SALESOPS  /  MEDWAY',2.38,.40,4,.23,10,WHITE if dark else MUTED,True)
    txt(s,section.upper(),9.15,.40,3.55,.23,10,AQUA if dark else MUTED,True,PP_ALIGN.RIGHT)
    txt(s,title,.65,1.06,12.03,1.1,30,WHITE if dark else NAVY,True)
    if source:txt(s,source,.66,6.81,11.85,.26,10,WHITE if dark else MUTED)
    txt(s,f'{n:02d} / 09' if n<=9 else f'APÊNDICE {n-9} · FORA DO VÍDEO',9.65,7.12,3.02,.23,10,WHITE if dark else MUTED,True,PP_ALIGN.RIGHT)
    return s
def chart(s,cats,series,x,y,w,h,maxval,kind=XL_CHART_TYPE.COLUMN_CLUSTERED):
    data=CategoryChartData();data.categories=cats
    for name,vals in series:data.add_series(name,vals)
    ch=s.shapes.add_chart(kind,Inches(x),Inches(y),Inches(w),Inches(h),data).chart
    ch.has_legend=len(series)>1
    if ch.has_legend:
        ch.legend.font.name='Montserrat';ch.legend.font.size=Pt(11)
    ch.category_axis.tick_labels.font.name='Montserrat';ch.category_axis.tick_labels.font.size=Pt(11)
    ch.category_axis.tick_labels.font.color.rgb=MUTED;ch.category_axis.major_tick_mark=XL_TICK_MARK.NONE
    ch.value_axis.tick_labels.font.name='Montserrat';ch.value_axis.tick_labels.font.size=Pt(10)
    ch.value_axis.tick_labels.font.color.rgb=MUTED;ch.value_axis.major_tick_mark=XL_TICK_MARK.NONE
    ch.value_axis.minimum_scale=0;ch.value_axis.maximum_scale=maxval
    ch.value_axis.has_major_gridlines=True;ch.value_axis.major_gridlines.format.line.color.rgb=GRID
    for i,ser in enumerate(ch.series):
        ser.format.fill.solid();ser.format.fill.fore_color.rgb=AQUA if i else BLUE
        ser.format.line.fill.background()
    return ch

def metric(s,big,label,x,y,w: float=4.0,color=NAVY):
    txt(s,big,x,y,w,.83,40,color,True);txt(s,label,x,y+.90,w,.69,15,WHITE if color==AQUA and s.background.fill.fore_color.rgb==NAVY else MUTED)

m25=[next(r for r in B['monthly'] if r['name']==f'2025-{i:02d}') for i in range(1,8)]
m26=[next(r for r in B['monthly'] if r['name']==f'2026-{i:02d}') for i in range(1,8)]
v25=sum(r['cents'] for r in m25);v26=sum(r['cents'] for r in m26)
n25=sum(r['count'] for r in m25);n26=sum(r['count'] for r in m26)
gv=v26/v25-1;gn=n26/n25-1;gt=(v26/n26)/(v25/n25)-1
assert (v25,v26,n25,n26)==(667939685,1602853495,745,1760)
assert (round(gv*100,2),round(gn*100,2),round(gt*100,2))==(139.97,136.24,1.58)
sep=next(r for r in B['monthly'] if r['name']=='2025-09')
day=next(r for r in B['daily'] if r['name']=='2025-09-30')
do=sorted((r for r in B['daily_origin'] if r['date']=='2025-09-30'),key=lambda r:-r['cents'])
dp=sorted((r for r in B['daily_product'] if r['date']=='2025-09-30'),key=lambda r:-r['cents'])
assert (day['count'],day['cents'],sep['cents'])==(327,312791719,602863925)
assert sum(r['cents'] for r in do)==day['cents']==sum(r['cents'] for r in dp)
active=C['active_monthly_cents'];cell=next(r for r in C['plan_region'] if r['plan']=='Institucional Enterprise' and r['region']=='SP')
assert active==18094400 and C['active_contracts']==26
assert (cell['count'],cell['active_monthly_cents'],round(cell['active_monthly_cents']/active*100,2))==(4,6705000,37.06)
event=B['event_types'][0];ambassador=B['ambassadors'][0];icp=B['by_icp'][0]
audit={r['name']:r for r in B['coupon_audit']}
top_pair=max(B['icp_product'],key=lambda r:r['cents'])
assert (event['name'],event['count'],event['cents'])==('Encontro Local',278,258706000)
assert (ambassador['name'],ambassador['count'],ambassador['cents'])==('Embaixador 07',61,49570057)
assert (icp['name'],icp['count'],icp['cents'])==('Recém-formado',1191,1089572468)
assert (audit['Códigos diferentes']['count'],audit['Códigos coincidentes']['count'])==(705,36)
assert (top_pair['icp'],top_pair['product'],top_pair['count'],top_pair['cents'])==('Recém-formado','Extensivo R1',380,425940196)

# MAIN 1 — answer first.
s=base(1,'Tese executiva','Crescimento B2C pede eficiência; concentração pede validação.',dark=True)
metric(s,'+139,97%','valor pago · jan–jul 2026 vs. 2025',.74,2.53,5.2,AQUA)
rect(s,.75,4.58,10.85,1.22,RGBColor(18,68,108))
txt(s,'Decisão: auditar atribuição e pico; segmentar B2C; proteger B2B.',1.00,4.94,10.28,.54,22,WHITE,True)
txt(s,'Pergunta do case: como B2C e B2B performam juntos? Unidades distintas, sem soma artificial.',.76,6.30,11.9,.40,14,WHITE)

# MAIN 2 — comparable window and one visual.
s=base(2,'B2C · crescimento','O valor pago mais que dobrou em sete meses equivalentes.',source='Fonte: CSV B2C fornecido · valor_pago por data_venda · jan–jul em cada ano; inclui lançamentos negativo e zero.')
txt(s,'+139,97%',.76,2.23,4.6,.95,47,NAVY,True)
txt(s,money(v25)+'  →  '+money(v26),.78,3.27,11.3,.51,22,NAVY,True)
txt(s,'VALOR PAGO MENSAL · R$ MIL · EIXO A PARTIR DE ZERO',.78,4.03,11.4,.30,12,MUTED,True)
chart(s,['jan','fev','mar','abr','mai','jun','jul'],[('2025',[r['cents']/100000 for r in m25]),('2026',[r['cents']/100000 for r in m26])],.82,4.39,11.58,2.13,3200)

# MAIN 3 — multiplicative decomposition without equal charts.
s=base(3,'B2C · motor','O crescimento veio quase todo de mais registros.',source='Fonte: CSV B2C · jan–jul 2025 vs. jan–jul 2026. Valor = registros × ticket médio; variações arredondadas.',shade=True)
metric(s,'+136,24%','volume · 745 → 1.760 registros',.76,2.20,5.38,NAVY)
rect(s,6.34,2.38,5.43,2.24,WHITE)
txt(s,'TICKET MÉDIO',6.64,2.69,4.7,.26,12,MUTED,True)
txt(s,'+1,58%',6.64,3.10,4.4,.70,32,NAVY,True)
txt(s,money(v25/n25)+' → '+money(v26/n26),6.64,4.02,4.58,.36,15,MUTED)
rect(s,.77,5.24,11.08,.74,NAVY)
txt(s,'2,3624 × 1,0158 ≈ 2,3997  |  volume × ticket = valor',1.04,5.40,10.52,.43,19,WHITE,True)

# MAIN 4 — spike = anomaly, not cause.
s=base(4,'B2C · anomalia','Antes de projetar setembro, explicar o dia 30.',source='Fonte: CSV B2C · 30/09/2025 contra setembro/2025, somando as quatro origens; origem atribuída não prova causa.',dark=True)
metric(s,'51,88%','do valor de setembro em um dia',.78,2.24,6.0,AQUA)
txt(s,'30/09 · '+money(day['cents']),.80,3.72,5.7,.35,15,WHITE,True)
txt(s,'Demais dias · '+money(sep['cents']-day['cents']),6.70,3.72,5.75,.35,15,PALE,True,PP_ALIGN.RIGHT)
rect(s,.80,4.16,11.50,.38,RGBColor(121,151,179))
rect(s,.80,4.16,11.50*day['cents']/sep['cents'],.38,AQUA)
rect(s,.80+11.50*day['cents']/sep['cents']-.015,4.16,.03,.38,WHITE)
txt(s,'327 linhas em 30/09/2025 · quatro origens no dia.',.80,4.90,11.5,.43,22,WHITE,True)
txt(s,'Campanha, lote ou data de registro são hipóteses — auditar antes de projetar.',.80,5.60,11.5,.63,18,PALE)

# MAIN 5 — concentration intersection, no double counting.
s=base(5,'B2B · carteira ativa','Quatro contratos Enterprise × SP concentram 37,06%.',source='Fonte: API de contratos B2B · foto coletada em '+snapshot_at+', horário de Brasília; status ativo apenas. Valor contratado, não recebido.')
metric(s,'37,06%','da soma mensal ativa · Enterprise × SP',.78,2.28,7.0,NAVY)
txt(s,'4 contratos · '+money(cell['active_monthly_cents'],0)+'/mês',.80,3.71,5.76,.33,15,NAVY,True)
txt(s,'Demais ativos · '+money(active-cell['active_monthly_cents'],0)+'/mês',6.74,3.71,5.55,.33,15,MUTED,True,PP_ALIGN.RIGHT)
rect(s,.80,4.13,11.50,.38,BLUE)
rect(s,.80,4.13,11.50*cell['active_monthly_cents']/active,.38,AQUA)
rect(s,.78,4.82,11.75,.92,ICE)
txt(s,'4 de 26 contratos ativos na interseção Enterprise × SP',1.08,5.02,10.9,.43,22,NAVY,True)
txt(s,'Total: 26 ativos · '+money(active,0)+'/mês',.82,6.15,11.5,.39,18,MUTED)

# MAIN 6 — source segmentation and attribution integrity.
s=base(6,'B2C · segmentação','Evento, embaixador e ICP orientam próximos testes.',source='Fonte: CSV B2C · jan/2025–jul/2026 · rankings por valor pago; códigos de cupom sem de-para oficial.',shade=True)
for x,heading,big,label,action in [
    (.78,'FORMATO DE EVENTO',fmt(event['count']),event['name']+' · '+money(event['cents'],0),'Comparar custo e margem por formato.'),
    (4.84,'EMBAIXADOR',fmt(ambassador['count']),ambassador['name']+' · '+money(ambassador['cents'],0),'Ranking por campo; validar cupom.'),
    (8.90,'ICP COMPRADOR',fmt(icp['count']),icp['name']+' · '+money(icp['cents'],0),'Recém-formado × R1: 380 linhas.')]:
    rect(s,x,2.23,3.64,2.98,WHITE)
    rect(s,x,2.23,3.64,.07,AQUA)
    txt(s,heading,x+.23,2.48,3.20,.28,12,MUTED,True)
    txt(s,big,x+.23,2.92,3.17,.70,36,NAVY,True)
    txt(s,label,x+.23,3.70,3.17,.66,14,NAVY,True)
    txt(s,action,x+.23,4.52,3.17,.51,13,MUTED)
rect(s,.78,5.50,11.75,.75,NAVY)
txt(s,'705 de 741 códigos embaixador/cupom divergem (95,14%). Validar o de-para antes de atribuir desempenho.',1.03,5.66,11.15,.54,17,WHITE,True)

# MAIN 7 — proof and limits.
s=base(7,'Método · rastreabilidade','O pipeline reconcilia snapshots; não cria histórico ausente.',source='Fonte: processamento do CSV B2C e snapshot GET /contratos B2B; verificações internas, sem conciliação financeira.')
for i,(heading,body) in enumerate([
    ('01  CSV B2C','Normalizar datas e moeda; manter negativo, zero e linhas idênticas sem ID.'),
    ('02  TESTES','Somar 4.435 linhas / R$ 40.165.219,74; 28 IDs B2B = 26 ativos + 2 fora do ativo.'),
    ('03  ATUALIZAÇÃO','B2C: CSV observado na prévia local; site público usa exportação validada. B2B: coleta agendada com token.')]):
    y=2.18+i*1.30;rect(s,.77,y,11.74,1.10,ICE if i!=1 else PALE)
    txt(s,heading,1.04,y+.15,2.48,.41,16,NAVY,True)
    txt(s,body,3.52,y+.15,8.65,.82,16,NAVY)
txt(s,'Sem histórico de cobranças/status: não calcular MRR histórico ou churn.',.80,6.23,11.68,.45,17,NAVY,True)

# MAIN 8 — responsible tool choice and operational scope.
s=base(8,'Ferramentas · limites','Automação e IA aceleram análise, mas não validam causalidade.',source='Escopo: CSV entregue + API contratual; propostas e hipóteses exigem checagem humana com fontes transacionais.',shade=True)
rect(s,.78,2.23,5.65,3.46,WHITE);rect(s,6.68,2.23,5.65,3.46,WHITE)
txt(s,'CÓDIGO + TESTES',1.05,2.59,5.0,.38,15,NAVY,True)
txt(s,'Parser determinístico, agregações e asserts para totais, janela comparável e status ativo.',1.05,3.18,4.96,1.70,19,NAVY)
txt(s,'IA + REVISÃO',6.95,2.59,5.0,.38,15,NAVY,True)
txt(s,'IA apoiou testes e visualizações; código reconciliou 28 IDs = 26 ativos + 2 fora. Conclusões limitadas ao dado disponível.',6.95,3.18,5.00,1.77,19,NAVY)
txt(s,'CSV local observado; Google Sheet original não compartilhada. Token B2B no servidor; HTTPS depende da fonte.',.81,6.11,11.69,.58,16,NAVY,True)

# MAIN 9 — prioritized action close.
s=base(9,'Decisão · próximos passos','A ordem é conciliar, analisar e proteger.',dark=True)
for i,(title,body) in enumerate([
    ('01  CONCILIAR','Cupom × embaixador: 705/741 códigos diferentes. Validar de-para antes de atribuir comissão.'),
    ('02  ANALISAR','Eventos e ICP × produto: cruzar custo, margem e conversão antes de mudar prioridades.'),
    ('03  PROTEGER','Dono proposto: Comercial/CS · prova: vigência e uso · avançar: plano por conta.')]):
    y=2.13+i*1.31;rect(s,.76,y,11.73,1.12,RGBColor(18,68,108))
    txt(s,title,1.04,y+.24,2.10,.39,18,AQUA,True)
    txt(s,body,3.25,y+.16,8.73,.82,16,WHITE)
link='https://fabriciogcruz-ai.github.io/medway-salesops-case/'
link_shape=txt(s,'Dashboard · 4 visões: fabriciogcruz-ai.github.io/medway-salesops-case/',.83,6.00,11.6,.36,14,AQUA,True)
link_shape.click_action.hyperlink.address=link
txt(s,'Nenhuma recomendação depende de ROI, churn ou MRR histórico inventados.',.83,6.40,11.6,.36,15,WHITE)

# APPENDIX 1 — product/origin mix, out of video.
s=base(10,'Apêndice · fora do vídeo','O mix de produto e origem é diagnóstico, não ROI.',source='Fonte: CSV B2C · jan/2025–jul/2026 · valor pago; custo de aquisição e margem indisponíveis.')
orig=sorted(B['by_origin'],key=lambda r:-r['cents']);prod=sorted(B['by_product'],key=lambda r:-r['cents'])
txt(s,'ORIGEM · R$ MI',.83,2.20,4.9,.30,13,NAVY,True)
txt(s,'PRODUTO · R$ MI',6.89,2.20,4.9,.30,13,NAVY,True)
chart(s,[r['name'] for r in reversed(orig)],[('Valor',[r['cents']/100_000_000 for r in reversed(orig)])],.78,2.62,5.75,3.38,20,XL_CHART_TYPE.BAR_CLUSTERED)
chart(s,[r['name'].replace('Extensivo ','Ext. ') for r in reversed(prod)],[('Valor',[r['cents']/100_000_000 for r in reversed(prod)])],6.65,2.62,5.74,3.38,16,XL_CHART_TYPE.BAR_CLUSTERED)
txt(s,'Valor pago por categoria não informa retorno sobre investimento.',.84,6.24,11.3,.36,16,NAVY,True)

# APPENDIX 2 — cohort, no historical MRR claim.
s=base(11,'Apêndice · fora do vídeo','Ano de início segmenta a foto atual — não reconstrói MRR.',source='Fonte: API de contratos B2B · ano de início × status atual; sem fim de vigência, cobrança e eventos de status.',shade=True)
a25=next(r for r in C['start_year_status'] if r['year']=='2025' and r['status']=='ativo')
a26=next(r for r in C['start_year_status'] if r['year']=='2026' and r['status']=='ativo')
assert a25['active_monthly_cents']+a26['active_monthly_cents']==active
txt(s,'VALOR MENSAL CONTRATADO DOS ATIVOS HOJE · R$ MIL/MÊS',.87,2.21,7.7,.30,12,MUTED,True)
chart(s,['2025','2026'],[('R$ mil/mês, ativos hoje',[a25['active_monthly_cents']/100000,a26['active_monthly_cents']/100000])],.84,2.58,7.13,3.49,120)
txt(s,'12 ativos\n'+money(a25['active_monthly_cents'],0)+'/mês',8.49,2.54,3.62,1.11,22,NAVY,True)
txt(s,'14 ativos\n'+money(a26['active_monthly_cents'],0)+'/mês',8.49,4.17,3.62,1.11,22,NAVY,True)
txt(s,'Dois contratos fora do ativo não entram no total.',.89,6.32,11.4,.37,16,NAVY)

# APPENDIX 3 — QA granular.
s=base(12,'Apêndice · fora do vídeo','Exceções permanecem visíveis até haver ID e conciliação.',source='Fonte: quality do CSV B2C e auditoria embaixador × cupom; sem classificar divergência como perda.')
q=B['quality']
for i,(big,label) in enumerate([
    (fmt(q['date_formats']['BR']),'datas BR; demais 3.689 ISO'),
    (fmt(q['money_formats']['PONTO']),'valores com ponto; 4.319 BR'),
    (fmt(q['identical_extra_rows_retained']),'linhas idênticas extras mantidas sem ID'),
    (fmt(audit['Códigos diferentes']['count']),'de 741 códigos comparáveis divergentes; validar cupom')]):
    x=.80+(i%2)*6.09;y=2.27+(i//2)*1.84
    rect(s,x,y,5.65,1.56,ICE if i%2 else PALE)
    txt(s,big,x+.24,y+.18,1.51,.69,32,NAVY,True)
    txt(s,label,x+1.73,y+.31,3.64,.96,15,NAVY)
txt(s,'Reconciliar com financeiro e IDs antes de remover, corrigir ou explicar lançamentos.',.83,6.22,11.5,.46,16,NAVY,True)

assert len(prs.slides)==12
prs.save(OUT)
print(f'{OUT} | slides={len(prs.slides)} | native editable charts={sum(shape.has_chart for slide in prs.slides for shape in slide.shapes)}')
print('Jan–Jul',v25,v26,n25,n26,'growth',round(gv*100,2),round(gn*100,2),round(gt*100,2))
print('Sept 30',day['count'],day['cents'],'share',round(day['cents']/sep['cents']*100,2))
print('B2B',active,C['active_contracts'],'Enterprise×SP',cell['count'],cell['active_monthly_cents'],round(cell['active_monthly_cents']/active*100,2))

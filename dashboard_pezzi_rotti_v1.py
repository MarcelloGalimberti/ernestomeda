# env neuralprophet
# modifiche: 20260324 V1 

# import necessary libraries
import pandas as pd
import numpy as np
import warnings
import plotly.express as px
warnings.filterwarnings('ignore')
from io import BytesIO
import streamlit as st
import plotly.graph_objects as go

##############################################################################
# PALETTE COLORI — toni grigi, bronzo, marrone
##############################################################################
C_BRONZO        = '#8B7355'   # bronzo medio  — colore primario barre
C_BRONZO_CHIARO = '#C4A882'   # bronzo chiaro — secondario
C_MARRONE       = '#5C3D1E'   # marrone scuro — linee, accenti
C_GRIGIO        = '#8A8A8A'   # grigio medio
C_GRIGIO_CHIARO = '#C8C0B8'   # grigio chiaro — valori mancanti

# Criticità (rimangono leggibili ma nei toni della palette)
COLORI_CRITICITA = {
    'Alta':         '#7A3B2E',   # rosso-marrone scuro
    'Media':        '#C4915A',   # bronzo-arancio
    'Bassa':        '#8A9E8A',   # grigio-verde tenue
    'Non definita': '#C8C0B8',   # grigio chiaro
}

# Heatmap: crema → bronzo → marrone scuro
HEATMAP_SCALE = [
    [0.0, '#F5F0EB'],
    [0.3, '#D4B896'],
    [0.6, '#A07850'],
    [1.0, '#5C3D1E'],
]

# Palette qualitativa per serie multiple (linee, aree, sunburst…)
PALETTE_Q = [
    '#8B7355','#A89880','#6B5B45','#C4A882',
    '#5C4A32','#9E8E7E','#7A6A5A','#B8A898',
    '#4A3828','#D4C4B0',
]

####### Impaginazione

st.set_page_config(layout="wide")

url_immagine = 'ernestomeda_nero70.jpg'#'Scavolini_logo.png?raw=true'

col_1, col_2 = st.columns([1, 4])

with col_1:
    st.image(url_immagine, width=150)

with col_2:
    st.header('Dashboard Scarti | Ernestomeda', divider='grey')


# Metti nella sidebar i file uploader per tutti i file necessari
st.sidebar.header('Caricamento file')
###### Caricamento del file Gestione Cause
st.sidebar.subheader('Caricamento database Gestione Cause', divider='grey')
uploaded_gestione_cause = st.sidebar.file_uploader(
    "Carica file Gestione Cause")
if not uploaded_gestione_cause:
    st.stop()

###### Caricamento del file Gruppo Merci
st.sidebar.subheader('Caricamento Gruppo Merci', divider='grey')
uploaded_gruppo_merci = st.sidebar.file_uploader(
    "Carica file Gruppo Merci | ZSD63")
if not uploaded_gruppo_merci:
    st.stop()

#Funzione per caricare i file Excel per st.cache_data
@st.cache_data
def load_excel(file):
    return pd.read_excel(file, parse_dates=True)

df_gestione_cause = load_excel(uploaded_gestione_cause)
df_gruppo_merci = load_excel(uploaded_gruppo_merci)


# Pre-processing dei file caricati
colonne_gestione_cause = ['Articolo', 'Descrizione', 'Stato.','Linea','Linea Resp','Data Segn.','Data Sped.','Responsabilità','TipoNC','PosDifetto','Causa','Soluzione','Macro Errore']
colonne_gruppo_merci = ['Gr. merci','Definizione','T.m.','Materiale','UM']

df_gestione_cause = df_gestione_cause[colonne_gestione_cause]
df_gruppo_merci = df_gruppo_merci[colonne_gruppo_merci]

# Rimuovi duplicati in df_gruppo_merci basati sulla colonna 'Materiale', mantenendo la prima occorrenza
df_gruppo_merci = df_gruppo_merci.drop_duplicates(subset=['Materiale'], keep='first').reset_index(drop=True)


df_gestione_cause['Articolo'] = df_gestione_cause['Articolo'].astype(str).str.strip()
df_gruppo_merci['Materiale'] = df_gruppo_merci['Materiale'].astype(str).str.strip()
df_gruppo_merci['Gr. merci'] = df_gruppo_merci['Gr. merci'].astype(str).str.strip()



# Merge dei due database per identificare i materiali presenti in Gestione Cause e il loro gruppo merci
df_merged = pd.merge(df_gestione_cause, df_gruppo_merci, left_on='Articolo', right_on='Materiale', how='left')

with st.expander('Anteprima database caricati', expanded=False):
    st.write('##### Database Gestione Cause')
    st.dataframe(df_gestione_cause.head(5))
    st.write('Lunghezza: :green[{}] righe — Articoli univoci: :green[{}]'.format(
        len(df_gestione_cause), df_gestione_cause['Articolo'].nunique()))

    st.write('##### Database Gruppo Merci')
    st.dataframe(df_gruppo_merci.head(5))
    st.write('Lunghezza: :green[{}] righe — Materiali univoci: :green[{}]'.format(
        len(df_gruppo_merci), df_gruppo_merci['Materiale'].nunique()))

    st.write('##### Database unificato dopo merge')
    st.dataframe(df_merged.head(5))
    st.write('Lunghezza: :green[{}] righe — Articoli univoci: :green[{}]'.format(
        len(df_merged), df_merged['Articolo'].nunique()))





##############################################################################
# FEATURE ENGINEERING — Criticità
##############################################################################

# Delta giorni tra segnalazione e spedizione: delta piccolo = alta criticità
df_merged['Data Segn.'] = pd.to_datetime(df_merged['Data Segn.'], errors='coerce')
df_merged['Data Sped.'] = pd.to_datetime(df_merged['Data Sped.'], errors='coerce')
df_merged['Delta_giorni'] = (df_merged['Data Sped.'] - df_merged['Data Segn.']).dt.days

# Definizione soglie criticità tramite slider in sidebar
st.sidebar.subheader('Soglie Criticità', divider='grey')
SOGLIA_ALTA  = st.sidebar.slider('Soglia Alta (≤ N giorni)', min_value=0, max_value=30, value=3, step=1)
SOGLIA_MEDIA = st.sidebar.slider('Soglia Media (≤ N giorni)', min_value=0, max_value=60, value=7, step=1)
if SOGLIA_MEDIA <= SOGLIA_ALTA:
    st.sidebar.warning('La soglia Media deve essere maggiore della soglia Alta.')

def classifica_criticita(delta):
    if pd.isna(delta) or delta < 0:
        return 'Non definita'
    elif delta <= SOGLIA_ALTA:
        return 'Alta'
    elif delta <= SOGLIA_MEDIA:
        return 'Media'
    else:
        return 'Bassa'

df_merged['Criticità'] = df_merged['Delta_giorni'].apply(classifica_criticita)

##############################################################################
# FILTRO ANNI
##############################################################################

anni_disponibili_filtro = sorted(df_merged['Data Segn.'].dt.year.dropna().unique().astype(int).tolist())
anni_selezionati = st.pills(
    'Anni da analizzare',
    options=anni_disponibili_filtro,
    default=anni_disponibili_filtro[-2:],
    selection_mode='multi'
)
if not anni_selezionati:
    st.warning('Seleziona almeno un anno per visualizzare l\'analisi.')
    st.stop()

df_merged = df_merged[df_merged['Data Segn.'].dt.year.isin(anni_selezionati)].copy()

##############################################################################
# STEP 1 — Qualità del dato
##############################################################################

st.header('Step 1 — Qualità del dato', divider='grey')

# ── 1a. Completezza PosDifetto ───────────────────────────────────────────────
pos_vuote = df_merged['PosDifetto'].isna() | \
            df_merged['PosDifetto'].astype(str).str.strip().isin(['', 'Selezionare una posizione'])
n_pos_ok   = (~pos_vuote).sum()
n_pos_vuote = pos_vuote.sum()

# ── 1b. Completezza Soluzione ────────────────────────────────────────────────
sol_vuote  = df_merged['Soluzione'].isna() | \
             df_merged['Soluzione'].astype(str).str.strip().eq('')
n_sol_ok   = (~sol_vuote).sum()
n_sol_vuote = sol_vuote.sum()

# ── 1c. Match Gruppo Merci ───────────────────────────────────────────────────
n_no_match = df_merged['Gr. merci'].isna().sum()
n_match    = len(df_merged) - n_no_match

# ── 1d. Righe con date mancanti o negative ───────────────────────────────────
n_data_segn_null = df_merged['Data Segn.'].isna().sum()
n_data_sped_null = df_merged['Data Sped.'].isna().sum()
n_delta_negativo = (df_merged['Delta_giorni'] < 0).sum()

# ── 1e. Duplicati ────────────────────────────────────────────────────────────
n_duplicati = df_merged.duplicated().sum()

# ── Grafico 1: Completezza campi chiave (barchart orizzontale) ───────────────
totale = len(df_merged)
campi = ['PosDifetto', 'Soluzione', 'Gr. merci']
n_ok  = [n_pos_ok, n_sol_ok, n_match]
n_ko  = [n_pos_vuote, n_sol_vuote, n_no_match]
pct_ok = [round(v / totale * 100, 1) for v in n_ok]

fig_completezza = go.Figure()
fig_completezza.add_trace(go.Bar(
    name='Compilato',
    y=campi,
    x=pct_ok,
    orientation='h',
    marker_color=C_BRONZO,
    text=[f'{p}%' for p in pct_ok],
    textposition='inside'
))
fig_completezza.add_trace(go.Bar(
    name='Mancante',
    y=campi,
    x=[round(100 - p, 1) for p in pct_ok],
    orientation='h',
    marker_color=C_GRIGIO_CHIARO,
    text=[f'{round(100-p,1)}%' for p in pct_ok],
    textposition='inside'
))
fig_completezza.update_layout(
    barmode='stack',
    title='Completezza dei campi chiave (%)',
    xaxis_title='%',
    xaxis_range=[0, 100],
    legend=dict(orientation='h', yanchor='bottom', y=1.02),
    height=300
)
st.plotly_chart(fig_completezza, use_container_width=True)

# ── Grafico 2: Distribuzione Criticità (pie) ─────────────────────────────────
criticita_counts = df_merged['Criticità'].value_counts().reset_index()
criticita_counts.columns = ['Criticità', 'Conteggio']
colori_criticita = COLORI_CRITICITA

fig_crit = px.pie(
    criticita_counts,
    names='Criticità',
    values='Conteggio',
    color='Criticità',
    color_discrete_map=colori_criticita,
    title=f'Distribuzione Criticità (soglia Alta ≤ {SOGLIA_ALTA}gg, Media ≤ {SOGLIA_MEDIA}gg)',
    hole=0.4
)
fig_crit.update_traces(textinfo='label+percent+value')

# ── Grafico 3: Distribuzione Delta_giorni (histogram) ───────────────────────
df_delta_valido = df_merged[df_merged['Delta_giorni'].between(0, 365)]
fig_delta = px.histogram(
    df_delta_valido,
    x='Delta_giorni',
    nbins=50,
    color='Criticità',
    color_discrete_map=colori_criticita,
    title='Distribuzione delta giorni (Segn. → Sped.)',
    labels={'Delta_giorni': 'Giorni'},
    barmode='overlay'
)
fig_delta.add_vline(x=SOGLIA_ALTA,  line_dash='dash', line_color='crimson',
                    annotation_text=f'Alta ({SOGLIA_ALTA}gg)', annotation_position='top right')
fig_delta.add_vline(x=SOGLIA_MEDIA, line_dash='dash', line_color='orange',
                    annotation_text=f'Media ({SOGLIA_MEDIA}gg)', annotation_position='top right')

col_crit, col_delta = st.columns(2)
with col_crit:
    st.plotly_chart(fig_crit,  use_container_width=True)
with col_delta:
    st.plotly_chart(fig_delta, use_container_width=True)

# ── Riepilogo testuale ────────────────────────────────────────────────────────
st.write('##### Riepilogo qualità del dato')
col1, col2, col3, col4 = st.columns(4)
col1.metric('Totale righe',     totale)
col2.metric('Duplicati',        n_duplicati)
col3.metric('Data Segn. nulle', n_data_segn_null)
col4.metric('Delta negativi',   n_delta_negativo)

st.write(f'- **PosDifetto** valorizzata: **{n_pos_ok}** righe ({pct_ok[0]}%) — mancante: {n_pos_vuote}')
st.write(f'- **Soluzione** valorizzata: **{n_sol_ok}** righe ({pct_ok[1]}%) — mancante: {n_sol_vuote}')
st.write(f'- **Gr. merci** con match: **{n_match}** righe ({pct_ok[2]}%) — senza match: {n_no_match}')
st.write(f'- Range temporale: **{df_merged["Data Segn."].min().date()}** → **{df_merged["Data Segn."].max().date()}**')



##############################################################################
# STEP 2 — Analisi temporale
##############################################################################

st.header('Step 2 — Analisi temporale', divider='grey')

# Lavoriamo solo su righe con Data Segn. valida
df_tempo = df_merged.dropna(subset=['Data Segn.']).copy()
df_tempo['Anno']      = df_tempo['Data Segn.'].dt.year
df_tempo['Mese']      = df_tempo['Data Segn.'].dt.month
df_tempo['AnnoMese']  = df_tempo['Data Segn.'].dt.to_period('M').astype(str)
df_tempo['Settimana'] = df_tempo['Data Segn.'].dt.isocalendar().week.astype(int)
df_tempo['AnnoSett']  = df_tempo['Anno'].astype(str) + '-W' + df_tempo['Settimana'].astype(str).str.zfill(2)

# ── Grafico 1: Year Over Year — scarti mensili per anno ──────────────────────
yoy = (df_tempo.groupby(['Anno', 'Mese'])
               .size()
               .reset_index(name='Scarti'))
yoy['MeseNome'] = yoy['Mese'].map(
    {1:'Gen',2:'Feb',3:'Mar',4:'Apr',5:'Mag',6:'Giu',
     7:'Lug',8:'Ago',9:'Set',10:'Ott',11:'Nov',12:'Dic'})
yoy['Anno'] = yoy['Anno'].astype(str)

anni_disponibili = sorted(yoy['Anno'].unique())
n_anni = len(anni_disponibili)
colori_yoy = PALETTE_Q[:n_anni]

fig_yoy = go.Figure()
for i, anno in enumerate(anni_disponibili):
    df_anno = yoy[yoy['Anno'] == anno].sort_values('Mese')
    fig_yoy.add_trace(go.Scatter(
        x=df_anno['MeseNome'], y=df_anno['Scarti'],
        mode='lines+markers',
        name=anno,
        line=dict(color=colori_yoy[i], width=2),
        marker=dict(size=7)
    ))

ordine_mesi = ['Gen','Feb','Mar','Apr','Mag','Giu','Lug','Ago','Set','Ott','Nov','Dic']
fig_yoy.update_layout(
    title='Trend mensile scarti — Year Over Year',
    xaxis=dict(title='Mese', categoryorder='array', categoryarray=ordine_mesi),
    yaxis_title='N. scarti',
    legend_title='Anno',
    legend=dict(orientation='h', yanchor='bottom', y=1.02),
    height=500
)
st.plotly_chart(fig_yoy, use_container_width=True)

# ── Grafico 2: Heatmap Anno × Mese ───────────────────────────────────────────
nomi_mesi = {1:'Gen',2:'Feb',3:'Mar',4:'Apr',5:'Mag',6:'Giu',
             7:'Lug',8:'Ago',9:'Set',10:'Ott',11:'Nov',12:'Dic'}

heatmap_data = (df_tempo.groupby(['Anno', 'Mese'])
                        .size()
                        .reset_index(name='Scarti'))
heatmap_data['Anno'] = heatmap_data['Anno'].astype(int).astype(str)
heatmap_data['MeseNome'] = heatmap_data['Mese'].map(nomi_mesi)
heatmap_pivot = heatmap_data.pivot(index='Anno', columns='Mese', values='Scarti').fillna(0)

fig_heatmap = go.Figure(go.Heatmap(
    z=heatmap_pivot.values,
    x=[nomi_mesi[m] for m in heatmap_pivot.columns],
    y=heatmap_pivot.index.astype(str),
    colorscale=HEATMAP_SCALE,
    text=heatmap_pivot.values.astype(int),
    texttemplate='%{text}',
    hovertemplate='Anno: %{y}<br>Mese: %{x}<br>Scarti: %{z}<extra></extra>'
))
fig_heatmap.update_layout(
    title='Heatmap scarti per Anno × Mese',
    xaxis_title='Mese',
    yaxis=dict(title='Anno', type='category', categoryorder='category ascending'),
    height=450
)
st.plotly_chart(fig_heatmap, use_container_width=True)

# ── Grafico 3: Evoluzione mix TipoNC nel tempo (area % stacked) ───────────────
top_tiponc = df_tempo['TipoNC'].value_counts().head(8).index.tolist()
df_tiponc_tempo = df_tempo.copy()
df_tiponc_tempo['TipoNC_gruppo'] = df_tiponc_tempo['TipoNC'].where(
    df_tiponc_tempo['TipoNC'].isin(top_tiponc), other='Altro'
)
mix_tiponc = (df_tiponc_tempo.groupby(['AnnoMese', 'TipoNC_gruppo'])
                              .size()
                              .reset_index(name='Scarti')
                              .sort_values('AnnoMese'))

fig_mix = px.area(
    mix_tiponc,
    x='AnnoMese', y='Scarti',
    color='TipoNC_gruppo',
    groupnorm='percent',
    color_discrete_sequence=PALETTE_Q,
    title='Evoluzione mix TipoNC nel tempo (% mensile) — top 8 + Altro',
    labels={'AnnoMese': 'Mese', 'Scarti': '%', 'TipoNC_gruppo': 'TipoNC'}
)
fig_mix.update_xaxes(tickangle=45)
fig_mix.update_layout(yaxis_title='%', height=500)
st.plotly_chart(fig_mix, use_container_width=True)



##############################################################################
# STEP 3 — Analisi per Gruppo Merci e Articolo
##############################################################################

st.header('Step 3 — Analisi per Gruppo Merci e Articolo', divider='grey')

# Etichetta leggibile: "codice — definizione"
df_gm = df_merged.dropna(subset=['Gr. merci']).copy()
df_gm['GM_label'] = df_gm['Gr. merci'].astype(str) + ' — ' + df_gm['Definizione'].fillna('').astype(str)

# ── Grafico 1: Pareto per Gr. merci ──────────────────────────────────────────
pareto_gm = (df_gm.groupby('GM_label')
                  .size()
                  .reset_index(name='Scarti')
                  .sort_values('Scarti', ascending=False))
pareto_gm['Cumulata_%'] = pareto_gm['Scarti'].cumsum() / pareto_gm['Scarti'].sum() * 100

fig_pareto_gm = go.Figure()
fig_pareto_gm.add_trace(go.Bar(
    x=pareto_gm['GM_label'], y=pareto_gm['Scarti'],
    name='Scarti', marker_color=C_BRONZO
))
fig_pareto_gm.add_trace(go.Scatter(
    x=pareto_gm['GM_label'], y=pareto_gm['Cumulata_%'],
    name='Cumulata %', yaxis='y2',
    mode='lines+markers', line=dict(color=C_MARRONE, width=2)
))
fig_pareto_gm.add_hline(
    y=80, yref='y2', line_dash='dash', line_color=C_GRIGIO,
    annotation_text='80%', annotation_position='top right'
)
fig_pareto_gm.update_layout(
    title='Pareto scarti per Gruppo Merci',
    xaxis_tickangle=45,
    yaxis=dict(title='N. scarti'),
    yaxis2=dict(title='Cumulata %', overlaying='y', side='right', range=[0, 105]),
    legend=dict(orientation='h', yanchor='bottom', y=1.02),
    height=550
)
st.plotly_chart(fig_pareto_gm, use_container_width=True)

# ── Grafico 2: Top N articoli (slider) per gruppo merci selezionato ───────────
st.subheader('Top articoli per Gruppo Merci')
col_sel, col_n = st.columns([3, 1])

gruppi_disponibili = ['Tutti'] + pareto_gm['GM_label'].tolist()  # ordinati per scarti decrescenti
gruppo_scelto = col_sel.selectbox('Seleziona Gruppo Merci', gruppi_disponibili)
top_n = col_n.slider('Top N articoli', min_value=5, max_value=30, value=15, step=1)

df_filtrato_gm = df_gm if gruppo_scelto == 'Tutti' else df_gm[df_gm['GM_label'] == gruppo_scelto]

top_articoli = (df_filtrato_gm.groupby(['Articolo', 'Descrizione'])
                               .size()
                               .reset_index(name='Scarti')
                               .sort_values('Scarti', ascending=False)
                               .head(top_n))
top_articoli['Art_label'] = top_articoli['Articolo'] + ' — ' + top_articoli['Descrizione'].fillna('')

fig_top_art = px.bar(
    top_articoli.sort_values('Scarti'),
    x='Scarti', y='Art_label',
    orientation='h',
    title=f'Top {top_n} articoli — {gruppo_scelto}',
    labels={'Art_label': 'Articolo', 'Scarti': 'N. scarti'},
    color='Scarti', color_continuous_scale=['#F5F0EB','#5C3D1E']
)
fig_top_art.update_layout(height=600, coloraxis_showscale=False)
st.plotly_chart(fig_top_art, use_container_width=True)

# ── Grafico 3: Scatter articoli "cronici" (frequenza × varietà difetti) ───────
st.subheader('Articoli cronici — frequenza vs varietà di difetti')

scatter_data = (df_gm.groupby(['Articolo', 'Descrizione', 'GM_label'])
                     .agg(
                         Frequenza=('Articolo', 'count'),
                         Varieta_TipoNC=('TipoNC', 'nunique'),
                         Criticita_Alta=('Criticità', lambda x: (x == 'Alta').sum())
                     )
                     .reset_index())

fig_scatter = px.scatter(
    scatter_data,
    x='Frequenza', y='Varieta_TipoNC',
    size='Criticita_Alta',
    color='GM_label',
    color_discrete_sequence=PALETTE_Q,
    hover_name='Articolo',
    hover_data={'Descrizione': True, 'Frequenza': True,
                'Varieta_TipoNC': True, 'Criticita_Alta': True, 'GM_label': False},
    title='Articoli cronici — frequenza scarti vs varietà TipoNC (dimensione = n. scarti Alta criticità)',
    labels={
        'Frequenza': 'N. scarti totali',
        'Varieta_TipoNC': 'N. TipoNC distinti',
        'GM_label': 'Gruppo Merci'
    },
    size_max=40
)
fig_scatter.update_layout(height=600)
st.plotly_chart(fig_scatter, use_container_width=True)

# ── Grafico 4: Griglia 2×3 trend mensile per top 6 Gr. merci ─────────────────
from plotly.subplots import make_subplots

st.subheader('Trend mensile per Gruppo Merci')

top_gm_trend = pareto_gm.head(6)['GM_label'].tolist()
df_trend_gm = df_gm[df_gm['GM_label'].isin(top_gm_trend)].copy()
df_trend_gm['AnnoMese'] = df_trend_gm['Data Segn.'].dt.to_period('M').astype(str)

tutti_mesi = sorted(df_trend_gm['AnnoMese'].unique().tolist())

fig_grid = make_subplots(rows=3, cols=2, subplot_titles=top_gm_trend, shared_xaxes=False)

colori_grid = PALETTE_Q

for i, gm in enumerate(top_gm_trend):
    riga = i // 2 + 1
    col  = i %  2 + 1
    df_sub = (df_trend_gm[df_trend_gm['GM_label'] == gm]
              .groupby('AnnoMese').size()
              .reindex(tutti_mesi, fill_value=0)
              .reset_index(name='Scarti')
              .rename(columns={'index': 'AnnoMese'}))
    fig_grid.add_trace(
        go.Scatter(
            x=df_sub['AnnoMese'], y=df_sub['Scarti'],
            mode='lines+markers',
            line=dict(color=colori_grid[i], width=2),
            marker=dict(size=5),
            name=gm,
            showlegend=False
        ),
        row=riga, col=col
    )
    fig_grid.update_xaxes(tickangle=45, row=riga, col=col)
    fig_grid.update_yaxes(title_text='N. scarti', row=riga, col=col)

fig_grid.update_layout(
    title='Trend mensile scarti — top 6 Gruppi Merci',
    height=900
)
st.plotly_chart(fig_grid, use_container_width=True)



##############################################################################
# STEP 4 — Stratificazione per TipoNC
##############################################################################

st.header('Step 4 — Stratificazione per TipoNC', divider='grey')

# ── Grafico 1: Pareto TipoNC ──────────────────────────────────────────────────
pareto_nc = (df_merged.groupby('TipoNC')
                      .size()
                      .reset_index(name='Scarti')
                      .sort_values('Scarti', ascending=False))
pareto_nc['Cumulata_%'] = pareto_nc['Scarti'].cumsum() / pareto_nc['Scarti'].sum() * 100

fig_pareto_nc = go.Figure()
fig_pareto_nc.add_trace(go.Bar(
    x=pareto_nc['TipoNC'], y=pareto_nc['Scarti'],
    name='Scarti', marker_color=C_BRONZO
))
fig_pareto_nc.add_trace(go.Scatter(
    x=pareto_nc['TipoNC'], y=pareto_nc['Cumulata_%'],
    name='Cumulata %', yaxis='y2',
    mode='lines+markers', line=dict(color=C_MARRONE, width=2)
))
fig_pareto_nc.add_hline(
    y=80, yref='y2', line_dash='dash', line_color=C_GRIGIO,
    annotation_text='80%', annotation_position='top right'
)
fig_pareto_nc.update_layout(
    title='Pareto scarti per TipoNC',
    xaxis_tickangle=45,
    yaxis=dict(title='N. scarti'),
    yaxis2=dict(title='Cumulata %', overlaying='y', side='right', range=[0, 105]),
    legend=dict(orientation='h', yanchor='bottom', y=1.02),
    height=550
)
st.plotly_chart(fig_pareto_nc, use_container_width=True)

# ── Grafico 2: Heatmap TipoNC × Linea Resp ───────────────────────────────────
st.subheader('TipoNC × Linea Resp')

# Limitiamo ai top TipoNC e top Linee per leggibilità
top_nc_hm   = pareto_nc.head(12)['TipoNC'].tolist()
top_linee   = (df_merged.groupby('Linea Resp')
                        .size()
                        .sort_values(ascending=False)
                        .head(12).index.tolist())

hm_nc_linea = (df_merged[df_merged['TipoNC'].isin(top_nc_hm) & df_merged['Linea Resp'].isin(top_linee)]
               .groupby(['Linea Resp', 'TipoNC'])
               .size()
               .reset_index(name='Scarti'))
hm_pivot = hm_nc_linea.pivot(index='Linea Resp', columns='TipoNC', values='Scarti').fillna(0)

fig_hm_nc = go.Figure(go.Heatmap(
    z=hm_pivot.values,
    x=hm_pivot.columns.tolist(),
    y=hm_pivot.index.tolist(),
    colorscale=HEATMAP_SCALE,
    text=hm_pivot.values.astype(int),
    texttemplate='%{text}',
    hovertemplate='Linea: %{y}<br>TipoNC: %{x}<br>Scarti: %{z}<extra></extra>'
))
fig_hm_nc.update_layout(
    title='Heatmap TipoNC × Linea Resp — top 12 per entrambe le dimensioni',
    xaxis_tickangle=45,
    xaxis_title='TipoNC',
    yaxis_title='Linea Resp',
    height=550
)
st.plotly_chart(fig_hm_nc, use_container_width=True)

# ── Grafico 3: Heatmap TipoNC × Gr. merci ────────────────────────────────────
st.subheader('TipoNC × Gruppo Merci')

top_gm_hm = pareto_gm.head(12)['GM_label'].tolist()

hm_nc_gm = (df_gm[df_gm['TipoNC'].isin(top_nc_hm) & df_gm['GM_label'].isin(top_gm_hm)]
            .groupby(['GM_label', 'TipoNC'])
            .size()
            .reset_index(name='Scarti'))
hm_gm_pivot = hm_nc_gm.pivot(index='GM_label', columns='TipoNC', values='Scarti').fillna(0)

fig_hm_gm = go.Figure(go.Heatmap(
    z=hm_gm_pivot.values,
    x=hm_gm_pivot.columns.tolist(),
    y=hm_gm_pivot.index.tolist(),
    colorscale=HEATMAP_SCALE,
    text=hm_gm_pivot.values.astype(int),
    texttemplate='%{text}',
    hovertemplate='Gruppo Merci: %{y}<br>TipoNC: %{x}<br>Scarti: %{z}<extra></extra>'
))
fig_hm_gm.update_layout(
    title='Heatmap TipoNC × Gruppo Merci — top 12 per entrambe le dimensioni',
    xaxis_tickangle=45,
    xaxis_title='TipoNC',
    yaxis_title='Gruppo Merci',
    height=550
)
st.plotly_chart(fig_hm_gm, use_container_width=True)

# ── Grafico 4: Evoluzione mensile TipoNC (area % stacked, con filtro) ─────────
st.subheader('Evoluzione mensile TipoNC per Linea Resp')

linee_disponibili = ['Tutte'] + sorted(df_merged['Linea Resp'].dropna().unique().tolist())
linea_scelta = st.selectbox('Seleziona Linea Resp', linee_disponibili, key='sel_linea_nc')

df_nc_tempo = df_merged.dropna(subset=['Data Segn.']).copy()
df_nc_tempo['AnnoMese'] = df_nc_tempo['Data Segn.'].dt.to_period('M').astype(str)

if linea_scelta != 'Tutte':
    df_nc_tempo = df_nc_tempo[df_nc_tempo['Linea Resp'] == linea_scelta]

df_nc_tempo['TipoNC_gruppo'] = df_nc_tempo['TipoNC'].where(
    df_nc_tempo['TipoNC'].isin(top_nc_hm), other='Altro'
)
mix_nc = (df_nc_tempo.groupby(['AnnoMese', 'TipoNC_gruppo'])
                     .size()
                     .reset_index(name='Scarti')
                     .sort_values('AnnoMese'))

fig_mix_nc = px.area(
    mix_nc,
    x='AnnoMese', y='Scarti',
    color='TipoNC_gruppo',
    color_discrete_sequence=PALETTE_Q,
    title=f'Evoluzione mix TipoNC — {"Tutte le linee" if linea_scelta == "Tutte" else linea_scelta}',
    labels={'AnnoMese': 'Mese', 'Scarti': 'N. scarti', 'TipoNC_gruppo': 'TipoNC'}
)
fig_mix_nc.update_xaxes(tickangle=45)
fig_mix_nc.update_layout(yaxis_title='N. scarti', height=500)
st.plotly_chart(fig_mix_nc, use_container_width=True)



##############################################################################
# STEP 5 — Responsabilità e Macro Errore
##############################################################################

st.header('Step 5 — Responsabilità e Macro Errore', divider='grey')

df_resp = df_merged.dropna(subset=['Responsabilità']).copy()
df_resp['AnnoMese'] = df_resp['Data Segn.'].dt.to_period('M').astype(str)

# ── Grafico 1: Distribuzione per Responsabilità (pareto orizzontale) ──────────
pareto_resp = (df_resp.groupby('Responsabilità')
                      .size()
                      .reset_index(name='Scarti')
                      .sort_values('Scarti', ascending=False))
pareto_resp['Cumulata_%'] = pareto_resp['Scarti'].cumsum() / pareto_resp['Scarti'].sum() * 100

fig_pareto_resp = go.Figure()
fig_pareto_resp.add_trace(go.Bar(
    x=pareto_resp['Responsabilità'], y=pareto_resp['Scarti'],
    name='Scarti', marker_color=C_BRONZO
))
fig_pareto_resp.add_trace(go.Scatter(
    x=pareto_resp['Responsabilità'], y=pareto_resp['Cumulata_%'],
    name='Cumulata %', yaxis='y2',
    mode='lines+markers', line=dict(color=C_MARRONE, width=2)
))
fig_pareto_resp.add_hline(
    y=80, yref='y2', line_dash='dash', line_color=C_GRIGIO,
    annotation_text='80%', annotation_position='top right'
)
fig_pareto_resp.update_layout(
    title='Pareto scarti per Responsabilità',
    xaxis_tickangle=45,
    yaxis=dict(title='N. scarti'),
    yaxis2=dict(title='Cumulata %', overlaying='y', side='right', range=[0, 105]),
    legend=dict(orientation='h', yanchor='bottom', y=1.02),
    height=500
)
st.plotly_chart(fig_pareto_resp, use_container_width=True)

# ── Grafico 2: Drill-down Macro Errore per Responsabilità (stacked bar) ───────
st.subheader('Macro Errore per Responsabilità')

drill = (df_resp.dropna(subset=['Macro Errore'])
               .groupby(['Responsabilità', 'Macro Errore'])
               .size()
               .reset_index(name='Scarti')
               .sort_values('Scarti', ascending=False))

# Ordine Responsabilità per volume totale
ordine_resp = pareto_resp['Responsabilità'].tolist()

fig_drill = px.bar(
    drill,
    x='Responsabilità', y='Scarti',
    color='Macro Errore',
    color_discrete_sequence=PALETTE_Q,
    title='Composizione Macro Errore per Responsabilità',
    labels={'Scarti': 'N. scarti'},
    category_orders={'Responsabilità': ordine_resp},
    text_auto=False
)
fig_drill.update_xaxes(tickangle=45)
fig_drill.update_layout(
    barmode='stack',
    legend=dict(orientation='v', x=1.02, xanchor='left', y=1, yanchor='top'),
    height=550
)
st.plotly_chart(fig_drill, use_container_width=True)

# ── Grafico 3: Heatmap Responsabilità × Linea Resp ────────────────────────────
st.subheader('Responsabilità × Linea Resp')

hm_resp_linea = (df_resp[df_resp['Linea Resp'].isin(top_linee)]
                 .groupby(['Linea Resp', 'Responsabilità'])
                 .size()
                 .reset_index(name='Scarti'))
hm_resp_pivot = hm_resp_linea.pivot(index='Linea Resp', columns='Responsabilità', values='Scarti').fillna(0)

fig_hm_resp = go.Figure(go.Heatmap(
    z=hm_resp_pivot.values,
    x=hm_resp_pivot.columns.tolist(),
    y=hm_resp_pivot.index.tolist(),
    colorscale=HEATMAP_SCALE,
    text=hm_resp_pivot.values.astype(int),
    texttemplate='%{text}',
    hovertemplate='Linea: %{y}<br>Responsabilità: %{x}<br>Scarti: %{z}<extra></extra>'
))
fig_hm_resp.update_layout(
    title='Heatmap Responsabilità × Linea Resp — top 12 linee',
    xaxis_tickangle=45,
    xaxis_title='Responsabilità',
    yaxis_title='Linea Resp',
    height=550
)
st.plotly_chart(fig_hm_resp, use_container_width=True)

# ── Grafico 4: Heatmap Responsabilità × Gr. merci ────────────────────────────
st.subheader('Responsabilità × Gruppo Merci')

df_resp_gm = df_resp.dropna(subset=['Gr. merci']).copy()
df_resp_gm['GM_label'] = df_resp_gm['Gr. merci'].astype(str) + ' — ' + df_resp_gm['Definizione'].fillna('').astype(str)

hm_resp_gm = (df_resp_gm[df_resp_gm['GM_label'].isin(top_gm_hm)]
              .groupby(['GM_label', 'Responsabilità'])
              .size()
              .reset_index(name='Scarti'))
hm_resp_gm_pivot = hm_resp_gm.pivot(index='GM_label', columns='Responsabilità', values='Scarti').fillna(0)

fig_hm_resp_gm = go.Figure(go.Heatmap(
    z=hm_resp_gm_pivot.values,
    x=hm_resp_gm_pivot.columns.tolist(),
    y=hm_resp_gm_pivot.index.tolist(),
    colorscale=HEATMAP_SCALE,
    text=hm_resp_gm_pivot.values.astype(int),
    texttemplate='%{text}',
    hovertemplate='Gruppo Merci: %{y}<br>Responsabilità: %{x}<br>Scarti: %{z}<extra></extra>'
))
fig_hm_resp_gm.update_layout(
    title='Heatmap Responsabilità × Gruppo Merci — top 12 gruppi',
    xaxis_tickangle=45,
    xaxis_title='Responsabilità',
    yaxis_title='Gruppo Merci',
    height=550
)
st.plotly_chart(fig_hm_resp_gm, use_container_width=True)

# ── Grafico 5: Trend mensile quota Responsabilità (area assoluta) ─────────────
st.subheader('Trend mensile per Responsabilità')

trend_resp = (df_resp.groupby(['AnnoMese', 'Responsabilità'])
                     .size()
                     .reset_index(name='Scarti')
                     .sort_values('AnnoMese'))

fig_trend_resp = px.area(
    trend_resp,
    x='AnnoMese', y='Scarti',
    color='Responsabilità',
    color_discrete_sequence=PALETTE_Q,
    title='Trend mensile scarti per Responsabilità',
    labels={'AnnoMese': 'Mese', 'Scarti': 'N. scarti'}
)
fig_trend_resp.update_xaxes(tickangle=45)
fig_trend_resp.update_layout(
    legend=dict(orientation='h', yanchor='bottom', y=1.02),
    height=500
)
st.plotly_chart(fig_trend_resp, use_container_width=True)



##############################################################################
# STEP 6 — Analisi per Linea Resp
##############################################################################

st.header('Step 6 — Analisi per Linea Resp', divider='grey')

df_linea = df_merged.dropna(subset=['Linea Resp']).copy()
df_linea['AnnoMese'] = df_linea['Data Segn.'].dt.to_period('M').astype(str)

# ── Grafico 1: Volume scarti per linea (pareto) ───────────────────────────────
pareto_linea = (df_linea.groupby('Linea Resp')
                        .size()
                        .reset_index(name='Scarti')
                        .sort_values('Scarti', ascending=False))
pareto_linea['Cumulata_%'] = pareto_linea['Scarti'].cumsum() / pareto_linea['Scarti'].sum() * 100
pareto_linea['%_totale']   = (pareto_linea['Scarti'] / pareto_linea['Scarti'].sum() * 100).round(1)

fig_pareto_linea = go.Figure()
fig_pareto_linea.add_trace(go.Bar(
    x=pareto_linea['Linea Resp'], y=pareto_linea['Scarti'],
    name='Scarti', marker_color=C_BRONZO,
    text=pareto_linea['%_totale'].astype(str) + '%',
    textposition='outside'
))
fig_pareto_linea.add_trace(go.Scatter(
    x=pareto_linea['Linea Resp'], y=pareto_linea['Cumulata_%'],
    name='Cumulata %', yaxis='y2',
    mode='lines+markers', line=dict(color=C_MARRONE, width=2)
))
fig_pareto_linea.add_hline(
    y=80, yref='y2', line_dash='dash', line_color=C_GRIGIO,
    annotation_text='80%', annotation_position='top right'
)
fig_pareto_linea.update_layout(
    title='Pareto scarti per Linea Resp',
    xaxis_tickangle=45,
    yaxis=dict(title='N. scarti'),
    yaxis2=dict(title='Cumulata %', overlaying='y', side='right', range=[0, 110]),
    legend=dict(orientation='h', yanchor='bottom', y=1.02),
    height=550
)
st.plotly_chart(fig_pareto_linea, use_container_width=True)

# ── Grafico 2: Mix TipoNC per linea (stacked bar 100%) ───────────────────────
st.subheader('Mix TipoNC per Linea Resp')

# Top linee per volume, top TipoNC già calcolati nello step 4
top_linee_6 = pareto_linea.head(12)['Linea Resp'].tolist()

df_mix_linea = df_linea[df_linea['Linea Resp'].isin(top_linee_6)].copy()
df_mix_linea['TipoNC_gruppo'] = df_mix_linea['TipoNC'].where(
    df_mix_linea['TipoNC'].isin(top_nc_hm), other='Altro'
)
mix_linea = (df_mix_linea.groupby(['Linea Resp', 'TipoNC_gruppo'])
                         .size()
                         .reset_index(name='Scarti'))
totali_linea = mix_linea.groupby('Linea Resp')['Scarti'].transform('sum')
mix_linea['%'] = (mix_linea['Scarti'] / totali_linea * 100).round(1)

fig_mix_linea = px.bar(
    mix_linea,
    x='Linea Resp', y='%',
    color='TipoNC_gruppo',
    color_discrete_sequence=PALETTE_Q,
    barmode='stack',
    title='Mix TipoNC per Linea Resp (% — top 12 linee)',
    labels={'%': '%', 'TipoNC_gruppo': 'TipoNC'},
    category_orders={'Linea Resp': top_linee_6}
)
fig_mix_linea.update_xaxes(tickangle=45)
fig_mix_linea.update_layout(
    yaxis_title='%',
    legend=dict(orientation='v', x=1.02, xanchor='left', y=1, yanchor='top'),
    height=550
)
st.plotly_chart(fig_mix_linea, use_container_width=True)

# ── Grafico 3: Trend mensile per linea (griglia 2 colonne) ────────────────────
st.subheader('Trend mensile per Linea Resp')

n_linee_grid = st.slider('Numero di linee da mostrare', min_value=2, max_value=12, value=6, step=2)
top_linee_grid = pareto_linea.head(n_linee_grid)['Linea Resp'].tolist()

n_cols = 2
n_rows = int(np.ceil(n_linee_grid / n_cols))

df_trend_linea = df_linea[df_linea['Linea Resp'].isin(top_linee_grid)]
tutti_mesi_linea = sorted(df_trend_linea['AnnoMese'].dropna().unique().tolist())

fig_grid_linea = make_subplots(
    rows=n_rows, cols=n_cols,
    subplot_titles=top_linee_grid,
    shared_xaxes=False
)

for i, linea in enumerate(top_linee_grid):
    riga = i // n_cols + 1
    col  = i %  n_cols + 1
    df_sub = (df_trend_linea[df_trend_linea['Linea Resp'] == linea]
              .groupby('AnnoMese').size()
              .reindex(tutti_mesi_linea, fill_value=0)
              .reset_index(name='Scarti')
              .rename(columns={'index': 'AnnoMese'}))
    fig_grid_linea.add_trace(
        go.Scatter(
            x=df_sub['AnnoMese'], y=df_sub['Scarti'],
            mode='lines+markers',
            line=dict(color=colori_grid[i % len(colori_grid)], width=2),
            marker=dict(size=5),
            showlegend=False
        ),
        row=riga, col=col
    )
    fig_grid_linea.update_xaxes(tickangle=45, row=riga, col=col)
    fig_grid_linea.update_yaxes(title_text='N. scarti', row=riga, col=col)

fig_grid_linea.update_layout(
    title=f'Trend mensile scarti — top {n_linee_grid} Linee Resp',
    height=350 * n_rows
)
st.plotly_chart(fig_grid_linea, use_container_width=True)


##############################################################################
# STEP 8 — Analisi testuale su Causa
##############################################################################

st.header('Step 7 — Analisi testuale su Causa', divider='grey')

import re
from collections import Counter

# Stopwords italiane
STOPWORDS_IT = {
    'di','a','da','in','con','su','per','tra','fra','il','lo','la','i','gli','le',
    'un','uno','una','e','è','ed','o','ma','se','che','non','si','mi','ti','ci',
    'vi','ne','del','dello','della','dei','degli','delle','al','allo','alla','ai',
    'agli','alle','dal','dallo','dalla','dai','dagli','dalle','nel','nello','nella',
    'nei','negli','nelle','sul','sullo','sulla','sui','sugli','sulle','col','coi',
    'come','dove','quando','perché','perche','anche','ancora','già','poi','però',
    'quindi','questo','questa','questi','queste','quello','quella','quelli','quelle',
    'essere','stato','stata','stati','state','ha','hanno','ho','hai','era','erano',
    'più','meno','molto','troppo','poco','tutto','tutti','altra','altro','altri',
    'altre','dopo','prima','sopra','sotto','durante','ad','sua','suo','suoi','sue',
    'loro','presso','senza','mentre','sempre','mai','solo','chi','cui','quale',
    'quali','ogni','nessun','né','le','alle','della','delle','degli','allo',
}

def tokenizza(testo):
    testo = str(testo).lower()
    testo = re.sub(r'[^a-zàáèéìíòóùú\s]', ' ', testo)
    token = testo.split()
    return [t for t in token if t not in STOPWORDS_IT and len(t) > 2]

df_causa = df_merged.dropna(subset=['Causa']).copy()
df_causa = df_causa[df_causa['Causa'].astype(str).str.strip() != '']
df_causa['token'] = df_causa['Causa'].apply(tokenizza)

st.write(f'Righe con Causa valorizzata: **{len(df_causa)}** su {len(df_merged)}')

# ── Grafico 1: Top N parole più frequenti (globale) ───────────────────────────
st.subheader('Parole più frequenti nelle note Causa')

top_n_parole = st.slider('Numero di parole da mostrare', min_value=10, max_value=50, value=25, step=5)

tutti_token = [t for tokens in df_causa['token'] for t in tokens]
freq_globale = Counter(tutti_token).most_common(top_n_parole)
df_freq = pd.DataFrame(freq_globale, columns=['Parola', 'Frequenza']).sort_values('Frequenza')

fig_freq = px.bar(
    df_freq,
    x='Frequenza', y='Parola',
    orientation='h',
    title=f'Top {top_n_parole} parole nelle note Causa',
    color='Frequenza', color_continuous_scale=['#F5F0EB','#5C3D1E']
)
fig_freq.update_layout(height=600, coloraxis_showscale=False, yaxis_title='')
st.plotly_chart(fig_freq, use_container_width=True)

# ── Grafico 2: Heatmap parole × TipoNC ───────────────────────────────────────
st.subheader('Parole chiave per TipoNC')

top_n_hm_causa = st.slider('Numero di parole nella heatmap', min_value=10, max_value=30, value=15, step=5)

top_parole_hm = [p for p, _ in Counter(tutti_token).most_common(top_n_hm_causa)]

df_causa_exp = df_causa[df_causa['TipoNC'].isin(top_nc_hm)].explode('token')
df_causa_exp = df_causa_exp[df_causa_exp['token'].isin(top_parole_hm)]

freq_nc = (df_causa_exp.groupby(['TipoNC', 'token'])
                       .size()
                       .reset_index(name='Frequenza'))
freq_nc_pivot = (freq_nc.pivot(index='token', columns='TipoNC', values='Frequenza')
                        .reindex(index=top_parole_hm)
                        .fillna(0))

fig_hm_causa = go.Figure(go.Heatmap(
    z=freq_nc_pivot.values,
    x=freq_nc_pivot.columns.tolist(),
    y=freq_nc_pivot.index.tolist(),
    colorscale=HEATMAP_SCALE,
    text=freq_nc_pivot.values.astype(int),
    texttemplate='%{text}',
    hovertemplate='TipoNC: %{x}<br>Parola: %{y}<br>Frequenza: %{z}<extra></extra>'
))
fig_hm_causa.update_layout(
    title='Frequenza parole chiave per TipoNC',
    xaxis_tickangle=45,
    xaxis_title='TipoNC',
    yaxis_title='Parola',
    height=600
)
st.plotly_chart(fig_hm_causa, use_container_width=True)

# ── Grafico 3: Top parole per TipoNC selezionato ─────────────────────────────
st.subheader('Parole più frequenti per TipoNC specifico')

tiponc_scelto = st.selectbox(
    'Seleziona TipoNC',
    ['Tutti'] + pareto_nc['TipoNC'].tolist(),
    key='sel_tiponc_causa'
)

df_causa_filt = df_causa if tiponc_scelto == 'Tutti' else df_causa[df_causa['TipoNC'] == tiponc_scelto]
token_filt = [t for tokens in df_causa_filt['token'] for t in tokens]
freq_filt = Counter(token_filt).most_common(top_n_parole)
df_freq_filt = pd.DataFrame(freq_filt, columns=['Parola', 'Frequenza']).sort_values('Frequenza')

fig_freq_filt = px.bar(
    df_freq_filt,
    x='Frequenza', y='Parola',
    orientation='h',
    title=f'Top {top_n_parole} parole — {tiponc_scelto}',
    color='Frequenza', color_continuous_scale=['#F5F0EB','#5C3D1E']
)
fig_freq_filt.update_layout(height=600, coloraxis_showscale=False, yaxis_title='')
st.plotly_chart(fig_freq_filt, use_container_width=True)


##############################################################################
# STEP 9 — Analisi multi-dimensionale
##############################################################################

st.header('Step 8 — Analisi multi-dimensionale', divider='grey')

df_multi = df_merged.dropna(subset=['Gr. merci', 'TipoNC', 'Responsabilità']).copy()
df_multi['GM_label'] = df_multi['Gr. merci'].astype(str) + ' — ' + df_multi['Definizione'].fillna('').astype(str)

# ── Grafico 1: Pareto composto Gr. merci × TipoNC × Responsabilità ────────────
st.subheader('Pareto composto — combinazioni prioritarie')

pareto_composto = (df_multi
    .groupby(['GM_label', 'TipoNC', 'Responsabilità'])
    .size()
    .reset_index(name='Scarti')
    .sort_values('Scarti', ascending=False)
    .reset_index(drop=True))

pareto_composto['Cumulata_%'] = (pareto_composto['Scarti'].cumsum()
                                  / pareto_composto['Scarti'].sum() * 100)
pareto_composto['Combinazione'] = (pareto_composto['GM_label'] + ' | '
                                   + pareto_composto['TipoNC'] + ' | '
                                   + pareto_composto['Responsabilità'])

soglia_pareto = st.slider('Soglia cumulata % da mostrare', min_value=50, max_value=100, value=80, step=5)
df_pareto_filt = pareto_composto[pareto_composto['Cumulata_%'] <= soglia_pareto]

fig_pareto_comp = go.Figure()
fig_pareto_comp.add_trace(go.Bar(
    x=df_pareto_filt['Combinazione'], y=df_pareto_filt['Scarti'],
    name='Scarti', marker_color=C_BRONZO
))
fig_pareto_comp.add_trace(go.Scatter(
    x=df_pareto_filt['Combinazione'], y=df_pareto_filt['Cumulata_%'],
    name='Cumulata %', yaxis='y2',
    mode='lines+markers', line=dict(color=C_MARRONE, width=2)
))
fig_pareto_comp.add_hline(
    y=soglia_pareto, yref='y2', line_dash='dash', line_color=C_GRIGIO,
    annotation_text=f'{soglia_pareto}%', annotation_position='top right'
)
fig_pareto_comp.update_layout(
    title=f'Pareto composto — combinazioni che coprono il {soglia_pareto}% degli scarti ({len(df_pareto_filt)} combinazioni)',
    xaxis_tickangle=45,
    xaxis_tickfont=dict(size=9),
    yaxis=dict(title='N. scarti'),
    yaxis2=dict(title='Cumulata %', overlaying='y', side='right', range=[0, 105]),
    legend=dict(orientation='h', yanchor='bottom', y=1.02),
    height=600
)
st.plotly_chart(fig_pareto_comp, use_container_width=True)

st.dataframe(
    df_pareto_filt[['Combinazione', 'Scarti', 'Cumulata_%']].reset_index(drop=True),
    use_container_width=True, height=300
)

# ── Grafico 2: Heatmap Gr. merci × TipoNC colorata per Criticità Alta ─────────
st.subheader('Mappa di rischio — Gr. merci × TipoNC')

rischio = (df_multi.groupby(['GM_label', 'TipoNC'])
           .agg(
               Scarti=('TipoNC', 'count'),
               N_Alta=('Criticità', lambda x: (x == 'Alta').sum())
           )
           .reset_index())
rischio['%_Alta'] = (rischio['N_Alta'] / rischio['Scarti'] * 100).round(1)

# Filtra top GM e top TipoNC per leggibilità
rischio_filt = rischio[
    rischio['GM_label'].isin(top_gm_hm) &
    rischio['TipoNC'].isin(top_nc_hm)
]

pivot_scarti  = rischio_filt.pivot(index='GM_label', columns='TipoNC', values='Scarti').fillna(0)
pivot_pct     = rischio_filt.pivot(index='GM_label', columns='TipoNC', values='%_Alta').fillna(0)

# Testo cella: "N scarti\n(XX% Alta)"
text_matrix = [[
    f"{int(pivot_scarti.loc[r, c])}<br>({pivot_pct.loc[r, c]:.0f}% Alta)"
    if c in pivot_scarti.columns and r in pivot_scarti.index else ''
    for c in pivot_scarti.columns]
    for r in pivot_scarti.index]

fig_rischio = go.Figure(go.Heatmap(
    z=pivot_scarti.values,
    x=pivot_scarti.columns.tolist(),
    y=pivot_scarti.index.tolist(),
    colorscale=HEATMAP_SCALE,
    text=text_matrix,
    texttemplate='%{text}',
    hovertemplate='Gr. merci: %{y}<br>TipoNC: %{x}<br>Scarti: %{z}<extra></extra>'
))
fig_rischio.update_layout(
    title='Mappa di rischio — N. scarti e % Alta criticità per cella (Gr. merci × TipoNC)',
    xaxis_tickangle=45,
    xaxis_title='TipoNC',
    yaxis_title='Gruppo Merci',
    height=600
)
st.plotly_chart(fig_rischio, use_container_width=True)

# ── Grafico 3: Sunburst Gr. merci → TipoNC → Responsabilità ──────────────────
st.subheader('Gerarchia scarti — Gr. merci → TipoNC → Responsabilità')

# Limitiamo per non sovraffollare il sunburst
top_gm_sb  = pareto_gm.head(8)['GM_label'].tolist()
top_nc_sb  = pareto_nc.head(8)['TipoNC'].tolist()

df_sb = df_multi[
    df_multi['GM_label'].isin(top_gm_sb) &
    df_multi['TipoNC'].isin(top_nc_sb)
].groupby(['GM_label', 'TipoNC', 'Responsabilità']).size().reset_index(name='Scarti')

fig_sunburst = px.sunburst(
    df_sb,
    path=['GM_label', 'TipoNC', 'Responsabilità'],
    values='Scarti',
    title='Sunburst — Gr. merci → TipoNC → Responsabilità (top 8 per livello)',
    color='Scarti',
    color_continuous_scale=['#F5F0EB','#5C3D1E']
)
fig_sunburst.update_layout(height=700, coloraxis_showscale=False)
fig_sunburst.update_traces(textinfo='label+percent entry')
st.plotly_chart(fig_sunburst, use_container_width=True)


st.stop()



import streamlit as st
import pandas as pd
import sqlite3
import os
import time
import requests
import json
from datetime import datetime, timedelta
from nba_api.stats.endpoints import leaguegamelog, scoreboardv2, commonteamroster
from nba_api.stats.static import teams as nba_static_teams

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="NBA Analyzer Pro",
    page_icon="🏀",
    layout="wide"
)

# ==========================================
# 2. CSS DEFINITIVO (CORREGIDO)
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Teko:wght@300..700&family=Inter:wght@300;400;500;600;700&display=swap');

/* ============================
   LAYOUT GENERAL
   ============================ */
.main .block-container {
    max-width: 1320px !important;
    padding: 1.5rem 1.75rem 3rem 1.75rem !important;
    margin: 0 auto !important;
}

body {
    background: radial-gradient(circle at top, #101624 0, #05070c 40%, #020308 100%) !important;
    color: #e3e7f1 !important;
    font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* Quitar centrado agresivo por defecto */
h1, h2, h3, h4, h5, h6, p {
    text-align: left !important;
}

/* Encabezados principales */
h1 {
    font-family: 'Teko', system-ui !important;
    font-size: 52px !important;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #ffffff;
    margin-bottom: 8px !important;
}

h2 {
    font-family: 'Teko', system-ui !important;
    font-size: 30px !important;
    text-transform: uppercase;
    letter-spacing: 0.14em;
    color: #e3f2fd;
    margin-top: 28px !important;
    margin-bottom: 8px !important;
}

h3 {
    font-family: 'Inter', system-ui !important;
    font-size: 17px !important;
    text-transform: none;
    letter-spacing: 0.04em;
    font-weight: 600;
    color: #c5d1ff;
    text-transform: uppercase;
}

p, span, label {
    font-size: 14px !important;
}

/* ============================
   SIDEBAR
   ============================ */
[data-testid="stSidebar"] {
    background: linear-gradient(180deg, #050816 0, #020308 35%, #050816 100%) !important;
    border-right: 1px solid rgba(148, 163, 184, 0.22);
}

[data-testid="stSidebar"] * {
    font-family: 'Inter', system-ui !important;
}

[data-testid="stSidebarNav"]::before {
    content: "NBA Analyzer Pro";
    margin-left: 10px;
    margin-top: 12px;
    font-weight: 600;
    font-size: 13px;
    letter-spacing: 0.18em;
    text-transform: uppercase;
    color: #9ca3af;
}

[data-testid="stSidebar"] .stRadio > label {
    font-weight: 500;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    font-size: 12px;
}

/* ============================
   CARDS / CONTENEDORES
   ============================ */
.card-elevated {
    background: radial-gradient(circle at top left, #18212f 0, #090d16 40%, #05070d 100%);
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.28);
    box-shadow: 0 18px 40px rgba(15, 23, 42, 0.85);
    padding: 18px 20px;
    margin-bottom: 18px;
}

.card-section-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
}

.pill-label {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: 999px;
    background: rgba(15, 23, 42, 0.88);
    border: 1px solid rgba(148, 163, 184, 0.45);
    font-size: 11px;
    text-transform: uppercase;
    letter-spacing: 0.08em;
    color: #e5e7eb;
}

.subtext-muted {
    font-size: 12px;
    color: #9ca3af;
}

/* ============================
   TABLAS / DATAFRAMES
   ============================ */
[data-testid="stDataFrame"] {
    width: 100% !important;
    max-width: 100% !important;
    margin: 0.25rem auto 0.75rem auto !important;
}

.table-responsive {
    display: flex !important;
    justify-content: center !important;
    width: 100% !important;
    overflow-x: auto;
    margin-bottom: 0.75rem;
}

table.custom-table {
    margin: 0 auto !important;
    border-collapse: collapse;
    font-size: 13px;
    min-width: 360px;
    width: 100%;
    background: rgba(15, 23, 42, 0.92);
}

table.custom-table th {
    background: linear-gradient(90deg, #111827, #020617);
    color: #f9fafb;
    text-align: center !important;
    padding: 9px 8px;
    border-bottom: 1px solid rgba(55, 65, 81, 0.9);
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.08em;
}

table.custom-table td {
    text-align: center !important;
    padding: 7px 6px;
    border-bottom: 1px solid rgba(31, 41, 55, 0.85);
    color: #e5e7eb;
}

table.custom-table tr:nth-child(even) td {
    background-color: rgba(15, 23, 42, 0.72);
}

table.custom-table tr:hover td {
    background-color: rgba(30, 64, 175, 0.35);
}

/* ============================
   GAME CARDS / MATCHUPS
   ============================ */
.game-card {
    background: radial-gradient(circle at top left, #1d2535 0, #080b12 45%, #05070c 100%);
    border-radius: 18px;
    border: 1px solid rgba(148, 163, 184, 0.35);
    padding: 15px 16px 14px 16px;
    margin-bottom: 14px;
    width: 100%;
    text-align: center;
    box-shadow: 0 14px 35px rgba(15, 23, 42, 0.9);
}

.game-matchup {
    display: flex;
    justify-content: center;
    align-items: center;
    gap: 14px;
    margin-bottom: 6px;
}

.team-logo {
    width: 46px;
    height: 46px;
    object-fit: contain;
    filter: drop-shadow(0 0 12px rgba(15, 23, 42, 0.9));
}

.game-time {
    color: #facc15;
    font-size: 20px;
    font-family: 'Teko', system-ui;
    letter-spacing: 0.16em;
}

.vs-text {
    font-size: 18px;
    color: #9ca3af;
    letter-spacing: 0.18em;
}

/* ============================
   BOTONES
   ============================ */
div.stButton > button {
    width: 100%;
    border-radius: 999px !important;
    font-weight: 600 !important;
    font-size: 13px !important;
    background: linear-gradient(90deg, #0f172a, #1d4ed8);
    color: #f9fafb !important;
    border: 1px solid rgba(129, 140, 248, 0.9);
    transition: all 0.18s ease-out;
    box-shadow: 0 10px 25px rgba(15, 23, 42, 0.9);
}

div.stButton > button:hover {
    border-color: #facc15 !important;
    color: #facc15 !important;
    transform: translateY(-1px);
    box-shadow: 0 14px 30px rgba(30, 64, 175, 0.9);
}

/* ============================
   PARLAY / PATRONES / DNP
   ============================ */
.parlay-box {
    background: radial-gradient(circle at top, #111827 0, #020617 70%);
    border: 1px solid rgba(147, 197, 253, 0.22);
    border-radius: 16px;
    padding: 12px 14px;
    margin-bottom: 15px;
}

.parlay-header {
    font-size: 16px;
    font-weight: 600;
    margin-bottom: 8px;
    border-bottom: 1px solid rgba(55, 65, 81, 0.9);
    padding-bottom: 6px;
    text-align: left !important;
    color: #e5e7eb;
    letter-spacing: 0.16em;
    text-transform: uppercase;
}

.parlay-leg {
    background: linear-gradient(90deg, rgba(15, 23, 42, 0.9), rgba(17, 24, 39, 0.5));
    margin: 5px 0;
    padding: 8px 10px;
    border-radius: 10px;
    display: flex;
    justify-content: space-between;
    align-items: center;
    color: #f9fafb;
    font-size: 13px;
}

.parlay-leg .leg-player {
    font-weight: 500;
}

.parlay-leg .leg-info {
    text-align: right;
}

.parlay-leg .leg-val {
    font-weight: 700;
}

.dnp-missing {
    color: #f97373;
    font-weight: 600;
}

.dnp-full {
    color: #4ade80;
    font-weight: 600;
}

.pat-stars {
    color: #fb7185;
    font-weight: 600;
}

.pat-impact {
    color: #a5b4fc;
}

/* ============================
   CUOTAS
   ============================ */
.odds-info {
    background: radial-gradient(circle at top, #0f172a 0, #020617 70%);
    border: 1px solid rgba(129, 140, 248, 0.55);
    border-radius: 14px;
    padding: 12px 14px;
    margin-bottom: 16px;
    text-align: left;
    color: #e5e7eb;
}

.odds-timestamp {
    color: #facc15;
    font-weight: 600;
    font-size: 16px;
}

/* ============================
   OTROS
   ============================ */
[data-testid="stElementToolbar"] { display: none !important; }
footer { display: none !important; }

[data-testid="stCheckbox"] {
    display: flex;
    justify-content: center;
    width: 100%;
}

.credits {
    margin-top: 1.25rem;
    font-size: 12px;
    color: #6b7280;
    text-align: right;
}

.next-game-btn {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    padding: 6px 14px;
    border-radius: 999px;
    border: 1px solid rgba(248, 250, 252, 0.95);
    font-size: 12px;
    text-decoration: none;
    color: #0f172a;
    background: #facc15;
    font-weight: 600;
    letter-spacing: 0.12em;
    text-transform: uppercase;
}

.match-link {
    text-decoration: none;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. GESTIÓN DE ESTADO
# ==========================================
API_KEY_DEFAULT = "ae1dd866651d5f06c234f972b0004084"

if 'page' not in st.session_state: st.session_state.page = "🏠 Inicio"
if 'selected_home' not in st.session_state: st.session_state.selected_home = None
if 'selected_visitor' not in st.session_state: st.session_state.selected_visitor = None
if 'selected_player' not in st.session_state: st.session_state.selected_player = None
if 'odds_api_key' not in st.session_state: st.session_state.odds_api_key = API_KEY_DEFAULT

def navegar_a_partido(home, visitor):
    st.session_state.selected_home = home
    st.session_state.selected_visitor = visitor
    st.session_state.page = "⚔️ Analizar Partido"

def navegar_a_jugador(player_name):
    st.session_state.selected_player = player_name
    st.session_state.page = "👤 Jugador"

def volver_inicio():
    st.session_state.page = "🏠 Inicio"

def volver_a_partido():
    st.session_state.page = "⚔️ Analizar Partido"

# ==========================================
# 4. LÓGICA DE DATOS
# ==========================================
DB_PATH = "nba.sqlite"
CSV_FOLDER = "csv"
if not os.path.exists(CSV_FOLDER): os.makedirs(CSV_FOLDER)
ODDS_CACHE_FILE = "odds_cache.json"

def download_data():
    progress_text = "Descargando datos..."
    my_bar = st.progress(0, text=progress_text)
    target_seasons = ['2024-25', '2025-26']
    all_seasons_data = []
    for i, season in enumerate(target_seasons):
        try:
            gamelogs = leaguegamelog.LeagueGameLog(season=season, player_or_team_abbreviation='P')
            df = gamelogs.get_data_frames()[0]
            if not df.empty: all_seasons_data.append(df)
            my_bar.progress((i + 1) * 50, text=f"Temporada {season} lista...")
        except Exception as e: st.error(f"Error: {e}")

    if all_seasons_data:
        full_df = pd.concat(all_seasons_data, ignore_index=True)
        cols_needed = ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'GAME_DATE', 'MATCHUP', 'PTS', 'REB', 'AST', 'FG3M', 'MIN', 'WL', 'GAME_ID']
        cols_final = [c for c in cols_needed if c in full_df.columns]
        df_clean = full_df[cols_final].copy()
        df_clean.columns = df_clean.columns.str.lower()
        df_clean.to_csv(f'{CSV_FOLDER}/player_stats.csv', index=False)
        try:
            conn = sqlite3.connect(DB_PATH)
            df_clean.to_sql('player', conn, if_exists='replace', index=False)
            conn.close()
        except: pass
        my_bar.progress(100, text="Completado")
        time.sleep(1)
        my_bar.empty()
        return True
    return False

def load_data():
    csv_path = f"{CSV_FOLDER}/player_stats.csv"
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        if 'game_date' in df.columns: df['game_date'] = pd.to_datetime(df['game_date'])
        if 'game_id' in df.columns: df['game_id'] = df['game_id'].astype(str).str.zfill(10)
        else: df['game_id'] = None
        if 'fg3m' not in df.columns: df['fg3m'] = 0
        return df
    return pd.DataFrame()

def convertir_hora_espanol(hora_et):
    if "Final" in hora_et: return "FINALIZADO"
    try:
        hora_clean = hora_et.replace(" ET", "").strip()
        dt = datetime.strptime(hora_clean, "%I:%M %p")
        dt_spain = dt + timedelta(hours=6)
        return dt_spain.strftime("%H:%M")
    except: return hora_et

def get_basketball_date():
    now = datetime.now()
    if now.hour < 12: 
        return now.date() - timedelta(days=1)
    return now.date()

@st.cache_data(ttl=86400) 
def get_nba_schedule():
    try:
        url = "https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json"
        response = requests.get(url, timeout=5).json()
        return response['leagueSchedule']['gameDates']
    except: return []

@st.cache_data(ttl=3600)
def get_team_roster_numbers(team_id):
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=team_id)
        df_roster = roster.get_data_frames()[0]
        df_roster['NUM'] = df_roster['NUM'].astype(str).str.replace('.0', '', regex=False)
        return dict(zip(df_roster['PLAYER'], df_roster['NUM']))
    except: return {}

def get_next_matchup_info(t1_abv, t2_abv):
    dates = get_nba_schedule()
    if not dates: return None
    nba_teams = nba_static_teams.get_teams()
    team_map = {t['abbreviation']: t['id'] for t in nba_teams}
    id1 = team_map.get(t1_abv)
    id2 = team_map.get(t2_abv)
    if not id1 or not id2: return None
    
    today = datetime.now().date()
    for day in dates:
        try:
            game_dt = datetime.strptime(day['gameDate'], "%m/%d/%Y %H:%M:%S").date()
            if game_dt < today: continue 
            for game in day['games']:
                h_id = game['homeTeam']['teamId']
                v_id = game['awayTeam']['teamId']
                if (h_id == id1 and v_id == id2) or (h_id == id2 and v_id == id1):
                    return {
                        'date': game_dt.strftime("%d/%m/%Y"),
                        'home': t1_abv if h_id == id1 else t2_abv,
                        'away': t2_abv if h_id == id1 else t1_abv,
                        'game_id': game['gameId']
                    }
        except: continue
    return None

def obtener_partidos():
    nba_teams = nba_static_teams.get_teams()
    team_map = {t['id']: t['abbreviation'] for t in nba_teams}
    
    # Pedimos datos de HOY y MAÑANA (Horario US)
    basket_today_us = get_basketball_date()
    fechas_us = [basket_today_us, basket_today_us + timedelta(days=1)]
    
    agenda = {}
    
    for fecha in fechas_us:
        fecha_str = fecha.strftime('%Y-%m-%d')
        try:
            board = scoreboardv2.ScoreboardV2(game_date=fecha_str)
            games = board.game_header.get_data_frame()
            
            if not games.empty:
                for _, game in games.iterrows():
                    h_id, v_id = game['HOME_TEAM_ID'], game['VISITOR_TEAM_ID']
                    status_text = game['GAME_STATUS_TEXT'] 
                    
                    # --- LÓGICA DE CONVERSIÓN DE FECHA ---
                    # Asumimos fecha base la de la API (US)
                    fecha_juego_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
                    hora_esp = status_text # Por defecto
                    
                    if "ET" in status_text:
                        try:
                            hora_clean = status_text.replace(" ET", "").strip()
                            # Creamos objeto datetime completo (Fecha US + Hora US)
                            dt_us = datetime.strptime(f"{fecha_str} {hora_clean}", "%Y-%m-%d %I:%M %p")
                            # Sumamos 6 horas para pasar a hora España
                            dt_es = dt_us + timedelta(hours=6)
                            
                            # Actualizamos la fecha y la hora formateada
                            fecha_juego_dt = dt_es
                            hora_esp = dt_es.strftime("%H:%M")
                        except:
                            pass 
                    elif "Final" in status_text:
                        hora_esp = "FINALIZADO"
                    
                    # Generamos la etiqueta REAL (Ej: "21/01") basada en la hora sumada
                    label_real = fecha_juego_dt.strftime("%d/%m")
                    
                    if label_real not in agenda:
                        agenda[label_real] = []
                        
                    agenda[label_real].append({
                        'game_id': game['GAME_ID'],
                        'v_abv': team_map.get(v_id), 'h_abv': team_map.get(h_id),
                        'v_logo': f"https://cdn.nba.com/logos/nba/{v_id}/global/L/logo.svg",
                        'h_logo': f"https://cdn.nba.com/logos/nba/{h_id}/global/L/logo.svg",
                        'time': hora_esp
                    })
        except: pass
        
    # Ordenamos las fechas
    keys_ordenadas = sorted(agenda.keys(), key=lambda x: datetime.strptime(x, "%d/%m").replace(year=datetime.now().year))
    agenda_ordenada = {k: agenda[k] for k in keys_ordenadas}
    
    return agenda_ordenada

# ==========================================
# 5. FUNCIONES UI (RENDERIZADO)
# ==========================================
def apply_custom_color(column, avg, col_name):
    styles = []
    if col_name in ['FG3M', '3PM']: tolerance = 1
    elif col_name == 'PTS': tolerance = 3
    elif col_name in ['REB', 'AST', 'MIN']: tolerance = 2
    else: tolerance = 5

    upper_bound = avg + tolerance
    lower_bound = avg - tolerance

    for val in column:
        text_color = "white"
        if val > upper_bound: color = '#2962ff'
        elif val < lower_bound: color = '#d32f2f'
        else:
            if val >= avg: color = '#00c853'
            else:
                color = '#fff176'
                text_color = "black"
        styles.append(f'background-color: {color}; color: {text_color}; font-weight: bold; text-align: center;')
    return styles

def mostrar_leyenda_colores():
    st.markdown("""
        <div style='display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin: 10px 0; font-family: sans-serif;'>
            <div style='background-color: #2962ff; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px;'>🔵 Supera</div>
            <div style='background-color: #00c853; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px;'>🟢 Iguala</div>
            <div style='background-color: #fff176; color: black; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px;'>⚠️ Cerca</div>
            <div style='background-color: #d32f2f; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px;'>🔴 Debajo</div>
        </div>
    """, unsafe_allow_html=True)

def mostrar_tabla_bonita(df_raw, col_principal_espanol, simple_mode=False, means_dict=None):
    cols_numericas = [c for c in df_raw.columns if c in ['PTS', 'REB', 'AST', 'FG3M', 'MIN', '3PM'] or '_PTS' in c or '_REB' in c]
    
    if simple_mode:
        html = df_raw.style\
            .format("{:.0f}", subset=[c for c in cols_numericas])\
            .hide(axis="index")\
            .to_html(classes="custom-table", escape=False)
    else:
        styler = df_raw.style.format("{:.1f}", subset=cols_numericas)
        if means_dict:
            for c in ['PTS', 'REB', 'AST', 'FG3M', 'MIN', '3PM']: 
                if c in df_raw.columns and c in means_dict:
                    styler.apply(apply_custom_color, avg=means_dict[c], col_name=c, subset=[c])
        else:
            styler.background_gradient(subset=[col_principal_espanol] if col_principal_espanol else None, cmap='Greens')
        html = styler.hide(axis="index").to_html(classes="custom-table", escape=False)
    
    st.markdown(f"<div class='table-responsive'>{html}</div>", unsafe_allow_html=True)

def render_clickable_player_table(df_stats, stat_col, jersey_map):
    if df_stats.empty:
        st.info("Sin datos.")
        return

    df_stats['JUGADOR_SOLO'] = df_stats['player_name']
    df_stats['EQ'] = df_stats['team_abbreviation']
    
    cols_to_show = ['JUGADOR_SOLO', 'EQ', stat_col.lower(), f'trend_{stat_col.lower()}', 'trend_min']
    df_interactive = df_stats[cols_to_show].copy()
    
    df_interactive.columns = ['JUGADOR', 'EQ', stat_col, 'RACHA', 'MIN']
    
    selection = st.dataframe(
        df_interactive,
        use_container_width=True,
        hide_index=True,
        on_select="rerun", 
        selection_mode="single-row",
        column_config={
            "JUGADOR": st.column_config.TextColumn("JUGADOR", width=None),
            "EQ": st.column_config.TextColumn("EQ", width="small"),
            stat_col: st.column_config.NumberColumn(stat_col, format="%.1f", width=60),
            "RACHA": st.column_config.TextColumn("RACHA (Últ. Partidos)", width=150), 
            "MIN": st.column_config.TextColumn("MIN", width=115) 
        }
    )
    
    if len(selection.selection.rows) > 0:
        row_idx = selection.selection.rows[0]
        player_name = df_interactive.iloc[row_idx]['JUGADOR']
        navegar_a_jugador(player_name)
        st.rerun()

# --- FUNCIONES DE API DE CUOTAS Y CACHÉ ---
def get_sports_odds(api_key, market_key):
    # --- CORRECCIÓN ERROR 422 ---
    region = 'eu'
    if market_key == 'player_points':
        region = 'us' 
    
    try:
        odds_response = requests.get(
            f'https://api.the-odds-api.com/v4/sports/basketball_nba/odds',
            params={
                'api_key': api_key,
                'regions': region,
                'markets': market_key, 
                'oddsFormat': 'decimal',
                'dateFormat': 'iso',
            }
        )
        if odds_response.status_code != 200:
            if odds_response.status_code == 422:
                return None, "Error 422: Tu plan gratuito no soporta este mercado o región. Prueba 'Ganador Partido'."
            return None, f"Error API: {odds_response.status_code}"
        return odds_response.json(), None
    except Exception as e:
        return None, str(e)

def save_cache(data, market_type):
    cache = {
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "market": market_type,
        "data": data
    }
    with open(ODDS_CACHE_FILE, 'w') as f:
        json.dump(cache, f)

def load_cache():
    if os.path.exists(ODDS_CACHE_FILE):
        try:
            with open(ODDS_CACHE_FILE, 'r') as f:
                return json.load(f)
        except: return None
    return None

# ==========================================
# 6. APP PRINCIPAL
# ==========================================
st.markdown("<h1>🏀 NBA PRO ANALYZER 🏀</h1>", unsafe_allow_html=True)

pages = ["🏠 Inicio", "👤 Jugador", "⚔️ Analizar Partido", "💰 Buscador de Cuotas", "🔄 Actualizar Datos"]
if st.session_state.page not in pages: st.session_state.page = "🏠 Inicio"
current_index = pages.index(st.session_state.page)
opcion = st.sidebar.radio("Menú:", pages, index=current_index)

if opcion != st.session_state.page:
    st.session_state.page = opcion
    st.rerun()

df = load_data()

latest_teams_map = {}
if not df.empty:
    latest_entries = df.sort_values('game_date').drop_duplicates('player_name', keep='last')
    latest_teams_map = dict(zip(latest_entries['player_name'], latest_entries['team_abbreviation']))

# --- PÁGINA INICIO ---
if st.session_state.page == "🏠 Inicio":
    agenda = obtener_partidos()
    
    # Obtenemos las dos primeras fechas disponibles
    fechas_disponibles = list(agenda.keys())
    
    titulo_col1 = fechas_disponibles[0] if len(fechas_disponibles) > 0 else "HOY"
    titulo_col2 = fechas_disponibles[1] if len(fechas_disponibles) > 1 else "MAÑANA"
    
    c1, c2 = st.columns(2)
    
    def render_block(col, title, games, color):
        with col:
            st.markdown(f"<h3 style='color:{color}; text-align: center;'>{title}</h3>", unsafe_allow_html=True)
            if not games: 
                st.caption("No hay partidos programados.")
                return 

            for i, g in enumerate(games):
                st.markdown(f"""
                <div class='game-card'>
                    <div class='game-matchup'>
                        <img src='{g['v_logo']}' class='team-logo'> <span class='vs-text'>@</span> <img src='{g['h_logo']}' class='team-logo'>
                    </div>
                    <div style='color:white; font-weight:bold;'>{g['v_abv']} vs {g['h_abv']}</div>
                    <div class='game-time'>{g['time']}</div>
                </div>
                """, unsafe_allow_html=True)
                
                unique_key = f"btn_{title}_{g['game_id']}_{i}"
                if st.button(f"🔍 ANALIZAR {g['v_abv']} vs {g['h_abv']}", key=unique_key):
                    navegar_a_partido(g['h_abv'], g['v_abv'])
                    st.rerun()
                
                st.write("")

    render_block(c1, titulo_col1, agenda.get(titulo_col1, []), "#4caf50")
    render_block(c2, titulo_col2, agenda.get(titulo_col2, []), "#2196f3")
    
    st.markdown("<div class='credits'>Creado por ad.ri.</div>", unsafe_allow_html=True)

# --- PÁGINA ACTUALIZAR ---
elif st.session_state.page == "🔄 Actualizar Datos":
    st.write("### 🔄 Sincronización")
    if st.button("Descargar y Actualizar Ahora"):
        with st.spinner("Conectando con servidores NBA..."):
            success = download_data()
            if success:
                st.success("¡Datos actualizados con Triples!")
                st.rerun()

# --- PÁGINA JUGADOR ---
elif st.session_state.page == "👤 Jugador":
    c_back, c_title, c_dummy = st.columns([1, 10, 1])
    with c_back:
        st.write("")
        if st.session_state.selected_home and st.session_state.selected_visitor:
            if st.button(f"⬅️ Volver"):
                volver_a_partido()
                st.rerun()
    with c_title:
        st.markdown("<h2 style='text-align: center; margin-top: 0; padding-top: 0;'>👤 Buscador de Jugadores</h2>", unsafe_allow_html=True)
    with c_dummy:
        st.write("")

    if df.empty:
        st.error("Primero actualiza los datos.")
    else:
        todos_jugadores = sorted(df['player_name'].unique())
        todos_equipos = sorted(df['team_abbreviation'].unique())
        idx_sel = todos_jugadores.index(st.session_state.selected_player) if st.session_state.selected_player in todos_jugadores else None
        jugador = st.selectbox("Nombre del Jugador:", todos_jugadores, index=idx_sel)
        
        if jugador and jugador != st.session_state.selected_player:
            st.session_state.selected_player = jugador

        if jugador:
            player_data = df[df['player_name'] == jugador].sort_values('game_date', ascending=False)
            rival = st.selectbox("Filtrar vs Rival (Opcional):", todos_equipos, index=None)
            
            mean_pts = player_data['pts'].mean()
            mean_reb = player_data['reb'].mean()
            mean_ast = player_data['ast'].mean()
            mean_3pm = player_data['fg3m'].mean()
            mean_min = player_data['min'].mean()

            means_dict = {'PTS': mean_pts, 'REB': mean_reb, 'AST': mean_ast, '3PM': mean_3pm, 'MIN': mean_min}

            # Tarjeta visual tipo perfil NBA para estadísticas medias
            team_for_player = latest_teams_map.get(jugador, "")
            player_initials = "".join([p[0] for p in jugador.split() if p]).upper()[:3]

            st.markdown(f"""
            <div style="
                background: linear-gradient(135deg, #1976d2 0%, #0d47a1 60%, #121212 100%);
                border-radius: 18px;
                padding: 20px 24px;
                margin-bottom: 20px;
                display: flex;
                align-items: center;
                justify-content: space-between;
                box-shadow: 0 10px 25px rgba(0,0,0,0.55);
            ">
                <div style="display:flex; align-items:center; gap:18px;">
                    <div style="
                        width:72px;
                        height:72px;
                        border-radius:50%;
                        background:#0d47a1;
                        border:3px solid rgba(255,255,255,0.25);
                        display:flex;
                        align-items:center;
                        justify-content:center;
                        font-family:'Teko', sans-serif;
                        font-size:32px;
                        color:white;
                    ">{player_initials}</div>
                    <div>
                        <div style="
                            font-family:'Teko', sans-serif;
                            font-size:34px;
                            color:#ffffff;
                            text-transform:uppercase;
                            letter-spacing:1px;
                        ">{jugador}</div>
                        <div style="margin-top:4px; display:flex; flex-wrap:wrap; gap:8px; align-items:center;">
                            <span style="
                                background:rgba(0,0,0,0.35);
                                border-radius:999px;
                                padding:3px 12px;
                                font-size:12px;
                                color:#e3f2fd;
                                text-transform:uppercase;
                                letter-spacing:0.08em;
                            ">TEMPORADA 2025-26</span>
                            {f"<span style='background:#ffbd45; color:#000; border-radius:999px; padding:3px 12px; font-size:12px; font-weight:600;'>{team_for_player}</span>" if team_for_player else ""}
                        </div>
                    </div>
                </div>
                <div style="
                    display:grid;
                    grid-template-columns:repeat(5,minmax(60px,1fr));
                    gap:10px;
                    max-width:520px;
                    width:100%;
                    margin-left:20px;
                ">
                    <div style="background:rgba(0,0,0,0.28); border-radius:12px; padding:8px 6px; text-align:center;">
                        <div style="font-size:11px; color:#bbdefb; text-transform:uppercase; letter-spacing:0.07em;">PTS</div>
                        <div style="font-size:22px; color:#ffffff; font-weight:700; margin-top:2px;">{mean_pts:.1f}</div>
                        <div style="font-size:10px; color:#90caf9; margin-top:1px;">por partido</div>
                    </div>
                    <div style="background:rgba(0,0,0,0.28); border-radius:12px; padding:8px 6px; text-align:center;">
                        <div style="font-size:11px; color:#bbdefb; text-transform:uppercase; letter-spacing:0.07em;">REB</div>
                        <div style="font-size:22px; color:#ffffff; font-weight:700; margin-top:2px;">{mean_reb:.1f}</div>
                        <div style="font-size:10px; color:#90caf9; margin-top:1px;">por partido</div>
                    </div>
                    <div style="background:rgba(0,0,0,0.28); border-radius:12px; padding:8px 6px; text-align:center;">
                        <div style="font-size:11px; color:#bbdefb; text-transform:uppercase; letter-spacing:0.07em;">AST</div>
                        <div style="font-size:22px; color:#ffffff; font-weight:700; margin-top:2px;">{mean_ast:.1f}</div>
                        <div style="font-size:10px; color:#90caf9; margin-top:1px;">por partido</div>
                    </div>
                    <div style="background:rgba(0,0,0,0.28); border-radius:12px; padding:8px 6px; text-align:center;">
                        <div style="font-size:11px; color:#bbdefb; text-transform:uppercase; letter-spacing:0.07em;">3PM</div>
                        <div style="font-size:22px; color:#ffffff; font-weight:700; margin-top:2px;">{mean_3pm:.1f}</div>
                        <div style="font-size:10px; color:#90caf9; margin-top:1px;">triples</div>
                    </div>
                    <div style="background:rgba(0,0,0,0.28); border-radius:12px; padding:8px 6px; text-align:center;">
                        <div style="font-size:11px; color:#bbdefb; text-transform:uppercase; letter-spacing:0.07em;">MIN</div>
                        <div style="font-size:22px; color:#ffffff; font-weight:700; margin-top:2px;">{mean_min:.1f}</div>
                        <div style="font-size:10px; color:#90caf9; margin-top:1px;">minutos</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            st.subheader("Últimos 5 Partidos")
            cols = ['game_date', 'wl', 'matchup', 'min', 'pts', 'reb', 'ast', 'fg3m']
            if 'game_id' in player_data.columns: cols.append('game_id')
            view = player_data[cols].head(5).copy()
            view['min'] = view['min'].astype(int)
            view['RES'] = view['wl'].map({'W': '✅', 'L': '❌'})
            
            if 'game_id' in view.columns:
                view['FICHA'] = view['game_id'].apply(lambda x: f"<a href='https://www.nba.com/game/{x}' target='_blank' class='match-link'>📊</a>" if pd.notnull(x) else "-")
                view = view.drop(columns=['game_id'])
                view = view[['game_date', 'RES', 'matchup', 'FICHA', 'min', 'pts', 'reb', 'ast', 'fg3m']]
            else: view['FICHA'] = "-"
            
            view.columns = ['FECHA', 'RES', 'PARTIDO', 'FICHA', 'MIN', 'PTS', 'REB', 'AST', '3PM']
            view['FECHA'] = view['FECHA'].dt.strftime('%d/%m') 
            
            mostrar_tabla_bonita(view, None, means_dict=means_dict)
            mostrar_leyenda_colores() 
            
            if rival:
                st.subheader(f"Historial vs {rival}")
                h2h = player_data[player_data['matchup'].str.contains(rival, case=False)]
                if not h2h.empty:
                    view_h2h = h2h[cols].copy()
                    view_h2h['min'] = view_h2h['min'].astype(int)
                    view_h2h['RES'] = view_h2h['wl'].map({'W': '✅', 'L': '❌'})
                    if 'game_id' in view_h2h.columns:
                        view_h2h['FICHA'] = view_h2h['game_id'].apply(lambda x: f"<a href='https://www.nba.com/game/{x}' target='_blank' class='match-link'>📊</a>" if pd.notnull(x) else "-")
                        view_h2h = view_h2h.drop(columns=['game_id'])
                        view_h2h = view_h2h[['game_date', 'RES', 'matchup', 'FICHA', 'min', 'pts', 'reb', 'ast', 'fg3m']]
                    view_h2h.columns = ['FECHA', 'RES', 'PARTIDO', 'FICHA', 'MIN', 'PTS', 'REB', 'AST', '3PM']
                    view_h2h['FECHA'] = view_h2h['FECHA'].dt.strftime('%d/%m')
                    mostrar_tabla_bonita(view_h2h, None, means_dict=means_dict)
                    mostrar_leyenda_colores()
                else: st.info(f"No hay registros recientes contra {rival}.")

# --- PÁGINA CUOTAS (CON CACHÉ Y BOTÓN DE ACTUALIZAR) ---
elif st.session_state.page == "💰 Buscador de Cuotas":
    st.header("💰 Buscador de Errores en Cuotas")
    st.caption("Compara Winamax, Bet365, Bwin y otras casas para encontrar errores de valoración.")

    api_key_input = st.text_input("API Key (Oculta):", value=st.session_state.odds_api_key, type="password")
    if api_key_input: st.session_state.odds_api_key = api_key_input

    tipo_mercado = st.selectbox("¿Qué quieres buscar?", ["Ganador Partido (H2H)", "Puntos de Jugador"])
    
    market_key = 'h2h'
    if tipo_mercado == "Puntos de Jugador": market_key = 'player_points'

    # 1. MOSTRAR DATOS CACHÉ SI EXISTEN
    cached_file = load_cache()
    odds_data_to_show = None
    
    if cached_file:
        cache_time = cached_file.get('timestamp', 'Desconocido')
        cache_market = cached_file.get('market', '')
        
        # Solo usamos la caché si coincide con lo que el usuario quiere ver
        if cache_market == market_key:
            st.markdown(f"""
            <div class='odds-info'>
                <div>📅 DATOS GUARDADOS DEL:</div>
                <div class='odds-timestamp'>{cache_time}</div>
                <div style='font-size:12px; margin-top:5px;'>(Tus amigos ven esto sin gastar cuota)</div>
            </div>
            """, unsafe_allow_html=True)
            odds_data_to_show = cached_file.get('data')
        else:
            st.info(f"Hay datos guardados de '{cache_market}', pero tú buscas '{market_key}'. Dale al botón para actualizar.")

    # 2. BOTÓN DE ACTUALIZAR
    if st.button("🔄 Actualizar y Guardar (Gasta Cuota API)"):
        if not st.session_state.odds_api_key:
            st.error("Falta API Key.")
        else:
            with st.spinner(f"Escaneando casas de apuestas ({tipo_mercado})..."):
                odds_data, error = get_sports_odds(st.session_state.odds_api_key, market_key)
                if error: 
                    st.error(error)
                elif not odds_data:
                    st.info("No hay datos disponibles ahora mismo.")
                else:
                    save_cache(odds_data, market_key)
                    odds_data_to_show = odds_data
                    st.rerun()

    # 3. RENDERIZADO DE DATOS (YA SEA DE CACHÉ O DE API)
    if odds_data_to_show:
        if market_key == 'h2h':
            for game in odds_data_to_show:
                home, away = game['home_team'], game['away_team']
                bookmakers = game.get('bookmakers', [])
                if not bookmakers: continue
                
                best_home, best_away = {'p': 0, 'b': ''}, {'p': 0, 'b': ''}
                worst_home, worst_away = {'p': 100, 'b': ''}, {'p': 100, 'b': ''}
                
                all_odds = []
                for bm in bookmakers:
                    markets = bm.get('markets', [])
                    if not markets: continue
                    outcomes = markets[0].get('outcomes', [])
                    o_h = next((x for x in outcomes if x['name'] == home), None)
                    o_a = next((x for x in outcomes if x['name'] == away), None)
                    if o_h and o_a:
                        ph, pa = o_h['price'], o_a['price']
                        all_odds.append({'Casa': bm['title'], f'{home}': ph, f'{away}': pa})
                        if ph > best_home['p']: best_home = {'p': ph, 'b': bm['title']}
                        if ph < worst_home['p']: worst_home = {'p': ph, 'b': bm['title']}
                        if pa > best_away['p']: best_away = {'p': pa, 'b': bm['title']}
                        if pa < worst_away['p']: worst_away = {'p': pa, 'b': bm['title']}
                
                st.markdown(f"#### 🏀 {away} @ {home}")
                c1, c2 = st.columns(2)
                c1.success(f"🏠 {home}: Mejor {best_home['p']} ({best_home['b']})")
                c2.success(f"✈️ {away}: Mejor {best_away['p']} ({best_away['b']})")
                
                if st.checkbox(f"Ver lista completa {home} vs {away}"):
                    st.dataframe(pd.DataFrame(all_odds))
                st.divider()

        elif market_key == 'player_points':
            found = False
            for game in odds_data_to_show:
                bookmakers = game.get('bookmakers', [])
                if not bookmakers: continue
                player_data = {}
                for bm in bookmakers:
                    markets = bm.get('markets', [])
                    for m in markets:
                        if m['key'] == 'player_points':
                            for out in m['outcomes']:
                                p_name = out['description']
                                line = out.get('point')
                                side = out['name']
                                price = out['price']
                                if p_name not in player_data: player_data[p_name] = []
                                player_data[p_name].append({'Casa': bm['title'], 'Linea': line, 'Tipo': side, 'Cuota': price})
                
                if player_data:
                    found = True
                    st.markdown(f"#### 🏀 {game['away_team']} @ {game['home_team']}")
                    for p_name, odds_list in player_data.items():
                        with st.container():
                            st.markdown(f"**👤 {p_name}**")
                            st.dataframe(pd.DataFrame(odds_list))
                    st.divider()
            
            if not found:
                st.warning("No hay datos de jugadores disponibles en este momento. Puede que el mercado esté cerrado.")

# --- PÁGINA ANALIZAR PARTIDO ---
elif st.session_state.page == "⚔️ Analizar Partido":
    
    c_back, c_title, c_dummy = st.columns([1, 10, 1])
    with c_back:
        st.write("") 
        if st.button("⬅️ Volver", key="back_btn_matchup"):
            volver_inicio()
            st.rerun()
    with c_title:
        st.markdown("<h2 style='text-align: center; margin-top: 0; padding-top: 0;'>⚔️ Análisis de Choque</h2>", unsafe_allow_html=True)
    with c_dummy:
        st.write("") 

    if df.empty:
        st.error("Datos no disponibles.")
    else:
        col1, col2 = st.columns(2)
        equipos = sorted(df['team_abbreviation'].unique())
        
        idx_t1 = equipos.index(st.session_state.selected_home) if st.session_state.selected_home in equipos else None
        idx_t2 = equipos.index(st.session_state.selected_visitor) if st.session_state.selected_visitor in equipos else None
        
        t1 = col1.selectbox("Local", equipos, index=idx_t1)
        t2 = col2.selectbox("Visitante", equipos, index=idx_t2)
        
        if t1 and t1 != st.session_state.selected_home: st.session_state.selected_home = t1
        if t2 and t2 != st.session_state.selected_visitor: st.session_state.selected_visitor = t2
        
        if t1 and t2:
            nba_teams = nba_static_teams.get_teams()
            team_map_id = {t['abbreviation']: t['id'] for t in nba_teams}
            roster_t1, roster_t2 = {}, {}
            if t1 in team_map_id: roster_t1 = get_team_roster_numbers(team_map_id[t1])
            if t2 in team_map_id: roster_t2 = get_team_roster_numbers(team_map_id[t2])
            full_roster_map = {**roster_t1, **roster_t2}

            with st.spinner("Cargando..."):
                next_game = get_next_matchup_info(t1, t2)
            if next_game:
                link_btn = f"<a href='https://www.nba.com/game/{next_game['game_id']}' target='_blank' class='next-game-btn'>🏥 Ver Ficha</a>"
                st.markdown(f"""
                <div class='game-card'>
                    <div style='color:#ffbd45; font-size:18px;'>📅 PRÓXIMO ENFRENTAMIENTO</div>
                    <div style='color:white; font-size:16px; margin: 10px 0;'>
                        <b>{next_game['date']}</b> - {next_game['away']} @ {next_game['home']}
                    </div>
                    {link_btn}
                </div>
                """, unsafe_allow_html=True)
            
            mask = ((df['team_abbreviation'] == t1) & (df['matchup'].str.contains(t2))) | \
                   ((df['team_abbreviation'] == t2) & (df['matchup'].str.contains(t1)))
            
            history = df[mask].sort_values('game_date', ascending=False)
            last_dates = sorted(history['game_date'].unique(), reverse=True)[:5]
            
            st.write("---")
            st.subheader("📅 Historial H2H")
            
            games_summary = []
            for date in last_dates:
                day_data = history[history['game_date'] == date]
                if day_data.empty: continue
                row_t1 = day_data[day_data['team_abbreviation'] == t1]
                if not row_t1.empty:
                    wl_t1 = row_t1.iloc[0]['wl']
                    icon1 = '✅' if wl_t1 == 'W' else '❌'
                    icon2 = '❌' if wl_t1 == 'W' else '✅'
                else:
                    row_t2 = day_data[day_data['team_abbreviation'] == t2]
                    if not row_t2.empty:
                        wl_t2 = row_t2.iloc[0]['wl']
                        icon2 = '✅' if wl_t2 == 'W' else '❌'
                        icon1 = '❌' if wl_t2 == 'W' else '✅'
                    else:
                        icon1, icon2 = '', ''
                match_str = f"{t1} {icon1} vs {t2} {icon2}"
                row = day_data.iloc[0]
                g_id = row.get('game_id')
                link = f"<a href='https://www.nba.com/game/{g_id}' target='_blank' class='match-link'>📊</a>" if pd.notnull(g_id) else "-"
                games_summary.append({'FECHA': date.strftime('%d/%m'), 'ENFRENTAMIENTO': match_str, 'FICHA': link})
            
            df_games = pd.DataFrame(games_summary)
            if not df_games.empty: mostrar_tabla_bonita(df_games, None)

            # Estadísticas Equipo H2H
            team_totals = history.groupby(['game_date', 'team_abbreviation'])[['pts', 'reb', 'ast']].sum().reset_index()
            filtered_totals = team_totals[team_totals['team_abbreviation'].isin([t1, t2])].copy()
            if not filtered_totals.empty:
                st.subheader("📊 Comparativa H2H")
                game_stats = []
                unique_game_dates = filtered_totals['game_date'].unique()
                for d in sorted(unique_game_dates, reverse=True):
                    day_data = filtered_totals[filtered_totals['game_date'] == d]
                    if not day_data.empty:
                        row = {'FECHA': pd.to_datetime(d).strftime('%d/%m')}
                        t1_d = day_data[day_data['team_abbreviation'] == t1]
                        row[f'{t1} PTS'] = t1_d['pts'].values[0] if not t1_d.empty else 0
                        row[f'{t1} REB'] = t1_d['reb'].values[0] if not t1_d.empty else 0
                        row[f'{t1} AST'] = t1_d['ast'].values[0] if not t1_d.empty else 0
                        t2_d = day_data[day_data['team_abbreviation'] == t2]
                        row[f'{t2} PTS'] = t2_d['pts'].values[0] if not t2_d.empty else 0
                        row[f'{t2} REB'] = t2_d['reb'].values[0] if not t2_d.empty else 0
                        row[f'{t2} AST'] = t2_d['ast'].values[0] if not t2_d.empty else 0
                        game_stats.append(row)
                if game_stats:
                    df_comparative = pd.DataFrame(game_stats)
                    cols_ordered = ['FECHA', f'{t1} PTS', f'{t2} PTS', f'{t1} REB', f'{t2} REB', f'{t1} AST', f'{t2} AST']
                    final_cols = [c for c in cols_ordered if c in df_comparative.columns]
                    mostrar_tabla_bonita(df_comparative[final_cols], None, simple_mode=True)

            recent_players = history[history['game_date'].isin(last_dates)].sort_values('game_date', ascending=False)
            
            # ==========================================
            # NUEVA LÓGICA DE ALINEACIÓN DE FECHAS
            # ==========================================
            target_dates_str = [d.strftime('%Y-%m-%d') for d in last_dates]
            recent_players['date_str'] = recent_players['game_date'].dt.strftime('%Y-%m-%d')

            def get_aligned_trend(df_source, val_col):
                pivoted = df_source.pivot_table(
                    index=['player_name', 'team_abbreviation'], 
                    columns='date_str', 
                    values=val_col, 
                    aggfunc='sum'
                )
                for d in target_dates_str:
                    if d not in pivoted.columns:
                        pivoted[d] = float('nan')
                pivoted = pivoted[target_dates_str]
                def formatter(row):
                    vals = []
                    for v in row:
                        if pd.isna(v) or v == 0: 
                            vals.append("❌") 
                        else:
                            vals.append(str(int(v)))
                    return "/".join(vals)
                return pivoted.apply(formatter, axis=1)

            base_stats = recent_players.groupby(['player_name', 'team_abbreviation']).agg(
                pts=('pts', 'mean'), 
                reb=('reb', 'mean'), 
                ast=('ast', 'mean'),
                gp=('game_date', 'count')
            )

            trend_pts = get_aligned_trend(recent_players, 'pts').rename('trend_pts')
            trend_reb = get_aligned_trend(recent_players, 'reb').rename('trend_reb')
            trend_ast = get_aligned_trend(recent_players, 'ast').rename('trend_ast')
            trend_min = get_aligned_trend(recent_players, 'min').rename('trend_min')

            stats = base_stats.join([trend_pts, trend_reb, trend_ast, trend_min]).reset_index()
            stats = stats[stats['player_name'].apply(lambda x: latest_teams_map.get(x) in [t1, t2])]
            # ==========================================

            st.write("---")
            st.subheader("🔥 Top Anotadores 👇")
            render_clickable_player_table(stats.sort_values('pts', ascending=False).head(10), 'PTS', full_roster_map)
            
            st.subheader("🔥 Top Reboteadores 👇")
            render_clickable_player_table(stats.sort_values('reb', ascending=False).head(10), 'REB', full_roster_map)
            
            st.subheader("🤝 Top Asistentes 👇")
            render_clickable_player_table(stats.sort_values('ast', ascending=False).head(10), 'AST', full_roster_map)
            
            st.write("---")
            st.subheader("🏥 Historial Bajas")
            avg_mins = recent_players.groupby(['player_name', 'team_abbreviation'])['min'].mean()
            active_key_players = [p for p in avg_mins[avg_mins > 12.0].index.tolist() if latest_teams_map.get(p[0]) in [t1, t2]]
            
            dnp_table_data = []
            for date in last_dates:
                date_str = date.strftime('%d/%m')
                played_on_date = recent_players[recent_players['game_date'] == date]['player_name'].unique()
                missing_t1, missing_t2 = [], []
                for p_name, p_team in active_key_players:
                    current_real_team = latest_teams_map.get(p_name, p_team)
                    if current_real_team != p_team: continue 
                    team_played = not recent_players[(recent_players['game_date'] == date) & (recent_players['team_abbreviation'] == p_team)].empty
                    if team_played and (p_name not in played_on_date):
                        if p_team == t1: missing_t1.append(p_name)
                        elif p_team == t2: missing_t2.append(p_name)
                cell_t1 = f"<span class='dnp-missing'>{', '.join(missing_t1)}</span>" if missing_t1 else "<span class='dnp-full'>OK</span>"
                cell_t2 = f"<span class='dnp-missing'>{', '.join(missing_t2)}</span>" if missing_t2 else "<span class='dnp-full'>OK</span>"
                dnp_table_data.append({'FECHA': date_str, f'BAJAS {t1}': cell_t1, f'BAJAS {t2}': cell_t2})
            if dnp_table_data:
                df_dnp = pd.DataFrame(dnp_table_data)
                mostrar_tabla_bonita(df_dnp, None)
            else: st.success("✅ Sin bajas importantes.")
            
            st.write("---")
            st.subheader("🕵️ Patrones")
            global_means = df.groupby('player_name')[['pts', 'reb', 'ast']].mean()
            star_scorers = global_means[global_means['pts'] > 18].index.tolist()
            star_rebounders = global_means[global_means['reb'] > 7].index.tolist()
            star_assisters = global_means[global_means['ast'] > 5].index.tolist()
            all_stars = list(set(star_scorers + star_rebounders + star_assisters))
            patterns_data = []

            for date in last_dates:
                roster_day = recent_players[recent_players['game_date'] == date]
                players_present = roster_day['player_name'].unique()
                teams_active = roster_day['team_abbreviation'].unique()
                for team in teams_active:
                    missing_stars_today = []
                    for star in all_stars:
                        current_real_team = latest_teams_map.get(star, None)
                        if current_real_team == team and (star not in players_present): missing_stars_today.append(star)
                    if missing_stars_today:
                        teammates = roster_day[roster_day['team_abbreviation'] == team]
                        beneficiaries = []
                        for _, row in teammates.iterrows():
                            p_name = row['player_name']
                            if latest_teams_map.get(p_name) != team: continue
                            if p_name in global_means.index: avg_p = global_means.loc[p_name]
                            else: continue 
                            diff_pts = row['pts'] - avg_p['pts']
                            diff_reb = row['reb'] - avg_p['reb']
                            diff_ast = row['ast'] - avg_p['ast']
                            impact_msgs = []
                            if any(s in star_scorers for s in missing_stars_today):
                                if row['pts'] >= 15 and diff_pts >= 8: impact_msgs.append(f"🏀+{int(diff_pts)}")
                            if any(s in star_rebounders for s in missing_stars_today):
                                if row['reb'] >= 7 and diff_reb >= 4: impact_msgs.append(f"🖐+{int(diff_reb)}")
                            if any(s in star_assisters for s in missing_stars_today):
                                if row['ast'] >= 5 and diff_ast >= 4: impact_msgs.append(f"🎁+{int(diff_ast)}")
                            if impact_msgs: beneficiaries.append(f"<b>{p_name}</b> ({', '.join(impact_msgs)})")
                        if beneficiaries:
                            date_str = date.strftime('%d/%m')
                            missing_str = ", ".join(missing_stars_today)
                            impact_str = "<br>".join(beneficiaries)
                            patterns_data.append({'FECHA': date_str, 'EQUIPO': team, 'FALTA': f"<span class='pat-stars'>{missing_str}</span>", 'IMPACTO': f"<span class='pat-impact'>{impact_str}</span>"})
            if patterns_data:
                df_patterns = pd.DataFrame(patterns_data)
                mostrar_tabla_bonita(df_patterns, None)
            else: st.write("Sin impactos.")

            st.write("---")
            st.subheader("🎲 Parlay Generator")
            min_games_needed = max(3, int(len(last_dates) * 0.6))
            candidates = stats[stats['gp'] >= min_games_needed].copy()
            
            safe_legs_pts, safe_legs_reb, safe_legs_ast = [], [], []
            risky_legs_pts, risky_legs_reb, risky_legs_ast = [], [], []

            for _, row in candidates.iterrows():
                p_name, p_team = row['player_name'], row['team_abbreviation']
                logs = recent_players[(recent_players['player_name'] == p_name) & (recent_players['team_abbreviation'] == p_team)]
                if logs.empty: continue
                pts_vals = sorted(logs['pts'].tolist())
                reb_vals = sorted(logs['reb'].tolist())
                ast_vals = sorted(logs['ast'].tolist())
                
                smart_min_pts = pts_vals[1] if len(pts_vals) >= 4 else pts_vals[0]
                smart_min_reb = reb_vals[1] if len(reb_vals) >= 4 else reb_vals[0]
                smart_min_ast = ast_vals[1] if len(ast_vals) >= 4 else ast_vals[0]
                avg_pts, avg_reb, avg_ast = row['pts'], row['reb'], row['ast']

                if smart_min_pts >= 12: safe_legs_pts.append({'player': p_name, 'val': int(smart_min_pts), 'score': avg_pts, 'desc': f"Suelo"})
                if smart_min_reb >= 6: safe_legs_reb.append({'player': p_name, 'val': int(smart_min_reb), 'score': avg_reb, 'desc': f"Suelo"})
                if smart_min_ast >= 4: safe_legs_ast.append({'player': p_name, 'val': int(smart_min_ast), 'score': avg_ast, 'desc': f"Suelo"})

                if avg_pts >= 15 and avg_pts > (smart_min_pts + 1.0): risky_legs_pts.append({'player': p_name, 'val': int(avg_pts), 'score': avg_pts, 'desc': f"Media"})
                if avg_reb >= 8 and avg_reb > (smart_min_reb + 1.0): risky_legs_reb.append({'player': p_name, 'val': int(avg_reb), 'score': avg_reb, 'desc': f"Media"})
                if avg_ast >= 6 and avg_ast > (smart_min_ast + 1.0): risky_legs_ast.append({'player': p_name, 'val': int(avg_ast), 'score': avg_ast, 'desc': f"Media"})

            for l in [safe_legs_pts, safe_legs_reb, safe_legs_ast, risky_legs_pts, risky_legs_reb, risky_legs_ast]: l.sort(key=lambda x: x['score'], reverse=True)

            def render_ticket(title, legs, icon, color_border, css_class):
                final_legs = legs[:5] 
                if not final_legs: return f"<div class='{css_class}' style='border:1px solid {color_border};'><div class='parlay-header' style='color:white;'>{title}</div><div style='color:#ccc; text-align:center;'>---</div></div>"
                html_legs = ""
                for leg in final_legs:
                    html_legs += f"<div class='parlay-leg' style='border-left: 5px solid {color_border};'><div class='leg-player'>{icon} {leg['player']}</div><div class='leg-info'><div class='leg-val'>+{leg['val']}</div><div class='leg-stat'>{leg['desc']}</div></div></div>"
                return f"<div class='{css_class}' style='border:1px solid {color_border};'><div class='parlay-header' style='color:white;'>{title}</div>{html_legs}</div>"

            col_safe, col_risky = st.columns(2)
            with col_safe:
                st.markdown("### 🛡️ CONSERVADOR")
                st.markdown(render_ticket("PTS", safe_legs_pts, "🏀", "#4caf50", "parlay-box"), unsafe_allow_html=True)
                if safe_legs_reb: st.markdown(render_ticket("REB", safe_legs_reb, "🖐", "#4caf50", "parlay-box"), unsafe_allow_html=True)
                if safe_legs_ast: st.markdown(render_ticket("AST", safe_legs_ast, "🎁", "#4caf50", "parlay-box"), unsafe_allow_html=True)
            with col_risky:
                st.markdown("### 🚀 ARRIESGADO")
                st.markdown(render_ticket("PTS", risky_legs_pts, "🏀", "#ff5252", "parlay-box"), unsafe_allow_html=True)
                if risky_legs_reb: st.markdown(render_ticket("REB", risky_legs_reb, "🖐", "#ff5252", "parlay-box"), unsafe_allow_html=True)
                if risky_legs_ast: st.markdown(render_ticket("AST", risky_legs_ast, "🎁", "#ff5252", "parlay-box"), unsafe_allow_html=True)

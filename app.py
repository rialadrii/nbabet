import streamlit as st
import pandas as pd
import sqlite3
import os
import time
import requests
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
# 2. CSS DEFINITIVO
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Teko:wght@300..700&display=swap');

/* --- CENTRADO GLOBAL --- */
.main .block-container {
    max-width: 1300px !important;
    padding-left: 0.5rem !important;
    padding-right: 0.5rem !important;
    margin: 0 auto !important;
    display: flex;
    flex-direction: column;
    align-items: center;
}

/* Forzar alineación de textos */
h1, h2, h3, h4, p, span, label, div.stMarkdown {
    text-align: center !important;
    width: 100% !important;
}

/* --- FIX TABLAS INTERACTIVAS --- */
[data-testid="stDataFrame"] {
    width: 100% !important;
    max-width: 100% !important;
    margin: 0 auto !important;
}

/* --- FIX TABLAS HTML --- */
.table-responsive {
    display: flex !important;
    justify-content: center !important;
    width: 100% !important;
    overflow-x: auto;
    -webkit-overflow-scrolling: touch;
    margin-bottom: 1rem;
}

table.custom-table {
    margin-left: auto !important;
    margin-right: auto !important;
    border-collapse: collapse;
    font-size: 14px;
    min-width: 350px; 
    width: 100%;
}

table.custom-table th {
    background-color: #31333F;
    color: white;
    text-align: center !important;
    padding: 8px;
    border-bottom: 2px solid #555;
    white-space: nowrap;
    font-size: 13px;
}

table.custom-table td {
    text-align: center !important;
    padding: 6px;
    border-bottom: 1px solid #444;
    color: white;
    font-size: 13px;
}

/* --- ESTILOS VISUALES --- */
h1 {
    font-family: 'Teko', sans-serif !important;
    font-size: 55px !important;
    text-transform: uppercase;
    color: white;
    line-height: 1;
    margin-bottom: 20px;
}
h3 {
    font-family: 'Teko', sans-serif !important;
    font-size: 28px !important;
    text-transform: uppercase;
    color: #ffbd45;
    margin-top: 30px;
}

.game-card {
    background-color: #2d2d2d;
    border: 1px solid #444;
    border-radius: 8px;
    padding: 15px;
    margin-bottom: 15px;
    width: 100%;
    text-align: center;
}
.game-matchup { display: flex; justify-content: center; align-items: center; gap: 10px; margin-bottom: 5px; }
.team-logo { width: 45px; height: 45px; object-fit: contain; }
.game-time { color: #ffbd45; font-size: 22px; font-family: 'Teko', sans-serif; }

div.stButton > button {
    width: 100%;
    border-radius: 8px !important;
    font-weight: bold;
    background-color: #1e1e1e;
    color: #fff;
    border: 1px solid #444;
    transition: all 0.2s;
}
div.stButton > button:hover { border-color: #ffbd45; color: #ffbd45; }

.parlay-box { background-color: #1e1e1e; border: 1px solid #444; border-radius: 10px; padding: 10px; margin-bottom: 15px; }
.parlay-header { font-size: 18px; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #444; padding-bottom: 5px; text-align: center !important; color:white; }
.parlay-leg { background-color: #2d2d2d; margin: 5px 0; padding: 8px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; color: white; }

.dnp-missing { color: #ff5252; font-weight:bold; }
.dnp-full { color: #4caf50; font-weight:bold; }
.pat-stars { color: #ff5252; font-weight: bold; }
.pat-impact { color: #4caf50; }

[data-testid="stElementToolbar"] { display: none !important; }
footer { display: none !important; }
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. GESTIÓN DE ESTADO
# ==========================================
if 'page' not in st.session_state: st.session_state.page = "🏠 Inicio"
if 'selected_home' not in st.session_state: st.session_state.selected_home = None
if 'selected_visitor' not in st.session_state: st.session_state.selected_visitor = None
if 'selected_player' not in st.session_state: st.session_state.selected_player = None

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
        cols_needed = ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'GAME_DATE', 'MATCHUP', 'PTS', 'REB', 'AST', 'MIN', 'WL', 'GAME_ID']
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
    basket_today = get_basketball_date()
    fechas = [basket_today, basket_today + timedelta(days=1)]
    agenda = {}
    for i, fecha in enumerate(fechas):
        fecha_str = fecha.strftime('%Y-%m-%d')
        label = "HOY" if i == 0 else "MAÑANA"
        agenda[label] = []
        try:
            board = scoreboardv2.ScoreboardV2(game_date=fecha_str)
            games = board.game_header.get_data_frame()
            if not games.empty:
                for _, game in games.iterrows():
                    h_id, v_id = game['HOME_TEAM_ID'], game['VISITOR_TEAM_ID']
                    agenda[label].append({
                        'game_id': game['GAME_ID'],
                        'v_abv': team_map.get(v_id), 'h_abv': team_map.get(h_id),
                        'v_logo': f"https://cdn.nba.com/logos/nba/{v_id}/global/L/logo.svg",
                        'h_logo': f"https://cdn.nba.com/logos/nba/{h_id}/global/L/logo.svg",
                        'time': convertir_hora_espanol(game['GAME_STATUS_TEXT'])
                    })
        except: pass
    return agenda

# ==========================================
# 5. FUNCIONES UI (RENDERIZADO)
# ==========================================
def apply_custom_color(column, avg, col_name):
    styles = []
    tolerance = 2 if col_name in ['REB', 'AST'] else 5
    for val in column:
        text_color = "white"
        if val > avg: color = '#2962ff'
        elif val == avg: color = '#00c853'
        elif val >= (avg - tolerance): 
            color = '#fff176'
            text_color = "black"
        else: color = '#d32f2f'
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
    if simple_mode:
        html = df_raw.style\
            .format("{:.0f}", subset=[c for c in df_raw.columns if 'PTS' in c or 'REB' in c or 'AST' in c])\
            .hide(axis="index")\
            .to_html(classes="custom-table", escape=False)
    else:
        styler = df_raw.style.format("{:.1f}", subset=[c for c in df_raw.columns if c in ['PTS', 'REB', 'AST', 'MIN'] or '_PTS' in c or '_REB' in c or '_AST' in c])
        if means_dict:
            for c in ['PTS', 'REB', 'AST', 'MIN']:
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

    df_stats['NUM'] = df_stats['player_name'].map(jersey_map).fillna('-')
    df_stats['JUGADOR'] = df_stats['player_name'] + ' (' + df_stats['team_abbreviation'] + ')'

    # Solo mostramos columnas críticas
    # trend_{stat_col} ya viene alineado con guiones si se usa la nueva lógica
    df_interactive = df_stats[['JUGADOR', 'player_name', stat_col.lower(), f'trend_{stat_col.lower()}', 'trend_min']].copy()
    df_interactive.columns = ['JUGADOR', 'player_name_hidden', stat_col, 'RACHA', 'MIN']
    
    selection = st.dataframe(
        df_interactive,
        use_container_width=True,
        hide_index=True,
        on_select="rerun", 
        selection_mode="single-row",
        column_config={
            "JUGADOR": st.column_config.TextColumn("JUGADOR", width=None),
            "player_name_hidden": None,
            # AJUSTE DE ANCHOS PARA QUE QUEPA TODO
            stat_col: st.column_config.NumberColumn(stat_col, format="%.1f", width=50),
            "RACHA": st.column_config.TextColumn("RACHA (Últ. Partidos)", width=150), 
            "MIN": st.column_config.TextColumn("MIN", width=90)
        }
    )
    
    if len(selection.selection.rows) > 0:
        row_idx = selection.selection.rows[0]
        player_name = df_interactive.iloc[row_idx]['player_name_hidden']
        navegar_a_jugador(player_name)
        st.rerun()

# ==========================================
# 6. APP PRINCIPAL
# ==========================================
st.markdown("<h1>🏀 NBA PRO ANALYZER 🏀</h1>", unsafe_allow_html=True)

pages = ["🏠 Inicio", "👤 Jugador", "⚔️ Analizar Partido", "🔄 Actualizar Datos"]
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
    c1, c2 = st.columns(2)
    
    def render_block(col, title, games, color):
        with col:
            st.markdown(f"<h3 style='color:{color}; text-align: center;'>{title}</h3>", unsafe_allow_html=True)
            if not games: st.caption("No hay partidos.")
            for g in games:
                st.markdown(f"""
                <div class='game-card'>
                    <div class='game-matchup'>
                        <img src='{g['v_logo']}' class='team-logo'> <span class='vs-text'>@</span> <img src='{g['h_logo']}' class='team-logo'>
                    </div>
                    <div style='color:white; font-weight:bold;'>{g['v_abv']} vs {g['h_abv']}</div>
                    <div class='game-time'>{g['time']}</div>
                </div>
                """, unsafe_allow_html=True)
                if st.button(f"🔍 ANALIZAR {g['v_abv']} vs {g['h_abv']}", key=f"btn_{g['game_id']}"):
                    navegar_a_partido(g['h_abv'], g['v_abv'])
                    st.rerun()
                st.write("")

    render_block(c1, "HOY", agenda.get("HOY", []), "#4caf50")
    render_block(c2, "MAÑANA", agenda.get("MAÑANA", []), "#2196f3")
    st.markdown("<div class='credits'>Creado por ad.ri.</div>", unsafe_allow_html=True)

# --- PÁGINA ACTUALIZAR ---
elif st.session_state.page == "🔄 Actualizar Datos":
    st.write("### 🔄 Sincronización")
    if st.button("Descargar y Actualizar Ahora"):
        with st.spinner("Conectando con servidores NBA..."):
            success = download_data()
            if success:
                st.success("¡Datos actualizados!")
                st.rerun()

# --- PÁGINA JUGADOR ---
elif st.session_state.page == "👤 Jugador":
    c_back, c_title = st.columns([1, 6])
    with c_back:
        if st.session_state.selected_home and st.session_state.selected_visitor:
            if st.button(f"⬅️ Volver"):
                volver_a_partido()
                st.rerun()
    with c_title:
        st.header("👤 Buscador de Jugadores")

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
            mean_min = player_data['min'].mean()
            means_dict = {'PTS': mean_pts, 'REB': mean_reb, 'AST': mean_ast, 'MIN': mean_min}

            c1, c2, c3, c4 = st.columns(4)
            c1.metric("PTS", f"{mean_pts:.1f}")
            c2.metric("REB", f"{mean_reb:.1f}")
            c3.metric("AST", f"{mean_ast:.1f}")
            c4.metric("MIN", f"{mean_min:.1f}")
            
            st.subheader("Últimos 5 Partidos")
            cols = ['game_date', 'wl', 'matchup', 'min', 'pts', 'reb', 'ast']
            if 'game_id' in player_data.columns: cols.append('game_id')
            view = player_data[cols].head(5).copy()
            view['min'] = view['min'].astype(int)
            view['RES'] = view['wl'].map({'W': '✅', 'L': '❌'})
            
            if 'game_id' in view.columns:
                view['FICHA'] = view['game_id'].apply(lambda x: f"<a href='https://www.nba.com/game/{x}' target='_blank' class='match-link'>📊</a>" if pd.notnull(x) else "-")
                view = view.drop(columns=['game_id'])
                view = view[['game_date', 'RES', 'matchup', 'FICHA', 'min', 'pts', 'reb', 'ast']]
            else: view['FICHA'] = "-"
                
            view.columns = ['FECHA', 'RES', 'PARTIDO', 'FICHA', 'MIN', 'PTS', 'REB', 'AST']
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
                        view_h2h = view_h2h[['game_date', 'RES', 'matchup', 'FICHA', 'min', 'pts', 'reb', 'ast']]
                    view_h2h.columns = ['FECHA', 'RES', 'PARTIDO', 'FICHA', 'MIN', 'PTS', 'REB', 'AST']
                    view_h2h['FECHA'] = view_h2h['FECHA'].dt.strftime('%d/%m')
                    mostrar_tabla_bonita(view_h2h, None, means_dict=means_dict)
                    mostrar_leyenda_colores()
                else: st.info(f"No hay registros recientes contra {rival}.")

# --- PÁGINA ANALIZAR PARTIDO (CÓDIGO COMPLETO) ---
elif st.session_state.page == "⚔️ Analizar Partido":
    
    # CAMBIO AQUÍ: Usamos 3 columnas [1, 10, 1] para que el título quede en el centro real
    c_back, c_title, c_dummy = st.columns([1, 10, 1])
    
    with c_back:
        # Añadimos un poco de margen superior (padding-top) si el botón se ve muy arriba respecto al texto
        st.write("") 
        if st.button("⬅️ Volver", key="back_btn_matchup"):
            volver_inicio()
            st.rerun()
            
    with c_title:
        # Usamos markdown directo para asegurar el alineado y quitar márgenes extraños
        st.markdown("<h2 style='text-align: center; margin-top: 0; padding-top: 0;'>⚔️ Análisis de Choque</h2>", unsafe_allow_html=True)
        
    with c_dummy:
        st.write("") # Esta columna vacía equilibra el layout

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
                            vals.append("❌") # <--- CAMBIO AQUÍ
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


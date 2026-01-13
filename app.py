import streamlit as st
import pandas as pd
import sqlite3
import os
import time
from datetime import datetime, timedelta
from nba_api.stats.endpoints import leaguegamelog, scoreboardv2
from nba_api.stats.static import teams as nba_static_teams

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA (VISUAL)
# ==========================================
st.set_page_config(page_title="NBA Analyzer Pro", page_icon="🏀", layout="wide")

# --- CSS: FUENTES + MODO OSCURO + ESTILOS ---
st.markdown("""
    <style>
    /* IMPORTAR FUENTE DEPORTIVA (TEKO) */
    @import url('https://fonts.googleapis.com/css2?family=Teko:wght@300..700&display=swap');

    /* Estilo del Título Principal */
    h1 {
        font-family: 'Teko', sans-serif !important;
        font-size: 60px !important;
        text-transform: uppercase;
        letter-spacing: 2px;
        text-shadow: 2px 2px 4px #000000;
        text-align: center;
        margin-bottom: 10px;
    }

    /* Estilo para las tarjetas de métricas */
    div[data-testid="stMetric"] {
        background-color: #262730;
        border: 1px solid #464b5f;
        padding: 10px;
        border-radius: 10px;
        color: white;
    }
    
    h2, h3 { text-align: center; }
    
    /* ESTILOS TABLA HTML */
    table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
        color: white; 
        font-family: sans-serif;
    }
    th {
        background-color: #31333F;
        color: white;
        font-weight: bold;
        text-align: center !important; 
        padding: 10px;
        border-bottom: 2px solid #464b5f;
        text-transform: uppercase;
    }
    td {
        text-align: center !important; 
        padding: 8px;
        border-bottom: 1px solid #464b5f;
        font-size: 14px;
        vertical-align: middle;
    }
    div.table-wrapper {
        overflow-x: auto;
    }
    
    /* Estilos específicos para STATUS */
    .status-played { color: #4caf50; font-weight: bold; font-size: 16px; }
    .status-missed { color: #ff5252; font-weight: bold; font-size: 16px; }
    .status-date { font-size: 10px; color: #aaaaaa; display: block; }
    .status-cell { display: inline-block; margin: 0 4px; text-align: center; }

    /* Estilos para la tabla de BAJAS */
    .dnp-full { color: #4caf50; font-weight: bold; }
    .dnp-missing { color: #ff5252; }
    
    /* Estilos para Patrones */
    .pat-stars { color: #ffbd45; font-weight: bold; }
    .pat-impact { color: #4caf50; font-weight: bold; }

    /* ESTILO TICKET PARLAY */
    .parlay-box {
        background-color: #1e1e1e;
        border: 1px solid #444;
        border-radius: 15px;
        padding: 15px;
        margin-bottom: 20px;
        text-align: center;
    }
    .parlay-header {
        font-size: 20px;
        font-weight: bold;
        margin-bottom: 15px;
        text-transform: uppercase;
        letter-spacing: 1px;
        border-bottom: 1px solid #444;
        padding-bottom: 10px;
    }
    .parlay-leg {
        background-color: #2d2d2d;
        margin: 10px 0;
        padding: 10px;
        border-radius: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.3);
    }
    .leg-player { font-weight: bold; color: white; font-size: 14px; text-align: left; }
    .leg-val { font-weight: bold; font-size: 18px; text-align: right; }
    .leg-stat { color: #aaaaaa; font-size: 11px; display: block; margin-top: 4px; text-align: right; }
    
    /* Créditos Footer */
    .credits {
        font-family: 'Teko', sans-serif;
        font-size: 20px;
        color: #888;
        text-align: center;
        margin-top: 20px;
        letter-spacing: 1px;
    }

    /* CALENDARIO CARDS MEJORADO */
    .game-card {
        background-color: #2d2d2d;
        border: 1px solid #444;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        text-align: center;
        transition: transform 0.2s;
    }
    .game-card:hover {
        transform: scale(1.02);
        border-color: #666;
    }
    .game-matchup {
        display: flex;
        justify-content: center;
        align-items: center;
        gap: 15px;
        margin-bottom: 10px;
    }
    .team-logo {
        width: 45px;
        height: 45px;
        object-fit: contain;
    }
    .vs-text {
        font-weight: bold;
        font-size: 14px;
        color: #888;
    }
    .game-time { 
        color: #ffbd45; 
        font-size: 18px; 
        font-weight: bold; 
        font-family: 'Teko', sans-serif;
        letter-spacing: 1px;
    }
    .game-status { color: #aaa; font-size: 12px; }
    .injuries-link {
        font-size: 12px;
        color: #4caf50;
        text-decoration: none;
        border: 1px solid #4caf50;
        padding: 4px 8px;
        border-radius: 4px;
        margin-top: 8px;
        display: inline-block;
    }
    .injuries-link:hover {
        background-color: #4caf50;
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# LÓGICA DE BASE DE DATOS Y DESCARGA
# ==========================================
DB_PATH = "nba.sqlite"
CSV_FOLDER = "csv"

if not os.path.exists(CSV_FOLDER):
    os.makedirs(CSV_FOLDER)

def download_data():
    progress_text = "Descargando datos de la NBA (2024-2026)... Por favor espera."
    my_bar = st.progress(0, text=progress_text)
    
    target_seasons = ['2024-25', '2025-26']
    all_seasons_data = []

    for i, season in enumerate(target_seasons):
        try:
            gamelogs = leaguegamelog.LeagueGameLog(season=season, player_or_team_abbreviation='P')
            df = gamelogs.get_data_frames()[0]
            if not df.empty:
                all_seasons_data.append(df)
            my_bar.progress((i + 1) * 50, text=f"Temporada {season} descargada...")
            time.sleep(1)
        except Exception as e:
            st.error(f"Error descargando {season}: {e}")

    if all_seasons_data:
        full_df = pd.concat(all_seasons_data, ignore_index=True)
        cols_needed = ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'GAME_DATE', 'MATCHUP', 'PTS', 'REB', 'AST', 'MIN', 'WL']
        cols_final = [c for c in cols_needed if c in full_df.columns]
        df_clean = full_df[cols_final].copy()
        df_clean.columns = df_clean.columns.str.lower()
        
        df_clean.to_csv(f'{CSV_FOLDER}/player_stats.csv', index=False)
        conn = sqlite3.connect(DB_PATH)
        df_clean.to_sql('player', conn, if_exists='replace', index=False)
        conn.close()
        
        my_bar.progress(100, text="¡Datos actualizados correctamente!")
        time.sleep(1)
        my_bar.empty()
        return True
    return False

def load_data():
    csv_path = f"{CSV_FOLDER}/player_stats.csv"
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        if 'game_date' in df.columns:
            df['game_date'] = pd.to_datetime(df['game_date'])
        if 'min' in df.columns:
            df['min'] = pd.to_numeric(df['min'], errors='coerce')
        return df
    return pd.DataFrame()

# --- FUNCIONES DE CALENDARIO Y HORA ---

def convertir_hora_espanol(hora_et):
    """Convierte '7:00 pm ET' a formato 24h España (+6h aprox)"""
    if "Final" in hora_et:
        return "Finalizado"
    if "pm" not in hora_et.lower() and "am" not in hora_et.lower():
        return hora_et # Por si devuelve otro estado
        
    try:
        # Limpiar string
        hora_clean = hora_et.replace(" ET", "").strip()
        # Parsear hora
        dt = datetime.strptime(hora_clean, "%I:%M %p")
        # Sumar 6 horas (Aprox ET a CET)
        dt_spain = dt + timedelta(hours=6)
        return dt_spain.strftime("%H:%M")
    except:
        return hora_et

def obtener_partidos_hoy_manana():
    nba_teams = nba_static_teams.get_teams()
    team_map = {t['id']: t['abbreviation'] for t in nba_teams}
    
    fechas = [datetime.now(), datetime.now() + timedelta(days=1)]
    agenda = {}
    
    for fecha in fechas:
        fecha_str = fecha.strftime('%Y-%m-%d')
        # Determinar etiqueta
        is_today = fecha.date() == datetime.now().date()
        label = "JORNADA DE HOY" if is_today else "JORNADA DE MAÑANA"
        agenda[label] = []
        
        try:
            board = scoreboardv2.ScoreboardV2(game_date=fecha_str)
            games = board.game_header.get_data_frame()
            
            if not games.empty:
                for _, game in games.iterrows():
                    home_id = game['HOME_TEAM_ID']
                    visitor_id = game['VISITOR_TEAM_ID']
                    home_abv = team_map.get(home_id, "N/A")
                    vis_abv = team_map.get(visitor_id, "N/A")
                    status_raw = game['GAME_STATUS_TEXT'] 
                    
                    # Convertir hora
                    hora_esp = convertir_hora_espanol(status_raw)
                    
                    # URLs de logos
                    logo_home = f"https://cdn.nba.com/logos/nba/{home_id}/global/L/logo.svg"
                    logo_vis = f"https://cdn.nba.com/logos/nba/{visitor_id}/global/L/logo.svg"
                    
                    # Link a reporte de bajas (Rotowire es fiable)
                    injury_url = f"https://www.rotowire.com/basketball/nba-lineups.php" 

                    agenda[label].append({
                        'h_abv': home_abv,
                        'v_abv': vis_abv,
                        'h_logo': logo_home,
                        'v_logo': logo_vis,
                        'time': hora_esp,
                        'raw_status': status_raw,
                        'injury_link': injury_url
                    })
        except:
            pass
            
    return agenda

# ==========================================
# INTERFAZ PRINCIPAL
# ==========================================

st.markdown("<h1>🏀 NBA Pro Analyzer 🏀</h1>", unsafe_allow_html=True)

st.sidebar.header("Menú de Control")
opcion = st.sidebar.radio("Selecciona modo:", ["🏠 Inicio", "👤 Analizar Jugador", "⚔️ Analizar Partido", "🔄 Actualizar Datos"])

df = load_data()

latest_teams_map = {}
if not df.empty:
    latest_entries = df.sort_values('game_date').drop_duplicates('player_name', keep='last')
    latest_teams_map = dict(zip(latest_entries['player_name'], latest_entries['team_abbreviation']))

# --- FUNCION PARA MOSTRAR TABLA LIMPIA ---
def mostrar_tabla_bonita(df_raw, col_principal_espanol):
    cols_fmt = [c for c in df_raw.columns if c in ['PTS', 'REB', 'AST']] 
    
    html = df_raw.style\
        .format("{:.1f}", subset=cols_fmt)\
        .background_gradient(subset=[col_principal_espanol] if col_principal_espanol else None, cmap='YlOrBr' if col_principal_espanol=='REB' else ('Greens' if col_principal_espanol=='PTS' else ('Blues' if col_principal_espanol=='AST' else None)))\
        .hide(axis="index")\
        .to_html(classes="custom-table")
    
    st.markdown(f"<div class='table-wrapper'>{html}</div>", unsafe_allow_html=True)
    
    # --- CALENDARIO DE PARTIDOS ---
    st.write("---")
    
    with st.spinner("Cargando agenda de la NBA..."):
        agenda = obtener_partidos_hoy_manana()
    
    col_hoy, col_manana = st.columns(2)
    
    def render_calendar_col(col, title, games, color_title):
        with col:
            st.markdown(f"<h3 style='color:{color_title};'>{title}</h3>", unsafe_allow_html=True)
            if games:
                for game in games:
                    st.markdown(f"""
                    <div class='game-card'>
                        <div class='game-matchup'>
                            <img src='{game['v_logo']}' class='team-logo'>
                            <span class='vs-text'>@</span>
                            <img src='{game['h_logo']}' class='team-logo'>
                        </div>
                        <div class='game-teams'>{game['v_abv']} vs {game['h_abv']}</div>
                        <div class='game-time'>{game['time']}</div>
                        <a href='{game['injury_link']}' target='_blank' class='injuries-link'>🏥 Ver Bajas / Lineups</a>
                    </div>
                    """, unsafe_allow_html=True)
            else:
                st.caption("No hay partidos programados.")

    render_calendar_col(col_hoy, "JORNADA DE HOY (Madrugada)", agenda.get("JORNADA DE HOY", []), "#4caf50")
    render_calendar_col(col_manana, "JORNADA DE MAÑANA", agenda.get("JORNADA DE MAÑANA", []), "#2196f3")
            
    st.write("---")
    
    if df.empty:
        st.warning("⚠️ No hay datos históricos. Ve a 'Actualizar Datos' primero.")
    else:
        st.write(f"Base de Datos Histórica: **{len(df)}** registros cargados.")
        st.write("Última actualización de datos: ", df['game_date'].max().strftime('%d/%m/%Y') if not df.empty else "N/A")
    
    st.markdown("---")
    st.markdown("<div class='credits'>👨‍💻 Creado por ad.ri.</div>", unsafe_allow_html=True)

elif opcion == "🔄 Actualizar Datos":
    st.write("### 🔄 Sincronización con NBA API")
    st.write("Pulsa el botón para bajar las estadísticas más recientes.")
    if st.button("Descargar y Actualizar Ahora"):
        with st.spinner("Conectando con servidores NBA..."):
            success = download_data()
            if success:
                st.success("¡Base de datos regenerada! Ya puedes analizar.")
                st.rerun()

elif opcion == "👤 Analizar Jugador":
    st.header("👤 Buscador de Jugadores")
    if df.empty:
        st.error("Primero actualiza los datos.")
    else:
        todos_jugadores = sorted(df['player_name'].unique())
        todos_equipos = sorted(df['team_abbreviation'].unique())

        jugador = st.selectbox("Escribe el nombre del Jugador:", todos_jugadores, index=None, placeholder="Ej: Kevin Love")
        
        if jugador:
            player_data = df[df['player_name'] == jugador].sort_values('game_date', ascending=False)
            
            rival = st.selectbox("Filtrar vs Rival (Opcional):", todos_equipos, index=None, placeholder="Selecciona equipo rival...")
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("PTS", f"{player_data['pts'].mean():.1f}")
            c2.metric("REB", f"{player_data['reb'].mean():.1f}")
            c3.metric("AST", f"{player_data['ast'].mean():.1f}")
            c4.metric("MIN", f"{player_data['min'].mean():.1f}")
            
            st.subheader("Últimos 5 Partidos")
            
            view = player_data[['game_date', 'matchup', 'min', 'pts', 'reb', 'ast']].head(5).copy()
            view['min'] = view['min'].astype(int)
            view.columns = ['FECHA', 'PARTIDO', 'MIN', 'PTS', 'REB', 'AST']
            view['FECHA'] = view['FECHA'].dt.strftime('%d/%m/%Y') 
            mostrar_tabla_bonita(view, None)
            
            if rival:
                st.subheader(f"Historial vs {rival}")
                h2h = player_data[player_data['matchup'].str.contains(rival, case=False)]
                if not h2h.empty:
                    view_h2h = h2h[['game_date', 'matchup', 'min', 'pts', 'reb', 'ast']].copy()
                    view_h2h['min'] = view_h2h['min'].astype(int)
                    view_h2h.columns = ['FECHA', 'PARTIDO', 'MIN', 'PTS', 'REB', 'AST']
                    view_h2h['FECHA'] = view_h2h['FECHA'].dt.strftime('%d/%m/%Y')
                    mostrar_tabla_bonita(view_h2h, None)
                else:
                    st.info(f"No hay registros recientes de {jugador} contra {rival}.")

elif opcion == "⚔️ Analizar Partido":
    st.header("⚔️ Análisis de Choque")
    if df.empty:
        st.error("Datos no disponibles.")
    else:
        col1, col2 = st.columns(2)
        equipos = sorted(df['team_abbreviation'].unique())
        t1 = col1.selectbox("Equipo Local", equipos, index=None)
        t2 = col2.selectbox("Equipo Visitante", equipos, index=None)
        
        if t1 and t2:
            mask = ((df['team_abbreviation'] == t1) & (df['matchup'].str.contains(t2))) | \
                   ((df['team_abbreviation'] == t2) & (df['matchup'].str.contains(t1)))
            
            history = df[mask].sort_values('game_date', ascending=False)
            last_dates = sorted(history['game_date'].unique(), reverse=True)[:5]
            
            st.write("---")
            st.subheader("📅 Partidos Analizados")
            
            games_summary = []
            for date in last_dates:
                row = history[history['game_date'] == date].iloc[0]
                games_summary.append({
                    'FECHA': date.strftime('%d/%m/%Y'),
                    'ENFRENTAMIENTO': row['matchup']
                })
            
            df_games = pd.DataFrame(games_summary)
            mostrar_tabla_bonita(df_games, None)

            # --- ESTADÍSTICAS DE EQUIPO ---
            team_totals = history.groupby(['game_date', 'team_abbreviation'])[['pts', 'reb', 'ast']].sum().reset_index()
            team_avgs = team_totals.groupby('team_abbreviation')[['pts', 'reb', 'ast']].mean().reset_index()
            team_avgs = team_avgs[team_avgs['team_abbreviation'].isin([t1, t2])]
            
            if not team_avgs.empty:
                st.write("---")
                st.subheader("📊 Estadísticas Medias de Equipo (H2H)")
                team_avgs.columns = ['EQUIPO', 'PTS', 'REB', 'AST']
                mostrar_tabla_bonita(team_avgs, 'PTS')
            
            recent_players = history[history['game_date'].isin(last_dates)].sort_values('game_date', ascending=False)
            
            # AGREGACIÓN JUGADORES
            stats = recent_players.groupby(['player_name', 'team_abbreviation']).agg(
                pts=('pts', 'mean'),
                reb=('reb', 'mean'),
                ast=('ast', 'mean'),
                trend_pts=('pts', lambda x: '/'.join(x.astype(int).astype(str))),
                trend_reb=('reb', lambda x: '/'.join(x.astype(int).astype(str))),
                trend_ast=('ast', lambda x: '/'.join(x.astype(int).astype(str))),
                trend_min=('min', lambda x: '/'.join(x.astype(int).astype(str))),
                gp=('game_date', 'count')
            ).reset_index()

            # --- FILTRO: SOLO JUGADORES ACTUALES ---
            stats = stats[stats['player_name'].apply(lambda x: latest_teams_map.get(x) in [t1, t2])]

            # Status visual
            status_list = []
            for idx, row in stats.iterrows():
                p_name = row['player_name']
                p_team = row['team_abbreviation']
                real_team = latest_teams_map.get(p_name, p_team)
                
                player_games = recent_players[(recent_players['player_name'] == p_name) & (recent_players['team_abbreviation'] == p_team)]
                dates_played = player_games['game_date'].unique()
                
                html_str = ""
                for d in last_dates:
                    d_short = d.strftime('%d/%m')
                    if d in dates_played:
                        html_str += f"<div class='status-cell'><span class='status-played'>✅</span><span class='status-date'>{d_short}</span></div>"
                    else:
                        if real_team != p_team:
                             html_str += f"<div class='status-cell'><span class='status-date'>N/A</span></div>"
                        else:
                            html_str += f"<div class='status-cell'><span class='status-missed'>❌</span><span class='status-date'>{d_short}</span></div>"
                status_list.append(html_str)
            
            stats['STATUS_HTML'] = status_list

            st.write("---")
            
            # TABLAS PRINCIPALES
            st.subheader("🔥 Top Reboteadores")
            reb_df = stats.sort_values('reb', ascending=False).head(15).copy()
            if not reb_df.empty:
                reb_final = reb_df[['player_name', 'team_abbreviation', 'STATUS_HTML', 'reb', 'trend_reb', 'trend_min']]
                reb_final.columns = ['JUGADOR', 'EQUIPO', 'STATUS', 'REB', 'RACHA', 'MIN (SEQ)']
                mostrar_tabla_bonita(reb_final, 'REB')
            else:
                st.info("Sin datos suficientes.")
            
            st.subheader("🎯 Top Anotadores")
            pts_df = stats.sort_values('pts', ascending=False).head(15).copy()
            if not pts_df.empty:
                pts_final = pts_df[['player_name', 'team_abbreviation', 'STATUS_HTML', 'pts', 'trend_pts', 'trend_min']]
                pts_final.columns = ['JUGADOR', 'EQUIPO', 'STATUS', 'PTS', 'RACHA', 'MIN (SEQ)']
                mostrar_tabla_bonita(pts_final, 'PTS')
            else:
                st.info("Sin datos suficientes.")
            
            st.subheader("🤝 Top Asistentes")
            ast_df = stats.sort_values('ast', ascending=False).head(15).copy()
            if not ast_df.empty:
                ast_final = ast_df[['player_name', 'team_abbreviation', 'STATUS_HTML', 'ast', 'trend_ast', 'trend_min']]
                ast_final.columns = ['JUGADOR', 'EQUIPO', 'STATUS', 'AST', 'RACHA', 'MIN (SEQ)']
                mostrar_tabla_bonita(ast_final, 'AST')
            else:
                st.info("Sin datos suficientes.")
            
            # --- BAJAS POR EQUIPO ---
            st.write("---")
            st.subheader("🏥 Historial de Bajas (Por Equipo)")
            
            avg_mins = recent_players.groupby(['player_name', 'team_abbreviation'])['min'].mean()
            active_key_players = [p for p in avg_mins[avg_mins > 12.0].index.tolist() if latest_teams_map.get(p[0]) in [t1, t2]]
            
            dnp_table_data = []
            for date in last_dates:
                date_str = date.strftime('%d/%m/%Y')
                played_on_date = recent_players[recent_players['game_date'] == date]['player_name'].unique()
                missing_t1 = []
                missing_t2 = []
                
                for p_name, p_team in active_key_players:
                    current_real_team = latest_teams_map.get(p_name, p_team)
                    if current_real_team != p_team: continue 

                    team_played = not recent_players[(recent_players['game_date'] == date) & (recent_players['team_abbreviation'] == p_team)].empty
                    if team_played and (p_name not in played_on_date):
                        if p_team == t1: missing_t1.append(p_name)
                        elif p_team == t2: missing_t2.append(p_name)
                
                cell_t1 = f"<span class='dnp-missing'>{', '.join(missing_t1)}</span>" if missing_t1 else "<span class='dnp-full'>✅ Completo</span>"
                cell_t2 = f"<span class='dnp-missing'>{', '.join(missing_t2)}</span>" if missing_t2 else "<span class='dnp-full'>✅ Completo</span>"
                dnp_table_data.append({'FECHA': date_str, f'BAJAS {t1}': cell_t1, f'BAJAS {t2}': cell_t2})
            
            if dnp_table_data:
                df_dnp = pd.DataFrame(dnp_table_data)
                html_dnp = df_dnp.style.hide(axis="index").to_html(classes="custom-table")
                st.markdown(f"<div class='table-wrapper'>{html_dnp}</div>", unsafe_allow_html=True)
            else:
                st.success("✅ No hubo bajas importantes.")

            # --- DETECCIÓN DE PATRONES ---
            st.write("---")
            st.subheader("🕵️ Detección de Patrones")
            
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
                        if current_real_team == team and (star not in players_present):
                            missing_stars_today.append(star)
                    
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
                                if row['pts'] >= 15 and diff_pts >= 8: impact_msgs.append(f"🏀 +{int(diff_pts)} PTS")
                            if any(s in star_rebounders for s in missing_stars_today):
                                if row['reb'] >= 7 and diff_reb >= 4: impact_msgs.append(f"🖐 +{int(diff_reb)} REB")
                            if any(s in star_assisters for s in missing_stars_today):
                                if row['ast'] >= 5 and diff_ast >= 4: impact_msgs.append(f"🎁 +{int(diff_ast)} AST")
                            
                            if impact_msgs: beneficiaries.append(f"<b>{p_name}</b> ({', '.join(impact_msgs)})")
                        
                        if beneficiaries:
                            date_str = date.strftime('%d/%m')
                            missing_str = ", ".join(missing_stars_today)
                            impact_str = "<br>".join(beneficiaries)
                            formatted_missing = f"<span class='pat-stars'>{missing_str}</span>"
                            formatted_impact = f"<span class='pat-impact'>{impact_str}</span>"
                            patterns_data.append({'FECHA': date_str, 'EQUIPO': team, 'BAJAS ESTELARES': formatted_missing, 'IMPACTO': formatted_impact})

            if patterns_data:
                df_patterns = pd.DataFrame(patterns_data)
                html_pat = df_patterns.style.hide(axis="index").to_html(classes="custom-table")
                st.markdown(f"<div class='table-wrapper'>{html_pat}</div>", unsafe_allow_html=True)
            else:
                st.write("No se detectaron impactos significativos por bajas.")

            # --- GENERADOR DE PARLAY (DUAL: SAFE vs RISKY) ---
            st.write("---")
            st.subheader("🎲 GENERADOR DE PARLAY (Dual Strategy)")
            
            min_games_needed = max(3, int(len(last_dates) * 0.6))
            candidates = stats[stats['gp'] >= min_games_needed].copy()
            
            safe_legs_pts = []
            safe_legs_reb = []
            safe_legs_ast = []
            risky_legs_pts = []
            risky_legs_reb = []
            risky_legs_ast = []

            for _, row in candidates.iterrows():
                p_name = row['player_name']
                p_team = row['team_abbreviation']
                
                logs = recent_players[(recent_players['player_name'] == p_name) & (recent_players['team_abbreviation'] == p_team)]
                if logs.empty: continue
                
                pts_vals = sorted(logs['pts'].tolist())
                reb_vals = sorted(logs['reb'].tolist())
                ast_vals = sorted(logs['ast'].tolist())
                
                if len(pts_vals) >= 4: smart_min_pts = pts_vals[1] 
                else: smart_min_pts = pts_vals[0]
                if len(reb_vals) >= 4: smart_min_reb = reb_vals[1]
                else: smart_min_reb = reb_vals[0]
                if len(ast_vals) >= 4: smart_min_ast = ast_vals[1]
                else: smart_min_ast = ast_vals[0]
                
                avg_pts = row['pts']
                avg_reb = row['reb']
                avg_ast = row['ast']

                if smart_min_pts >= 12: 
                    safe_legs_pts.append({'player': p_name, 'val': int(smart_min_pts), 'score': avg_pts, 'desc': f"Suelo vs Rival"})
                if smart_min_reb >= 6: 
                    safe_legs_reb.append({'player': p_name, 'val': int(smart_min_reb), 'score': avg_reb, 'desc': f"Suelo vs Rival"})
                if smart_min_ast >= 4: 
                    safe_legs_ast.append({'player': p_name, 'val': int(smart_min_ast), 'score': avg_ast, 'desc': f"Suelo vs Rival"})

                if avg_pts >= 15 and avg_pts > (smart_min_pts + 1.0):
                    risky_legs_pts.append({'player': p_name, 'val': int(avg_pts), 'score': avg_pts, 'desc': f"Media vs Rival (Alto Valor)"})
                if avg_reb >= 8 and avg_reb > (smart_min_reb + 1.0):
                    risky_legs_reb.append({'player': p_name, 'val': int(avg_reb), 'score': avg_reb, 'desc': f"Media vs Rival (Alto Valor)"})
                if avg_ast >= 6 and avg_ast > (smart_min_ast + 1.0):
                    risky_legs_ast.append({'player': p_name, 'val': int(avg_ast), 'score': avg_ast, 'desc': f"Media vs Rival (Alto Valor)"})

            for l in [safe_legs_pts, safe_legs_reb, safe_legs_ast, risky_legs_pts, risky_legs_reb, risky_legs_ast]:
                l.sort(key=lambda x: x['score'], reverse=True)

            def render_ticket(title, legs, icon, color_border, css_class):
                final_legs = legs[:5] 
                if not final_legs: return f"<div class='{css_class}' style='border:1px solid {color_border};'><div class='parlay-header' style='color:{color_border};'>{title}</div><div style='color:#888;'>Sin opciones claras</div></div>"
                html_legs = ""
                for leg in final_legs:
                    html_legs += f"<div class='parlay-leg' style='border-left: 5px solid {color_border};'><div class='leg-player'>{icon} {leg['player']}</div><div class='leg-info'><div class='leg-val'>+{leg['val']}</div><div class='leg-stat'>{leg['desc']}</div></div></div>"
                return f"<div class='{css_class}' style='border:1px solid {color_border};'><div class='parlay-header' style='color:{color_border};'>{title}</div>{html_legs}</div>"

            col_safe, col_risky = st.columns(2)
            
            with col_safe:
                st.markdown("### 🛡️ CONSERVADOR")
                st.markdown(render_ticket("PTS (Seguro)", safe_legs_pts, "🏀", "#4caf50", "parlay-box"), unsafe_allow_html=True)
                if safe_legs_reb: st.markdown(render_ticket("REB (Seguro)", safe_legs_reb, "🖐", "#4caf50", "parlay-box"), unsafe_allow_html=True)
                if safe_legs_ast: st.markdown(render_ticket("AST (Seguro)", safe_legs_ast, "🎁", "#4caf50", "parlay-box"), unsafe_allow_html=True)

            with col_risky:
                st.markdown("### 🚀 ARRIESGADO")
                st.markdown(render_ticket("PTS (High Value)", risky_legs_pts, "🏀", "#ff5252", "parlay-box"), unsafe_allow_html=True)
                if risky_legs_reb: st.markdown(render_ticket("REB (High Value)", risky_legs_reb, "🖐", "#ff5252", "parlay-box"), unsafe_allow_html=True)
                if risky_legs_ast: st.markdown(render_ticket("AST (High Value)", risky_legs_ast, "🎁", "#ff5252", "parlay-box"), unsafe_allow_html=True)


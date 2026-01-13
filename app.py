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

# --- CSS: FUENTE TEKO + DISEÑO LIMPIO ---
st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Teko:wght@300..700&display=swap');

    /* Título principal con balones a los lados */
    h1 {
        font-family: 'Teko', sans-serif !important;
        font-size: 65px !important;
        text-transform: uppercase;
        letter-spacing: 3px;
        text-align: center;
        margin-bottom: 30px;
        color: white;
    }

    /* Estilo de los encabezados de jornada */
    h3 {
        font-family: 'Teko', sans-serif !important;
        font-size: 35px !important;
        text-transform: uppercase;
        letter-spacing: 1px;
    }

    /* Tarjetas del calendario */
    .game-card {
        background-color: #2d2d2d;
        border: 1px solid #444;
        border-radius: 12px;
        padding: 15px;
        margin-bottom: 15px;
        text-align: center;
    }
    .game-matchup { display: flex; justify-content: center; align-items: center; gap: 15px; margin-bottom: 10px; }
    .team-logo { width: 45px; height: 45px; object-fit: contain; }
    .vs-text { font-weight: bold; font-size: 14px; color: #888; }
    .game-time { 
        color: #ffbd45; 
        font-size: 24px; 
        font-weight: bold; 
        font-family: 'Teko', sans-serif; 
        margin-top: 5px;
    }
    
    .injuries-link {
        font-size: 13px;
        color: #4caf50;
        text-decoration: none;
        border: 1px solid #4caf50;
        padding: 5px 10px;
        border-radius: 5px;
        margin-top: 10px;
        display: inline-block;
    }

    /* Enlace de la ficha del partido en la tabla */
    a.match-link {
        color: #2196f3 !important;
        text-decoration: none;
        font-weight: bold;
        border: 1px solid #2196f3;
        padding: 2px 8px;
        border-radius: 4px;
        font-size: 12px;
    }
    a.match-link:hover {
        background-color: #2196f3;
        color: white !important;
    }

    .credits { 
        font-family: 'Teko', sans-serif; 
        font-size: 24px; 
        color: #666; 
        text-align: center; 
        margin-top: 40px; 
    }
    
    /* Ajustes tabla */
    table { width: 100%; border-collapse: collapse; margin-bottom: 20px; color: white; font-family: sans-serif; }
    th { background-color: #31333F; color: white; font-weight: bold; text-align: center !important; padding: 10px; border-bottom: 2px solid #464b5f; text-transform: uppercase; }
    td { text-align: center !important; padding: 8px; border-bottom: 1px solid #464b5f; font-size: 14px; vertical-align: middle; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# LÓGICA DE DATOS
# ==========================================
CSV_FOLDER = "csv"
if not os.path.exists(CSV_FOLDER): os.makedirs(CSV_FOLDER)

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
        # --- AÑADIDO 'GAME_ID' A LAS COLUMNAS NECESARIAS ---
        cols_needed = ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'GAME_DATE', 'MATCHUP', 'PTS', 'REB', 'AST', 'MIN', 'WL', 'GAME_ID']
        cols_final = [c for c in cols_needed if c in full_df.columns]
        df_clean = full_df[cols_final].copy()
        df_clean.columns = df_clean.columns.str.lower()
        
        df_clean.to_csv(f'{CSV_FOLDER}/player_stats.csv', index=False)
        # SQLite opcional, lo mantenemos por si lo usas luego
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
        if 'game_date' in df.columns: df['game_date'] = pd.to_datetime(df['game_date'])
        # Asegurarnos de que game_id sea string para que no pierda ceros iniciales
        if 'game_id' in df.columns: df['game_id'] = df['game_id'].astype(str).str.zfill(10)
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

def obtener_partidos():
    nba_teams = nba_static_teams.get_teams()
    team_map = {t['id']: t['abbreviation'] for t in nba_teams}
    fechas = [datetime.now(), datetime.now() + timedelta(days=1)]
    agenda = {}
    for fecha in fechas:
        fecha_str = fecha.strftime('%Y-%m-%d')
        label = "HOY" if fecha.date() == datetime.now().date() else "MAÑANA"
        agenda[label] = []
        try:
            board = scoreboardv2.ScoreboardV2(game_date=fecha_str)
            games = board.game_header.get_data_frame()
            if not games.empty:
                for _, game in games.iterrows():
                    h_id, v_id = game['HOME_TEAM_ID'], game['VISITOR_TEAM_ID']
                    agenda[label].append({
                        'v_abv': team_map.get(v_id), 'h_abv': team_map.get(h_id),
                        'v_logo': f"https://cdn.nba.com/logos/nba/{v_id}/global/L/logo.svg",
                        'h_logo': f"https://cdn.nba.com/logos/nba/{h_id}/global/L/logo.svg",
                        'time': convertir_hora_espanol(game['GAME_STATUS_TEXT'])
                    })
        except: pass
    return agenda

# --- MODIFICADO: FUNCIÓN PARA MOSTRAR TABLA CON HTML (LINKS) ---
def mostrar_tabla_bonita(df_raw, col_principal_espanol):
    # Columnas numéricas para formatear
    cols_fmt = [c for c in df_raw.columns if c in ['PTS', 'REB', 'AST']] 
    
    html = df_raw.style\
        .format("{:.1f}", subset=cols_fmt)\
        .background_gradient(subset=[col_principal_espanol] if col_principal_espanol else None, cmap='YlOrBr' if col_principal_espanol=='REB' else ('Greens' if col_principal_espanol=='PTS' else ('Blues' if col_principal_espanol=='AST' else None)))\
        .hide(axis="index")\
        .to_html(classes="custom-table", escape=False) # escape=False es CLAVE para que funcione el link
    
    st.markdown(f"<div class='table-wrapper'>{html}</div>", unsafe_allow_html=True)

# ==========================================
# INTERFAZ (Pestaña Inicio)
# ==========================================
st.markdown("<h1>🏀 NBA PRO ANALYZER 🏀</h1>", unsafe_allow_html=True)

opcion = st.sidebar.radio("Menú:", ["🏠 Inicio", "👤 Jugador", "⚔️ Analizar Partido", "🔄 Actualizar Datos"])
df = load_data()

if opcion == "🏠 Inicio":
    agenda = obtener_partidos()
    c1, c2 = st.columns(2)
    
    with c1:
        st.markdown("<h3 style='color:#4caf50; text-align: center;'>JORNADA DE HOY (Madrugada)</h3>", unsafe_allow_html=True)
        for g in agenda.get("HOY", []):
            st.markdown(f"""
            <div class='game-card'>
                <div class='game-matchup'>
                    <img src='{g['v_logo']}' class='team-logo'> <span class='vs-text'>@</span> <img src='{g['h_logo']}' class='team-logo'>
                </div>
                <div style='color:white; font-weight:bold;'>{g['v_abv']} vs {g['h_abv']}</div>
                <div class='game-time'>{g['time']}</div>
                <a href='https://www.rotowire.com/basketball/nba-lineups.php' target='_blank' class='injuries-link'>🏥 Ver Bajas / Lineups</a>
            </div>
            """, unsafe_allow_html=True)

    with c2:
        st.markdown("<h3 style='color:#2196f3; text-align: center;'>JORNADA DE MAÑANA</h3>", unsafe_allow_html=True)
        for g in agenda.get("MAÑANA", []):
            st.markdown(f"""
            <div class='game-card'>
                <div class='game-matchup'>
                    <img src='{g['v_logo']}' class='team-logo'> <span class='vs-text'>@</span> <img src='{g['h_logo']}' class='team-logo'>
                </div>
                <div style='color:white; font-weight:bold;'>{g['v_abv']} vs {g['h_abv']}</div>
                <div class='game-time'>{g['time']}</div>
                <a href='https://www.rotowire.com/basketball/nba-lineups.php' target='_blank' class='injuries-link'>🏥 Ver Bajas / Lineups</a>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<div class='credits'>Creado por ad.ri.</div>", unsafe_allow_html=True)

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
            
            # --- MODIFICADO: AÑADIR LINK DE FICHA ---
            cols_to_view = ['game_date', 'matchup', 'min', 'pts', 'reb', 'ast']
            if 'game_id' in player_data.columns:
                cols_to_view.append('game_id')
            
            view = player_data[cols_to_view].head(5).copy()
            view['min'] = view['min'].astype(int)
            
            # Crear columna de link si existe game_id
            if 'game_id' in view.columns:
                view['FICHA'] = view['game_id'].apply(lambda x: f"<a href='https://www.nba.com/game/{x}' target='_blank' class='match-link'>📊 Ver</a>")
                view = view.drop(columns=['game_id'])
                # Reordenar
                view = view[['game_date', 'matchup', 'FICHA', 'min', 'pts', 'reb', 'ast']]
            
            view.columns = ['FECHA', 'PARTIDO', 'FICHA', 'MIN', 'PTS', 'REB', 'AST'] if 'FICHA' in view.columns else ['FECHA', 'PARTIDO', 'MIN', 'PTS', 'REB', 'AST']
            view['FECHA'] = view['FECHA'].dt.strftime('%d/%m/%Y') 
            
            if 'FICHA' not in view.columns:
                st.warning("⚠️ Pulsa 'Actualizar Datos' para ver los enlaces a las fichas.")
                
            mostrar_tabla_bonita(view, None)
            
            if rival:
                st.subheader(f"Historial vs {rival}")
                h2h = player_data[player_data['matchup'].str.contains(rival, case=False)]
                if not h2h.empty:
                    view_h2h = h2h[cols_to_view].copy()
                    view_h2h['min'] = view_h2h['min'].astype(int)
                    
                    if 'game_id' in view_h2h.columns:
                        view_h2h['FICHA'] = view_h2h['game_id'].apply(lambda x: f"<a href='https://www.nba.com/game/{x}' target='_blank' class='match-link'>📊 Ver</a>")
                        view_h2h = view_h2h.drop(columns=['game_id'])
                        view_h2h = view_h2h[['game_date', 'matchup', 'FICHA', 'min', 'pts', 'reb', 'ast']]
                    
                    view_h2h.columns = ['FECHA', 'PARTIDO', 'FICHA', 'MIN', 'PTS', 'REB', 'AST'] if 'FICHA' in view_h2h.columns else ['FECHA', 'PARTIDO', 'MIN', 'PTS', 'REB', 'AST']
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
                # Obtener ID si existe
                g_id = row['game_id'] if 'game_id' in row else None
                link_html = f"<a href='https://www.nba.com/game/{g_id}' target='_blank' class='match-link'>📊 Ver Ficha</a>" if g_id else "-"
                
                games_summary.append({
                    'FECHA': date.strftime('%d/%m/%Y'),
                    'ENFRENTAMIENTO': row['matchup'],
                    'FICHA': link_html
                })
            
            df_games = pd.DataFrame(games_summary)
            if 'game_id' not in df.columns:
                 st.warning("⚠️ Pulsa 'Actualizar Datos' para habilitar los enlaces.")
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

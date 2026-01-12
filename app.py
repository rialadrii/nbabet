import streamlit as st
import pandas as pd
import sqlite3
import os
import time
from nba_api.stats.endpoints import leaguegamelog

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA (VISUAL)
# ==========================================
st.set_page_config(page_title="NBA Analyzer Pro", page_icon="🏀", layout="wide")

# --- CSS: MODO OSCURO + CENTRADO ---
st.markdown("""
    <style>
    /* Estilo para las tarjetas de métricas */
    div[data-testid="stMetric"] {
        background-color: #262730;
        border: 1px solid #464b5f;
        padding: 10px;
        border-radius: 10px;
        color: white;
    }
    /* Centrar títulos */
    h1, h2, h3 { text-align: center; }
    
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
        border: 2px dashed #ffd700;
        border-radius: 15px;
        padding: 20px;
        margin-top: 20px;
        text-align: center;
        max-width: 600px; /* Centrado en PC */
        margin-left: auto;
        margin-right: auto;
    }
    .parlay-header {
        font-size: 24px;
        font-weight: bold;
        margin-bottom: 15px;
        text-transform: uppercase;
        letter-spacing: 1px;
    }
    .parlay-leg {
        background-color: #2d2d2d;
        margin: 10px 0;
        padding: 12px;
        border-radius: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        box-shadow: 0 2px 5px rgba(0,0,0,0.3);
    }
    .leg-player { font-weight: bold; color: white; font-size: 15px; text-align: left; }
    .leg-bet { font-weight: bold; font-size: 18px; text-align: right; }
    .leg-stat { color: #aaaaaa; font-size: 11px; display: block; margin-top: 4px; text-align: right; }
    .leg-info { text-align: right; }
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

# ==========================================
# INTERFAZ PRINCIPAL
# ==========================================

st.markdown("<h1 style='text-align: center;'>🏀 NBA Pro Analyzer (Mobile)</h1>", unsafe_allow_html=True)

st.sidebar.header("Menú de Control")
opcion = st.sidebar.radio("Selecciona modo:", ["🏠 Inicio", "👤 Analizar Jugador", "⚔️ Analizar Partido", "🔄 Actualizar Datos"])

df = load_data()

# --- MAPA DE EQUIPOS ACTUALES (Anti-Traspasos) ---
latest_teams_map = {}
if not df.empty:
    latest_entries = df.sort_values('game_date').drop_duplicates('player_name', keep='last')
    latest_teams_map = dict(zip(latest_entries['player_name'], latest_entries['team_abbreviation']))

# --- FUNCION PARA MOSTRAR TABLA LIMPIA ---
def mostrar_tabla_bonita(df_raw, col_principal_espanol):
    cols_fmt = [c for c in df_raw.columns if c in ['PTS', 'REB', 'AST', 'MIN']]
    
    html = df_raw.style\
        .format("{:.1f}", subset=cols_fmt)\
        .background_gradient(subset=[col_principal_espanol] if col_principal_espanol else None, cmap='YlOrBr' if col_principal_espanol=='REB' else ('Greens' if col_principal_espanol=='PTS' else ('Blues' if col_principal_espanol=='AST' else None)))\
        .hide(axis="index")\
        .to_html(classes="custom-table")
    
    st.markdown(f"<div class='table-wrapper'>{html}</div>", unsafe_allow_html=True)

if opcion == "🏠 Inicio":
    st.info("Bienvenido. Usa el menú de la izquierda para navegar.")
    st.markdown("---")
    st.markdown("<h3 style='text-align: center;'>👨‍💻 CREADO POR RIALADRI</h3>", unsafe_allow_html=True)
    st.markdown("---")
    
    if df.empty:
        st.warning("⚠️ No hay datos. Ve a 'Actualizar Datos' primero.")
    else:
        st.write(f"Datos cargados: **{len(df)}** registros.")
        st.write("Última actualización: ", df['game_date'].max().strftime('%d/%m/%Y') if not df.empty else "N/A")

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
        jugador = st.selectbox("Escribe el nombre:", todos_jugadores, index=None, placeholder="Ej: Kevin Love")
        
        if jugador:
            player_data = df[df['player_name'] == jugador].sort_values('game_date', ascending=False)
            rival = st.text_input("Filtrar vs Rival (Opcional, ej: CHA):").upper()
            
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("PTS", f"{player_data['pts'].mean():.1f}")
            c2.metric("REB", f"{player_data['reb'].mean():.1f}")
            c3.metric("AST", f"{player_data['ast'].mean():.1f}")
            c4.metric("MIN", f"{player_data['min'].mean():.1f}")
            
            st.subheader("Últimos 5 Partidos")
            
            view = player_data[['game_date', 'matchup', 'min', 'pts', 'reb', 'ast']].head(5).copy()
            view.columns = ['FECHA', 'PARTIDO', 'MIN', 'PTS', 'REB', 'AST']
            view['FECHA'] = view['FECHA'].dt.strftime('%d/%m/%Y') 
            mostrar_tabla_bonita(view, None)
            
            if rival:
                st.subheader(f"Historial vs {rival}")
                h2h = player_data[player_data['matchup'].str.contains(rival, case=False)]
                if not h2h.empty:
                    view_h2h = h2h[['game_date', 'matchup', 'min', 'pts', 'reb', 'ast']].copy()
                    view_h2h.columns = ['FECHA', 'PARTIDO', 'MIN', 'PTS', 'REB', 'AST']
                    view_h2h['FECHA'] = view_h2h['FECHA'].dt.strftime('%d/%m/%Y')
                    mostrar_tabla_bonita(view_h2h, None)

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
            
            recent_players = history[history['game_date'].isin(last_dates)].sort_values('game_date', ascending=False)
            
            stats = recent_players.groupby(['player_name', 'team_abbreviation']).agg(
                pts=('pts', 'mean'),
                reb=('reb', 'mean'),
                ast=('ast', 'mean'),
                min=('min', 'mean'),
                trend_pts=('pts', lambda x: '/'.join(x.astype(int).astype(str))),
                trend_reb=('reb', lambda x: '/'.join(x.astype(int).astype(str))),
                trend_ast=('ast', lambda x: '/'.join(x.astype(int).astype(str))),
                gp=('game_date', 'count')
            ).reset_index()

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
            st.subheader("🔥 Top Reboteadores")
            reb_df = stats.sort_values('reb', ascending=False).head(15).copy()
            reb_final = reb_df[['player_name', 'team_abbreviation', 'STATUS_HTML', 'reb', 'trend_reb', 'min']]
            reb_final.columns = ['JUGADOR', 'EQUIPO', 'STATUS', 'REB', 'RACHA', 'MIN']
            mostrar_tabla_bonita(reb_final, 'REB')
            
            st.subheader("🎯 Top Anotadores")
            pts_df = stats.sort_values('pts', ascending=False).head(15).copy()
            pts_final = pts_df[['player_name', 'team_abbreviation', 'STATUS_HTML', 'pts', 'trend_pts', 'min']]
            pts_final.columns = ['JUGADOR', 'EQUIPO', 'STATUS', 'PTS', 'RACHA', 'MIN']
            mostrar_tabla_bonita(pts_final, 'PTS')
            
            st.subheader("🤝 Top Asistentes")
            ast_df = stats.sort_values('ast', ascending=False).head(15).copy()
            ast_final = ast_df[['player_name', 'team_abbreviation', 'STATUS_HTML', 'ast', 'trend_ast', 'min']]
            ast_final.columns = ['JUGADOR', 'EQUIPO', 'STATUS', 'AST', 'RACHA', 'MIN']
            mostrar_tabla_bonita(ast_final, 'AST')
            
            # --- BAJAS POR EQUIPO ---
            st.write("---")
            st.subheader("🏥 Historial de Bajas (Por Equipo)")
            
            avg_mins = recent_players.groupby(['player_name', 'team_abbreviation'])['min'].mean()
            key_players_list = avg_mins[avg_mins > 12.0].index.tolist() 
            
            dnp_table_data = []

            for date in last_dates:
                date_str = date.strftime('%d/%m/%Y')
                played_on_date = recent_players[recent_players['game_date'] == date]['player_name'].unique()
                missing_t1 = []
                missing_t2 = []
                
                for p_name, p_team in key_players_list:
                    current_real_team = latest_teams_map.get(p_name, p_team)
                    if current_real_team != p_team:
                        continue 

                    team_played = not recent_players[(recent_players['game_date'] == date) & (recent_players['team_abbreviation'] == p_team)].empty
                    if team_played and (p_name not in played_on_date):
                        if p_team == t1:
                            missing_t1.append(p_name)
                        elif p_team == t2:
                            missing_t2.append(p_name)
                
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
            st.subheader("🕵️ Detección de Patrones (Impacto REAL y Agrupado)")
            
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
                            if p_name in global_means.index:
                                avg_p = global_means.loc[p_name]
                            else:
                                continue 
                            
                            diff_pts = row['pts'] - avg_p['pts']
                            diff_reb = row['reb'] - avg_p['reb']
                            diff_ast = row['ast'] - avg_p['ast']
                            
                            impact_msgs = []
                            
                            if any(s in star_scorers for s in missing_stars_today):
                                if row['pts'] >= 15 and diff_pts >= 8:
                                    impact_msgs.append(f"🏀 +{int(diff_pts)} PTS")
                            
                            if any(s in star_rebounders for s in missing_stars_today):
                                if row['reb'] >= 7 and diff_reb >= 4:
                                    impact_msgs.append(f"🖐 +{int(diff_reb)} REB")
                                    
                            if any(s in star_assisters for s in missing_stars_today):
                                if row['ast'] >= 5 and diff_ast >= 4:
                                    impact_msgs.append(f"🎁 +{int(diff_ast)} AST")
                            
                            if impact_msgs:
                                beneficiaries.append(f"<b>{p_name}</b> ({', '.join(impact_msgs)})")
                        
                        if beneficiaries:
                            date_str = date.strftime('%d/%m')
                            missing_str = ", ".join(missing_stars_today)
                            impact_str = "<br>".join(beneficiaries)
                            
                            formatted_missing = f"<span class='pat-stars'>{missing_str}</span>"
                            formatted_impact = f"<span class='pat-impact'>{impact_str}</span>"
                            
                            patterns_data.append({
                                'FECHA': date_str, 
                                'EQUIPO': team,
                                'BAJAS ESTELARES': formatted_missing, 
                                'IMPACTO': formatted_impact
                            })

            if patterns_data:
                df_patterns = pd.DataFrame(patterns_data)
                html_pat = df_patterns.style.hide(axis="index").to_html(classes="custom-table")
                st.markdown(f"<div class='table-wrapper'>{html_pat}</div>", unsafe_allow_html=True)
            else:
                st.write("No se detectaron impactos significativos por bajas en estos partidos.")

            # --- GENERADOR DE PARLAY (3 TICKETS DE 5 PICKS) ---
            st.write("---")
            st.subheader("🎲 IA Parlay Generator (3 Tickets)")
            st.info("Predicciones de seguridad (Suelos) basadas en mínimos históricos H2H.")

            min_games_needed = max(3, int(len(last_dates) * 0.6))
            candidates = stats[stats['gp'] >= min_games_needed].copy()
            
            # Listas separadas
            legs_pts = []
            legs_reb = []
            legs_ast = []

            for _, row in candidates.iterrows():
                p_name = row['player_name']
                p_team = row['team_abbreviation']
                
                logs = recent_players[(recent_players['player_name'] == p_name) & (recent_players['team_abbreviation'] == p_team)]
                if logs.empty: continue
                
                min_pts = logs['pts'].min()
                min_reb = logs['reb'].min()
                min_ast = logs['ast'].min()
                
                # PTS
                if min_pts >= 10:
                    safe_line = int(min_pts - 1)
                    legs_pts.append({
                        'player': p_name,
                        'val': safe_line,
                        'avg': row['pts'],
                        'desc': f"Mínimo H2H: {int(min_pts)}"
                    })
                
                # REB
                if min_reb >= 4:
                    safe_line = int(min_reb - 1)
                    legs_reb.append({
                        'player': p_name,
                        'val': safe_line,
                        'avg': row['reb'],
                        'desc': f"Mínimo H2H: {int(min_reb)}"
                    })
                    
                # AST
                if min_ast >= 3:
                    safe_line = int(min_ast - 1)
                    legs_ast.append({
                        'player': p_name,
                        'val': safe_line,
                        'avg': row['ast'],
                        'desc': f"Mínimo H2H: {int(min_ast)}"
                    })

            # Ordenar por calidad (Media más alta)
            legs_pts.sort(key=lambda x: x['avg'], reverse=True)
            legs_reb.sort(key=lambda x: x['avg'], reverse=True)
            legs_ast.sort(key=lambda x: x['avg'], reverse=True)

            # Función para renderizar tickets
            def render_ticket(title, legs, icon, color_border):
                final_legs = legs[:5] # Top 5
                if not final_legs: return ""
                
                html_legs = ""
                for leg in final_legs:
                    # HTML en una sola línea para evitar errores de markdown
                    html_legs += f"<div class='parlay-leg' style='border-left: 5px solid {color_border};'><div class='leg-player'>{icon} {leg['player']}</div><div class='leg-info'><div class='leg-bet'>+{leg['val']}</div><div class='leg-stat'>{leg['desc']}</div></div></div>"
                
                return f"<div class='parlay-box'><div class='parlay-header' style='color:{color_border};'>{title}</div>{html_legs}</div>"

            # Renderizar los 3 tickets
            if legs_pts:
                st.markdown(render_ticket("ANOTADORES (PTS)", legs_pts, "🏀", "#4caf50"), unsafe_allow_html=True)
            
            if legs_reb:
                st.markdown(render_ticket("REBOTEADORES (REB)", legs_reb, "🖐", "#ff9800"), unsafe_allow_html=True)
                
            if legs_ast:
                st.markdown(render_ticket("ASISTENTES (AST)", legs_ast, "🎁", "#2196f3"), unsafe_allow_html=True)

            if not (legs_pts or legs_reb or legs_ast):
                st.warning("No hay suficientes datos consistentes para generar tickets seguros hoy.")

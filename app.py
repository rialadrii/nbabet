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
    }
    div.table-wrapper {
        overflow-x: auto;
    }
    
    /* Estilo para Patrones */
    .pattern-box {
        background-color: #2b2d3e;
        border-left: 5px solid #ffbd45;
        padding: 15px;
        margin-bottom: 10px;
        border-radius: 5px;
    }
    .pattern-title {
        color: #ffbd45;
        font-weight: bold;
        font-size: 16px;
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

# ==========================================
# INTERFAZ PRINCIPAL
# ==========================================

st.markdown("<h1 style='text-align: center;'>🏀 NBA Pro Analyzer (Mobile)</h1>", unsafe_allow_html=True)

st.sidebar.header("Menú de Control")
opcion = st.sidebar.radio("Selecciona modo:", ["🏠 Inicio", "👤 Analizar Jugador", "⚔️ Analizar Partido", "🔄 Actualizar Datos"])

df = load_data()

# --- FUNCION PARA MOSTRAR TABLA LIMPIA ---
def mostrar_tabla_bonita(df_raw, col_principal_espanol):
    html = df_raw.style\
        .format("{:.1f}", subset=[c for c in df_raw.columns if c in ['PTS', 'REB', 'AST', 'MIN']])\
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
            total_games_matchup = len(last_dates)
            
            st.write("---")
            st.subheader("📅 Partidos Analizados (Orden de la Racha)")
            
            games_summary = []
            for date in last_dates:
                row = history[history['game_date'] == date].iloc[0]
                games_summary.append({
                    'FECHA': date.strftime('%d/%m/%Y'),
                    'ENFRENTAMIENTO': row['matchup']
                })
            
            df_games = pd.DataFrame(games_summary)
            mostrar_tabla_bonita(df_games, None)
            st.info("💡 NOTA: Los números en la columna 'RACHA' siguen este orden (el primero es el más reciente).")
            
            recent_players = history[history['game_date'].isin(last_dates)].sort_values('game_date', ascending=False)
            
            stats = recent_players.groupby(['player_name', 'team_abbreviation']).agg(
                pts=('pts', 'mean'),
                reb=('reb', 'mean'),
                ast=('ast', 'mean'),
                min=('min', 'mean'),
                gp=('game_date', 'count'),
                trend_pts=('pts', lambda x: '/'.join(x.astype(int).astype(str))),
                trend_reb=('reb', lambda x: '/'.join(x.astype(int).astype(str))),
                trend_ast=('ast', lambda x: '/'.join(x.astype(int).astype(str)))
            ).reset_index()
            
            stats['GP'] = stats['gp'].astype(str) + "/" + str(total_games_matchup)
            
            st.write("---")
            
            st.subheader("🔥 Top Reboteadores")
            reb_df = stats.sort_values('reb', ascending=False).head(15).copy()
            reb_final = reb_df[['player_name', 'team_abbreviation', 'GP', 'reb', 'trend_reb', 'min']]
            reb_final.columns = ['JUGADOR', 'EQUIPO', 'PJ', 'REB', 'RACHA', 'MIN']
            mostrar_tabla_bonita(reb_final, 'REB')
            
            st.subheader("🎯 Top Anotadores")
            pts_df = stats.sort_values('pts', ascending=False).head(15).copy()
            pts_final = pts_df[['player_name', 'team_abbreviation', 'GP', 'pts', 'trend_pts', 'min']]
            pts_final.columns = ['JUGADOR', 'EQUIPO', 'PJ', 'PTS', 'RACHA', 'MIN']
            mostrar_tabla_bonita(pts_final, 'PTS')
            
            st.subheader("🤝 Top Asistentes")
            ast_df = stats.sort_values('ast', ascending=False).head(15).copy()
            ast_final = ast_df[['player_name', 'team_abbreviation', 'GP', 'ast', 'trend_ast', 'min']]
            ast_final.columns = ['JUGADOR', 'EQUIPO', 'PJ', 'AST', 'RACHA', 'MIN']
            mostrar_tabla_bonita(ast_final, 'AST')
            
            st.write("---")
            st.subheader("📉 Bajas Clave (DNP)")
            
            avg_mins = recent_players.groupby(['player_name', 'team_abbreviation'])['min'].mean()
            key_players_list = avg_mins[avg_mins > 12.0].index.tolist()
            found_dnps = False
            
            for date in last_dates:
                date_str = date.strftime('%d/%m/%Y')
                played_on_date = recent_players[recent_players['game_date'] == date]['player_name'].unique()
                missing_in_game = []
                for p_name, p_team in key_players_list:
                    team_played_match = not recent_players[(recent_players['game_date'] == date) & (recent_players['team_abbreviation'] == p_team)].empty
                    if team_played_match and (p_name not in played_on_date):
                        missing_in_game.append(f"{p_name} ({p_team})")
                
                if missing_in_game:
                    found_dnps = True
                    st.write(f"**📅 {date_str}:**")
                    for p in missing_in_game:
                        st.error(f"❌ {p}")
            
            if not found_dnps:
                st.success("✅ No hubo bajas importantes en los últimos enfrentamientos.")

            # --- NUEVA SECCIÓN: DETECCIÓN DE PATRONES ---
            st.write("---")
            st.subheader("🕵️ Detección de Patrones (Impacto de Bajas)")
            st.info("Análisis automático: ¿Quién mejora sus números cuando falta una estrella en estos partidos?")

            # Lógica de detección
            # 1. Identificar "Estrellas" (Top players por media en estos partidos)
            top_scorers = stats.sort_values('pts', ascending=False).head(4)['player_name'].tolist()
            top_rebounders = stats.sort_values('reb', ascending=False).head(4)['player_name'].tolist()
            top_assisters = stats.sort_values('ast', ascending=False).head(4)['player_name'].tolist()
            
            all_stars = list(set(top_scorers + top_rebounders + top_assisters))
            
            patterns_found = []

            for date in last_dates:
                # Jugadores que jugaron ese día
                roster_day = recent_players[recent_players['game_date'] == date]
                players_present = roster_day['player_name'].unique()
                
                # Checkeamos si faltó alguna estrella de los equipos que jugaron
                teams_active = roster_day['team_abbreviation'].unique()
                
                for star in all_stars:
                    star_team = stats[stats['player_name'] == star]['team_abbreviation'].values[0]
                    
                    if (star_team in teams_active) and (star not in players_present):
                        # LA ESTRELLA FALTÓ. ¿Quién dio un paso adelante?
                        
                        # Filtramos compañeros de equipo ese día
                        teammates = roster_day[roster_day['team_abbreviation'] == star_team]
                        
                        # Buscamos anomalías positivas (Game Stats > Average Stats)
                        best_diff_pts = -1
                        beneficiary_pts = None
                        
                        best_diff_reb = -1
                        beneficiary_reb = None

                        best_diff_ast = -1
                        beneficiary_ast = None
                        
                        for _, row in teammates.iterrows():
                            p_name = row['player_name']
                            # Sus medias
                            avg_p = stats[stats['player_name'] == p_name].iloc[0]
                            
                            # Diferenciales
                            diff_pts = row['pts'] - avg_p['pts']
                            diff_reb = row['reb'] - avg_p['reb']
                            diff_ast = row['ast'] - avg_p['ast']
                            
                            # Detectar Puntos (Umbral significativo: +5 pts sobre media)
                            if diff_pts > 5 and diff_pts > best_diff_pts:
                                best_diff_pts = diff_pts
                                beneficiary_pts = f"{p_name} (+{int(diff_pts)} PTS)"
                                
                            # Detectar Rebotes (Umbral: +3 reb sobre media)
                            if diff_reb > 3 and diff_reb > best_diff_reb:
                                best_diff_reb = diff_reb
                                beneficiary_reb = f"{p_name} (+{int(diff_reb)} REB)"

                            # Detectar Asistencias (Umbral: +3 ast sobre media)
                            if diff_ast > 3 and diff_ast > best_diff_ast:
                                best_diff_ast = diff_ast
                                beneficiary_ast = f"{p_name} (+{int(diff_ast)} AST)"
                        
                        # Guardar patrón si hubo beneficiario claro
                        date_str = date.strftime('%d/%m')
                        if beneficiary_pts:
                            patterns_found.append(f"📅 {date_str} | Sin **{star}** ➔ 🏀 **{beneficiary_pts}** tomó el relevo.")
                        if beneficiary_reb:
                            patterns_found.append(f"📅 {date_str} | Sin **{star}** ➔ 🖐 **{beneficiary_reb}** dominó el tablero.")
                        if beneficiary_ast:
                            patterns_found.append(f"📅 {date_str} | Sin **{star}** ➔ 🎁 **{beneficiary_ast}** repartió juego.")

            if patterns_found:
                for pat in patterns_found:
                    st.markdown(f"<div class='pattern-box'><span class='pattern-title'>Patrón:</span> {pat}</div>", unsafe_allow_html=True)
            else:
                st.write("No se detectaron patrones claros de 'beneficiarios' por bajas en estos 5 partidos.")

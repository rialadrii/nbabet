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

# --- CSS FUERTE: MODO OSCURO + CENTRADO HTML ---
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
    
    /* ESTILOS PARA LAS TABLAS HTML (Centrado forzoso) */
    table {
        width: 100%;
        border-collapse: collapse;
        margin-bottom: 20px;
        color: white; /* Texto blanco */
        font-family: sans-serif;
    }
    th {
        background-color: #31333F;
        color: white;
        font-weight: bold;
        text-align: center !important; /* CENTRADO CABECERAS */
        padding: 10px;
        border-bottom: 2px solid #464b5f;
    }
    td {
        text-align: center !important; /* CENTRADO CELDAS */
        padding: 8px;
        border-bottom: 1px solid #464b5f;
        font-size: 14px;
    }
    /* Scroll horizontal en móvil si la tabla es muy ancha */
    div.table-wrapper {
        overflow-x: auto;
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
    """Descarga datos de la NBA API"""
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
        
        # Guardar CSV y SQL
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
    """Carga los datos en memoria para análisis"""
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

# --- BARRA LATERAL (MENU) ---
st.sidebar.header("Menú de Control")
opcion = st.sidebar.radio("Selecciona modo:", ["🏠 Inicio", "👤 Analizar Jugador", "⚔️ Analizar Partido", "🔄 Actualizar Datos"])

df = load_data()

# --- PÁGINA: INICIO ---
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

# --- PÁGINA: ACTUALIZAR ---
elif opcion == "🔄 Actualizar Datos":
    st.write("### 🔄 Sincronización con NBA API")
    st.write("Pulsa el botón para bajar las estadísticas más recientes de 2024-2026.")
    if st.button("Descargar y Actualizar Ahora"):
        with st.spinner("Conectando con servidores NBA..."):
            success = download_data()
            if success:
                st.success("¡Base de datos regenerada! Ya puedes analizar.")
                st.rerun()

# --- PÁGINA: JUGADOR ---
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
            
            # Tabla Individual en HTML
            tabla_html = player_data[['game_date', 'matchup', 'min', 'pts', 'reb', 'ast']].head(5)\
                .style.format("{:.1f}", subset=['min', 'pts', 'reb', 'ast'])\
                .to_html(index=False)
            st.markdown(f"<div class='table-wrapper'>{tabla_html}</div>", unsafe_allow_html=True)
            
            if rival:
                st.subheader(f"Historial vs {rival}")
                h2h = player_data[player_data['matchup'].str.contains(rival, case=False)]
                if not h2h.empty:
                    tabla_h2h = h2h[['game_date', 'matchup', 'min', 'pts', 'reb', 'ast']]\
                        .style.format("{:.1f}", subset=['min', 'pts', 'reb', 'ast'])\
                        .to_html(index=False)
                    st.markdown(f"<div class='table-wrapper'>{tabla_h2h}</div>", unsafe_allow_html=True)

# --- PÁGINA: PARTIDO ---
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
            
            recent_players = history[history['game_date'].isin(last_dates)]
            
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
            
            # --- FUNCIÓN NUEVA: RENDER HTML PURO (Centrado Perfecto) ---
            def mostrar_tabla_html(dataframe, col_color):
                # Columnas disponibles
                cols_format = [c for c in ['pts', 'reb', 'ast', 'min'] if c in dataframe.columns]
                
                # Generamos el HTML con estilos incrustados
                html = dataframe.style\
                    .format("{:.1f}", subset=cols_format)\
                    .background_gradient(subset=[col_color], cmap='YlOrBr' if col_color=='reb' else ('Greens' if col_color=='pts' else 'Blues'))\
                    .to_html(index=False, classes="custom-table")
                
                # Lo pintamos como Markdown (HTML inseguro permitido)
                st.markdown(f"<div class='table-wrapper'>{html}</div>", unsafe_allow_html=True)
            
            # REBOTEADORES
            st.subheader("🔥 Top Reboteadores")
            reb_df = stats.sort_values('reb', ascending=False).head(15)
            mostrar_tabla_html(
                reb_df[['player_name', 'team_abbreviation', 'GP', 'reb', 'trend_reb', 'min']], 
                'reb'
            )
            
            # ANOTADORES
            st.subheader("🎯 Top Anotadores")
            pts_df = stats.sort_values('pts', ascending=False).head(15)
            mostrar_tabla_html(
                pts_df[['player_name', 'team_abbreviation', 'GP', 'pts', 'trend_pts', 'min']], 
                'pts'
            )
            
            # ASISTENTES
            st.subheader("🤝 Top Asistentes")
            ast_df = stats.sort_values('ast', ascending=False).head(15)
            mostrar_tabla_html(
                ast_df[['player_name', 'team_abbreviation', 'GP', 'ast', 'trend_ast', 'min']], 
                'ast'
            )
            
            # --- SECCIÓN BAJAS (DNP) ---
            st.write("---")
            st.subheader("📉 Bajas Clave (DNP)")
            st.info("Jugadores (+12 min media) ausentes en duelos recientes:")
            
            avg_mins = recent_players.groupby(['player_name', 'team_abbreviation'])['min'].mean()
            key_players = avg_mins[avg_mins > 12.0].index.tolist()
            
            found_dnps = False
            
            for date in last_dates:
                date_str = date.strftime('%d/%m/%Y')
                played_on_date = recent_players[recent_players['game_date'] == date]['player_name'].unique()
                
                missing_in_game = []
                for p_name, p_team in key_players:
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

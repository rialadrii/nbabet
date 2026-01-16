import streamlit as st
import pandas as pd
from modules import ui, data_loader
from nba_api.stats.static import teams as nba_static_teams
from datetime import datetime

# CONFIGURACIÓN INICIAL
st.set_page_config(page_title="NBA Analyzer Pro", page_icon="🏀", layout="wide")

# 1. CARGAR ESTILOS (Aquí se arregla el centrado)
ui.cargar_css()

# 2. CARGAR DATOS
df = data_loader.load_data()

# 3. NAVEGACIÓN
if 'page' not in st.session_state: st.session_state.page = "🏠 Inicio"

# Menú lateral
st.sidebar.title("Menú")
opcion = st.sidebar.radio("", ["🏠 Inicio", "👤 Jugador", "⚔️ Analizar Partido", "🔄 Actualizar"], label_visibility="collapsed")

if opcion != st.session_state.page and opcion != "🔄 Actualizar":
    st.session_state.page = opcion
    st.rerun()

# --- PÁGINA: INICIO ---
if st.session_state.page == "🏠 Inicio":
    ui.render_header()
    st.write("### Selecciona una opción del menú para comenzar")
    st.info("👈 Usa el menú lateral para navegar")

# --- PÁGINA: ACTUALIZAR ---
elif opcion == "🔄 Actualizar":
    ui.render_header()
    st.write("### 🔄 Sincronización de Datos")
    if st.button("Descargar Datos Nuevos"):
        if data_loader.download_data_fresh():
            st.rerun()

# --- PÁGINA: JUGADOR ---
elif st.session_state.page == "👤 Jugador":
    ui.render_header()
    st.write("### 👤 Buscador de Jugadores")
    
    if df.empty:
        st.warning("⚠️ No hay datos. Ve a 'Actualizar' primero.")
    else:
        players = sorted(df['player_name'].unique())
        p_sel = st.selectbox("Buscar Jugador:", players)
        
        if p_sel:
            p_data = df[df['player_name'] == p_sel].sort_values('game_date', ascending=False)
            
            # Métricas
            c1, c2, c3 = st.columns(3)
            c1.metric("PTS", f"{p_data['pts'].mean():.1f}")
            c2.metric("REB", f"{p_data['reb'].mean():.1f}")
            c3.metric("AST", f"{p_data['ast'].mean():.1f}")
            
            st.write("### Últimos 5 Partidos")
            cols = ['game_date', 'matchup', 'wl', 'pts', 'reb', 'ast', 'min']
            view = p_data[cols].head(5).copy()
            
            # Formateo para la tabla bonita
            view.columns = ['FECHA', 'RIVAL', 'RES', 'PTS', 'REB', 'AST', 'MIN']
            view['FECHA'] = view['FECHA'].dt.strftime('%d/%m')
            
            means = {'PTS': p_data['pts'].mean(), 'REB': p_data['reb'].mean(), 'AST': p_data['ast'].mean()}
            
            # USAMOS LA NUEVA TABLA RESPONSIVE
            ui.mostrar_tabla_html(view, means_dict=means)

# --- PÁGINA: ANALIZAR PARTIDO ---
elif st.session_state.page == "⚔️ Analizar Partido":
    ui.render_header()
    st.write("### ⚔️ Análisis de Choque")
    
    teams = sorted(df['team_abbreviation'].unique()) if not df.empty else []
    c1, c2 = st.columns(2)
    t1 = c1.selectbox("Local", teams)
    t2 = c2.selectbox("Visitante", teams, index=1 if len(teams)>1 else 0)
    
    if t1 and t2:
        st.markdown("---")
        # Aquí iría tu lógica de H2H. 
        # Ejemplo rápido de tabla centrada:
        st.write(f"### Historial {t1} vs {t2}")
        
        mask = ((df['team_abbreviation'] == t1) & (df['matchup'].str.contains(t2))) | \
               ((df['team_abbreviation'] == t2) & (df['matchup'].str.contains(t1)))
        h2h = df[mask].sort_values('game_date', ascending=False).head(5)
        
        if not h2h.empty:
            view_h2h = h2h[['game_date', 'matchup', 'wl', 'pts', 'reb', 'ast']]
            view_h2h.columns = ['FECHA', 'PARTIDO', 'RES', 'PTS', 'REB', 'AST']
            view_h2h['FECHA'] = view_h2h['FECHA'].dt.strftime('%d/%m')
            ui.mostrar_tabla_html(view_h2h)
        else:
            st.info("Sin registros recientes.")

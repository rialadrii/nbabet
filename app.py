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

    .credits { 
        font-family: 'Teko', sans-serif; 
        font-size: 24px; 
        color: #666; 
        text-align: center; 
        margin-top: 40px; 
    }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# LÓGICA DE DATOS
# ==========================================
CSV_FOLDER = "csv"
if not os.path.exists(CSV_FOLDER): os.makedirs(CSV_FOLDER)

def load_data():
    csv_path = f"{CSV_FOLDER}/player_stats.csv"
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        if 'game_date' in df.columns: df['game_date'] = pd.to_datetime(df['game_date'])
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

# ==========================================
# INTERFAZ (Pestaña Inicio)
# ==========================================
st.markdown("<h1>🏀 NBA PRO ANALYZER 🏀</h1>", unsafe_allow_html=True)

opcion = st.sidebar.radio("Menú:", ["🏠 Inicio", "👤 Jugador", "⚔️ Partido", "🔄 Actualizar"])
df = load_data()

if opcion == "🏠 Inicio":
    agenda = obtener_partidos()
    c1, c2 = st.columns(2)
    
    with c1:
        # AÑADIDO: text-align: center
        st.markdown("<h3 style='text-align: center; color:#4caf50;'>JORNADA DE HOY (Madrugada)</h3>", unsafe_allow_html=True)
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
        # AÑADIDO: text-align: center
        st.markdown("<h3 style='text-align: center; color:#2196f3;'>JORNADA DE MAÑANA</h3>", unsafe_allow_html=True)
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

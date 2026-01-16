import pandas as pd
import sqlite3
import os
import streamlit as st
from nba_api.stats.endpoints import leaguegamelog, commonteamroster

DB_PATH = "nba.sqlite"
CSV_PATH = "player_stats.csv" # Asegúrate que coincida con tu repo o carpeta

@st.cache_data(ttl=3600)
def get_roster_map(team_id):
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=team_id)
        df = roster.get_data_frames()[0]
        df['NUM'] = df['NUM'].astype(str).str.replace('.0', '', regex=False)
        return dict(zip(df['PLAYER'], df['NUM']))
    except:
        return {}

def load_data():
    if os.path.exists(CSV_PATH):
        try:
            df = pd.read_csv(CSV_PATH)
            # Normalizar nombres de columnas a minúsculas para evitar errores
            df.columns = df.columns.str.lower()
            if 'game_date' in df.columns:
                df['game_date'] = pd.to_datetime(df['game_date'])
            return df
        except Exception as e:
            st.error(f"Error cargando CSV: {e}")
            return pd.DataFrame()
    return pd.DataFrame()

def download_data_fresh():
    seasons = ['2024-25', '2025-26']
    dfs = []
    status = st.empty()
    bar = st.progress(0)
    
    try:
        for i, season in enumerate(seasons):
            status.text(f"Descargando {season}...")
            # Usamos headers estándar si nba_api falla, pero por defecto debería ir bien
            gamelogs = leaguegamelog.LeagueGameLog(season=season, player_or_team_abbreviation='P')
            df = gamelogs.get_data_frames()[0]
            if not df.empty: dfs.append(df)
            bar.progress((i + 1) * 50)
            
        if dfs:
            full_df = pd.concat(dfs, ignore_index=True)
            full_df.columns = full_df.columns.str.lower()
            full_df.to_csv(CSV_PATH, index=False)
            status.success("¡Datos actualizados!")
            return True
    except Exception as e:
        st.error(f"Error API NBA: {e}")
    finally:
        bar.empty()
    return False

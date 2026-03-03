import streamlit as st
import pandas as pd
import sqlite3
import os
import time
from nba_api.stats.endpoints import leaguegamelog, scoreboardv2, commonteamroster
from nba_api.stats.static import teams as nba_static_teams
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup
import backoff

DB_PATH = "nba.sqlite"
CSV_FOLDER = "csv"

@st.cache_data(ttl=86400)
def load_data():
    csv_path = f"{CSV_FOLDER}/player_stats.csv"
    if os.path.exists(csv_path):
        df = pd.read_csv(csv_path)
        if 'game_date' in df.columns:
            df['game_date'] = pd.to_datetime(df['game_date'])
        if 'game_id' in df.columns:
            df['game_id'] = df['game_id'].astype(str).str.zfill(10)
        else:
            df['game_id'] = None
        if 'fg3m' not in df.columns:
            df['fg3m'] = 0
        return df
    return pd.DataFrame()

def download_data(seasons=None, progress_callback=None):
    if seasons is None:
        seasons = ['2024-25', '2025-26']
    all_seasons_data = []
    for i, season in enumerate(seasons):
        try:
            gamelogs = leaguegamelog.LeagueGameLog(season=season, player_or_team_abbreviation='P')
            df = gamelogs.get_data_frames()[0]
            if not df.empty:
                all_seasons_data.append(df)
            if progress_callback:
                progress_callback((i + 1) * (100 // len(seasons)))
        except Exception as e:
            st.error(f"Error descargando temporada {season}: {e}")

    if all_seasons_data:
        full_df = pd.concat(all_seasons_data, ignore_index=True)
        cols_needed = ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'GAME_DATE', 'MATCHUP',
                       'PTS', 'REB', 'AST', 'FG3M', 'FGM', 'FGA', 'FG_PCT', 'FG3A', 'FTM', 'FTA',
                       'OREB', 'DREB', 'STL', 'BLK', 'TOV', 'MIN', 'WL', 'GAME_ID']
        cols_final = [c for c in cols_needed if c in full_df.columns]
        df_clean = full_df[cols_final].copy()
        df_clean.columns = df_clean.columns.str.lower()
        os.makedirs(CSV_FOLDER, exist_ok=True)
        df_clean.to_csv(f'{CSV_FOLDER}/player_stats.csv', index=False)

        conn = sqlite3.connect(DB_PATH)
        df_clean.to_sql('player', conn, if_exists='replace', index=False)
        conn.execute('CREATE INDEX IF NOT EXISTS idx_player_name ON player(player_name);')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_team ON player(team_abbreviation);')
        conn.execute('CREATE INDEX IF NOT EXISTS idx_game_date ON player(game_date);')
        conn.close()
        return True
    return False

def query_player_stats(player_name=None, team=None, start_date=None, end_date=None):
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    query = "SELECT * FROM player WHERE 1=1"
    params = []
    if player_name:
        query += " AND player_name = ?"
        params.append(player_name)
    if team:
        query += " AND team_abbreviation = ?"
        params.append(team)
    if start_date:
        query += " AND game_date >= ?"
        params.append(start_date)
    if end_date:
        query += " AND game_date <= ?"
        params.append(end_date)
    df = pd.read_sql_query(query, conn, params=params)
    conn.close()
    if 'game_date' in df.columns:
        df['game_date'] = pd.to_datetime(df['game_date'])
    return df

def get_team_roster_numbers(team_id):
    try:
        roster = commonteamroster.CommonTeamRoster(team_id=team_id)
        df_roster = roster.get_data_frames()[0]
        df_roster['NUM'] = df_roster['NUM'].astype(str).str.replace('.0', '', regex=False)
        return dict(zip(df_roster['PLAYER'], df_roster['NUM']))
    except:
        return {}

@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3)
def safe_get(url, timeout=5):
    return requests.get(url, timeout=timeout)

def get_next_matchup_info(t1_abv, t2_abv):
    try:
        response = safe_get("https://cdn.nba.com/static/json/staticData/scheduleLeagueV2.json", timeout=5)
        data = response.json()
        dates = data['leagueSchedule']['gameDates']
    except:
        return None

    nba_teams = nba_static_teams.get_teams()
    team_map = {t['abbreviation']: t['id'] for t in nba_teams}
    id1 = team_map.get(t1_abv)
    id2 = team_map.get(t2_abv)
    if not id1 or not id2:
        return None

    today = datetime.now().date()
    for day in dates:
        try:
            game_dt = datetime.strptime(day['gameDate'], "%m/%d/%Y %H:%M:%S").date()
            if game_dt < today:
                continue
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
        except:
            continue
    return None

def obtener_partidos():
    from nba_api.stats.endpoints import scoreboardv2
    from nba_api.stats.static import teams as nba_static_teams
    from utils import get_basketball_date, convertir_hora_espanol
    
    nba_teams = nba_static_teams.get_teams()
    team_map = {t['id']: t['abbreviation'] for t in nba_teams}

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

                    fecha_juego_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
                    hora_esp = status_text

                    if "ET" in status_text:
                        try:
                            hora_clean = status_text.replace(" ET", "").strip()
                            dt_us = datetime.strptime(f"{fecha_str} {hora_clean}", "%Y-%m-%d %I:%M %p")
                            dt_es = dt_us + timedelta(hours=6)
                            fecha_juego_dt = dt_es
                            hora_esp = dt_es.strftime("%H:%M")
                        except:
                            pass
                    elif "Final" in status_text:
                        hora_esp = "FINALIZADO"

                    label_real = fecha_juego_dt.strftime("%d/%m")

                    if label_real not in agenda:
                        agenda[label_real] = []

                    agenda[label_real].append({
                        'game_id': game['GAME_ID'],
                        'v_abv': team_map.get(v_id),
                        'h_abv': team_map.get(h_id),
                        'v_logo': f"https://cdn.nba.com/logos/nba/{v_id}/global/L/logo.svg",
                        'h_logo': f"https://cdn.nba.com/logos/nba/{h_id}/global/L/logo.svg",
                        'time': hora_esp
                    })
        except:
            pass

    keys_ordenadas = sorted(agenda.keys(), key=lambda x: datetime.strptime(x, "%d/%m").replace(year=datetime.now().year))
    agenda_ordenada = {k: agenda[k] for k in keys_ordenadas}
    return agenda_ordenada

@st.cache_data(ttl=21600)
def get_injuries():
    """
    Scrapea lesiones desde CBSSports
    """
    url = "https://www.cbssports.com/nba/injuries/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        injuries = []
        
        # Mapeo simple de equipos
        team_map = {
            'Hawks': 'ATL', 'Celtics': 'BOS', 'Nets': 'BKN', 'Hornets': 'CHA',
            'Bulls': 'CHI', 'Cavaliers': 'CLE', 'Mavericks': 'DAL', 'Nuggets': 'DEN',
            'Pistons': 'DET', 'Warriors': 'GSW', 'Rockets': 'HOU', 'Pacers': 'IND',
            'Clippers': 'LAC', 'Lakers': 'LAL', 'Grizzlies': 'MEM', 'Heat': 'MIA',
            'Bucks': 'MIL', 'Timberwolves': 'MIN', 'Pelicans': 'NOP', 'Knicks': 'NYK',
            'Thunder': 'OKC', 'Magic': 'ORL', '76ers': 'PHI', 'Suns': 'PHX',
            'Blazers': 'POR', 'Kings': 'SAC', 'Spurs': 'SAS', 'Raptors': 'TOR',
            'Jazz': 'UTA', 'Wizards': 'WAS'
        }
        
        # Buscar tablas
        tables = soup.find_all('table', class_='TableBase-table')
        
        for table in tables:
            team_header = table.find_previous('h4')
            if team_header:
                team_text = team_header.text.strip()
                # Extraer nombre del equipo
                for team_name, abbr in team_map.items():
                    if team_name in team_text:
                        team_abbr = abbr
                        break
                else:
                    continue
                
                rows = table.find_all('tr')[1:]
                for row in rows:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        player = cols[0].text.strip().split('\n')[0]
                        status = cols[2].text.strip() if len(cols) > 2 else ""
                        date = cols[3].text.strip() if len(cols) > 3 else ""
                        
                        if player and status:
                            injuries.append({
                                'player': player,
                                'team': team_abbr,
                                'status': f"{status} - {date}" if date else status
                            })
        
        return injuries
        
    except Exception as e:
        print(f"Error: {e}")
        return []
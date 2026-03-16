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
    seen_game_ids = set()

    for fecha in fechas_us:
        fecha_str = fecha.strftime('%Y-%m-%d')
        try:
            board = scoreboardv2.ScoreboardV2(game_date=fecha_str)
            games = board.game_header.get_data_frame()

            if not games.empty:
                for _, game in games.iterrows():
                    h_id, v_id = game['HOME_TEAM_ID'], game['VISITOR_TEAM_ID']
                    status_text = game['GAME_STATUS_TEXT']
                    game_id = game['GAME_ID']

                    # Evitar duplicados: si ya hemos añadido este GAME_ID, lo saltamos
                    if game_id in seen_game_ids:
                        continue

                    fecha_juego_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
                    hora_esp = status_text

                    if "ET" in status_text:
                        try:
                            hora_clean = status_text.replace(" ET", "").strip()
                            dt_us = datetime.strptime(f"{fecha_str} {hora_clean}", "%Y-%m-%d %I:%M %p")
                            # Ajuste horario: ET+5 para España
                            dt_es = dt_us + timedelta(hours=5)
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
                        'game_id': game_id,
                        'v_abv': team_map.get(v_id),
                        'h_abv': team_map.get(h_id),
                        'v_logo': f"https://cdn.nba.com/logos/nba/{v_id}/global/L/logo.svg",
                        'h_logo': f"https://cdn.nba.com/logos/nba/{h_id}/global/L/logo.svg",
                        'time': hora_esp
                    })
                    seen_game_ids.add(game_id)
        except:
            pass

    keys_ordenadas = sorted(agenda.keys(), key=lambda x: datetime.strptime(x, "%d/%m").replace(year=datetime.now().year))
    agenda_ordenada = {k: agenda[k] for k in keys_ordenadas}
    return agenda_ordenada

@st.cache_data(ttl=21600)
def get_injuries():
    """
    Scrapea lesiones desde CBSSports (más confiable que ESPN)
    """
    url = "https://www.cbssports.com/nba/injuries/"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        response = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        
        injuries = []
        
        # Mapeo de equipos (CBSSports usa nombres completos)
        team_map = {
            'Atlanta': 'ATL', 'Boston': 'BOS', 'Brooklyn': 'BKN', 'Charlotte': 'CHA',
            'Chicago': 'CHI', 'Cleveland': 'CLE', 'Dallas': 'DAL', 'Denver': 'DEN',
            'Detroit': 'DET', 'Golden State': 'GSW', 'Houston': 'HOU', 'Indiana': 'IND',
            'LA Clippers': 'LAC', 'LA Lakers': 'LAL', 'Memphis': 'MEM', 'Miami': 'MIA',
            'Milwaukee': 'MIL', 'Minnesota': 'MIN', 'New Orleans': 'NOP', 'New York': 'NYK',
            'Oklahoma City': 'OKC', 'Orlando': 'ORL', 'Philadelphia': 'PHI', 'Phoenix': 'PHX',
            'Portland': 'POR', 'Sacramento': 'SAC', 'San Antonio': 'SAS', 'Toronto': 'TOR',
            'Utah': 'UTA', 'Washington': 'WAS'
        }
        
        # CBSSports tiene las tablas con clase 'TableBase-table'
        tables = soup.find_all('table', class_='TableBase-table')
        
        for table in tables:
            # Buscar el nombre del equipo en el encabezado
            team_header = table.find_previous('h4')
            if not team_header:
                continue
                
            team_text = team_header.text.strip()
            # Extraer solo el nombre del equipo (ej: "Dallas Mavericks" -> "Dallas")
            team_city = team_text.split()[0]
            team_abbr = team_map.get(team_city, team_city[:3].upper())
            
            # Procesar filas
            rows = table.find_all('tr')[1:]  # Saltar cabecera
            for row in rows:
                cols = row.find_all('td')
                if len(cols) >= 4:
                    # FIX: Extraer solo el nombre limpio del enlace
                    enlace_nombre = cols[0].find('a')
                    if enlace_nombre:
                        player = enlace_nombre.text.strip()
                    else:
                        player = cols[0].text.strip() # Backup por si no hay enlace
                    
                    position = cols[1].text.strip()
                    status = cols[2].text.strip()
                    date = cols[3].text.strip()
                    
                    injuries.append({
                        'player': player,
                        'team': team_abbr,
                        'status': f"{status} - {date}",
                        'date': date,
                        'position': position
                    })
        
        # Si no encuentra nada con el método anterior, intentar búsqueda más general
        if not injuries:
            # Buscar todas las filas que contengan información de jugadores
            all_rows = soup.find_all('tr')
            current_team = None
            
            for row in all_rows:
                # Intentar identificar encabezados de equipo
                team_header = row.find('h4')
                if team_header:
                    team_text = team_header.text.strip()
                    team_city = team_text.split()[0]
                    current_team = team_map.get(team_city, team_city[:3].upper())
                    continue
                
                # Si tenemos un equipo y la fila tiene celdas, es un jugador
                if current_team:
                    cols = row.find_all('td')
                    if len(cols) >= 3:
                        player = cols[0].text.strip()
                        status = cols[1].text.strip()
                        date = cols[2].text.strip() if len(cols) > 2 else ""
                        
                        if player and status and len(player) > 1:
                            injuries.append({
                                'player': player,
                                'team': current_team,
                                'status': status,
                                'date': date
                            })
        
        return injuries
        
    except Exception as e:
        print(f"Error scraping CBSSports: {e}")
        # Si falla CBSSports, intentar con otra fuente (ESPN como backup)
        try:
            # Backup: ESPN
            espn_url = "https://www.espn.com/nba/injuries"
            response = requests.get(espn_url, headers=headers, timeout=10)
            soup = BeautifulSoup(response.text, 'html.parser')
            
            injuries = []
            tables = soup.find_all('table')
            
            for table in tables:
                team_header = table.find_previous('h2')
                if team_header:
                    team_text = team_header.text.strip()
                    team_map_espn = {
                        'Atlanta Hawks': 'ATL', 'Boston Celtics': 'BOS', 'Brooklyn Nets': 'BKN',
                        'Charlotte Hornets': 'CHA', 'Chicago Bulls': 'CHI', 'Cleveland Cavaliers': 'CLE',
                        'Dallas Mavericks': 'DAL', 'Denver Nuggets': 'DEN', 'Detroit Pistons': 'DET',
                        'Golden State Warriors': 'GSW', 'Houston Rockets': 'HOU', 'Indiana Pacers': 'IND',
                        'LA Clippers': 'LAC', 'Los Angeles Lakers': 'LAL', 'Memphis Grizzlies': 'MEM',
                        'Miami Heat': 'MIA', 'Milwaukee Bucks': 'MIL', 'Minnesota Timberwolves': 'MIN',
                        'New Orleans Pelicans': 'NOP', 'New York Knicks': 'NYK', 'Oklahoma City Thunder': 'OKC',
                        'Orlando Magic': 'ORL', 'Philadelphia 76ers': 'PHI', 'Phoenix Suns': 'PHX',
                        'Portland Trail Blazers': 'POR', 'Sacramento Kings': 'SAC', 'San Antonio Spurs': 'SAS',
                        'Toronto Raptors': 'TOR', 'Utah Jazz': 'UTA', 'Washington Wizards': 'WAS'
                    }
                    team_abbr = team_map_espn.get(team_text, '')
                    
                    rows = table.find_all('tr')[1:]
                    for row in rows:
                        cols = row.find_all('td')
                        if len(cols) >= 3:
                            injuries.append({
                                'player': cols[0].text.strip(),
                                'team': team_abbr,
                                'status': cols[1].text.strip(),
                                'date': cols[2].text.strip()
                            })
            return injuries
        except:
            return []

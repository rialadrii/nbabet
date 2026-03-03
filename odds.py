import streamlit as st
import requests
import json
import os
from datetime import datetime
import backoff

ODDS_CACHE_FILE = "odds_cache.json"

@backoff.on_exception(backoff.expo, requests.exceptions.RequestException, max_tries=3)
def get_sports_odds(api_key, market_key):
    """Obtiene cuotas de TheOddsAPI con manejo de errores y regiones adecuadas."""
    region = 'eu' if market_key != 'player_points' else 'us'
    try:
        odds_response = requests.get(
            f'https://api.the-odds-api.com/v4/sports/basketball_nba/odds',
            params={
                'api_key': api_key,
                'regions': region,
                'markets': market_key,
                'oddsFormat': 'decimal',
                'dateFormat': 'iso',
            },
            timeout=10
        )
        if odds_response.status_code != 200:
            if odds_response.status_code == 422:
                return None, "Error 422: Tu plan gratuito no soporta este mercado o región. Prueba 'Ganador Partido'."
            return None, f"Error API: {odds_response.status_code}"
        return odds_response.json(), None
    except requests.exceptions.Timeout:
        return None, "Timeout: la API tardó demasiado en responder."
    except Exception as e:
        return None, str(e)

def save_cache(data, market_type):
    """Guarda los datos de cuotas en caché con timestamp."""
    cache = {
        "timestamp": datetime.now().strftime("%d/%m/%Y %H:%M:%S"),
        "market": market_type,
        "data": data
    }
    with open(ODDS_CACHE_FILE, 'w') as f:
        json.dump(cache, f)

def load_cache():
    """Carga la caché de cuotas si existe."""
    if os.path.exists(ODDS_CACHE_FILE):
        try:
            with open(ODDS_CACHE_FILE, 'r') as f:
                return json.load(f)
        except:
            return None
    return None

def detect_value_odds(odds_data, market_key='h2h', threshold=0.10):
    """
    Detecta cuotas con valor (por encima de la media del mercado en más de un threshold%).
    Retorna una lista de dicts con la información.
    """
    if market_key != 'h2h':
        return []

    value_odds = []
    for game in odds_data:
        home = game['home_team']
        away = game['away_team']
        bookmakers = game.get('bookmakers', [])
        all_home = []
        all_away = []
        for bm in bookmakers:
            markets = bm.get('markets', [])
            if not markets:
                continue
            outcomes = markets[0].get('outcomes', [])
            o_h = next((x for x in outcomes if x['name'] == home), None)
            o_a = next((x for x in outcomes if x['name'] == away), None)
            if o_h and o_a:
                all_home.append({'bookmaker': bm['title'], 'price': o_h['price']})
                all_away.append({'bookmaker': bm['title'], 'price': o_a['price']})
        if all_home:
            avg_home = sum(x['price'] for x in all_home) / len(all_home)
            for item in all_home:
                if item['price'] > avg_home * (1 + threshold):
                    value_odds.append({
                        'game': f"{away} @ {home}",
                        'team': home,
                        'bookmaker': item['bookmaker'],
                        'price': item['price'],
                        'avg': round(avg_home, 2),
                        'over_percent': round((item['price'] - avg_home) / avg_home * 100, 1)
                    })
        if all_away:
            avg_away = sum(x['price'] for x in all_away) / len(all_away)
            for item in all_away:
                if item['price'] > avg_away * (1 + threshold):
                    value_odds.append({
                        'game': f"{away} @ {home}",
                        'team': away,
                        'bookmaker': item['bookmaker'],
                        'price': item['price'],
                        'avg': round(avg_away, 2),
                        'over_percent': round((item['price'] - avg_away) / avg_away * 100, 1)
                    })
    return value_odds
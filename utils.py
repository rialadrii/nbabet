from datetime import datetime, timedelta
import streamlit as st
import requests
import time

def convertir_hora_espanol(hora_et):
    """Convierte hora ET a hora española. Ajustado a ET+5 para evitar desfase de 1h."""
    if "Final" in hora_et:
        return "FINALIZADO"
    try:
        hora_clean = hora_et.replace(" ET", "").strip()
        dt = datetime.strptime(hora_clean, "%I:%M %p")
        # Horario España habitual: ET+5 (corrige el desfase de 1h reportado)
        dt_spain = dt + timedelta(hours=5)
        return dt_spain.strftime("%H:%M")
    except:
        return hora_et

def get_basketball_date():
    """Obtiene la fecha 'baloncestística' (si es antes de las 12, se considera día anterior)."""
    now = datetime.now()
    if now.hour < 12:
        return now.date() - timedelta(days=1)
    return now.date()

def safe_request(url, timeout=5, retries=3):
    """Realiza una petición GET con reintentos y backoff exponencial."""
    for i in range(retries):
        try:
            response = requests.get(url, timeout=timeout)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if i == retries - 1:
                raise e
            time.sleep(2 ** i)
    return None
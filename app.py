# Busca la función obtener_partidos y reemplázala por esta:
def obtener_partidos():
    nba_teams = nba_static_teams.get_teams()
    team_map = {t['id']: t['abbreviation'] for t in nba_teams}
    
    # Pedimos datos de HOY y MAÑANA (Horario US)
    # A veces un partido de "pasado mañana" en España es "mañana" en EEUU
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
                    status_text = game['GAME_STATUS_TEXT'] # Ej: "7:00 pm ET" o "Final"
                    
                    # --- LÓGICA DE CONVERSIÓN DE FECHA ---
                    # Asumimos fecha base la de la API (US)
                    fecha_juego_dt = datetime.strptime(fecha_str, "%Y-%m-%d")
                    hora_esp = status_text # Por defecto
                    
                    # Intentamos parsear la hora para sumar las 6 horas y ver si cambia de día
                    if "ET" in status_text:
                        try:
                            hora_clean = status_text.replace(" ET", "").strip()
                            # Creamos objeto datetime completo (Fecha US + Hora US)
                            dt_us = datetime.strptime(f"{fecha_str} {hora_clean}", "%Y-%m-%d %I:%M %p")
                            # Sumamos 6 horas para pasar a hora España
                            dt_es = dt_us + timedelta(hours=6)
                            
                            # Actualizamos la fecha y la hora formateada
                            fecha_juego_dt = dt_es
                            hora_esp = dt_es.strftime("%H:%M")
                        except:
                            pass # Si falla, se queda con la fecha original
                    elif "Final" in status_text:
                        hora_esp = "FINALIZADO"
                        # Si ya acabó, generalmente pertenece al día siguiente en España si fue nocturno,
                        # pero para análisis a posteriori no es tan crítico. Lo dejamos en su fecha base
                        # o podrías sumar 1 día si prefieres.
                    
                    # Generamos la etiqueta REAL (Ej: "21/01") basada en la hora sumada
                    label_real = fecha_juego_dt.strftime("%d/%m")
                    
                    if label_real not in agenda:
                        agenda[label_real] = []
                        
                    agenda[label_real].append({
                        'game_id': game['GAME_ID'],
                        'v_abv': team_map.get(v_id), 'h_abv': team_map.get(h_id),
                        'v_logo': f"https://cdn.nba.com/logos/nba/{v_id}/global/L/logo.svg",
                        'h_logo': f"https://cdn.nba.com/logos/nba/{h_id}/global/L/logo.svg",
                        'time': hora_esp
                    })
        except: pass
        
    # Ordenamos las fechas para que salgan cronológicas en la agenda
    # (Esto devuelve un diccionario ordenado si usas Python 3.7+)
    keys_ordenadas = sorted(agenda.keys(), key=lambda x: datetime.strptime(x, "%d/%m").replace(year=datetime.now().year))
    agenda_ordenada = {k: agenda[k] for k in keys_ordenadas}
    
    return agenda_ordenada

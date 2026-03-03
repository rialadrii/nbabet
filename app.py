import streamlit as st
import pandas as pd
import os
from datetime import datetime, timedelta
import plotly.express as px

# Importar módulos propios
from data import load_data, download_data, get_team_roster_numbers, get_next_matchup_info, query_player_stats, get_injuries
from odds import get_sports_odds, save_cache, load_cache, detect_value_odds
from ui import mostrar_leyenda_colores, mostrar_tabla_bonita, render_clickable_player_table
from utils import convertir_hora_espanol, get_basketball_date, safe_request

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA
# ==========================================
st.set_page_config(
    page_title="NBA Analyzer Pro",
    page_icon="🏀",
    layout="wide"
)

# ==========================================
# 2. CSS DEFINITIVO
# ==========================================
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Teko:wght@300..700&display=swap');

.main .block-container {
    max-width: 1300px !important;
    padding-left: 0.5rem !important;
    padding-right: 0.5rem !important;
    margin: 0 auto !important;
}

h1, h2, h3, h4, p {
    text-align: center !important;
    width: 100% !important;
}

label, span {
    text-align: inherit;
}

[data-testid="stHeaderAction"] { display: none !important; }
h1 a, h2 a, h3 a, h4 a, h5 a, h6 a { display: none !important; color: transparent !important; pointer-events: none !important; }
.css-10trblm, .css-16idsys, a.anchor-link { display: none !important; }

[data-testid="stDataFrame"] { width: 100% !important; max-width: 100% !important; margin: 0 auto !important; }
.table-responsive { display: flex !important; justify-content: center !important; width: 100% !important; overflow-x: auto; margin-bottom: 1rem; }

table.custom-table { margin: 0 auto !important; border-collapse: collapse; font-size: 14px; min-width: 350px; width: 100%; }
table.custom-table th { background-color: #31333F; color: white; text-align: center !important; padding: 8px; border-bottom: 2px solid #555; }
table.custom-table td { text-align: center !important; padding: 6px; border-bottom: 1px solid #444; color: white; }

h1 { font-family: 'Teko', sans-serif !important; font-size: 55px !important; text-transform: uppercase; color: white; margin-bottom: 20px; }
h3 { font-family: 'Teko', sans-serif !important; font-size: 28px !important; text-transform: uppercase; color: #ffbd45; margin-top: 30px; }

.game-card { background-color: #2d2d2d; border: 1px solid #444; border-radius: 8px; padding: 15px; margin-bottom: 15px; width: 100%; text-align: center; }
.game-matchup { display: flex; justify-content: center; align-items: center; gap: 10px; margin-bottom: 5px; }
.team-logo { width: 45px; height: 45px; object-fit: contain; }
.game-time { color: #ffbd45; font-size: 22px; font-family: 'Teko', sans-serif; }

div.stButton > button { width: 100%; border-radius: 8px !important; font-weight: bold; background-color: #1e1e1e; color: #fff; border: 1px solid #444; transition: all 0.2s; }
div.stButton > button:hover { border-color: #ffbd45; color: #ffbd45; }

.parlay-box { background-color: #1e1e1e; border: 1px solid #444; border-radius: 10px; padding: 10px; margin-bottom: 15px; }
.parlay-header { font-size: 18px; font-weight: bold; margin-bottom: 10px; border-bottom: 1px solid #444; padding-bottom: 5px; text-align: center !important; color: white; }
.parlay-leg { background-color: #2d2d2d; margin: 5px 0; padding: 8px; border-radius: 6px; display: flex; justify-content: space-between; align-items: center; color: white; }

.dnp-missing { color: #ff5252; font-weight:bold; }
.dnp-full { color: #4caf50; font-weight:bold; }
.pat-stars { color: #ff5252; font-weight: bold; }
.pat-impact { color: #4caf50; }

.odds-info { background-color: #263238; border: 1px solid #37474f; border-radius: 5px; padding: 10px; margin-bottom: 15px; text-align: center; color: #eceff1; }
.odds-timestamp { color: #ffbd45; font-weight: bold; font-size: 18px; }

[data-testid="stElementToolbar"] { display: none !important; }
footer { display: none !important; }

[data-testid="stCheckbox"] {
    display: flex;
    justify-content: center; 
    width: 100%;
}
</style>
""", unsafe_allow_html=True)

# ==========================================
# 3. GESTIÓN DE ESTADO
# ==========================================
API_KEY_DEFAULT = os.getenv("ODDS_API_KEY", "ae1dd866651d5f06c234f972b0004084")

if 'page' not in st.session_state:
    st.session_state.page = "🏠 Inicio"
if 'selected_home' not in st.session_state:
    st.session_state.selected_home = None
if 'selected_visitor' not in st.session_state:
    st.session_state.selected_visitor = None
if 'selected_player' not in st.session_state:
    st.session_state.selected_player = None
if 'odds_api_key' not in st.session_state:
    st.session_state.odds_api_key = API_KEY_DEFAULT
if 'selected_parlay_legs' not in st.session_state:
    st.session_state.selected_parlay_legs = []

def navegar_a_partido(home, visitor):
    st.session_state.selected_home = home
    st.session_state.selected_visitor = visitor
    st.session_state.page = "⚔️ Analizar Partido"

def navegar_a_jugador(player_name):
    st.session_state.selected_player = player_name
    st.session_state.page = "👤 Jugador"

def volver_inicio():
    st.session_state.page = "🏠 Inicio"

def volver_a_partido():
    st.session_state.page = "⚔️ Analizar Partido"

# ==========================================
# 4. CARGA DE DATOS (CON ACTUALIZACIÓN AUTOMÁTICA)
# ==========================================
df = load_data()
if not df.empty:
    last_date = df['game_date'].max()
    if last_date.date() < datetime.now().date() - timedelta(days=1):
        with st.spinner("Actualizando datos automáticamente..."):
            if download_data():
                st.cache_data.clear()
                st.rerun()

latest_teams_map = {}
if not df.empty:
    latest_entries = df.sort_values('game_date').drop_duplicates('player_name', keep='last')
    latest_teams_map = dict(zip(latest_entries['player_name'], latest_entries['team_abbreviation']))

# ==========================================
# 5. MENÚ PRINCIPAL
# ==========================================
st.markdown("<h1>🏀 NBA PRO ANALYZER 🏀</h1>", unsafe_allow_html=True)

pages = ["🏠 Inicio", "👤 Jugador", "⚔️ Analizar Partido", "💰 Buscador de Cuotas", "🔄 Actualizar Datos"]
if st.session_state.page not in pages:
    st.session_state.page = "🏠 Inicio"
current_index = pages.index(st.session_state.page)
opcion = st.sidebar.radio("Menú:", pages, index=current_index)

if opcion != st.session_state.page:
    st.session_state.page = opcion
    st.rerun()

# ==========================================
# 6. PÁGINAS
# ==========================================

# --- PÁGINA INICIO ---
if st.session_state.page == "🏠 Inicio":
    from data import obtener_partidos
    agenda = obtener_partidos()
    fechas_disponibles = list(agenda.keys())
    titulo_col1 = fechas_disponibles[0] if len(fechas_disponibles) > 0 else "HOY"
    titulo_col2 = fechas_disponibles[1] if len(fechas_disponibles) > 1 else "MAÑANA"

    c1, c2 = st.columns(2)

    def render_block(col, title, games, color):
        with col:
            st.markdown(f"<h3 style='color:{color}; text-align: center;'>{title}</h3>", unsafe_allow_html=True)
            if not games:
                st.caption("No hay partidos programados.")
                return

            for i, g in enumerate(games):
                st.markdown(f"""
                <div class='game-card'>
                    <div class='game-matchup'>
                        <img src='{g['v_logo']}' class='team-logo'> <span class='vs-text'>@</span> <img src='{g['h_logo']}' class='team-logo'>
                    </div>
                    <div style='color:white; font-weight:bold;'>{g['v_abv']} vs {g['h_abv']}</div>
                    <div class='game-time'>{g['time']}</div>
                </div>
                """, unsafe_allow_html=True)

                unique_key = f"btn_{title}_{g['game_id']}_{i}"
                if st.button(f"🔍 ANALIZAR {g['v_abv']} vs {g['h_abv']}", key=unique_key):
                    navegar_a_partido(g['h_abv'], g['v_abv'])
                    st.rerun()

                st.write("")

    render_block(c1, titulo_col1, agenda.get(titulo_col1, []), "#4caf50")
    render_block(c2, titulo_col2, agenda.get(titulo_col2, []), "#2196f3")

    st.markdown("<div class='credits'>Creado por ad.ri.</div>", unsafe_allow_html=True)

# --- PÁGINA ACTUALIZAR DATOS ---
elif st.session_state.page == "🔄 Actualizar Datos":
    st.write("### 🔄 Sincronización")
    st.caption("Selecciona las temporadas que quieres incluir en la base de datos.")
    temporadas_disponibles = ['2023-24', '2024-25', '2025-26']
    seleccionadas = st.multiselect("Temporadas", temporadas_disponibles, default=['2024-25', '2025-26'])

    if st.button("Descargar y Actualizar Ahora"):
        with st.spinner("Conectando con servidores NBA..."):
            success = download_data(seasons=seleccionadas)
            if success:
                st.success("¡Datos actualizados con Triples!")
                st.cache_data.clear()
                st.rerun()

# --- PÁGINA JUGADOR ---
elif st.session_state.page == "👤 Jugador":
    c_back, c_title, c_dummy = st.columns([1, 10, 1])
    with c_back:
        st.write("")
        if st.session_state.selected_home and st.session_state.selected_visitor:
            if st.button(f"⬅️ Volver"):
                volver_a_partido()
                st.rerun()
    with c_title:
        st.markdown("<h2 style='text-align: center; margin-top: 0; padding-top: 0;'>👤 Buscador de Jugadores</h2>", unsafe_allow_html=True)
    with c_dummy:
        st.write("")

    if df.empty:
        st.error("Primero actualiza los datos.")
    else:
        todos_jugadores = sorted(df['player_name'].unique())
        todos_equipos = sorted(df['team_abbreviation'].unique())
        idx_sel = todos_jugadores.index(st.session_state.selected_player) if st.session_state.selected_player in todos_jugadores else None
        jugador = st.selectbox("Nombre del Jugador:", todos_jugadores, index=idx_sel)

        if jugador and jugador != st.session_state.selected_player:
            st.session_state.selected_player = jugador

        if jugador:
            player_data = query_player_stats(player_name=jugador).sort_values('game_date', ascending=False)

            rival = st.selectbox("Filtrar vs Rival (Opcional):", todos_equipos, index=None)

            mean_pts = player_data['pts'].mean()
            mean_reb = player_data['reb'].mean()
            mean_ast = player_data['ast'].mean()
            mean_3pm = player_data['fg3m'].mean()
            mean_min = player_data['min'].mean()

            means_dict = {'PTS': mean_pts, 'REB': mean_reb, 'AST': mean_ast, '3PM': mean_3pm, 'MIN': mean_min}

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("PTS", f"{mean_pts:.1f}")
            c2.metric("REB", f"{mean_reb:.1f}")
            c3.metric("AST", f"{mean_ast:.1f}")
            c4.metric("3PM", f"{mean_3pm:.1f}")
            c5.metric("MIN", f"{mean_min:.1f}")

            # GRÁFICO DE BARRAS - Últimos 10 partidos
            st.subheader("📊 Comparativa últimos 10 partidos (barras)")
            player_data_sorted = player_data.sort_values('game_date').tail(10)
            if not player_data_sorted.empty and len(player_data_sorted) > 1:
                # Preparar datos para gráfico de barras
                df_chart = player_data_sorted.copy()
                df_chart['fecha_corta'] = df_chart['game_date'].dt.strftime('%d/%m')
                
                fig = px.bar(df_chart, x='fecha_corta', y=['pts', 'reb', 'ast'],
                             title=f'Estadísticas de {jugador} - Últimos 10 partidos',
                             labels={'value': 'Valor', 'variable': 'Estadística', 'fecha_corta': 'Fecha'},
                             barmode='group')
                fig.update_layout(legend_title_text='Estadística')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("No hay suficientes datos para mostrar gráfico")

            st.subheader("Últimos 5 Partidos")
            cols = ['game_date', 'wl', 'matchup', 'min', 'pts', 'reb', 'ast', 'fg3m']
            if 'game_id' in player_data.columns:
                cols.append('game_id')
            view = player_data[cols].head(5).copy()
            view['min'] = view['min'].astype(int)
            view['RES'] = view['wl'].map({'W': '✅', 'L': '❌'})

            if 'game_id' in view.columns:
                view['FICHA'] = view['game_id'].apply(lambda x: f"<a href='https://www.nba.com/game/{x}' target='_blank' class='match-link'>📊</a>" if pd.notnull(x) else "-")
                view = view.drop(columns=['game_id'])
                view = view[['game_date', 'RES', 'matchup', 'FICHA', 'min', 'pts', 'reb', 'ast', 'fg3m']]
            else:
                view['FICHA'] = "-"

            view.columns = ['FECHA', 'RES', 'PARTIDO', 'FICHA', 'MIN', 'PTS', 'REB', 'AST', '3PM']
            view['FECHA'] = view['FECHA'].dt.strftime('%d/%m')

            mostrar_tabla_bonita(view, None, means_dict=means_dict)
            mostrar_leyenda_colores()

            csv = view.to_csv(index=False).encode('utf-8')
            st.download_button("📥 Descargar CSV", data=csv, file_name=f"{jugador}_ultimos.csv", mime="text/csv")

            if rival:
                st.subheader(f"Historial vs {rival}")
                h2h = player_data[player_data['matchup'].str.contains(rival, case=False)]
                if not h2h.empty:
                    view_h2h = h2h[cols].copy()
                    view_h2h['min'] = view_h2h['min'].astype(int)
                    view_h2h['RES'] = view_h2h['wl'].map({'W': '✅', 'L': '❌'})
                    if 'game_id' in view_h2h.columns:
                        view_h2h['FICHA'] = view_h2h['game_id'].apply(lambda x: f"<a href='https://www.nba.com/game/{x}' target='_blank' class='match-link'>📊</a>" if pd.notnull(x) else "-")
                        view_h2h = view_h2h.drop(columns=['game_id'])
                        view_h2h = view_h2h[['game_date', 'RES', 'matchup', 'FICHA', 'min', 'pts', 'reb', 'ast', 'fg3m']]
                    view_h2h.columns = ['FECHA', 'RES', 'PARTIDO', 'FICHA', 'MIN', 'PTS', 'REB', 'AST', '3PM']
                    view_h2h['FECHA'] = view_h2h['FECHA'].dt.strftime('%d/%m')
                    mostrar_tabla_bonita(view_h2h, None, means_dict=means_dict)
                    mostrar_leyenda_colores()
                else:
                    st.info(f"No hay registros recientes contra {rival}.")

            # COMPARATIVA CON OTRO JUGADOR
            st.write("---")
            st.subheader("🆚 Comparativa con otro jugador")
            todos_jugadores_list = sorted(df['player_name'].unique())
            otro_jugador = st.selectbox("Selecciona otro jugador", [""] + todos_jugadores_list, key="comparador")

            if otro_jugador and otro_jugador != jugador:
                df_j1 = player_data
                df_j2 = query_player_stats(player_name=otro_jugador)
                
                common_games = set(df_j1['game_id']).intersection(set(df_j2['game_id']))
                
                if common_games:
                    stats_j1 = df_j1[df_j1['game_id'].isin(common_games)][['pts', 'reb', 'ast']].mean()
                    stats_j2 = df_j2[df_j2['game_id'].isin(common_games)][['pts', 'reb', 'ast']].mean()
                    
                    comparativa = pd.DataFrame({
                        'Métrica': ['Puntos', 'Rebotes', 'Asistencias'],
                        jugador: [f"{stats_j1['pts']:.1f}", f"{stats_j1['reb']:.1f}", f"{stats_j1['ast']:.1f}"],
                        otro_jugador: [f"{stats_j2['pts']:.1f}", f"{stats_j2['reb']:.1f}", f"{stats_j2['ast']:.1f}"],
                        'Diferencia': [
                            f"{stats_j1['pts'] - stats_j2['pts']:+.1f}",
                            f"{stats_j1['reb'] - stats_j2['reb']:+.1f}",
                            f"{stats_j1['ast'] - stats_j2['ast']:+.1f}"
                        ]
                    })
                    
                    st.dataframe(comparativa, use_container_width=True, hide_index=True)
                    
                    fig = px.bar(comparativa, x='Métrica', y=[jugador, otro_jugador], 
                                 barmode='group', title=f'Comparativa: {jugador} vs {otro_jugador}')
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No hay partidos en común entre estos jugadores")

# --- PÁGINA CUOTAS ---
elif st.session_state.page == "💰 Buscador de Cuotas":
    st.header("💰 Buscador de Errores en Cuotas")
    st.caption("Compara Winamax, Bet365, Bwin y otras casas para encontrar errores de valoración.")

    api_key_input = st.text_input("API Key (Oculta):", value=st.session_state.odds_api_key, type="password")
    if api_key_input:
        st.session_state.odds_api_key = api_key_input

    tipo_mercado = st.selectbox("¿Qué quieres buscar?", ["Ganador Partido (H2H)", "Puntos de Jugador"])
    market_key = 'h2h' if tipo_mercado == "Ganador Partido (H2H)" else 'player_points'

    cached_file = load_cache()
    odds_data_to_show = None

    if cached_file:
        cache_time = cached_file.get('timestamp', 'Desconocido')
        cache_market = cached_file.get('market', '')
        if cache_market == market_key:
            st.markdown(f"""
            <div class='odds-info'>
                <div>📅 DATOS GUARDADOS DEL:</div>
                <div class='odds-timestamp'>{cache_time}</div>
                <div style='font-size:12px; margin-top:5px;'>(Tus amigos ven esto sin gastar cuota)</div>
            </div>
            """, unsafe_allow_html=True)
            odds_data_to_show = cached_file.get('data')
        else:
            st.info(f"Hay datos guardados de '{cache_market}', pero tú buscas '{market_key}'. Dale al botón para actualizar.")

    if st.button("🔄 Actualizar y Guardar (Gasta Cuota API)"):
        if not st.session_state.odds_api_key:
            st.error("Falta API Key.")
        else:
            with st.spinner(f"Escaneando casas de apuestas ({tipo_mercado})..."):
                odds_data, error = get_sports_odds(st.session_state.odds_api_key, market_key)
                if error:
                    st.error(error)
                elif not odds_data:
                    st.info("No hay datos disponibles ahora mismo.")
                else:
                    save_cache(odds_data, market_key)
                    odds_data_to_show = odds_data
                    st.rerun()

    if odds_data_to_show and market_key == 'h2h':
        value_alerts = detect_value_odds(odds_data_to_show, threshold=0.10)
        if value_alerts:
            st.subheader("🔔 Alertas de Valor (Cuotas >10% sobre la media)")
            df_alerts = pd.DataFrame(value_alerts)
            df_alerts.columns = ['Partido', 'Equipo', 'Casa', 'Cuota', 'Media', 'Sobre%']
            st.dataframe(df_alerts, use_container_width=True)

    if odds_data_to_show:
        if market_key == 'h2h':
            for game in odds_data_to_show:
                home, away = game['home_team'], game['away_team']
                bookmakers = game.get('bookmakers', [])
                if not bookmakers:
                    continue

                best_home, best_away = {'p': 0, 'b': ''}, {'p': 0, 'b': ''}
                worst_home, worst_away = {'p': 100, 'b': ''}, {'p': 100, 'b': ''}
                all_odds = []

                for bm in bookmakers:
                    markets = bm.get('markets', [])
                    if not markets:
                        continue
                    outcomes = markets[0].get('outcomes', [])
                    o_h = next((x for x in outcomes if x['name'] == home), None)
                    o_a = next((x for x in outcomes if x['name'] == away), None)
                    if o_h and o_a:
                        ph, pa = o_h['price'], o_a['price']
                        all_odds.append({'Casa': bm['title'], f'{home}': ph, f'{away}': pa})
                        if ph > best_home['p']:
                            best_home = {'p': ph, 'b': bm['title']}
                        if ph < worst_home['p']:
                            worst_home = {'p': ph, 'b': bm['title']}
                        if pa > best_away['p']:
                            best_away = {'p': pa, 'b': bm['title']}
                        if pa < worst_away['p']:
                            worst_away = {'p': pa, 'b': bm['title']}

                st.markdown(f"#### 🏀 {away} @ {home}")
                c1, c2 = st.columns(2)
                c1.success(f"🏠 {home}: Mejor {best_home['p']} ({best_home['b']})")
                c2.success(f"✈️ {away}: Mejor {best_away['p']} ({best_away['b']})")

                if st.checkbox(f"Ver lista completa {home} vs {away}"):
                    st.dataframe(pd.DataFrame(all_odds))
                st.divider()

        elif market_key == 'player_points':
            found = False
            for game in odds_data_to_show:
                bookmakers = game.get('bookmakers', [])
                if not bookmakers:
                    continue
                player_data_dict = {}
                for bm in bookmakers:
                    markets = bm.get('markets', [])
                    for m in markets:
                        if m['key'] == 'player_points':
                            for out in m['outcomes']:
                                p_name = out['description']
                                line = out.get('point')
                                side = out['name']
                                price = out['price']
                                if p_name not in player_data_dict:
                                    player_data_dict[p_name] = []
                                player_data_dict[p_name].append({'Casa': bm['title'], 'Linea': line, 'Tipo': side, 'Cuota': price})

                if player_data_dict:
                    found = True
                    st.markdown(f"#### 🏀 {game['away_team']} @ {game['home_team']}")
                    for p_name, odds_list in player_data_dict.items():
                        with st.container():
                            st.markdown(f"**👤 {p_name}**")
                            st.dataframe(pd.DataFrame(odds_list))
                    st.divider()

            if not found:
                st.warning("No hay datos de jugadores disponibles en este momento. Puede que el mercado esté cerrado.")

# --- PÁGINA ANALIZAR PARTIDO ---
elif st.session_state.page == "⚔️ Analizar Partido":
    c_back, c_title, c_dummy = st.columns([1, 10, 1])
    with c_back:
        st.write("")
        if st.button("⬅️ Volver", key="back_btn_matchup"):
            volver_inicio()
            st.rerun()
    with c_title:
        st.markdown("<h2 style='text-align: center; margin-top: 0; padding-top: 0;'>⚔️ Análisis de Choque</h2>", unsafe_allow_html=True)
    with c_dummy:
        st.write("")

    if df.empty:
        st.error("Datos no disponibles.")
    else:
        col1, col2 = st.columns(2)
        equipos = sorted(df['team_abbreviation'].unique())

        idx_t1 = equipos.index(st.session_state.selected_home) if st.session_state.selected_home in equipos else None
        idx_t2 = equipos.index(st.session_state.selected_visitor) if st.session_state.selected_visitor in equipos else None

        t1 = col1.selectbox("Local", equipos, index=idx_t1)
        t2 = col2.selectbox("Visitante", equipos, index=idx_t2)

        if t1 and t1 != st.session_state.selected_home:
            st.session_state.selected_home = t1
        if t2 and t2 != st.session_state.selected_visitor:
            st.session_state.selected_visitor = t2

        if t1 and t2:
            from nba_api.stats.static import teams as nba_static_teams
            nba_teams = nba_static_teams.get_teams()
            team_map_id = {t['abbreviation']: t['id'] for t in nba_teams}
            roster_t1, roster_t2 = {}, {}
            if t1 in team_map_id:
                roster_t1 = get_team_roster_numbers(team_map_id[t1])
            if t2 in team_map_id:
                roster_t2 = get_team_roster_numbers(team_map_id[t2])
            full_roster_map = {**roster_t1, **roster_t2}

            with st.spinner("Cargando..."):
                next_game = get_next_matchup_info(t1, t2)
            if next_game:
                link_btn = f"<a href='https://www.nba.com/game/{next_game['game_id']}' target='_blank' class='next-game-btn'>🏥 Ver Ficha</a>"
                st.markdown(f"""
                <div class='game-card'>
                    <div style='color:#ffbd45; font-size:18px;'>📅 PRÓXIMO ENFRENTAMIENTO</div>
                    <div style='color:white; font-size:16px; margin: 10px 0;'>
                        <b>{next_game['date']}</b> - {next_game['away']} @ {next_game['home']}
                    </div>
                    {link_btn}
                </div>
                """, unsafe_allow_html=True)

        # LESIONES - VERSIÓN CORREGIDA
        st.subheader("🏥 Lesiones reportadas")

        with st.spinner("Cargando partes médicos..."):
            injuries = get_injuries()

        if injuries:
            inj_t1 = [i for i in injuries if i.get('team') == t1]
            inj_t2 = [i for i in injuries if i.get('team') == t2]
            
            # Crear columnas
            col_i1, col_i2 = st.columns(2)
            
            with col_i1:
                st.markdown(f"### {t1}")
                if inj_t1:
                    for i in inj_t1:
                        # Formato más simple sin HTML complejo
                        player_name = i['player']
                        status_info = i['status']
                        st.markdown(f"- **{player_name}**: {status_info}")
                else:
                    st.info("✅ Sin lesionados")
            
            with col_i2:
                st.markdown(f"### {t2}")
                if inj_t2:
                    for i in inj_t2:
                        player_name = i['player']
                        status_info = i['status']
                        st.markdown(f"- **{player_name}**: {status_info}")
                else:
                    st.info("✅ Sin lesionados")
        else:
            st.error("❌ No se pudo conectar con la fuente de lesiones")

            mask = ((df['team_abbreviation'] == t1) & (df['matchup'].str.contains(t2))) | \
            ((df['team_abbreviation'] == t2) & (df['matchup'].str.contains(t1)))
            history = df[mask].sort_values('game_date', ascending=False)
            last_dates = sorted(history['game_date'].unique(), reverse=True)[:5]

            st.write("---")
            st.subheader("📅 Historial H2H")

            games_summary = []
            for date in last_dates:
                day_data = history[history['game_date'] == date]
                if day_data.empty:
                    continue
                row_t1 = day_data[day_data['team_abbreviation'] == t1]
                if not row_t1.empty:
                    wl_t1 = row_t1.iloc[0]['wl']
                    icon1 = '✅' if wl_t1 == 'W' else '❌'
                    icon2 = '❌' if wl_t1 == 'W' else '✅'
                else:
                    row_t2 = day_data[day_data['team_abbreviation'] == t2]
                    if not row_t2.empty:
                        wl_t2 = row_t2.iloc[0]['wl']
                        icon2 = '✅' if wl_t2 == 'W' else '❌'
                        icon1 = '❌' if wl_t2 == 'W' else '✅'
                    else:
                        icon1, icon2 = '', ''
                match_str = f"{t1} {icon1} vs {t2} {icon2}"
                row = day_data.iloc[0]
                g_id = row.get('game_id')
                link = f"<a href='https://www.nba.com/game/{g_id}' target='_blank' class='match-link'>📊</a>" if pd.notnull(g_id) else "-"
                games_summary.append({'FECHA': date.strftime('%d/%m'), 'ENFRENTAMIENTO': match_str, 'FICHA': link})

            df_games = pd.DataFrame(games_summary)
            if not df_games.empty:
                mostrar_tabla_bonita(df_games, None)

            team_totals = history.groupby(['game_date', 'team_abbreviation'])[['pts', 'reb', 'ast']].sum().reset_index()
            filtered_totals = team_totals[team_totals['team_abbreviation'].isin([t1, t2])].copy()
            if not filtered_totals.empty:
                st.subheader("📊 Comparativa H2H")
                game_stats = []
                unique_game_dates = filtered_totals['game_date'].unique()
                for d in sorted(unique_game_dates, reverse=True):
                    day_data = filtered_totals[filtered_totals['game_date'] == d]
                    if not day_data.empty:
                        row = {'FECHA': pd.to_datetime(d).strftime('%d/%m')}
                        t1_d = day_data[day_data['team_abbreviation'] == t1]
                        row[f'{t1} PTS'] = t1_d['pts'].values[0] if not t1_d.empty else 0
                        row[f'{t1} REB'] = t1_d['reb'].values[0] if not t1_d.empty else 0
                        row[f'{t1} AST'] = t1_d['ast'].values[0] if not t1_d.empty else 0
                        t2_d = day_data[day_data['team_abbreviation'] == t2]
                        row[f'{t2} PTS'] = t2_d['pts'].values[0] if not t2_d.empty else 0
                        row[f'{t2} REB'] = t2_d['reb'].values[0] if not t2_d.empty else 0
                        row[f'{t2} AST'] = t2_d['ast'].values[0] if not t2_d.empty else 0
                        game_stats.append(row)
                if game_stats:
                    df_comparative = pd.DataFrame(game_stats)
                    cols_ordered = ['FECHA', f'{t1} PTS', f'{t2} PTS', f'{t1} REB', f'{t2} REB', f'{t1} AST', f'{t2} AST']
                    final_cols = [c for c in cols_ordered if c in df_comparative.columns]
                    mostrar_tabla_bonita(df_comparative[final_cols], None, simple_mode=True)

            recent_players = history[history['game_date'].isin(last_dates)].sort_values('game_date', ascending=False)
            target_dates_str = [d.strftime('%Y-%m-%d') for d in last_dates]
            recent_players['date_str'] = recent_players['game_date'].dt.strftime('%Y-%m-%d')

            def get_aligned_trend(df_source, val_col):
                pivoted = df_source.pivot_table(
                    index=['player_name', 'team_abbreviation'],
                    columns='date_str',
                    values=val_col,
                    aggfunc='sum'
                )
                for d in target_dates_str:
                    if d not in pivoted.columns:
                        pivoted[d] = float('nan')
                pivoted = pivoted[target_dates_str]
                def formatter(row):
                    vals = []
                    for v in row:
                        if pd.isna(v) or v == 0:
                            vals.append("❌")
                        else:
                            vals.append(str(int(v)))
                    return "/".join(vals)
                return pivoted.apply(formatter, axis=1)

            base_stats = recent_players.groupby(['player_name', 'team_abbreviation']).agg(
                pts=('pts', 'mean'),
                reb=('reb', 'mean'),
                ast=('ast', 'mean'),
                gp=('game_date', 'count')
            )

            trend_pts = get_aligned_trend(recent_players, 'pts').rename('trend_pts')
            trend_reb = get_aligned_trend(recent_players, 'reb').rename('trend_reb')
            trend_ast = get_aligned_trend(recent_players, 'ast').rename('trend_ast')
            trend_min = get_aligned_trend(recent_players, 'min').rename('trend_min')

            stats = base_stats.join([trend_pts, trend_reb, trend_ast, trend_min]).reset_index()
            stats = stats[stats['player_name'].apply(lambda x: latest_teams_map.get(x) in [t1, t2])]

            st.write("---")
            st.subheader("🔥 Top Anotadores 👇")
            render_clickable_player_table(stats.sort_values('pts', ascending=False).head(10), 'PTS', full_roster_map, navegar_a_jugador)

            st.subheader("🔥 Top Reboteadores 👇")
            render_clickable_player_table(stats.sort_values('reb', ascending=False).head(10), 'REB', full_roster_map, navegar_a_jugador)

            st.subheader("🤝 Top Asistentes 👇")
            render_clickable_player_table(stats.sort_values('ast', ascending=False).head(10), 'AST', full_roster_map, navegar_a_jugador)

            # BAJAS (DNP) - CORREGIDO
            st.write("---")
            st.subheader("🏥 Historial de Bajas (Jugadores con >12 min promedio)")

            all_players_min = recent_players.groupby(['player_name', 'team_abbreviation'])['min'].mean().reset_index()
            key_players = all_players_min[all_players_min['min'] > 12.0].copy()
            key_players = key_players[key_players['team_abbreviation'].isin([t1, t2])]

            if not key_players.empty:
                dnp_data = []
                for date in last_dates[:5]:
                    date_str = date.strftime('%d/%m')
                    players_in_game = recent_players[recent_players['game_date'] == date]['player_name'].tolist()
                    
                    missing_t1 = []
                    missing_t2 = []
                    
                    for _, row in key_players.iterrows():
                        player = row['player_name']
                        team = row['team_abbreviation']
                        
                        team_played = not recent_players[(recent_players['game_date'] == date) & 
                                                        (recent_players['team_abbreviation'] == team)].empty
                        
                        if team_played and player not in players_in_game:
                            if team == t1:
                                missing_t1.append(player)
                            elif team == t2:
                                missing_t2.append(player)
                    
                    cell_t1 = f"<span class='dnp-missing'>{', '.join(missing_t1)}</span>" if missing_t1 else "<span class='dnp-full'>✓ Todos disponibles</span>"
                    cell_t2 = f"<span class='dnp-missing'>{', '.join(missing_t2)}</span>" if missing_t2 else "<span class='dnp-full'>✓ Todos disponibles</span>"
                    
                    dnp_data.append({
                        'FECHA': date_str,
                        f'BAJAS {t1}': cell_t1,
                        f'BAJAS {t2}': cell_t2
                    })
                
                if dnp_data:
                    df_dnp = pd.DataFrame(dnp_data)
                    mostrar_tabla_bonita(df_dnp, None)
                else:
                    st.success("✅ No hay bajas registradas en los últimos partidos")
            else:
                st.info("No hay suficientes datos de minutos para analizar bajas")

            # PATRONES
            st.write("---")
            st.subheader("🕵️ Patrones")
            global_means = df.groupby('player_name')[['pts', 'reb', 'ast']].mean()
            star_scorers = global_means[global_means['pts'] > 18].index.tolist()
            star_rebounders = global_means[global_means['reb'] > 7].index.tolist()
            star_assisters = global_means[global_means['ast'] > 5].index.tolist()
            all_stars = list(set(star_scorers + star_rebounders + star_assisters))
            patterns_data = []

            for date in last_dates:
                roster_day = recent_players[recent_players['game_date'] == date]
                players_present = roster_day['player_name'].unique()
                teams_active = roster_day['team_abbreviation'].unique()
                for team in teams_active:
                    missing_stars_today = []
                    for star in all_stars:
                        current_real_team = latest_teams_map.get(star, None)
                        if current_real_team == team and (star not in players_present):
                            missing_stars_today.append(star)
                    if missing_stars_today:
                        teammates = roster_day[roster_day['team_abbreviation'] == team]
                        beneficiaries = []
                        for _, row in teammates.iterrows():
                            p_name = row['player_name']
                            if latest_teams_map.get(p_name) != team:
                                continue
                            if p_name in global_means.index:
                                avg_p = global_means.loc[p_name]
                            else:
                                continue
                            diff_pts = row['pts'] - avg_p['pts']
                            diff_reb = row['reb'] - avg_p['reb']
                            diff_ast = row['ast'] - avg_p['ast']
                            impact_msgs = []
                            if any(s in star_scorers for s in missing_stars_today):
                                if row['pts'] >= 15 and diff_pts >= 8:
                                    impact_msgs.append(f"🏀+{int(diff_pts)}")
                            if any(s in star_rebounders for s in missing_stars_today):
                                if row['reb'] >= 7 and diff_reb >= 4:
                                    impact_msgs.append(f"🖐+{int(diff_reb)}")
                            if any(s in star_assisters for s in missing_stars_today):
                                if row['ast'] >= 5 and diff_ast >= 4:
                                    impact_msgs.append(f"🎁+{int(diff_ast)}")
                            if impact_msgs:
                                beneficiaries.append(f"<b>{p_name}</b> ({', '.join(impact_msgs)})")
                        if beneficiaries:
                            date_str = date.strftime('%d/%m')
                            missing_str = ", ".join(missing_stars_today)
                            impact_str = "<br>".join(beneficiaries)
                            patterns_data.append({'FECHA': date_str, 'EQUIPO': team, 'FALTA': f"<span class='pat-stars'>{missing_str}</span>", 'IMPACTO': f"<span class='pat-impact'>{impact_str}</span>"})
            if patterns_data:
                df_patterns = pd.DataFrame(patterns_data)
                mostrar_tabla_bonita(df_patterns, None)
            else:
                st.write("Sin impactos.")

            # PARLAY GENERATOR - CORREGIDO
            st.write("---")
            st.subheader("🎲 Generador de Parlays (selecciona piernas)")

            min_games_needed = max(3, int(len(last_dates) * 0.6))
            candidates = stats[stats['gp'] >= min_games_needed].copy()

            safe_legs_pts, safe_legs_reb, safe_legs_ast = [], [], []
            risky_legs_pts, risky_legs_reb, risky_legs_ast = [], [], []

            for _, row in candidates.iterrows():
                p_name, p_team = row['player_name'], row['team_abbreviation']
                logs = recent_players[(recent_players['player_name'] == p_name) & (recent_players['team_abbreviation'] == p_team)]
                if logs.empty:
                    continue
                
                pts_vals = sorted(logs['pts'].tolist())
                reb_vals = sorted(logs['reb'].tolist())
                ast_vals = sorted(logs['ast'].tolist())
                
                if len(pts_vals) >= 2:
                    safe_pts = pts_vals[1]
                    if safe_pts >= 10:
                        safe_legs_pts.append({'player': p_name, 'val': int(safe_pts), 'avg': row['pts'], 'type': 'PTS'})
                
                if len(reb_vals) >= 2:
                    safe_reb = reb_vals[1]
                    if safe_reb >= 5:
                        safe_legs_reb.append({'player': p_name, 'val': int(safe_reb), 'avg': row['reb'], 'type': 'REB'})
                
                if len(ast_vals) >= 2:
                    safe_ast = ast_vals[1]
                    if safe_ast >= 3:
                        safe_legs_ast.append({'player': p_name, 'val': int(safe_ast), 'avg': row['ast'], 'type': 'AST'})
                
                if row['pts'] >= 15:
                    risky_legs_pts.append({'player': p_name, 'val': int(row['pts']), 'avg': row['pts'], 'type': 'PTS'})
                if row['reb'] >= 7:
                    risky_legs_reb.append({'player': p_name, 'val': int(row['reb']), 'avg': row['reb'], 'type': 'REB'})
                if row['ast'] >= 5:
                    risky_legs_ast.append({'player': p_name, 'val': int(row['ast']), 'avg': row['ast'], 'type': 'AST'})

            safe_legs_pts.sort(key=lambda x: x['avg'], reverse=True)
            safe_legs_reb.sort(key=lambda x: x['avg'], reverse=True)
            safe_legs_ast.sort(key=lambda x: x['avg'], reverse=True)
            risky_legs_pts.sort(key=lambda x: x['avg'], reverse=True)
            risky_legs_reb.sort(key=lambda x: x['avg'], reverse=True)
            risky_legs_ast.sort(key=lambda x: x['avg'], reverse=True)

            def render_parlay_column(title, legs, color, icon, col):
                with col:
                    st.markdown(f"### {title}")
                    if not legs:
                        st.caption("Sin opciones")
                        return
                    
                    for leg in legs[:5]:
                        leg_id = f"{leg['player']}_{leg['type']}_{leg['val']}"
                        is_selected = leg_id in [f"{l['player']}_{l['type']}_{l['val']}" for l in st.session_state.selected_parlay_legs]
                        
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"{icon} **{leg['player']}**")
                            st.caption(f"Línea: +{leg['val']} | Prom: {leg['avg']:.1f}")
                        with col2:
                            if st.checkbox("", value=is_selected, key=f"chk_{leg_id}"):
                                if leg_id not in [f"{l['player']}_{l['type']}_{l['val']}" for l in st.session_state.selected_parlay_legs]:
                                    st.session_state.selected_parlay_legs.append(leg)
                            else:
                                st.session_state.selected_parlay_legs = [l for l in st.session_state.selected_parlay_legs 
                                                                        if f"{l['player']}_{l['type']}_{l['val']}" != leg_id]
                        st.divider()

            col_safe, col_risky = st.columns(2)
            render_parlay_column("🛡️ CONSERVADOR (Piso)", safe_legs_pts, "#4caf50", "🏀", col_safe)
            render_parlay_column("🛡️ CONSERVADOR (Piso)", safe_legs_reb, "#4caf50", "🖐", col_safe)
            render_parlay_column("🛡️ CONSERVADOR (Piso)", safe_legs_ast, "#4caf50", "🎁", col_safe)

            render_parlay_column("🚀 ARRIESGADO (Media)", risky_legs_pts, "#ff5252", "🏀", col_risky)
            render_parlay_column("🚀 ARRIESGADO (Media)", risky_legs_reb, "#ff5252", "🖐", col_risky)
            render_parlay_column("🚀 ARRIESGADO (Media)", risky_legs_ast, "#ff5252", "🎁", col_risky)

            if st.session_state.selected_parlay_legs:
                st.write("---")
                st.subheader("📝 Tu Parlay Seleccionado")
                
                total_odds = 1.0
                for i, leg in enumerate(st.session_state.selected_parlay_legs):
                    st.markdown(f"{i+1}. {leg['player']} - **+{leg['val']} {leg['type']}** (Prom: {leg['avg']:.1f})")
                    odds = st.number_input(f"Cuota para {leg['player']}", min_value=1.01, max_value=10.0, value=1.8, key=f"odds_{i}")
                    total_odds *= odds
                
                st.success(f"**Cuota total combinada: {total_odds:.2f}**")
                
                if st.button("🗑️ Limpiar selección"):
                    st.session_state.selected_parlay_legs = []
                    st.rerun()
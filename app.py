import streamlit as st
import pandas as pd
import os
import textwrap
from datetime import datetime, timedelta
import plotly.express as px

def html_clean(s: str) -> str:
    """
    Evita que Streamlit/Markdown interprete HTML como bloque de código por indentación.
    Dejamos cada línea sin espacios al inicio.
    """
    s = textwrap.dedent(s).strip("\n")
    return "\n".join([ln.lstrip() for ln in s.splitlines()])

# Importar módulos propios
from data import load_data, download_data, get_team_roster_numbers, get_next_matchup_info, query_player_stats, get_injuries
from odds import get_sports_odds, save_cache, load_cache, detect_value_odds
from ui import mostrar_leyenda_colores, mostrar_tabla_bonita, render_clickable_player_table, render_clickable_player_cards
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
@import url('https://fonts.googleapis.com/css2?family=Teko:wght@300..700&family=Inter:wght@300;400;500;600;700&family=JetBrains+Mono:wght@400;600;700&display=swap');

/* ============================
   LOOK PRO (como antes)
   ============================ */
.main .block-container {
    max-width: 1320px !important;
    padding: 1.5rem 1.75rem 3rem 1.75rem !important;
    margin: 0 auto !important;
}

body {
    background: radial-gradient(circle at top, #101624 0, #05070c 40%, #020308 100%) !important;
    color: #e3e7f1 !important;
    font-family: 'Inter', system-ui, -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif !important;
}

/* Espaciado global (evitar que quede todo junto) */
.main p, .main li, .main label, .main .stCaption {
    line-height: 1.45 !important;
}

.main .block-container > div {
    row-gap: 0.6rem;
}

/* H1 centrado y grande */
h1 {
    text-align: center !important;
    width: 100% !important;
    font-family: 'Teko', sans-serif !important;
    font-size: 64px !important;
    text-transform: uppercase;
    color: white;
    margin-bottom: 16px;
    letter-spacing: 0.08em;
}

/* Evitar centrado agresivo global */
h2, h3, h4, p { text-align: left !important; width: auto !important; }
label, span { text-align: inherit; }

/* Quitar iconos/anchors molestos */
[data-testid="stHeaderAction"] { display: none !important; }
h1 a, h2 a, h3 a, h4 a, h5 a, h6 a { display: none !important; color: transparent !important; pointer-events: none !important; }
.css-10trblm, .css-16idsys, a.anchor-link { display: none !important; }

/* TABLAS HTML (no redimensionables, limpias) */
.table-responsive { display: flex !important; justify-content: center !important; width: 100% !important; overflow-x: auto; margin-bottom: 0.9rem; }
table.custom-table { margin: 0 auto !important; border-collapse: collapse; font-size: 13px; min-width: 360px; width: 100%; background: rgba(15, 23, 42, 0.92); border-radius: 12px; overflow: hidden; }
table.custom-table th { background: linear-gradient(90deg, #111827, #020617); color: #f9fafb; text-align: center !important; padding: 9px 8px; border-bottom: 1px solid rgba(55, 65, 81, 0.9); font-weight: 600; text-transform: uppercase; letter-spacing: 0.08em; }
table.custom-table td { text-align: center !important; padding: 7px 6px; border-bottom: 1px solid rgba(31, 41, 55, 0.85); color: #e5e7eb; }
table.custom-table tr:nth-child(even) td { background-color: rgba(15, 23, 42, 0.72); }
table.custom-table tr:hover td { background-color: rgba(30, 64, 175, 0.35); }

/* Cards de partidos */
.game-card { background: radial-gradient(circle at top left, #1d2535 0, #080b12 45%, #05070c 100%); border: 1px solid rgba(148, 163, 184, 0.35); border-radius: 18px; padding: 15px; margin-bottom: 14px; width: 100%; text-align: center; box-shadow: 0 14px 35px rgba(15, 23, 42, 0.9); }
.game-matchup { display: flex; justify-content: center; align-items: center; gap: 14px; margin-bottom: 6px; }
.team-logo { width: 46px; height: 46px; object-fit: contain; filter: drop-shadow(0 0 12px rgba(15, 23, 42, 0.9)); }
.game-time { color: #facc15; font-size: 20px; font-family: 'Teko', sans-serif; letter-spacing: 0.16em; }
.vs-text { font-size: 18px; color: #9ca3af; letter-spacing: 0.18em; }

/* Botones pro */
div.stButton > button { width: 100%; border-radius: 999px !important; font-weight: 600; background: linear-gradient(90deg, #0f172a, #1d4ed8); color: #fff; border: 1px solid rgba(129, 140, 248, 0.9); transition: all 0.18s ease-out; box-shadow: 0 10px 25px rgba(15, 23, 42, 0.9); }
div.stButton > button:hover { border-color: #facc15; color: #facc15; transform: translateY(-1px); box-shadow: 0 14px 30px rgba(30, 64, 175, 0.9); }

/* Botón secundario (para "Ver") */
.btn-secondary div.stButton > button {
    background: linear-gradient(90deg, rgba(15,23,42,0.85), rgba(30,64,175,0.55)) !important;
    border: 1px solid rgba(148,163,184,0.38) !important;
    box-shadow: none !important;
}

/* Títulos con más fuerza (mejor en móvil) */
.section-title {
    text-align: center !important;
    font-family: 'Teko', sans-serif !important;
    font-size: 34px !important;
    letter-spacing: 0.12em;
    text-transform: uppercase;
    color: #ffffff;
    margin: 18px 0 10px 0;
}

.section-divider {
    height: 1px;
    background: linear-gradient(90deg, rgba(148,163,184,0.0), rgba(148,163,184,0.35), rgba(148,163,184,0.0));
    margin: 8px 0 16px 0;
}

/* Números (más legibles y con color) */
.num-mono { font-family: 'JetBrains Mono', ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; }
.num-strong { font-weight: 800; letter-spacing: -0.02em; }
.num-pts { color: #facc15; }
.num-min { color: #60a5fa; }
.num-3pm { color: #fb923c; }

/* Mobile: más presencia */
@media (max-width: 768px) {
  .section-title { font-size: 44px !important; margin: 22px 0 12px 0; }
  .main .block-container { padding-left: 1rem !important; padding-right: 1rem !important; }
  div[data-testid="column"] { width: 100% !important; flex: 1 1 100% !important; }
  table.custom-table { min-width: 520px; } /* permite scroll horizontal sin “aplastar” */
}

/* Leyendas / estados */
.dnp-missing { color: #f97373; font-weight: 600; }
.dnp-full { color: #4ade80; font-weight: 600; }
.pat-stars { color: #fb7185; font-weight: 600; }
.pat-impact { color: #a5b4fc; }

/* Cuotas info */
.odds-info { background: radial-gradient(circle at top, #0f172a 0, #020617 70%); border: 1px solid rgba(129, 140, 248, 0.55); border-radius: 14px; padding: 12px 14px; margin-bottom: 16px; text-align: left; color: #e5e7eb; }
.odds-timestamp { color: #facc15; font-weight: 600; font-size: 16px; }

/* Toolbar/footer fuera */
[data-testid="stElementToolbar"] { display: none !important; }
footer { display: none !important; }
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
if 'selected_team' not in st.session_state:
    st.session_state.selected_team = None
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
st.markdown(
    "<h1 style='text-align:center; font-size:64px;'>🏀 NBA PRO ANALYZER 🏀</h1>",
    unsafe_allow_html=True
)

pages = ["🏠 Inicio", "👤 Jugador", "⚔️ Analizar Partido", "🏟️ Equipos", "💰 Buscador de Cuotas", "🔄 Actualizar Datos"]
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

            # Desglose de puntos: 2PT / 3PT / TL
            # - Preferimos calcularlo con FGM/FG3M/FTM si existen
            # - Si no, lo calculamos desde PTS - (FG3M*3) - FTM (si FTM existe)
            mean_pts_2 = mean_pts_3 = mean_pts_ft = None
            if 'fg3m' in player_data.columns and 'pts' in player_data.columns:
                pts_3 = (player_data['fg3m'] * 3).mean()
                pts_ft = (player_data['ftm']).mean() if 'ftm' in player_data.columns else 0.0
                if 'fgm' in player_data.columns:
                    pts_2 = ((player_data['fgm'] - player_data['fg3m']) * 2).mean()
                else:
                    pts_2 = (player_data['pts'] - (player_data['fg3m'] * 3) - (player_data['ftm'] if 'ftm' in player_data.columns else 0)).mean()
                mean_pts_2, mean_pts_3, mean_pts_ft = float(pts_2), float(pts_3), float(pts_ft)

            # ===== PERFIL ESTILO TARJETAS (más estético, como la imagen) =====
            latest_row = player_data.iloc[0] if not player_data.empty else None
            team_for_player = latest_teams_map.get(
                jugador,
                latest_row['team_abbreviation'] if latest_row is not None and 'team_abbreviation' in latest_row else ""
            )
            initials = "".join([p[0] for p in jugador.split() if p]).upper()[:3]

            latest_match = latest_row['matchup'] if latest_row is not None and 'matchup' in latest_row else ""
            latest_date = latest_row['game_date'].strftime('%d/%m') if latest_row is not None and 'game_date' in latest_row and pd.notnull(latest_row['game_date']) else ""
            latest_wl = latest_row['wl'] if latest_row is not None and 'wl' in latest_row else ""

            latest_pts = float(latest_row['pts']) if latest_row is not None and 'pts' in latest_row and pd.notnull(latest_row['pts']) else None
            latest_reb = float(latest_row['reb']) if latest_row is not None and 'reb' in latest_row and pd.notnull(latest_row['reb']) else None
            latest_ast = float(latest_row['ast']) if latest_row is not None and 'ast' in latest_row and pd.notnull(latest_row['ast']) else None
            latest_3pm = float(latest_row['fg3m']) if latest_row is not None and 'fg3m' in latest_row and pd.notnull(latest_row['fg3m']) else None
            latest_min = float(latest_row['min']) if latest_row is not None and 'min' in latest_row and pd.notnull(latest_row['min']) else None

            left, right = st.columns([7, 5])
            with left:
                st.markdown(f"""
                <div class="card-elevated" style="
                    background: linear-gradient(135deg, rgba(30,64,175,0.45) 0%, rgba(15,23,42,0.85) 45%, rgba(2,6,23,0.95) 100%);
                    border: 1px solid rgba(148,163,184,0.35);
                    padding: 18px 18px;
                ">
                    <div style="display:flex; align-items:center; gap:16px;">
                        <div style="
                            width:74px; height:74px; border-radius:50%;
                            background: rgba(15,23,42,0.85);
                            border: 2px solid rgba(255,255,255,0.18);
                            display:flex; align-items:center; justify-content:center;
                            font-family:'Teko', sans-serif;
                            font-size:34px; letter-spacing:0.08em; color:#fff;
                        ">{initials}</div>
                        <div style="min-width:0;">
                            <div style="font-family:'Teko', sans-serif; font-size:40px; letter-spacing:0.06em; color:#fff; text-transform:uppercase; line-height:1;">
                                {jugador}
                            </div>
                            <div style="margin-top:6px; display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
                                <span class="pill-label">2025-26 Regular Season</span>
                                {f"<span class='pill-label' style='background:rgba(250,204,21,0.95); color:#0b1220; border-color:rgba(250,204,21,0.75); font-weight:700;'>{team_for_player}</span>" if team_for_player else ""}
                            </div>
                        </div>
                    </div>
                    <div style="margin-top:14px; display:grid; grid-template-columns:repeat(5, minmax(0,1fr)); gap:10px;">
                        <div style="background:rgba(15,23,42,0.55); border:1px solid rgba(148,163,184,0.18); border-radius:14px; padding:12px; text-align:center;">
                            <div style="font-size:11px; letter-spacing:0.14em; text-transform:uppercase; color:#9ca3af;">PPG</div>
                            <div style="font-size:26px; font-weight:800; color:#fff; margin-top:4px;">{mean_pts:.1f}</div>
                            {f"<div style='margin-top:8px; font-size:9px; color:#9ca3af; line-height:1.2;'>2PT {mean_pts_2:.1f} • 3PT {mean_pts_3:.1f} • TL {mean_pts_ft:.1f}</div>" if mean_pts_2 is not None else ""}
                        </div>
                        <div style="background:rgba(15,23,42,0.55); border:1px solid rgba(148,163,184,0.18); border-radius:14px; padding:10px; text-align:center;">
                            <div style="font-size:11px; letter-spacing:0.14em; text-transform:uppercase; color:#9ca3af;">RPG</div>
                            <div style="font-size:22px; font-weight:800; color:#fff; margin-top:2px;">{mean_reb:.1f}</div>
                        </div>
                        <div style="background:rgba(15,23,42,0.55); border:1px solid rgba(148,163,184,0.18); border-radius:14px; padding:10px; text-align:center;">
                            <div style="font-size:11px; letter-spacing:0.14em; text-transform:uppercase; color:#9ca3af;">APG</div>
                            <div style="font-size:22px; font-weight:800; color:#fff; margin-top:2px;">{mean_ast:.1f}</div>
                        </div>
                        <div style="background:rgba(15,23,42,0.55); border:1px solid rgba(148,163,184,0.18); border-radius:14px; padding:10px; text-align:center;">
                            <div style="font-size:11px; letter-spacing:0.14em; text-transform:uppercase; color:#9ca3af;">3PM</div>
                            <div style="font-size:22px; font-weight:800; color:#fff; margin-top:2px;">{mean_3pm:.1f}</div>
                        </div>
                        <div style="background:rgba(15,23,42,0.55); border:1px solid rgba(148,163,184,0.18); border-radius:14px; padding:10px; text-align:center;">
                            <div style="font-size:11px; letter-spacing:0.14em; text-transform:uppercase; color:#9ca3af;">MPG</div>
                            <div style="font-size:22px; font-weight:800; color:#fff; margin-top:2px;">{mean_min:.1f}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with right:
                st.markdown(f"""
                <div class="card-elevated" style="padding:16px 16px;">
                    <div style="display:flex; justify-content:space-between; align-items:center; gap:10px;">
                        <div style="font-weight:800; letter-spacing:0.12em; text-transform:uppercase; color:#c5d1ff; font-size:13px;">
                            Latest Performance
                        </div>
                        <div class="pill-label">{latest_date}</div>
                    </div>
                    <div style="margin-top:10px; font-weight:800; color:#fff; font-size:16px;">{jugador}</div>
                    <div style="margin-top:4px; color:#9ca3af; font-size:12px;">
                        {latest_match} &nbsp; {("• " + latest_wl) if latest_wl else ""}
                    </div>
                    <div style="margin-top:12px; display:grid; grid-template-columns:repeat(5, minmax(0,1fr)); gap:8px;">
                        <div style="background:rgba(2,6,23,0.55); border:1px solid rgba(148,163,184,0.14); border-radius:12px; padding:10px 8px; text-align:center;">
                            <div style="font-size:9px; color:#9ca3af; letter-spacing:0.14em; text-transform:uppercase;">MIN</div>
                            <div style="font-size:20px; font-weight:800; color:#fff;">{f"{latest_min:.0f}" if latest_min is not None else "-"}</div>
                        </div>
                        <div style="background:rgba(2,6,23,0.55); border:1px solid rgba(148,163,184,0.14); border-radius:12px; padding:10px 8px; text-align:center;">
                            <div style="font-size:9px; color:#9ca3af; letter-spacing:0.14em; text-transform:uppercase;">PTS</div>
                            <div style="font-size:20px; font-weight:800; color:#fff;">{f"{latest_pts:.0f}" if latest_pts is not None else "-"}</div>
                        </div>
                        <div style="background:rgba(2,6,23,0.55); border:1px solid rgba(148,163,184,0.14); border-radius:12px; padding:9px 8px; text-align:center;">
                            <div style="font-size:10px; color:#9ca3af; letter-spacing:0.14em; text-transform:uppercase;">REB</div>
                            <div style="font-size:16px; font-weight:800; color:#fff;">{f"{latest_reb:.0f}" if latest_reb is not None else "-"}</div>
                        </div>
                        <div style="background:rgba(2,6,23,0.55); border:1px solid rgba(148,163,184,0.14); border-radius:12px; padding:9px 8px; text-align:center;">
                            <div style="font-size:10px; color:#9ca3af; letter-spacing:0.14em; text-transform:uppercase;">AST</div>
                            <div style="font-size:16px; font-weight:800; color:#fff;">{f"{latest_ast:.0f}" if latest_ast is not None else "-"}</div>
                        </div>
                        <div style="background:rgba(2,6,23,0.55); border:1px solid rgba(148,163,184,0.14); border-radius:12px; padding:9px 8px; text-align:center;">
                            <div style="font-size:10px; color:#9ca3af; letter-spacing:0.14em; text-transform:uppercase;">3PM</div>
                            <div style="font-size:16px; font-weight:800; color:#fff;">{f"{latest_3pm:.0f}" if latest_3pm is not None else "-"}</div>
                        </div>
                    </div>
                </div>
                """, unsafe_allow_html=True)

            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("PTS", f"{mean_pts:.1f}")
            c2.metric("REB", f"{mean_reb:.1f}")
            c3.metric("AST", f"{mean_ast:.1f}")
            c4.metric("3PM", f"{mean_3pm:.1f}")
            c5.metric("MIN", f"{mean_min:.1f}")

            # GRÁFICO (BARRAS) – sin ajustes / sin edición
            st.subheader("📊 Últimos partidos (gráfico de barras)")
            metrica = st.radio(
                "Métrica a mostrar",
                ["PTS", "REB", "AST", "3PM", "MIN"],
                horizontal=True,
                index=0
            )

            def _metric_col(m):
                return "fg3m" if m == "3PM" else m.lower()

            metric_col = _metric_col(metrica)

            # Global: últimos 10 partidos
            base_series = player_data.sort_values('game_date').tail(10).copy()
            base_series['FECHA'] = base_series['game_date'].dt.strftime('%d/%m')

            fig_global = px.bar(
                base_series,
                x='FECHA',
                y=metric_col,
                title=f"{jugador} – {metrica} (últimos 10)",
                labels={'FECHA': 'Fecha', metric_col: metrica},
            )
            fig_global.update_traces(marker_color="#60a5fa")
            fig_global.update_layout(
                template="plotly_dark",
                margin=dict(l=10, r=10, t=45, b=10),
                hovermode="x unified",
                showlegend=False
            )

            # Vs rival: últimos 10 contra ese equipo (si existe)
            fig_vs = None
            if rival:
                vs_team = player_data[player_data['matchup'].str.contains(rival, case=False)].sort_values('game_date').tail(10).copy()
                if not vs_team.empty:
                    vs_team['FECHA'] = vs_team['game_date'].dt.strftime('%d/%m')
                    fig_vs = px.bar(
                        vs_team,
                        x='FECHA',
                        y=metric_col,
                        title=f"{jugador} – {metrica} vs {rival} (últimos 10)",
                        labels={'FECHA': 'Fecha', metric_col: metrica},
                    )
                    fig_vs.update_traces(marker_color="#fb923c")
                    fig_vs.update_layout(
                        template="plotly_dark",
                        margin=dict(l=10, r=10, t=45, b=10),
                        hovermode="x unified",
                        showlegend=False
                    )

            plotly_cfg = {
                "displayModeBar": False,
                "staticPlot": True,
                "scrollZoom": False,
                "responsive": True
            }

            if fig_vs is None:
                st.plotly_chart(fig_global, use_container_width=True, config=plotly_cfg)
            else:
                g1, g2 = st.columns(2)
                with g1:
                    st.plotly_chart(fig_global, use_container_width=True, config=plotly_cfg)
                with g2:
                    st.plotly_chart(fig_vs, use_container_width=True, config=plotly_cfg)

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

            mostrar_tabla_como_tarjetas(view, max_cols=2)

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
                    mostrar_tabla_como_tarjetas(view_h2h, max_cols=2)
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
                    
                    mostrar_tabla_como_tarjetas(comparativa, max_cols=2)
                    
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
            mostrar_tabla_como_tarjetas(df_alerts, max_cols=2)

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
                    st.table(pd.DataFrame(all_odds))
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
                            st.table(pd.DataFrame(odds_list))
                    st.divider()

            if not found:
                st.warning("No hay datos de jugadores disponibles en este momento. Puede que el mercado esté cerrado.")

# --- PÁGINA EQUIPOS ---
elif st.session_state.page == "🏟️ Equipos":
    st.markdown("<h2>🏟️ Equipos</h2>", unsafe_allow_html=True)
    st.caption("Overview, estadísticas, calendario y líderes (estilo StatMuse, usando tus datos).")
    if df.empty:
        st.error("Primero actualiza los datos.")
    else:
        equipos = sorted(df['team_abbreviation'].dropna().unique())
        idx_team = equipos.index(st.session_state.selected_team) if st.session_state.selected_team in equipos else 0
        team = st.selectbox("Equipo", equipos, index=idx_team)
        st.session_state.selected_team = team

        team_df = df[df['team_abbreviation'] == team].copy()
        if team_df.empty:
            st.info("Sin datos para este equipo.")
        else:
            # Header visual (más “StatMuse-like”)
            st.markdown(f"""
            <div class="card-elevated" style="
                background: linear-gradient(135deg, rgba(30,64,175,0.38) 0%, rgba(15,23,42,0.88) 55%, rgba(2,6,23,0.95) 100%);
                padding:16px 18px;
                margin-top:10px;
            ">
                <div style="display:flex; justify-content:space-between; align-items:center; gap:12px;">
                    <div>
                        <div style="font-family:'Teko', sans-serif; font-size:34px; letter-spacing:0.10em; text-transform:uppercase; color:#ffffff; line-height:1;">
                            {team}
                        </div>
                        <div style="margin-top:6px; color:#9ca3af; font-size:12px; line-height:1.5;">
                            Datos calculados desde tu base (player game logs agregados por partido).
                        </div>
                    </div>
                    <div class="pill-label">TEAM HUB</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

            # Agregado por partido (tipo StatMuse team game log)
            games = team_df.groupby(['game_id', 'game_date', 'matchup', 'wl'], dropna=False).agg(
                PTS=('pts', 'sum'),
                REB=('reb', 'sum'),
                AST=('ast', 'sum'),
                **{'3PM': ('fg3m', 'sum')},
                MIN=('min', 'sum')
            ).reset_index()
            games = games.sort_values('game_date', ascending=False)

            wins = int((games['wl'] == 'W').sum()) if 'wl' in games.columns else 0
            losses = int((games['wl'] == 'L').sum()) if 'wl' in games.columns else 0

            # KPIs (más espaciado y limpio)
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Record", f"{wins}-{losses}")
            c2.metric("GP", f"{len(games)}")
            c3.metric("PTS", f"{games['PTS'].mean():.1f}" if len(games) else "-")
            c4.metric("REB", f"{games['REB'].mean():.1f}" if len(games) else "-")
            c5.metric("AST", f"{games['AST'].mean():.1f}" if len(games) else "-")

            # Mini gráfico de forma (últimos 10)
            if len(games) >= 2:
                form = games.head(10).copy()
                form = form.sort_values('game_date')
                form['FECHA'] = form['game_date'].dt.strftime('%d/%m')
                fig_form = px.bar(form, x='FECHA', y='PTS', title=f"{team} – PTS últimos 10 partidos", labels={'FECHA': 'Fecha', 'PTS': 'PTS'})
                fig_form.update_traces(marker_color="#60a5fa")
                fig_form.update_layout(template="plotly_dark", margin=dict(l=10, r=10, t=45, b=10), showlegend=False)
                st.plotly_chart(fig_form, use_container_width=True, config={"displayModeBar": False, "staticPlot": True, "responsive": True})

            tab_overview, tab_stats, tab_schedule, tab_leaders = st.tabs(["Overview", "Stats", "Schedule", "Leaders"])

            with tab_overview:
                st.markdown(f"""
                <div class="card-elevated" style="padding:16px 18px;">
                    <div style="font-weight:900; letter-spacing:0.14em; text-transform:uppercase; color:#c5d1ff; font-size:13px;">
                        Overview
                    </div>
                    <div style="margin-top:10px; color:#9ca3af; font-size:12px; line-height:1.6;">
                        Aquí verás un resumen del equipo al estilo StatMuse: record, medias, racha de partidos y líderes.
                    </div>
                </div>
                """, unsafe_allow_html=True)

            with tab_stats:
                st.markdown("<div class='section-title'>📊 Team stats (por partido)</div>", unsafe_allow_html=True)
                st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)

                ppg = games['PTS'].mean() if len(games) else 0
                rpg = games['REB'].mean() if len(games) else 0
                apg = games['AST'].mean() if len(games) else 0
                tpm = games['3PM'].mean() if len(games) else 0
                mpg = games['MIN'].mean() / 5 if len(games) else 0  # min totales / 5 jugadores

                # Cards con presencia (mejor en móvil)
                k1, k2, k3, k4, k5 = st.columns(5)
                k1.metric("PPG", f"{ppg:.1f}")
                k2.metric("RPG", f"{rpg:.1f}")
                k3.metric("APG", f"{apg:.1f}")
                k4.metric("3PM", f"{tpm:.1f}")
                k5.metric("MPG (team)", f"{mpg:.1f}")

                st.markdown("<div class='card-elevated' style='padding:16px 16px;'>", unsafe_allow_html=True)
                stats_row = pd.DataFrame([{
                    'GP': len(games),
                    'PTS': ppg,
                    'REB': rpg,
                    'AST': apg,
                    '3PM': tpm,
                    'MIN': games['MIN'].mean() if len(games) else 0
                }]).round(1)
                mostrar_tabla_como_tarjetas(stats_row, max_cols=1)
                st.markdown("</div>", unsafe_allow_html=True)

            with tab_schedule:
                st.subheader("📅 Últimos partidos")
                sched = games.head(12).copy()
                sched['FECHA'] = sched['game_date'].dt.strftime('%d/%m')
                sched['RES'] = sched['wl'].map({'W': '✅', 'L': '❌'}).fillna('')
                sched['PARTIDO'] = sched['matchup']
                sched['PTS'] = sched['PTS'].fillna(0).astype(int)
                sched['REB'] = sched['REB'].fillna(0).astype(int)
                sched['AST'] = sched['AST'].fillna(0).astype(int)
                sched['3PM'] = sched['3PM'].fillna(0).astype(int)
                sched['FICHA'] = sched['game_id'].apply(lambda x: f"<a href='https://www.nba.com/game/{x}' target='_blank' class='match-link'>📊</a>" if pd.notnull(x) else "-")
                sched_view = sched[['FECHA', 'RES', 'PARTIDO', 'FICHA', 'PTS', 'REB', 'AST', '3PM']]
                mostrar_tabla_como_tarjetas(sched_view, max_cols=1)

            with tab_leaders:
                st.subheader("🏅 Leaders")
                current_players = [p for p, t in latest_teams_map.items() if t == team]
                leaders_df = df[(df['team_abbreviation'] == team) & (df['player_name'].isin(current_players))].copy()
                if leaders_df.empty:
                    leaders_df = df[df['team_abbreviation'] == team].copy()

                leaders = leaders_df.groupby('player_name').agg(
                    GP=('game_id', 'count'),
                    PTS=('pts', 'mean'),
                    REB=('reb', 'mean'),
                    AST=('ast', 'mean'),
                    **{'3PM': ('fg3m', 'mean')},
                    MIN=('min', 'mean')
                ).reset_index()
                leaders = leaders.sort_values('PTS', ascending=False).head(15)
                leaders[['PTS', 'REB', 'AST', '3PM', 'MIN']] = leaders[['PTS', 'REB', 'AST', '3PM', 'MIN']].round(1)
                leaders = leaders.rename(columns={'player_name': 'JUGADOR'})
                # Leaders en tarjetas (más visual) + tabla compacta debajo
                top5 = leaders.head(5).copy()
                if not top5.empty:
                    cols = st.columns(5, gap="small")
                    for i in range(len(top5)):
                        r = top5.iloc[i]
                        with cols[i]:
                            st.markdown(f"""
                            <div class="card-elevated" style="padding:12px 12px; text-align:left;">
                                <div style="font-weight:900; color:#ffffff; font-size:13px; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">{r['JUGADOR']}</div>
                                <div style="margin-top:8px; color:#9ca3af; font-size:11px; letter-spacing:0.10em; text-transform:uppercase;">PTS</div>
                                <div style="font-size:20px; font-weight:900; color:#e5e7eb;">{r['PTS']}</div>
                                <div style="margin-top:8px; color:#9ca3af; font-size:11px;">REB {r['REB']} • AST {r['AST']}</div>
                            </div>
                            """, unsafe_allow_html=True)
                st.write("")
                mostrar_tabla_como_tarjetas(leaders, max_cols=2)

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

            # LESIONES
            st.write("---")
            st.subheader("🏥 Lesiones reportadas")

            with st.spinner("Cargando partes médicos..."):
                injuries = get_injuries()

            if injuries:
                inj_t1 = [i for i in injuries if i.get('team') == t1]
                inj_t2 = [i for i in injuries if i.get('team') == t2]
                
                col_i1, col_i2 = st.columns(2)
                
                with col_i1:
                    st.markdown(f"""
                    <div class="card-elevated" style="padding:14px 16px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div style="font-weight:800; letter-spacing:0.14em; text-transform:uppercase; color:#c5d1ff; font-size:13px;">{t1}</div>
                            <div class="pill-label">{len(inj_t1)} lesion{'' if len(inj_t1)==1 else 'es'}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    if inj_t1:
                        for it in inj_t1:
                            st.markdown(f"""
                            <div style="margin-top:10px; padding:10px 10px; border-radius:12px; border:1px solid rgba(148,163,184,0.18); background:rgba(2,6,23,0.45);">
                                <div style="font-weight:800; color:#ffffff; font-size:13px;">{it.get('player','')}</div>
                                <div style="margin-top:4px; color:#9ca3af; font-size:12px; line-height:1.45;">{it.get('status','')}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='margin-top:10px; color:#4ade80; font-weight:700;'>✓ Sin lesionados</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
                
                with col_i2:
                    st.markdown(f"""
                    <div class="card-elevated" style="padding:14px 16px;">
                        <div style="display:flex; justify-content:space-between; align-items:center;">
                            <div style="font-weight:800; letter-spacing:0.14em; text-transform:uppercase; color:#c5d1ff; font-size:13px;">{t2}</div>
                            <div class="pill-label">{len(inj_t2)} lesion{'' if len(inj_t2)==1 else 'es'}</div>
                        </div>
                    """, unsafe_allow_html=True)
                    if inj_t2:
                        for it in inj_t2:
                            st.markdown(f"""
                            <div style="margin-top:10px; padding:10px 10px; border-radius:12px; border:1px solid rgba(148,163,184,0.18); background:rgba(2,6,23,0.45);">
                                <div style="font-weight:800; color:#ffffff; font-size:13px;">{it.get('player','')}</div>
                                <div style="margin-top:4px; color:#9ca3af; font-size:12px; line-height:1.45;">{it.get('status','')}</div>
                            </div>
                            """, unsafe_allow_html=True)
                    else:
                        st.markdown("<div style='margin-top:10px; color:#4ade80; font-weight:700;'>✓ Sin lesionados</div>", unsafe_allow_html=True)
                    st.markdown("</div>", unsafe_allow_html=True)
            else:
                st.error("❌ No se pudo conectar con la fuente de lesiones")

            # HISTORIAL H2H
            mask = ((df['team_abbreviation'] == t1) & (df['matchup'].str.contains(t2))) | \
            ((df['team_abbreviation'] == t2) & (df['matchup'].str.contains(t1)))
            
            history = df[mask].sort_values('game_date', ascending=False)
            last_dates = sorted(history['game_date'].unique(), reverse=True)[:5]

            st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>📅 Historial H2H</div>", unsafe_allow_html=True)

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
                # Resumen visual + tabla en card
                try:
                    wins_t1 = sum(1 for x in games_summary if f"{t1} ✅" in x.get('ENFRENTAMIENTO', ''))
                    wins_t2 = sum(1 for x in games_summary if f"{t2} ✅" in x.get('ENFRENTAMIENTO', ''))
                except Exception:
                    wins_t1, wins_t2 = 0, 0

                st.markdown("<div class='card-elevated' style='padding:16px 16px;'>", unsafe_allow_html=True)
                st.markdown(f"""
                <div style="display:flex; justify-content:space-between; align-items:center; gap:12px; flex-wrap:wrap; margin-bottom:12px;">
                    <div class="pill-label">Últimos {len(df_games)} enfrentamientos</div>
                    <div style="display:flex; gap:10px; flex-wrap:wrap;">
                        <span class="pill-label">{t1}: <span class="num-mono num-strong num-pts">{wins_t1}</span></span>
                        <span class="pill-label">{t2}: <span class="num-mono num-strong num-pts">{wins_t2}</span></span>
                    </div>
                </div>
                """, unsafe_allow_html=True)
                mostrar_tabla_como_tarjetas(df_games, max_cols=1)
                st.markdown("</div>", unsafe_allow_html=True)

            team_totals = history.groupby(['game_date', 'team_abbreviation'])[['pts', 'reb', 'ast']].sum().reset_index()
            filtered_totals = team_totals[team_totals['team_abbreviation'].isin([t1, t2])].copy()
            if not filtered_totals.empty:
                st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
                st.markdown("<div class='section-title'>📊 Comparativa H2H</div>", unsafe_allow_html=True)
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
                    st.markdown("<div class='card-elevated' style='padding:16px 16px;'>", unsafe_allow_html=True)
                    st.markdown("<div class='pill-label' style='margin-bottom:12px;'>Stats por partido (H2H)</div>", unsafe_allow_html=True)
                    mostrar_tabla_como_tarjetas(df_comparative[final_cols], max_cols=2)
                    st.markdown("</div>", unsafe_allow_html=True)

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

                        # ==========================================
            # TOP ANOTADORES - CORREGIDO Y BIEN INDENTADO
            # ==========================================
            st.markdown("<div class='section-divider'></div>", unsafe_allow_html=True)
            st.markdown("<div class='section-title'>🔥 Top anotadores</div>", unsafe_allow_html=True)
            
            top_scorers_df = stats.sort_values('pts', ascending=False).head(10)
            if not top_scorers_df.empty:
                cols = st.columns(2, gap="medium")
                for idx, (_, row) in enumerate(top_scorers_df.iterrows()):
                    with cols[idx % 2]:
                        player_name = row['player_name']
                        team = row['team_abbreviation']
                        avg_pts = row['pts']
                        
                        # Obtener logs del jugador
                        player_logs = df[df['player_name'] == player_name].sort_values('game_date', ascending=False).head(5)
                        
                        # Calcular desglose de puntos
                        if not player_logs.empty:
                            avg_fgm = player_logs['fgm'].mean() if 'fgm' in player_logs.columns else 0
                            avg_fg3m = player_logs['fg3m'].mean() if 'fg3m' in player_logs.columns else 0
                            avg_ftm = player_logs['ftm'].mean() if 'ftm' in player_logs.columns else 0
                            
                            avg_2pt = (avg_fgm - avg_fg3m) * 2
                            avg_3pt = avg_fg3m * 3
                            avg_ft = avg_ftm
                        else:
                            avg_2pt = 0
                            avg_3pt = 0
                            avg_ft = 0
                        
                        # Construir HTML del desglose directamente en la tarjeta
                        
                        # Triples (series + media)
                        tpm_values = player_logs['fg3m'].tolist() if not player_logs.empty and 'fg3m' in player_logs.columns else []
                        tpm_series = " • ".join([str(int(v)) for v in tpm_values]) if tpm_values else "Sin datos"
                        avg_3pm_made = float(pd.Series(tpm_values).mean()) if tpm_values else 0.0

                        # Serie de puntos
                        pts_values = player_logs['pts'].tolist() if not player_logs.empty else []
                        pts_series = " • ".join([str(int(v)) for v in pts_values]) if pts_values else "Sin datos"
                        
                        # Serie de minutos
                        min_values = player_logs['min'].tolist() if not player_logs.empty and 'min' in player_logs.columns else []
                        min_series = " • ".join([str(int(v)) for v in min_values]) if min_values else "Sin datos"
                        
                        # Tarjeta 1: media (PPG)
                        st.markdown(html_clean(f"""
<div class="card-elevated" style="
  padding: 18px 18px;
  margin-bottom: 12px;
  background: linear-gradient(135deg, rgba(250,204,21,0.12) 0%, rgba(15,23,42,0.95) 100%);
  border: 1px solid rgba(250,204,21,0.25);
  border-radius: 20px;
">
  <div style="display:flex; justify-content:space-between; align-items:center; gap:12px;">
    <div>
      <div style="font-weight:900; font-size:20px; color:#ffffff; letter-spacing:-0.02em;">{player_name}</div>
      <div style="margin-top:6px;">
        <span style="background: rgba(250,204,21,0.2); color:#facc15; padding:4px 12px; border-radius:999px; font-size:12px; font-weight:700;">{team}</span>
      </div>
    </div>
    <div style="text-align:right;">
      <div style="font-size:44px; font-weight:950; color:#facc15; line-height:1;">{avg_pts:.1f}</div>
      <div style="color:#9ca3af; font-size:12px; letter-spacing:0.16em; text-transform:uppercase;">PPG</div>
    </div>
  </div>
</div>
"""), unsafe_allow_html=True)

                        # Tarjeta 2: desglose + últimos 5
                        st.markdown(html_clean(f"""
<div class="card-elevated" style="
  padding: 16px 16px;
  margin-bottom: 18px;
  background: rgba(2,6,23,0.35);
  border: 1px solid rgba(148,163,184,0.18);
  border-radius: 20px;
">
  <div style="display:flex; gap:14px; justify-content:center; border-bottom:1px solid rgba(148,163,184,0.18); padding-bottom:12px; margin-bottom:12px; flex-wrap:wrap;">
    <div><span style="color:#9ca3af;">2PT:</span> <span class="num-mono num-strong" style="color:#e5e7eb;">{avg_2pt:.1f}</span></div>
    <div><span style="color:#9ca3af;">TL:</span> <span class="num-mono num-strong" style="color:#e5e7eb;">{avg_ft:.1f}</span></div>
    <div><span style="color:#9ca3af;">3PT pts:</span> <span class="num-mono num-strong num-3pm">{avg_3pt:.1f}</span></div>
  </div>

  <div style="background: rgba(0,0,0,0.22); padding: 14px; border-radius: 16px;">
    <div style="color:#facc15; font-size:11px; letter-spacing:0.14em; margin-bottom:8px; text-transform:uppercase;">⚡ Últimos 5 partidos</div>
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <span style="color:#9ca3af; font-size:12px;">PTS</span>
      <span class="num-mono num-strong num-pts" style="font-size:20px;">{pts_series}</span>
    </div>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
      <span style="color:#9ca3af; font-size:12px;">MIN</span>
      <span class="num-mono num-strong num-min" style="font-size:20px;">{min_series}</span>
    </div>
  </div>

  <div style="margin-top:10px; background: rgba(251,146,60,0.08); border:1px solid rgba(251,146,60,0.18); padding:10px 12px; border-radius:14px;">
    <div style="color:#fb923c; font-size:10px; letter-spacing:0.14em; margin-bottom:6px; text-transform:uppercase;">🎯 Triples (últimos 5)</div>
    <div style="display:flex; justify-content:space-between; align-items:center; gap:10px;">
      <span style="color:#9ca3af; font-size:12px;">3PM</span>
      <span class="num-mono num-strong num-3pm" style="font-size:18px;">{tpm_series}</span>
    </div>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:6px;">
      <span style="color:#9ca3af; font-size:12px;">Media</span>
      <span class="num-mono num-strong num-3pm" style="font-size:16px;">{avg_3pm_made:.1f}</span>
    </div>
  </div>
</div>
"""), unsafe_allow_html=True)
                        
                        if st.button(f"Ver {player_name}", key=f"scorer_fixed_{idx}"):
                            navegar_a_jugador(player_name)
                            st.rerun()
            else:
                st.caption("Sin datos de anotadores.")

            # ==========================================
            # TOP REBOTEADORES
            # ==========================================
            st.markdown("<div class='section-title'>🖐️ Top reboteadores</div>", unsafe_allow_html=True)
            
            top_rebounders_df = stats.sort_values('reb', ascending=False).head(10)
            if not top_rebounders_df.empty:
                cols = st.columns(2, gap="medium")
                for idx, (_, row) in enumerate(top_rebounders_df.iterrows()):
                    with cols[idx % 2]:
                        player_name = row['player_name']
                        team = row['team_abbreviation']
                        avg_reb = row['reb']
                        
                        player_logs = df[df['player_name'] == player_name].sort_values('game_date', ascending=False).head(5)
                        
                        # Serie de rebotes
                        reb_values = player_logs['reb'].tolist() if not player_logs.empty else []
                        reb_series = " • ".join([str(int(v)) for v in reb_values]) if reb_values else "Sin datos"
                        
                        # Serie de minutos
                        min_values = player_logs['min'].tolist() if not player_logs.empty and 'min' in player_logs.columns else []
                        min_series = " • ".join([str(int(v)) for v in min_values]) if min_values else "Sin datos"
                        
                        # Tarjeta 1: media (RPG)
                        st.markdown(html_clean(f"""
<div class="card-elevated" style="
  padding: 18px 18px;
  margin-bottom: 12px;
  background: linear-gradient(135deg, rgba(96,165,250,0.12) 0%, rgba(15,23,42,0.95) 100%);
  border: 1px solid rgba(96,165,250,0.25);
  border-radius: 20px;
">
  <div style="display:flex; justify-content:space-between; align-items:center; gap:12px;">
    <div>
      <div style="font-weight:900; font-size:20px; color:#ffffff; letter-spacing:-0.02em;">{player_name}</div>
      <div style="margin-top:6px;">
        <span style="background: rgba(96,165,250,0.2); color:#60a5fa; padding:4px 12px; border-radius:999px; font-size:12px; font-weight:700;">{team}</span>
      </div>
    </div>
    <div style="text-align:right;">
      <div style="font-size:44px; font-weight:950; color:#60a5fa; line-height:1;">{avg_reb:.1f}</div>
      <div style="color:#9ca3af; font-size:12px; letter-spacing:0.16em; text-transform:uppercase;">RPG</div>
    </div>
  </div>
</div>
"""), unsafe_allow_html=True)

                        # Tarjeta 2: últimos 5
                        st.markdown(html_clean(f"""
<div class="card-elevated" style="
  padding: 16px 16px;
  margin-bottom: 18px;
  background: rgba(2,6,23,0.35);
  border: 1px solid rgba(148,163,184,0.18);
  border-radius: 20px;
">
  <div style="background: rgba(0,0,0,0.22); padding: 12px; border-radius: 14px;">
    <div style="color:#60a5fa; font-size:11px; letter-spacing:0.14em; margin-bottom:8px; text-transform:uppercase;">⚡ Últimos 5 partidos</div>
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <span style="color:#9ca3af; font-size:12px;">REB</span>
      <span style="font-family:'JetBrains Mono', monospace; font-size:16px; font-weight:700; color:#e5e7eb;">{reb_series}</span>
    </div>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
      <span style="color:#9ca3af; font-size:12px;">MIN</span>
      <span style="font-family:'JetBrains Mono', monospace; font-size:16px; font-weight:700; color:#e5e7eb;">{min_series}</span>
    </div>
  </div>
</div>
"""), unsafe_allow_html=True)
                        
                        if st.button(f"Ver {player_name}", key=f"rebounder_fixed_{idx}"):
                            navegar_a_jugador(player_name)
                            st.rerun()
            else:
                st.caption("Sin datos de reboteadores.")

            # ==========================================
            # TOP ASISTENTES
            # ==========================================
            st.markdown("<div class='section-title'>🎁 Top asistentes</div>", unsafe_allow_html=True)
            
            top_assisters_df = stats.sort_values('ast', ascending=False).head(10)
            if not top_assisters_df.empty:
                cols = st.columns(2, gap="medium")
                for idx, (_, row) in enumerate(top_assisters_df.iterrows()):
                    with cols[idx % 2]:
                        player_name = row['player_name']
                        team = row['team_abbreviation']
                        avg_ast = row['ast']
                        
                        player_logs = df[df['player_name'] == player_name].sort_values('game_date', ascending=False).head(5)
                        
                        # Serie de asistencias
                        ast_values = player_logs['ast'].tolist() if not player_logs.empty else []
                        ast_series = " • ".join([str(int(v)) for v in ast_values]) if ast_values else "Sin datos"
                        
                        # Serie de minutos
                        min_values = player_logs['min'].tolist() if not player_logs.empty and 'min' in player_logs.columns else []
                        min_series = " • ".join([str(int(v)) for v in min_values]) if min_values else "Sin datos"
                        
                        # Tarjeta 1: media (APG)
                        st.markdown(html_clean(f"""
<div class="card-elevated" style="
  padding: 18px 18px;
  margin-bottom: 12px;
  background: linear-gradient(135deg, rgba(192,132,252,0.12) 0%, rgba(15,23,42,0.95) 100%);
  border: 1px solid rgba(192,132,252,0.25);
  border-radius: 20px;
">
  <div style="display:flex; justify-content:space-between; align-items:center; gap:12px;">
    <div>
      <div style="font-weight:900; font-size:20px; color:#ffffff; letter-spacing:-0.02em;">{player_name}</div>
      <div style="margin-top:6px;">
        <span style="background: rgba(192,132,252,0.2); color:#c084fc; padding:4px 12px; border-radius:999px; font-size:12px; font-weight:700;">{team}</span>
      </div>
    </div>
    <div style="text-align:right;">
      <div style="font-size:44px; font-weight:950; color:#c084fc; line-height:1;">{avg_ast:.1f}</div>
      <div style="color:#9ca3af; font-size:12px; letter-spacing:0.16em; text-transform:uppercase;">APG</div>
    </div>
  </div>
</div>
"""), unsafe_allow_html=True)

                        # Tarjeta 2: últimos 5
                        st.markdown(html_clean(f"""
<div class="card-elevated" style="
  padding: 16px 16px;
  margin-bottom: 18px;
  background: rgba(2,6,23,0.35);
  border: 1px solid rgba(148,163,184,0.18);
  border-radius: 20px;
">
  <div style="background: rgba(0,0,0,0.22); padding: 12px; border-radius: 14px;">
    <div style="color:#c084fc; font-size:11px; letter-spacing:0.14em; margin-bottom:8px; text-transform:uppercase;">⚡ Últimos 5 partidos</div>
    <div style="display:flex; justify-content:space-between; align-items:center;">
      <span style="color:#9ca3af; font-size:12px;">AST</span>
      <span style="font-family:'JetBrains Mono', monospace; font-size:16px; font-weight:700; color:#e5e7eb;">{ast_series}</span>
    </div>
    <div style="display:flex; justify-content:space-between; align-items:center; margin-top:8px;">
      <span style="color:#9ca3af; font-size:12px;">MIN</span>
      <span style="font-family:'JetBrains Mono', monospace; font-size:16px; font-weight:700; color:#e5e7eb;">{min_series}</span>
    </div>
  </div>
</div>
"""), unsafe_allow_html=True)
                        
                        if st.button(f"Ver {player_name}", key=f"assister_fixed_{idx}"):
                            navegar_a_jugador(player_name)
                            st.rerun()
            else:
                st.caption("Sin datos de asistentes.")
            # BAJAS (DNP)
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
                    mostrar_tabla_como_tarjetas(df_dnp, max_cols=1)
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
                mostrar_tabla_como_tarjetas(df_patterns, max_cols=1)
            else:
                st.write("Sin impactos.")

            # PARLAY GENERATOR
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

            def render_parlay_list(title, legs_list, col, col_prefix):
                with col:
                    st.markdown(f"### {title}")
                    if not legs_list:
                        st.caption("Sin opciones")
                        return
                    
                    for i, leg in enumerate(legs_list):
                        icon = "🏀" if leg['type'] == "PTS" else ("🖐" if leg['type'] == "REB" else "🎁")
                        # Mantenemos el leg_id original para comprobar si está seleccionado en la sesión
                        leg_id = f"{leg['player']}_{leg['type']}_{leg['val']}"
                        
                        is_selected = leg_id in [f"{l['player']}_{l['type']}_{l['val']}" for l in st.session_state.selected_parlay_legs]
                        
                        c1, c2 = st.columns([3, 1])
                        with c1:
                            st.markdown(f"{icon} **{leg['player']}**")
                            st.caption(f"Línea: +{leg['val']} | Prom: {leg['avg']:.1f}")
                        with c2:
                            # Añadimos col_prefix al key de Streamlit para que sea 100% único
                            if st.checkbox("", value=is_selected, key=f"chk_{col_prefix}_{leg_id}_{i}"):
                                if leg_id not in [f"{l['player']}_{l['type']}_{l['val']}" for l in st.session_state.selected_parlay_legs]:
                                    st.session_state.selected_parlay_legs.append(leg)
                            else:
                                st.session_state.selected_parlay_legs = [l for l in st.session_state.selected_parlay_legs 
                                                                        if f"{l['player']}_{l['type']}_{l['val']}" != leg_id]
                        st.divider()

            col_safe, col_risky = st.columns(2)
            
            # Unimos las listas tomando las 3 mejores opciones de cada estadística
            safe_combined = safe_legs_pts[:3] + safe_legs_reb[:3] + safe_legs_ast[:3]
            risky_combined = risky_legs_pts[:3] + risky_legs_reb[:3] + risky_legs_ast[:3]

            render_parlay_list("🛡️ CONSERVADOR (Piso)", safe_combined, col_safe, "safe")
            render_parlay_list("🚀 ARRIESGADO (Media)", risky_combined, col_risky, "risky")

            if st.session_state.selected_parlay_legs:
                st.write("---")
                st.subheader("📝 Tu Parlay Seleccionado")
                
                total_odds = 1.0
                for i, leg in enumerate(st.session_state.selected_parlay_legs):
                    st.markdown(f"{i+1}. {leg['player']} - **+{leg['val']} {leg['type']}** (Prom: {leg['avg']:.1f})")
                    odds = st.number_input(f"Cuota para {leg['player']}", min_value=1.01, max_value=10.0, value=1.8, key=f"odds_input_{i}")
                    total_odds *= odds
                
                st.success(f"**Cuota total combinada: {total_odds:.2f}**")
                
                if st.button("🗑️ Limpiar selección"):
                    st.session_state.selected_parlay_legs = []
                    st.rerun()

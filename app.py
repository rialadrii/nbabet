import streamlit as st
import pandas as pd
import sqlite3
import os
import time
from nba_api.stats.endpoints import leaguegamelog

# ==========================================
# CONFIGURACIÓN DE LA PÁGINA
# ==========================================
st.set_page_config(page_title="NBA Analyzer Pro", page_icon="🏀", layout="wide")

# --- CSS MEJORADO PARA COLUMNAS ---
st.markdown("""
    <style>
    div[data-testid="stMetric"] {
        background-color: #262730;
        border: 1px solid #464b5f;
        padding: 10px;
        border-radius: 10px;
        color: white;
    }
    h1, h2, h3 { text-align: center; }
    
    table { width: 100%; border-collapse: collapse; margin-bottom: 20px; color: white; font-family: sans-serif; }
    th { background-color: #31333F; color: white; font-weight: bold; text-align: center !important; padding: 10px; border-bottom: 2px solid #464b5f; text-transform: uppercase; }
    td { text-align: center !important; padding: 8px; border-bottom: 1px solid #464b5f; font-size: 14px; vertical-align: middle; }
    div.table-wrapper { overflow-x: auto; }
    
    .status-played { color: #4caf50; font-weight: bold; font-size: 16px; }
    .status-missed { color: #ff5252; font-weight: bold; font-size: 16px; }
    .status-date { font-size: 10px; color: #aaaaaa; display: block; }
    .status-cell { display: inline-block; margin: 0 4px; text-align: center; }
    .dnp-full { color: #4caf50; font-weight: bold; }
    .dnp-missing { color: #ff5252; }
    .pat-stars { color: #ffbd45; font-weight: bold; }
    .pat-impact { color: #4caf50; font-weight: bold; }

    /* ESTILOS DE PARLAY */
    .parlay-col { padding: 10px; }
    
    /* CONSERVADOR */
    .safe-box { background-color: #1a2e1a; border: 2px solid #4caf50; border-radius: 15px; padding: 15px; margin-bottom: 20px; }
    .safe-header { color: #4caf50; font-size: 20px; font-weight: bold; text-align: center; text-transform: uppercase; margin-bottom: 10px; letter-spacing: 1px; }
    
    /* ARRIESGADO */
    .risky-box { background-color: #2e1a1a; border: 2px solid #ff5252; border-radius: 15px; padding: 15px; margin-bottom: 20px; }
    .risky-header { color: #ff5252; font-size: 20px; font-weight: bold; text-align: center; text-transform: uppercase; margin-bottom: 10px; letter-spacing: 1px; }

    .ticket-leg {
        background-color: #2d2d2d;
        margin: 8px 0;
        padding: 10px;
        border-radius: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }
    .leg-player { font-weight: bold; color: white; font-size: 14px; }
    .leg-val { font-weight: bold; font-size: 16px; }
    .leg-desc { font-size: 11px; color: #aaa; text-align: right; }
    </style>
    """, unsafe_allow_html=True)

# ==========================================
# LÓGICA DE DATOS
# ==========================================
DB_PATH = "nba.sqlite"
CSV_FOLDER = "csv"
if not os.path.exists(CSV_FOLDER): os.makedirs(CSV_FOLDER)

def download_data():
    progress_text = "Descargando datos... Por favor espera."
    my_bar = st.progress(0, text=progress_text)
    target_seasons = ['2024-25', '2025-26']
    all_seasons_data = []
    for i, season in enumerate(target_seasons):
        try:
            gamelogs = leaguegamelog.LeagueGameLog(season=season, player_or_team_abbreviation='P')
            df = gamelogs.get_data_frames()[0]
            if not df.empty: all_seasons_data.append(df)
            my_bar.progress((i + 1) * 50, text=f"Temporada {season} descargada...")
        except: pass
    
    if all_seasons_data:
        full_df = pd.concat(all_seasons_data, ignore_index=True)
        cols = ['PLAYER_ID', 'PLAYER_NAME', 'TEAM_ABBREVIATION', 'GAME_DATE', 'MATCHUP', 'PTS', 'REB', 'AST', 'MIN']
        final_cols = [c for c in cols if c in full_df.columns]
        df_clean = full_df[final_cols].copy()
        df_clean.columns = df_clean.columns.str.lower()
        df_clean.to_csv(f'{CSV_FOLDER}/player_stats.csv', index=False)
        my_bar.empty()
        return True
    return False

def load_data():
    if os.path.exists(f"{CSV_FOLDER}/player_stats.csv"):
        df = pd.read_csv(f"{CSV_FOLDER}/player_stats.csv")
        if 'game_date' in df.columns: df['game_date'] = pd.to_datetime(df['game_date'])
        if 'min' in df.columns: df['min'] = pd.to_numeric(df['min'], errors='coerce')
        return df
    return pd.DataFrame()

# ==========================================
# INTERFAZ
# ==========================================
st.markdown("<h1 style='text-align: center;'>🏀 NBA Pro Analyzer</h1>", unsafe_allow_html=True)
st.sidebar.header("Menú")
opcion = st.sidebar.radio("Ir a:", ["🏠 Inicio", "👤 Jugador", "⚔️ Partido", "🔄 Actualizar"])
df = load_data()

latest_teams_map = {}
if not df.empty:
    latest = df.sort_values('game_date').drop_duplicates('player_name', keep='last')
    latest_teams_map = dict(zip(latest['player_name'], latest['team_abbreviation']))

def mostrar_tabla(df_raw, col_color):
    cols = [c for c in df_raw.columns if c in ['PTS', 'REB', 'AST']]
    html = df_raw.style.format("{:.1f}", subset=cols)\
        .background_gradient(subset=[col_color] if col_color else None, cmap='YlOrBr' if col_color=='REB' else ('Greens' if col_color=='PTS' else 'Blues'))\
        .hide(axis="index").to_html(classes="custom-table")
    st.markdown(f"<div class='table-wrapper'>{html}</div>", unsafe_allow_html=True)

if opcion == "🏠 Inicio":
    st.info("Bienvenido. Selecciona 'Analizar Partido' para ver los Parlays.")
    if df.empty: st.warning("⚠️ Sin datos. Actualiza primero.")
    else: st.write(f"Registros: {len(df)}")

elif opcion == "🔄 Actualizar":
    if st.button("Descargar Datos Nuevos"):
        if download_data(): st.success("¡Listo!")
            
elif opcion == "👤 Jugador":
    st.header("👤 Buscador")
    players = sorted(df['player_name'].unique()) if not df.empty else []
    p = st.selectbox("Jugador:", players, index=None)
    if p:
        p_data = df[df['player_name'] == p].sort_values('game_date', ascending=False)
        c1,c2,c3 = st.columns(3)
        c1.metric("PTS", f"{p_data['pts'].mean():.1f}")
        c2.metric("REB", f"{p_data['reb'].mean():.1f}")
        c3.metric("AST", f"{p_data['ast'].mean():.1f}")
        
        view = p_data.head(5)[['game_date','matchup','min','pts','reb','ast']].copy()
        view.columns = ['FECHA','RIVAL','MIN','PTS','REB','AST']
        view['FECHA'] = view['FECHA'].dt.strftime('%d/%m')
        mostrar_tabla(view, None)

elif opcion == "⚔️ Analizar Partido":
    st.header("⚔️ Análisis H2H")
    if df.empty: st.error("Sin datos.")
    else:
        c1, c2 = st.columns(2)
        teams = sorted(df['team_abbreviation'].unique())
        t1 = c1.selectbox("Local", teams, index=None)
        t2 = c2.selectbox("Visitante", teams, index=None)
        
        if t1 and t2:
            mask = ((df['team_abbreviation']==t1) & (df['matchup'].str.contains(t2))) | \
                   ((df['team_abbreviation']==t2) & (df['matchup'].str.contains(t1)))
            hist = df[mask].sort_values('game_date', ascending=False)
            dates = sorted(hist['game_date'].unique(), reverse=True)[:5]
            
            st.write("---")
            # TABLA FECHAS
            g_summ = []
            for d in dates:
                r = hist[hist['game_date']==d].iloc[0]
                g_summ.append({'FECHA': d.strftime('%d/%m/%y'), 'PARTIDO': r['matchup']})
            mostrar_tabla(pd.DataFrame(g_summ), None)
            
            rec = hist[hist['game_date'].isin(dates)]
            
            # STATS AGG
            stats = rec.groupby(['player_name','team_abbreviation']).agg(
                pts=('pts','mean'), reb=('reb','mean'), ast=('ast','mean'),
                t_pts=('pts', lambda x: '/'.join(x.astype(int).astype(str))),
                t_reb=('reb', lambda x: '/'.join(x.astype(int).astype(str))),
                t_ast=('ast', lambda x: '/'.join(x.astype(int).astype(str))),
                t_min=('min', lambda x: '/'.join(x.astype(int).astype(str))),
                gp=('game_date','count')
            ).reset_index()

            # VISUAL STATUS
            s_list = []
            for _, r in stats.iterrows():
                logs = rec[(rec['player_name']==r['player_name']) & (rec['team_abbreviation']==r['team_abbreviation'])]
                real_t = latest_teams_map.get(r['player_name'], r['team_abbreviation'])
                play_ds = logs['game_date'].unique()
                h = ""
                for d in dates:
                    if d in play_ds: h += "✅ "
                    else: h += "❌ " if real_t == r['team_abbreviation'] else "➖ "
                s_list.append(h)
            stats['STATUS'] = s_list

            st.write("---")
            c_pts, c_reb, c_ast = st.tabs(["PTS", "REB", "AST"])
            
            with c_pts:
                v = stats.sort_values('pts', ascending=False).head(10)[['player_name','team_abbreviation','STATUS','pts','t_pts','t_min']].copy()
                v.columns = ['JUGADOR','EQ','STATUS','PTS','RACHA','MIN']
                mostrar_tabla(v, 'PTS')
            with c_reb:
                v = stats.sort_values('reb', ascending=False).head(10)[['player_name','team_abbreviation','STATUS','reb','t_reb','t_min']].copy()
                v.columns = ['JUGADOR','EQ','STATUS','REB','RACHA','MIN']
                mostrar_tabla(v, 'REB')
            with c_ast:
                v = stats.sort_values('ast', ascending=False).head(10)[['player_name','team_abbreviation','STATUS','ast','t_ast','t_min']].copy()
                v.columns = ['JUGADOR','EQ','STATUS','AST','RACHA','MIN']
                mostrar_tabla(v, 'AST')

            # --- PARLAY DUAL ---
            st.write("---")
            st.subheader("🎲 GENERADOR DE PARLAY (Dual Strategy)")
            
            # Preparar candidatos (Min 60% partidos jugados)
            min_gp = max(3, int(len(dates)*0.6))
            cand = stats[stats['gp'] >= min_gp].copy()
            
            safe_picks = []
            risky_picks = []

            for _, r in cand.iterrows():
                p = r['player_name']
                logs = rec[rec['player_name'] == p]
                if logs.empty: continue
                
                # Datos Crudos
                l_pts = sorted(logs['pts'].tolist())
                l_reb = sorted(logs['reb'].tolist())
                l_ast = sorted(logs['ast'].tolist())
                
                # --- LOGICA CONSERVADORA (Smart Floor) ---
                # Ignoramos el peor partido si hay >=4 muestras
                sf_pts = l_pts[1] if len(l_pts)>=4 else l_pts[0]
                sf_reb = l_reb[1] if len(l_reb)>=4 else l_reb[0]
                sf_ast = l_ast[1] if len(l_ast)>=4 else l_ast[0]
                
                # --- LOGICA ARRIESGADA (Media H2H) ---
                # Buscamos el promedio real contra este rival
                avg_pts = r['pts']
                avg_reb = r['reb']
                avg_ast = r['ast']

                # --- FILTROS Y SELECCION ---
                
                # PUNTOS
                if sf_pts >= 12: # Safe
                    safe_picks.append({'p': p, 't': 'PTS', 'v': int(sf_pts), 'd': f"Suelo: {int(sf_pts)}", 's': avg_pts})
                if avg_pts >= 15 and avg_pts > sf_pts + 2: # Risky (Solo si es mayor que el suelo)
                    risky_picks.append({'p': p, 't': 'PTS', 'v': int(avg_pts), 'd': f"Media: {avg_pts:.1f}", 's': avg_pts})

                # REBOTES
                if sf_reb >= 6: 
                    safe_picks.append({'p': p, 't': 'REB', 'v': int(sf_reb), 'd': f"Suelo: {int(sf_reb)}", 's': avg_reb})
                if avg_reb >= 8 and avg_reb > sf_reb + 1:
                    risky_picks.append({'p': p, 't': 'REB', 'v': int(avg_reb), 'd': f"Media: {avg_reb:.1f}", 's': avg_reb})

                # ASISTENCIAS
                if sf_ast >= 4:
                    safe_picks.append({'p': p, 't': 'AST', 'v': int(sf_ast), 'd': f"Suelo: {int(sf_ast)}", 's': avg_ast})
                if avg_ast >= 6 and avg_ast > sf_ast + 1:
                    risky_picks.append({'p': p, 't': 'AST', 'v': int(avg_ast), 'd': f"Media: {avg_ast:.1f}", 's': avg_ast})

            # Ordenar por calidad (score)
            safe_picks.sort(key=lambda x: x['s'], reverse=True)
            risky_picks.sort(key=lambda x: x['s'], reverse=True)

            # --- RENDERIZADO ---
            col_safe, col_risky = st.columns(2)
            
            def render_card(container, title, picks, css_class, header_class, color):
                picks = picks[:5] # Top 5
                html = f"<div class='{css_class}'><div class='{header_class}'>{title}</div>"
                if not picks:
                    html += "<div style='text-align:center;color:#888;'>Sin oportunidades claras</div>"
                else:
                    for item in picks:
                        icon = "🏀" if item['t']=='PTS' else ("🖐" if item['t']=='REB' else "🎁")
                        html += f"""
                        <div class='ticket-leg' style='border-left: 5px solid {color}'>
                            <div class='leg-player'>{icon} {item['p']}</div>
                            <div>
                                <div class='leg-val' style='color:{color}'>+{item['v']} {item['t']}</div>
                                <div class='leg-desc'>{item['d']}</div>
                            </div>
                        </div>"""
                html += "</div>"
                container.markdown(html, unsafe_allow_html=True)

            render_card(col_safe, "🛡️ CONSERVADOR", safe_picks, "safe-box", "safe-header", "#4caf50")
            render_card(col_risky, "🚀 ARRIESGADO", risky_picks, "risky-box", "risky-header", "#ff5252")

            st.caption("Nota: 'Conservador' busca mínimos históricos. 'Arriesgado' busca promedios (mayor cuota).")

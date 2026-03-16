import streamlit as st
import pandas as pd

def apply_custom_color(column, avg, col_name):
    """Estilo condicional para celdas de estadísticas."""
    styles = []
    if col_name in ['FG3M', '3PM']:
        tolerance = 1
    elif col_name == 'PTS':
        tolerance = 3
    elif col_name in ['REB', 'AST', 'MIN']:
        tolerance = 2
    else:
        tolerance = 5

    upper_bound = avg + tolerance
    lower_bound = avg - tolerance

    for val in column:
        text_color = "white"
        if val > upper_bound:
            color = '#2962ff'
        elif val < lower_bound:
            color = '#d32f2f'
        else:
            if val >= avg:
                color = '#00c853'
            else:
                color = '#fff176'
                text_color = "black"
        styles.append(f'background-color: {color}; color: {text_color}; font-weight: bold; text-align: center;')
    return styles

def mostrar_leyenda_colores():
    """Muestra la leyenda de colores para las tablas."""
    st.markdown("""
        <div style='display: flex; flex-wrap: wrap; gap: 8px; justify-content: center; margin: 10px 0; font-family: sans-serif;'>
            <div style='background-color: #2962ff; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px;'>🔵 Supera</div>
            <div style='background-color: #00c853; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px;'>🟢 Iguala</div>
            <div style='background-color: #fff176; color: black; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px;'>⚠️ Cerca</div>
            <div style='background-color: #d32f2f; color: white; padding: 4px 10px; border-radius: 4px; font-weight: bold; font-size: 11px;'>🔴 Debajo</div>
        </div>
    """, unsafe_allow_html=True)

def mostrar_tabla_bonita(df_raw, col_principal_espanol=None, simple_mode=False, means_dict=None):
    """Renderiza una tabla con estilos personalizados."""
    cols_numericas = [c for c in df_raw.columns if c in ['PTS', 'REB', 'AST', 'FG3M', 'MIN', '3PM'] or '_PTS' in c or '_REB' in c]

    if simple_mode:
        html = df_raw.style\
            .format("{:.0f}", subset=[c for c in cols_numericas if c in df_raw.columns])\
            .hide(axis="index")\
            .to_html(classes="custom-table", escape=False)
    else:
        styler = df_raw.style.format("{:.1f}", subset=cols_numericas)
        if means_dict:
            for c in ['PTS', 'REB', 'AST', 'FG3M', 'MIN', '3PM']:
                if c in df_raw.columns and c in means_dict:
                    styler.apply(apply_custom_color, avg=means_dict[c], col_name=c, subset=[c])
        else:
            styler.background_gradient(subset=[col_principal_espanol] if col_principal_espanol else None, cmap='Greens')
        html = styler.hide(axis="index").to_html(classes="custom-table", escape=False)

    st.markdown(f"<div class='table-responsive'>{html}</div>", unsafe_allow_html=True)

def render_clickable_player_table(df_stats, stat_col, jersey_map, on_click_callback):
    """Renderiza una tabla de jugadores donde cada fila es clickeable para navegar al perfil."""
    if df_stats.empty:
        st.info("Sin datos.")
        return

    df_interactive = df_stats[['player_name', 'team_abbreviation', stat_col.lower(), f'trend_{stat_col.lower()}', 'trend_min']].copy()
    df_interactive.columns = ['JUGADOR', 'EQ', stat_col, 'RACHA', 'MIN']

    selection = st.dataframe(
        df_interactive,
        use_container_width=True,
        hide_index=True,
        on_select="rerun",
        selection_mode="single-row",
        column_config={
            "JUGADOR": st.column_config.TextColumn("JUGADOR"),
            "EQ": st.column_config.TextColumn("EQ", width="small"),
            stat_col: st.column_config.NumberColumn(stat_col, format="%.1f", width=60),
            "RACHA": st.column_config.TextColumn("RACHA (Últ. Partidos)", width=150),
            "MIN": st.column_config.TextColumn("MIN", width=115)
        }
    )
    if len(selection.selection.rows) > 0:
        row_idx = selection.selection.rows[0]
        player_name = df_interactive.iloc[row_idx]['JUGADOR']
        on_click_callback(player_name)
        st.rerun()

def render_clickable_player_cards(df_stats, stat_col, on_click_callback, subtitle=None, max_rows=10):
    """
    Renderiza tarjetas de jugadores con diseño unificado y desglose de puntos.
    Evita el error de texto plano al eliminar sangrías en el bloque HTML.
    """
    if df_stats is None or df_stats.empty:
        st.info("Sin datos.")
        return

    if subtitle:
        st.caption(subtitle)

    stat_key = stat_col.lower()
    df_view = df_stats.copy().head(max_rows).reset_index(drop=True)

    cols = st.columns(2, gap="large")
    for idx, row in df_view.iterrows():
        player = row.get('player_name', '')
        team = row.get('team_abbreviation', '')
        val = row.get(stat_key, 0)
        trend = row.get(f"trend_{stat_key}", "-")
        mins_trend = row.get('trend_min', "-")
        
        # Datos de desglose (deben venir calculados en el DataFrame stats)
        p2 = row.get('p2', "-")
        p3 = row.get('p3', "-")
        tl = row.get('tl', "-")

        with cols[idx % 2]:
            # IMPORTANTE: No indentes las líneas dentro del f-string para que Markdown no lo tome como bloque de código
            html_card = f"""
<div style="background: linear-gradient(135deg, rgba(250,204,21,0.1) 0%, rgba(15,23,42,0.95) 100%); border: 1px solid rgba(250,204,21,0.25); border-radius: 20px; padding: 20px; margin-bottom: 10px;">
<div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
<div>
<div style="font-weight: 800; font-size: 20px; color: white;">{player}</div>
<span style="background: rgba(250,204,21,0.2); color: #facc15; padding: 2px 10px; border-radius: 12px; font-size: 11px; font-weight: 600;">{team}</span>
</div>
<div style="text-align: right;">
<div style="font-size: 36px; font-weight: 900; color: #facc15; line-height: 1;">{float(val):.1f}</div>
<div style="color: #9ca3af; font-size: 11px;">{stat_col}</div>
</div>
</div>
<div style="display: flex; gap: 12px; justify-content: center; border-top: 1px solid rgba(148,163,184,0.2); padding-top: 10px; margin-top: 10px;">
<div><span style="color: #9ca3af; font-size: 11px;">2PT:</span> <span style="color: #e5e7eb; font-weight: 600;">{p2}</span></div>
<div><span style="color: #9ca3af; font-size: 11px;">3PT:</span> <span style="color: #e5e7eb; font-weight: 600;">{p3}</span></div>
<div><span style="color: #9ca3af; font-size: 11px;">TL:</span> <span style="color: #e5e7eb; font-weight: 600;">{tl}</span></div>
</div>
<div style="margin-top: 16px; background: rgba(0,0,0,0.25); padding: 12px; border-radius: 12px;">
<div style="color: #facc15; font-size: 10px; font-weight: bold; margin-bottom: 8px;">⚡ ÚLTIMOS PARTIDOS</div>
<div style="display: flex; justify-content: space-between; font-size: 12px; margin-bottom: 4px;">
<span style="color: #9ca3af;">{stat_col}</span>
<span style="color: white; font-family: monospace;">{trend}</span>
</div>
<div style="display: flex; justify-content: space-between; font-size: 12px;">
<span style="color: #9ca3af;">MIN</span>
<span style="color: white; font-family: monospace;">{mins_trend}</span>
</div>
</div>
</div>
"""
            st.markdown(html_card, unsafe_allow_html=True)
            
            # Botón nativo de Streamlit para la navegación
            if st.button(f"VER PERFIL COMPLETO →", key=f"btn_pc_{player}_{idx}", use_container_width=True):
                on_click_callback(player)
                st.rerun()

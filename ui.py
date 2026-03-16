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
    """
    Renderiza una tabla de jugadores donde cada fila es clickeable para navegar al perfil.
    Requiere una función callback que reciba el nombre del jugador.
    """
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
    Renderiza un listado NO editable (tarjetas + botón) para navegar a jugador.
    Esto evita los bugs de redimensionado de st.dataframe en secciones tipo 'Analizar Partido'.
    """
    if df_stats is None or df_stats.empty:
        st.info("Sin datos.")
        return

    if subtitle:
        st.caption(subtitle)

    stat_key = stat_col.lower()
    df_view = df_stats.copy().head(max_rows)

    for i, row in df_view.iterrows():
        player = row.get('player_name', '')
        team = row.get('team_abbreviation', '')
        val = row.get(stat_key, None)
        trend_key = f"trend_{stat_key}"
        trend = row.get(trend_key, None)
        mins_trend = row.get('trend_min', None)

        c1, c2 = st.columns([6, 2])
        with c1:
            st.markdown(f"""
            <div class="card-elevated" style="padding:14px 16px; margin-bottom:10px;">
                <div style="display:flex; justify-content:space-between; gap:12px; align-items:center;">
                    <div style="min-width:0;">
                        <div style="font-weight:700; font-size:15px; color:#ffffff; white-space:nowrap; overflow:hidden; text-overflow:ellipsis;">
                            {player}
                        </div>
                        <div style="margin-top:4px; display:flex; gap:8px; flex-wrap:wrap; align-items:center;">
                            <span class="pill-label">{team}</span>
                            <span style="color:#9ca3af; font-size:12px;">
                                {stat_col}: <b style="color:#e5e7eb;">{f"{float(val):.1f}" if val is not None else "-"}</b>
                            </span>
                        </div>
                        <div style="margin-top:6px; color:#a5b4fc; font-size:12px;">
                            RACHA: <span style="color:#e5e7eb;">{trend if trend is not None else "-"}</span>
                            &nbsp;&nbsp;•&nbsp;&nbsp; MIN: <span style="color:#e5e7eb;">{mins_trend if mins_trend is not None else "-"}</span>
                        </div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
        with c2:
            if st.button("Ver", key=f"btn_player_card_{stat_col}_{i}_{player}"):
                on_click_callback(player)
                st.rerun()

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
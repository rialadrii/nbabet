def render_clickable_player_table(df_stats, stat_col, jersey_map):
    if df_stats.empty:
        st.info("Sin datos.")
        return

    # Preparamos los datos
    # Ya no concatenamos nombre + equipo. Los mantenemos separados.
    cols_to_show = ['player_name', 'team_abbreviation', stat_col.lower(), f'trend_{stat_col.lower()}', 'trend_min']
    df_interactive = df_stats[cols_to_show].copy()
    
    # Renombramos las columnas para que se vean bien
    df_interactive.columns = ['JUGADOR', 'EQ', stat_col, 'RACHA', 'MIN']
    
    # === APLICACIÓN DE ESTILOS (COLOR) ===
    # Usamos Pandas Styler para colorear la columna 'EQ'
    # Color #ffbd45 es el amarillo/dorado de tus títulos
    styler = df_interactive.style.map(
        lambda x: 'color: #ffbd45; font-weight: bold;', 
        subset=['EQ']
    ).format({
        stat_col: "{:.1f}" # Aseguramos formato decimal para la stat principal
    })

    selection = st.dataframe(
        styler, # Pasamos el Styler con colores
        use_container_width=True,
        hide_index=True,
        on_select="rerun", 
        selection_mode="single-row",
        column_config={
            "JUGADOR": st.column_config.TextColumn("JUGADOR", width=None),
            # Hacemos la columna de equipo pequeña y centrada
            "EQ": st.column_config.TextColumn("EQ", width="small"), 
            
            # Ajuste de anchos
            stat_col: st.column_config.NumberColumn(stat_col, width=60),
            "RACHA": st.column_config.TextColumn("RACHA (Últ. Partidos)", width=150), 
            "MIN": st.column_config.TextColumn("MIN", width=115) 
        }
    )
    
    if len(selection.selection.rows) > 0:
        row_idx = selection.selection.rows[0]
        # Obtenemos el nombre directamente de la columna JUGADOR
        player_name = df_interactive.iloc[row_idx]['JUGADOR']
        navegar_a_jugador(player_name)
        st.rerun()

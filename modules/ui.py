import streamlit as st

def cargar_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Teko:wght@300..700&display=swap');

    /* --- 1. CENTRADO GLOBAL Y MÁRGENES --- */
    .block-container {
        max-width: 1000px !important;
        padding-top: 2rem;
        padding-bottom: 5rem;
        margin: 0 auto !important; /* CENTRADO CRÍTICO */
    }
    
    /* Forzar alineación al centro en textos y tablas */
    .stMarkdown, h1, h2, h3, p, li {
        text-align: center !important; 
    }
    
    /* Centrar contenido de tablas nativas de Streamlit */
    [data-testid="stDataFrame"] div, 
    [data-testid="stDataFrame"] th, 
    [data-testid="stDataFrame"] td {
        text-align: center !important;
        justify-content: center !important;
    }

    /* --- 2. TIPOGRAFÍA --- */
    h1 {
        font-family: 'Teko', sans-serif !important;
        font-size: 60px !important;
        text-transform: uppercase;
        color: white;
        margin-bottom: 10px;
    }
    h3 {
        font-family: 'Teko', sans-serif !important;
        font-size: 35px !important;
        color: #ffbd45;
        margin-top: 25px;
    }

    /* --- 3. FIX PARA MÓVIL (Scroll Horizontal) --- */
    .table-responsive {
        width: 100%;
        overflow-x: auto; /* ESTO HACE LA MAGIA EN MÓVIL */
        -webkit-overflow-scrolling: touch;
        margin-bottom: 1rem;
        border-radius: 8px;
        border: 1px solid #444;
    }

    table.custom-table {
        width: 100%;
        min-width: 600px; /* Fuerza ancho mínimo para activar scroll */
        border-collapse: collapse;
        font-size: 14px;
        margin: 0 auto;
    }
    table.custom-table th {
        background-color: #1f1f1f;
        color: #ffbd45;
        padding: 12px;
        text-align: center !important;
        border-bottom: 2px solid #555;
        white-space: nowrap;
    }
    table.custom-table td {
        padding: 10px;
        text-align: center !important;
        border-bottom: 1px solid #333;
        color: white;
    }

    /* --- 4. EXTRAS --- */
    .stButton > button {
        width: 100%;
        border-radius: 8px;
        background-color: #2d2d2d;
        color: white;
        border: 1px solid #555;
    }
    .stButton > button:hover {
        border-color: #ffbd45;
        color: #ffbd45;
    }
    footer {display: none !important;}
    </style>
    """, unsafe_allow_html=True)

def render_header():
    st.markdown("<h1>🏀 NBA ANALYZER PRO 🏀</h1>", unsafe_allow_html=True)

def mostrar_tabla_html(df, means_dict=None):
    if df.empty:
        st.info("Sin datos.")
        return

    # Función interna para colores condicionales
    def color_coding(val, avg, col_name):
        if not isinstance(val, (int, float)): return ""
        tolerance = 2 if col_name in ['REB', 'AST'] else 4
        if val > avg: return 'background-color: #1b5e20; color: white; font-weight: bold;' 
        elif val >= (avg - tolerance): return 'background-color: #fdd835; color: black; font-weight: bold;'
        return 'background-color: #b71c1c; color: white;'

    styler = df.style.format("{:.1f}", subset=[c for c in df.columns if c in ['PTS', 'REB', 'AST', 'MIN'] or 'PTS' in c])
    
    if means_dict:
        for col in ['PTS', 'REB', 'AST', 'MIN']:
            if col in df.columns and col in means_dict:
                styler.map(lambda x: color_coding(x, means_dict[col], col), subset=[col])
    
    html = styler.hide(axis="index").to_html(classes="custom-table", escape=False)
    
    # ENVOLTORIO CLAVE PARA MOVIL
    st.markdown(f'<div class="table-responsive">{html}</div>', unsafe_allow_html=True)

import streamlit as st
import pandas as pd
import plotly.express as px
import os
import re

# ======================================================
# CONFIGURAZIONE PAGINA
# ======================================================
st.set_page_config(
    page_title="Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ======================================================
# PASSWORD ADMIN
# ======================================================
ADMIN_CODE = "619"

# ======================================================
# TEMA SCURO
# ======================================================
st.markdown("""
<style>
html, body, [class*="css"] {
    background-color: #0e1117;
    color: #fafafa;
}
</style>
""", unsafe_allow_html=True)

# ======================================================
# SESSION STATE
# ======================================================
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

# ======================================================
# COLORI BASE PER STATO (NON PER TIPO)
# ======================================================
COLORI_STATO = {
    "lavorazione": "#1E88E5",
    "esitare": "#FB8C00",
    "scadute": "#D84315",
    "ok": "#2E7D32",
    "ko": "#C62828",
    "non lavorate": "#757575",
}

CATEGORIE_NASCOSTE_KEYWORDS = ["scadute"]

# ======================================================
# FUNZIONI
# ======================================================
def nome_mese_da_file(filename):
    nome = filename.replace("dashboard_", "").replace(".xlsx", "")
    return f"Dashboard {nome.replace('_', ' ').title()}"

def stato_da_categoria(nome):
    n = nome.lower()
    if "scadut" in n:
        return "scadute"
    if "esitare" in n:
        return "esitare"
    if "lavorazione" in n:
        return "lavorazione"
    if " ok" in n or n.endswith("ok"):
        return "ok"
    if " ko" in n or n.endswith("ko"):
        return "ko"
    if "non lavorate" in n:
        return "non lavorate"
    return "altro"

def colore_categoria(cat):
    stato = stato_da_categoria(cat)
    return COLORI_STATO.get(stato, "#9E9E9E")

def filtra_admin(df):
    if st.session_state.is_admin:
        return df
    mask = ~df["Categoria"].str.lower().str.contains("scadut", na=False)
    return df[mask]

def crea_grafico(df, titolo, tot):
    df = df.copy()
    df["Perc"] = df["Valore"] / tot * 100

    fig = px.pie(
        df,
        names="Categoria",
        values="Valore",
        title=titolo,
        color="Categoria",
        color_discrete_map={c: colore_categoria(c) for c in df["Categoria"]}
    )

    fig.update_traces(
        texttemplate="%{percent:.1%}<br>(%{value})",
        hovertemplate="<b>%{label}</b><br>%{value}<extra></extra>"
    )

    fig.update_layout(
        template="plotly_dark",
        title_x=0.5,
        legend_title_text=""
    )
    return fig

# ======================================================
# SIDEBAR
# ======================================================
with st.sidebar:
    st.title("🔐 Accesso")

    if not st.session_state.is_admin:
        codice = st.text_input("Codice amministratore", type="password")
        if st.button("Sblocca"):
            if codice.strip() == ADMIN_CODE:
                st.session_state.is_admin = True
                st.success("Accesso amministratore")
                st.rerun()
            else:
                st.error("Codice errato")
    else:
        st.success("Modalità amministratore")
        if st.button("Logout"):
            st.session_state.is_admin = False
            st.rerun()

    st.divider()
    vista = st.radio("Visualizzazione", ["Singolo negozio", "Totale tutti i negozi"])

# ======================================================
# CARICAMENTO FILE
# ======================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

files = sorted(f for f in os.listdir(DATA_DIR) if f.lower().endswith(".xlsx"))
file_map = {nome_mese_da_file(f): f for f in files}

mese = st.selectbox("📅 Seleziona mese", list(file_map.keys()))
df_raw = pd.read_excel(os.path.join(DATA_DIR, file_map[mese]), sheet_name="Main Per Grafico", header=None)

# ======================================================
# PARSER DEFINITIVO
# ======================================================
dati = {}
totali = {}

row = 0
while row < len(df_raw) - 2:
    header = df_raw.iloc[row, 0]

    if isinstance(header, str) and ";" in header:
        negozio = header.split(";", 1)[0].strip()

        row_cat = df_raw.iloc[row + 1]
        row_val = df_raw.iloc[row + 2]

        # totale = primo numero valido
        totale = None
        for v in row_val:
            if pd.notna(v) and str(v).strip().upper() != "#N/D":
                try:
                    totale = int(v)
                    break
                except:
                    pass

        categorie, valori = [], []

        prima_colonna = True

        for cat, val in zip(row_cat, row_val):
            if pd.isna(cat) or pd.isna(val):
                continue

            # usa la prima colonna SOLO come totale
            if prima_colonna:
                prima_colonna = False
                continue

            if str(val).strip().upper() == "#N/D":
                continue

            try:
                categorie.append(str(cat).strip())
                valori.append(float(val))
            except:
                pass


        if categorie and totale:
            tipo = categorie[0].split()[0]  # MNP / Family / Energia / altro
            dati.setdefault(negozio, {})[tipo] = pd.DataFrame({
                "Categoria": categorie,
                "Valore": valori
            })
            totali.setdefault(negozio, {})[tipo] = totale

        row += 3
    else:
        row += 1

# ======================================================
# VISUALIZZAZIONE
# ======================================================
if vista == "Singolo negozio":

    negozio = st.selectbox("📍 Punto vendita", sorted(dati.keys()))
    st.markdown(f"<h1 style='text-align:center;'>{mese} – {negozio}</h1>", unsafe_allow_html=True)

    tipi = list(dati[negozio].keys())
    cols = st.columns(len(tipi))

    for col, tipo in zip(cols, tipi):
        with col:
            df = filtra_admin(dati[negozio][tipo])
            tot = totali[negozio][tipo]
            st.plotly_chart(crea_grafico(df, f"{tipo} ({tot})", tot), use_container_width=True)

else:
    st.markdown(f"<h1 style='text-align:center;'>{mese} – TOTALE</h1>", unsafe_allow_html=True)

    tipi = sorted({t for n in dati for t in dati[n]})
    cols = st.columns(len(tipi))

    for col, tipo in zip(cols, tipi):
        frames, tot = [], 0
        for n in dati:
            if tipo in dati[n]:
                frames.append(dati[n][tipo])
                tot += totali[n][tipo]

        if frames:
            df = pd.concat(frames).groupby("Categoria", as_index=False).sum()
            df = filtra_admin(df)

            with col:
                st.plotly_chart(
                    crea_grafico(df, f"{tipo} TOTALE ({tot})", tot),
                    use_container_width=True
                )

# ======================================================
# FOOTER
# ======================================================
st.divider()
st.markdown("<p style='text-align:center;color:gray;font-size:0.8em;'>Dashboard | 2026</p>", unsafe_allow_html=True)

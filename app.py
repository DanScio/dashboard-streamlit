import streamlit as st
import pandas as pd
import plotly.express as px
import os

# ============================================
# CONFIGURAZIONE PAGINA
# ============================================
st.set_page_config(
    page_title="Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ============================================
# STATO SESSIONE
# ============================================
if "is_admin" not in st.session_state:
    st.session_state.is_admin = False

ADMIN_CODE = st.secrets.get("ADMIN_CODE", "")

# ============================================
# TEMA SCURO FORZATO
# ============================================
st.markdown("""
<style>
html, body, [class*="css"] {
    background-color: #0e1117;
    color: #fafafa;
}
</style>
""", unsafe_allow_html=True)

# ============================================
# PALETTE COLORI
# ============================================
COLORI_CATEGORIA = {
    "MNP in Lavorazione": "#1E88E5",
    "MNP Da Esitare Non Scadute": "#FB8C00",
    "MNP Da Esitare ScaduteT0": "#F4511E",
    "MNP Da Esitare ScaduteT1": "#D84315",
    "MNP OK": "#2E7D32",
    "MNP KO": "#C62828",
    "MNP Non Lavorate": "#757575",

    "Family in Lavorazione": "#1E88E5",
    "Family Da Esitare": "#FB8C00",
    "Family Da Esitare Scadute": "#D84315",
    "Family Ok": "#2E7D32",
    "Family Ko": "#C62828",
    "Family Non Lavorate": "#757575"
}

# ============================================
# CATEGORIE NASCOSTE PER UTENTE
# ============================================
CATEGORIE_NASCOSTE_UTENTE = {
    "MNP": [
        "MNP Da Esitare ScaduteT0",
        "MNP Da Esitare ScaduteT1"
    ],
    "Family": [
        "Family Da Esitare Scadute"
    ]
}

# ============================================
# FUNZIONI
# ============================================
def nome_mese_da_file(filename):
    nome = filename.replace("dashboard_", "").replace(".xlsx", "")
    nome = nome.replace("_", " ").title()
    return f"Dashboard {nome}"

def crea_grafico(df, titolo, tot):
    df = df.copy()
    df["PercTot"] = df["Valore"] / tot * 100

    fig = px.pie(
        df,
        names="Categoria",
        values="Valore",
        title=titolo,
        color="Categoria",
        color_discrete_map=COLORI_CATEGORIA
    )

    fig.update_traces(
        customdata=df["PercTot"],
        texttemplate="%{customdata:.1f}%<br>(%{value})",
        hovertemplate=(
            "<b>%{label}</b><br>"
            "Valore: %{value}<br>"
            "Percentuale su TOT: %{customdata:.1f}%"
            "<extra></extra>"
        )
    )

    fig.update_layout(
        template="plotly_dark",
        title_x=0.5,
        legend_title_text=""
    )

    return fig

def filtra_per_ruolo(df, tipo, is_admin):
    if df is None or is_admin:
        return df
    escluse = CATEGORIE_NASCOSTE_UTENTE.get(tipo, [])
    return df[~df["Categoria"].isin(escluse)]

def aggrega_tutti_negozi(dati, totali, tipo):
    df_list = []
    tot = 0

    for n in dati:
        if tipo in dati[n]:
            df_list.append(dati[n][tipo])
        if tipo in totali.get(n, {}):
            tot += totali[n][tipo]

    if not df_list or tot == 0:
        return None, None

    df_tot = (
        pd.concat(df_list)
        .groupby("Categoria", as_index=False)["Valore"]
        .sum()
    )

    return df_tot, tot

# ============================================
# ACCESSO AMMINISTRATORE
# ============================================
with st.expander("🔐 Accesso amministratore"):
    codice = st.text_input("Codice admin", type="password")
    if st.button("Sblocca"):
        if codice == ADMIN_CODE and ADMIN_CODE:
            st.session_state.is_admin = True
            st.success("Accesso amministratore abilitato")
        else:
            st.error("Codice non valido")

if st.session_state.is_admin:
    if st.button("🔒 Disattiva modalità amministratore"):
        st.session_state.is_admin = False
        st.experimental_rerun()

# ============================================
# NAVIGAZIONE
# ============================================
pagine = ["Vista Operativa"]
if st.session_state.is_admin:
    pagine.append("Vista Amministratore")

pagina = st.radio("🧭 Visualizzazione", pagine, horizontal=True)
is_admin = pagina == "Vista Amministratore"

# ============================================
# CARTELLA DATA
# ============================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

files = sorted(f for f in os.listdir(DATA_DIR) if f.lower().endswith(".xlsx"))
file_map = {nome_mese_da_file(f): f for f in files}

mese = st.selectbox("📅 Seleziona mese", list(file_map.keys()))
file_path = os.path.join(DATA_DIR, file_map[mese])

# ============================================
# LETTURA EXCEL
# ============================================
df_raw = pd.read_excel(file_path, sheet_name="Main Per Grafico", header=None)

dati = {}
totali = {}

row = 0
while row < len(df_raw) - 2:
    titolo = df_raw.iloc[row, 0]

    if isinstance(titolo, str) and ";" in titolo and "TOT" in titolo.upper():
        negozio, resto = titolo.split(";", 1)
        negozio = negozio.strip()
        tipo = "MNP" if "MNP" in resto.upper() else "Family"

        row_cat = df_raw.iloc[row + 1]
        row_val = df_raw.iloc[row + 2]

        cat, val = [], []

        for c in range(len(df_raw.columns)):
            if pd.isna(row_cat[c]) or pd.isna(row_val[c]):
                continue

            nome_cat = str(row_cat[c]).strip()
            low = nome_cat.lower()

            if low in ["tot", "mnp tot", "family tot"]:
                totali.setdefault(negozio, {})[tipo] = int(row_val[c])
                continue

            if low == "#n/d":
                continue

            cat.append(nome_cat)
            val.append(float(row_val[c]))

        if cat:
            dati.setdefault(negozio, {})[tipo] = pd.DataFrame({
                "Categoria": cat,
                "Valore": val
            })

        row += 3
    else:
        row += 1

# ============================================
# SELEZIONE NEGOZIO
# ============================================
opzioni = ["Tutti i negozi"] + sorted(dati.keys())
negozio = st.selectbox("📍 Punto vendita", opzioni)

if negozio == "Tutti i negozi":
    df_mnp, mnp_tot = aggrega_tutti_negozi(dati, totali, "MNP")
    df_family, family_tot = aggrega_tutti_negozi(dati, totali, "Family")
else:
    df_mnp = dati[negozio].get("MNP")
    df_family = dati[negozio].get("Family")
    mnp_tot = totali.get(negozio, {}).get("MNP")
    family_tot = totali.get(negozio, {}).get("Family")

df_mnp = filtra_per_ruolo(df_mnp, "MNP", is_admin)
df_family = filtra_per_ruolo(df_family, "Family", is_admin)

# ============================================
# TITOLO
# ============================================
titolo = f"{mese} – {negozio}"
st.markdown(f"<h1 style='text-align:center;'>{titolo}</h1>", unsafe_allow_html=True)

if is_admin:
    st.success("🔐 Modalità Amministratore")
else:
    st.info("👤 Modalità Operativa")


# ============================================
# LAYOUT GRAFICI
# ============================================
col1, col2 = st.columns(2)

with col1:
    if df_mnp is not None and mnp_tot:
        st.plotly_chart(crea_grafico(df_mnp, f"MNP ({mnp_tot})", mnp_tot), use_container_width=True)
    else:
        st.info("Nessun dato MNP")

with col2:
    if df_family is not None and family_tot:
        st.plotly_chart(crea_grafico(df_family, f"Family ({family_tot})", family_tot), use_container_width=True)
    else:
        st.info("Nessun dato Family")

# ============================================
# FOOTER
# ============================================
st.divider()
st.markdown(
    "<p style='text-align:center;color:gray;font-size:0.8em;'>Dashboard | 2026</p>",
    unsafe_allow_html=True
)

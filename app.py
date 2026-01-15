import streamlit as st
import pandas as pd
import plotly.express as px
import os

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
# PALETTE COLORI (COERENTE)
# ======================================================
COLORI_CATEGORIA = {
    # MNP
    "MNP in Lavorazione": "#1E88E5",
    "MNP Da Esitare Non Scadute": "#FB8C00",
    "MNP Da Esitare ScaduteT0": "#F4511E",
    "MNP Da Esitare ScaduteT1": "#D84315",
    "MNP OK": "#2E7D32",
    "MNP KO": "#C62828",
    "MNP Non Lavorate": "#757575",

    # FAMILY
    "Family in Lavorazione": "#1E88E5",
    "Family Da Esitare": "#FB8C00",
    "Family Da Esitare Scadute": "#D84315",
    "Family Ok": "#2E7D32",
    "Family Ko": "#C62828",
    "Family Non Lavorate": "#757575",

    # ENERGIA
    "Energia in Lavorazione": "#1E88E5",
    "Energia Da Esitare": "#FB8C00",
    "Energia Da Esitare Scadute": "#D84315",
    "Energia Ok": "#2E7D32",
    "Energia Ko": "#C62828",
    "Energia Non Lavorate": "#757575",
}

CATEGORIE_NASCOSTE = [
    "MNP Da Esitare ScaduteT0",
    "MNP Da Esitare ScaduteT1",
    "Family Da Esitare Scadute",
    "Energia Da Esitare Scadute"
]

# ======================================================
# FUNZIONI
# ======================================================
def nome_mese_da_file(filename):
    nome = filename.replace("dashboard_", "").replace(".xlsx", "")
    return f"Dashboard {nome.replace('_', ' ').title()}"

def filtra_categorie(df):
    if st.session_state.is_admin:
        return df
    return df[~df["Categoria"].isin(CATEGORIE_NASCOSTE)]

def crea_grafico(df, titolo, tot):
    df = df.copy()
    df["Perc"] = df["Valore"] / tot * 100

    fig = px.pie(
        df,
        names="Categoria",
        values="Valore",
        title=titolo,
        color="Categoria",
        color_discrete_map=COLORI_CATEGORIA
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
    vista = st.radio(
        "Visualizzazione",
        ["Singolo negozio", "Totale tutti i negozi"]
    )

# ======================================================
# CARICAMENTO FILE
# ======================================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_DIR = os.path.join(BASE_DIR, "data")

files = sorted(f for f in os.listdir(DATA_DIR) if f.lower().endswith(".xlsx"))
file_map = {nome_mese_da_file(f): f for f in files}

mese_selezionato = st.selectbox("📅 Seleziona mese", list(file_map.keys()))
file_path = os.path.join(DATA_DIR, file_map[mese_selezionato])

df_raw = pd.read_excel(file_path, sheet_name="Main Per Grafico", header=None)

# ======================================================
# PARSING EXCEL (ROBUSTO)
# ======================================================
dati = {}
totali = {}

row = 0
while row < len(df_raw) - 2:
    titolo = df_raw.iloc[row, 0]

    if isinstance(titolo, str) and ";" in titolo and "TOT" in titolo.upper():
        negozio, resto = titolo.split(";", 1)
        negozio = negozio.strip()

        if "MNP" in resto.upper():
            tipo = "MNP"
        elif "FAMILY" in resto.upper():
            tipo = "Family"
        elif "ENERGIA" in resto.upper():
            tipo = "Energia"
        else:
            row += 1
            continue

        row_cat = df_raw.iloc[row + 1]
        row_val = df_raw.iloc[row + 2]

        categorie, valori = [], []

        for col in range(len(df_raw.columns)):
            cat, val = row_cat[col], row_val[col]

            if pd.isna(cat) or pd.isna(val):
                continue

            if str(cat).strip().lower() in ["tot", f"{tipo.lower()} tot"]:
                totali.setdefault(negozio, {})[tipo] = int(val)
                continue

            if str(val).strip().upper() == "#N/D":
                continue

            try:
                categorie.append(str(cat).strip())
                valori.append(float(val))
            except:
                pass

        if categorie:
            dati.setdefault(negozio, {})[tipo] = pd.DataFrame({
                "Categoria": categorie,
                "Valore": valori
            })

        row += 3
    else:
        row += 1

# ======================================================
# VISUALIZZAZIONE
# ======================================================
if vista == "Singolo negozio":

    negozio = st.selectbox("📍 Punto vendita", sorted(dati.keys()))
    st.markdown(f"<h1 style='text-align:center;'>{mese_selezionato} – {negozio}</h1>", unsafe_allow_html=True)

    tipi = list(dati[negozio].keys())
    cols = st.columns(len(tipi))

    for col, tipo in zip(cols, tipi):
        with col:
            df = filtra_categorie(dati[negozio][tipo])
            tot = totali[negozio][tipo]
            st.plotly_chart(
                crea_grafico(df, f"{tipo} ({tot})", tot),
                use_container_width=True
            )

else:
    st.markdown(f"<h1 style='text-align:center;'>{mese_selezionato} – TOTALE</h1>", unsafe_allow_html=True)

    def aggrega(tipo):
        frames, tot = [], 0
        for n in dati:
            if tipo in dati[n]:
                frames.append(dati[n][tipo])
                tot += totali[n][tipo]
        if not frames:
            return None, 0
        df = pd.concat(frames).groupby("Categoria", as_index=False).sum()
        return filtra_categorie(df), tot

    tipi = sorted({t for n in dati for t in dati[n]})
    cols = st.columns(len(tipi))

    for col, tipo in zip(cols, tipi):
        with col:
            df, tot = aggrega(tipo)
            if df is not None:
                st.plotly_chart(
                    crea_grafico(df, f"{tipo} TOTALE ({tot})", tot),
                    use_container_width=True
                )

# ======================================================
# FOOTER
# ======================================================
st.divider()
st.markdown(
    "<p style='text-align:center;color:gray;font-size:0.8em;'>Dashboard | 2026</p>",
    unsafe_allow_html=True
)

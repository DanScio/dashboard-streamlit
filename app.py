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
# SECRET
# ======================================================
ADMIN_CODE = str(st.secrets.get("ADMIN_CODE", "")).strip()

# ======================================================
# PALETTE COLORI
# ======================================================
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

CATEGORIE_NASCOSTE = [
    "MNP Da Esitare ScaduteT0",
    "MNP Da Esitare ScaduteT1",
    "Family Da Esitare Scadute"
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
            "Percentuale: %{customdata:.1f}%"
            "<extra></extra>"
        )
    )

    fig.update_layout(
        template="plotly_dark",
        title_x=0.5,
        legend_title_text=""
    )

    return fig

# ======================================================
# SIDEBAR - LOGIN + MODALITÀ
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
# PARSING EXCEL
# ======================================================
dati = {}
totali = {}

row_idx = 0
while row_idx < len(df_raw) - 2:
    titolo = df_raw.iloc[row_idx, 0]

    if isinstance(titolo, str) and ";" in titolo and "TOT" in titolo.upper():
        negozio, resto = titolo.split(";", 1)
        negozio = negozio.strip()
        tipo = "MNP" if "MNP" in resto.upper() else "Family"

        row_cat = df_raw.iloc[row_idx + 1]
        row_val = df_raw.iloc[row_idx + 2]

        categorie, valori = [], []

        for col in range(len(df_raw.columns)):
            cat, val = row_cat[col], row_val[col]
            if pd.isna(cat) or pd.isna(val):
                continue

            if str(cat).strip().lower() in ["tot", "mnp tot", "family tot"]:
                totali.setdefault(negozio, {})[tipo] = int(val)
                continue

            categorie.append(str(cat).strip())
            valori.append(float(val))

        dati.setdefault(negozio, {})[tipo] = pd.DataFrame({
            "Categoria": categorie,
            "Valore": valori
        })

        row_idx += 3
    else:
        row_idx += 1

# ======================================================
# VISUALIZZAZIONE
# ======================================================
if vista == "Singolo negozio":

    negozio = st.selectbox("📍 Punto vendita", sorted(dati.keys()))

    st.markdown(
        f"<h1 style='text-align:center;'>{mese_selezionato} – {negozio}</h1>",
        unsafe_allow_html=True
    )

    col1, col2 = st.columns(2)

    with col1:
        st.plotly_chart(
            crea_grafico(
                filtra_categorie(dati[negozio]["MNP"]),
                f"MNP ({totali[negozio]['MNP']})",
                totali[negozio]["MNP"]
            ),
            use_container_width=True
        )

    with col2:
        st.plotly_chart(
            crea_grafico(
                filtra_categorie(dati[negozio]["Family"]),
                f"Family ({totali[negozio]['Family']})",
                totali[negozio]["Family"]
            ),
            use_container_width=True
        )

else:
    # =======================
    # TOTALE TUTTI I NEGOZI
    # =======================
    st.markdown(
        f"<h1 style='text-align:center;'>{mese_selezionato} – TOTALE</h1>",
        unsafe_allow_html=True
    )

    def aggrega(tipo):
        frames = []
        totale = 0
        for n in dati:
            df = dati[n].get(tipo)
            if df is not None:
                frames.append(df)
                totale += totali[n][tipo]

        df_tot = (
            pd.concat(frames)
            .groupby("Categoria", as_index=False)
            .sum()
        )

        return filtra_categorie(df_tot), totale

    col1, col2 = st.columns(2)

    df_mnp_tot, mnp_tot = aggrega("MNP")
    df_fam_tot, fam_tot = aggrega("Family")

    with col1:
        st.plotly_chart(
            crea_grafico(df_mnp_tot, f"MNP TOTALE ({mnp_tot})", mnp_tot),
            use_container_width=True
        )

    with col2:
        st.plotly_chart(
            crea_grafico(df_fam_tot, f"Family TOTALE ({fam_tot})", fam_tot),
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

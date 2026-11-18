
import pandas as pd
import streamlit as st

from data_loader import load_data


# ============================================================
# CONFIGURACIÓN
# ============================================================

st.set_page_config(
    page_title="Wind Farm | Project Control Tower",
    page_icon="🌬️",
    layout="wide"
)


# ============================================================
# CARGA DE DATOS
# ============================================================

@st.cache_data
def get_project_data():
    return load_data()


data = get_project_data()

# Datos compartidos por todas las páginas
st.session_state["project_data"] = data


# ============================================================
# CONTEXTO TEMPORAL GLOBAL
# ============================================================

tracking = (
    data["project_tracking"]
    .sort_values("TP")
    .reset_index(drop=True)
)

period_options = tracking["TP"].tolist()
default_tp = max(period_options)

if (
    "selected_tp" not in st.session_state
    or st.session_state["selected_tp"] not in period_options
):
    st.session_state["selected_tp"] = default_tp



# ============================================================
# SIDEBAR GLOBAL
# ============================================================

st.sidebar.title("🌬️ Project Control Tower")

st.sidebar.divider()

# Reporting Period
st.sidebar.subheader("Reporting Period")

selected_tp = st.sidebar.selectbox(
    "Tracking Period",
    options=period_options,
    format_func=lambda tp: (
        f"TP {int(tp):03d} · "
        f"{tracking.loc[
            tracking["TP"] == tp, "Status_Date"
        ].iloc[0]:%d/%m/%Y}"
    ),
    key="selected_tp"
)

selected_row = tracking.loc[
    tracking["TP"] == selected_tp
].iloc[0]

selected_date = pd.to_datetime(
    selected_row["Status_Date"]
)

st.session_state["selected_status_date"] = selected_date

st.sidebar.caption(
    f"Status Date: {selected_date:%d/%m/%Y}"
)

st.sidebar.caption(
    f"Period {period_options.index(selected_tp) + 1} "
    f"of {len(period_options)}"
)

# st.sidebar.divider()

# Menus
st.sidebar.subheader("Menus")




# ============================================================
# NAVEGACIÓN
# ============================================================

page_overview = st.Page(
    "pages/1_Executive_Overview.py",
    title="Executive Overview",
    icon="📊",
    default=True
)

page_schedule = st.Page(
    "pages/2_Schedule_Critical_Path.py",
    title="Schedule & Critical Path",
    icon="📅"
)

page_cost = st.Page(
    "pages/3_Cost_Performance.py",
    title="Cost & Performance",
    icon="💶"
)

page_supply = st.Page(
    "pages/4_Supply_Chain_Risk.py",
    title="Supply Chain & Risk",
    icon="🚚"
)

page_scenarios = st.Page(
    "pages/5_Scenario_Analysis.py",
    title="Scenario Analysis",
    icon="📈"
)

page_simulation = st.Page(
    "pages/6_Simulation_Lab.py",
    title="Simulation Lab",
    icon="🧪"
)

page_decision = st.Page(
    "pages/7_Decision_Cockpit.py",
    title="Decision Cockpit",
    icon="🎯"
)

pages = [
    page_overview,
    page_schedule,
    page_cost,
    page_supply,
    page_scenarios,
    page_simulation,
    page_decision
]

# Ocultar navegación automática
navigation = st.navigation(
    pages,
    position="hidden"
)

# Menú personalizado
st.sidebar.subheader("Menus")

st.sidebar.page_link(
    page_overview,
    label="Executive Overview",
    icon="📊"
)

st.sidebar.page_link(
    page_schedule,
    label="Schedule & Critical Path",
    icon="📅"
)

st.sidebar.page_link(
    page_cost,
    label="Cost & Performance",
    icon="💶"
)

st.sidebar.page_link(
    page_supply,
    label="Supply Chain & Risk",
    icon="🚚"
)

st.sidebar.page_link(
    page_scenarios,
    label="Scenario Analysis",
    icon="📈"
)

st.sidebar.page_link(
    page_simulation,
    label="Simulation Lab",
    icon="🧪"
)

st.sidebar.page_link(
    page_decision,
    label="Decision Cockpit",
    icon="🎯"
)

navigation.run()


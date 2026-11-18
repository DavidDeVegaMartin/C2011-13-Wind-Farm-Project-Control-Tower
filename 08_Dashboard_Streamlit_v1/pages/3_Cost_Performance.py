from pathlib import Path

import pandas as pd
import streamlit as st
import plotly.express as px
import plotly.graph_objects as go

# ============================================================
# 1. CONFIGURACIÓN Y DATOS
# ============================================================

st.title("Cost & Performance")
st.caption(
    "Economic performance, earned value analysis " "and planned budget exposure."
)

if "project_data" not in st.session_state:
    st.error(
        "Project data is not available. "
        "Please launch the application through app.py."
    )
    st.stop()

data = st.session_state["project_data"]

pt = data["project_tracking"].copy()
sc = data["schedule_control"].copy()

selected_tp = st.session_state.get("selected_tp")

# Normalización de fechas y tipos
pt["Status_Date"] = pd.to_datetime(pt["Status_Date"], errors="coerce")

for col in ["PV", "EV", "AC", "CPI", "CV", "SPI", "SPI_t"]:
    pt[col] = pd.to_numeric(pt[col], errors="coerce")

for col in ["Total_Cost_Plan", "Fixed_Cost", "Variable_Cost", "Resource_Cost"]:
    sc[col] = pd.to_numeric(sc[col], errors="coerce")


# ============================================================
# 2. PERIODO DE REFERENCIA
# ============================================================

if selected_tp is not None:
    selected_row = pt[
        pd.to_numeric(pt["TP"], errors="coerce")
        == pd.to_numeric(selected_tp, errors="coerce")
    ]
else:
    selected_row = pd.DataFrame()

if selected_row.empty:
    selected_row = pt.sort_values("TP").tail(1)

selected_row = selected_row.iloc[0]

selected_date = selected_row["Status_Date"]
selected_tp_value = selected_row["TP"]

pv = selected_row["PV"]
ev = selected_row["EV"]
ac = selected_row["AC"]
cpi = selected_row["CPI"]
cv = selected_row["CV"]

bac = sc["Total_Cost_Plan"].sum()

# Evitar divisiones por cero
cost_overrun = ac - ev
budget_consumed = ac / bac if bac else 0
earned_budget_ratio = ev / bac if bac else 0


# ============================================================
# 3. FUNCIONES AUXILIARES
# ============================================================


def eur_millions(value):
    if pd.isna(value):
        return "N/D"
    return f"{value / 1_000_000:,.2f} M€"


def eur_full(value):
    if pd.isna(value):
        return "N/D"
    return f"{value:,.0f} €"


def percentage(value):
    if pd.isna(value):
        return "N/D"
    return f"{value:.1%}"


def metric_delta(value, inverse=False):
    """
    Devuelve una etiqueta sencilla para las métricas económicas.
    En CV, un valor negativo es desfavorable.
    """
    if pd.isna(value):
        return None

    if inverse:
        return "Desfavorable" if value < 0 else "Favorable"

    return "Favorable" if value >= 1 else "Desfavorable"


# ============================================================
# 4. EXECUTIVE COST SUMMARY
# ============================================================

st.divider()
st.subheader("1. Executive Cost Summary")

st.caption(f"Reporting period: TP {selected_tp_value} · " f"{selected_date:%d %b %Y}")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Budget at Completion", eur_millions(bac))

with col2:
    st.metric("Actual Cost", eur_millions(ac))

with col3:
    st.metric("Earned Value", eur_millions(ev))

with col4:
    st.metric(
        "Cost Performance Index",
        f"{cpi:.3f}" if pd.notna(cpi) else "N/D",
        metric_delta(cpi),
    )

with col5:
    st.metric("Cost Variance", eur_millions(cv), metric_delta(cv, inverse=True))

# Lectura ejecutiva
st.markdown("#### Management interpretation")

if pd.notna(cpi) and cpi < 1:
    st.warning(
        f"The project is experiencing unfavorable cost performance. "
        f"For every euro spent, approximately {cpi:.2f} € of earned "
        f"value is being generated."
    )
elif pd.notna(cpi):
    st.success("Cost performance is currently at or above the planned level.")

if pd.notna(cv):
    if cv < 0:
        st.write(
            f"The cumulative cost variance is **{eur_millions(cv)}**. "
            "Actual expenditure exceeds the value of work performed."
        )
    else:
        st.write(
            f"The cumulative cost variance is favorable: " f"**{eur_millions(cv)}**."
        )

st.caption(
    "CV = EV − AC. CPI = EV / AC. "
    "A CPI below 1 indicates unfavorable cost efficiency."
)


# ============================================================
# 5. EARNED VALUE ANALYSIS
# ============================================================

st.divider()
st.subheader("2. Earned Value Analysis")

st.markdown(
    "Historical evolution of planned value, earned value " "and actual expenditure."
)

evm = pt.sort_values("Status_Date").copy()

evm_long = evm.melt(
    id_vars=["Status_Date", "TP"],
    value_vars=["PV", "EV", "AC"],
    var_name="Indicator",
    value_name="Amount",
)

evm_long["Amount_M"] = evm_long["Amount"] / 1_000_000

fig_evm = px.line(
    evm_long,
    x="Status_Date",
    y="Amount_M",
    color="Indicator",
    markers=False,
    labels={
        "Status_Date": "Tracking date",
        "Amount_M": "Amount (€M)",
        "Indicator": "Indicator",
    },
    color_discrete_map={"PV": "#7F8C8D", "EV": "#2980B9", "AC": "#E67E22"},
)

fig_evm.add_shape(
    type="line",
    x0=selected_date,
    x1=selected_date,
    y0=0,
    y1=1,
    xref="x",
    yref="paper",
    line=dict(color="#555555", dash="dash", width=1),
)

fig_evm.add_annotation(
    x=selected_date,
    y=1,
    xref="x",
    yref="paper",
    text="Selected period",
    showarrow=False,
    yshift=12,
)

fig_evm.update_layout(
    height=390,
    hovermode="x unified",
    legend_title_text="",
    margin=dict(l=15, r=15, t=35, b=15),
    yaxis_title="Cumulative amount (€M)",
    xaxis_title="",
)

st.plotly_chart(fig_evm, use_container_width=True)


# ============================================================
# 6. COST PERFORMANCE
# ============================================================

st.divider()
st.subheader("3. Cost Performance")

col1, col2 = st.columns(2)

with col1:
    st.markdown("#### Cost Performance Index")

    fig_cpi = go.Figure()

    fig_cpi.add_trace(
        go.Scatter(
            x=evm["Status_Date"],
            y=evm["CPI"],
            mode="lines",
            name="CPI",
            line=dict(color="#2980B9", width=2),
        )
    )

    fig_cpi.add_hline(
        y=1, line_dash="dash", line_color="#7F8C8D", annotation_text="CPI = 1.00"
    )

    fig_cpi.add_vline(x=selected_date, line_dash="dot", line_color="#555555")

    fig_cpi.update_layout(
        height=330,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title="",
        yaxis_title="CPI",
        showlegend=False,
    )

    st.plotly_chart(fig_cpi, use_container_width=True)

with col2:
    st.markdown("#### Cumulative Cost Variance")

    fig_cv = go.Figure()

    fig_cv.add_trace(
        go.Scatter(
            x=evm["Status_Date"],
            y=evm["CV"] / 1_000_000,
            mode="lines",
            name="Cost Variance",
            fill="tozeroy",
            line=dict(color="#E67E22", width=2),
        )
    )

    fig_cv.add_hline(y=0, line_dash="dash", line_color="#7F8C8D")

    fig_cv.add_vline(x=selected_date, line_dash="dot", line_color="#555555")

    fig_cv.update_layout(
        height=330,
        margin=dict(l=10, r=10, t=20, b=10),
        xaxis_title="",
        yaxis_title="Cost variance (€M)",
        showlegend=False,
    )

    st.plotly_chart(fig_cv, use_container_width=True)

st.caption(
    "The selected reporting period is highlighted in both charts. "
    "Negative cost variance indicates unfavorable cost performance."
)


# ============================================================
# 7. BUDGET STRUCTURE
# ============================================================

st.divider()
st.subheader("4. Budget Structure")

fixed_cost = sc["Fixed_Cost"].sum()
variable_cost = sc["Variable_Cost"].sum()
resource_cost = sc["Resource_Cost"].sum()

col1, col2 = st.columns([1.15, 1])

with col1:
    st.markdown("#### Planned cost composition")

    budget_mix = pd.DataFrame(
        {
            "Cost type": ["Fixed costs", "Variable costs", "Resource costs"],
            "Amount": [fixed_cost, variable_cost, resource_cost],
        }
    )

    budget_mix = budget_mix[budget_mix["Amount"] > 0]

    fig_budget = px.pie(
        budget_mix,
        names="Cost type",
        values="Amount",
        hole=0.58,
        color="Cost type",
        color_discrete_map={
            "Fixed costs": "#2980B9",
            "Variable costs": "#E67E22",
            "Resource costs": "#7F8C8D",
        },
    )

    fig_budget.update_traces(textposition="inside", texttemplate="%{percent:.1%}")

    fig_budget.update_layout(
        height=340,
        showlegend=True,
        legend_title_text="",
        margin=dict(l=10, r=10, t=15, b=10),
    )

    st.plotly_chart(fig_budget, use_container_width=True)

with col2:
    st.markdown("#### Budget breakdown")

    budget_table = pd.DataFrame(
        {
            "Cost component": [
                "Fixed costs",
                "Variable costs",
                "Resource costs",
                "Total planned cost",
            ],
            "Amount (€)": [fixed_cost, variable_cost, resource_cost, bac],
        }
    )

    budget_table["Share"] = budget_table["Amount (€)"] / bac if bac else 0

    st.dataframe(
        budget_table,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Amount (€)": st.column_config.NumberColumn(format="€ %.2f"),
            "Share": st.column_config.NumberColumn(format="%.1f%%"),
        },
    )

    st.markdown("#### Cost data availability")

    actual_cost_missing = sc["Actual_Cost"].isna().sum()
    activity_count = len(sc)

    st.metric(
        "Activities without actual cost", f"{actual_cost_missing} / {activity_count}"
    )

    st.info(
        "Actual costs are available at project level through EVM, "
        "but are not allocated to individual activities. "
        "Activity-level cost overruns cannot therefore be calculated."
    )


# ============================================================
# 8. COST EXPOSURE
# ============================================================

st.divider()
st.subheader("5. Cost Exposure")

st.markdown(
    "Analysis of the activities with the highest planned cost "
    "and their contribution to total budget exposure."
)

# ------------------------------------------------------------
# Activity cost ranking
# ------------------------------------------------------------

cost_ranking = sc[
    [
        "ID",
        "Name",
        "WBS",
        "Total_Cost_Plan",
        "Fixed_Cost",
        "Variable_Cost",
        "Resource_Cost",
    ]
].copy()

cost_ranking = cost_ranking.sort_values("Total_Cost_Plan", ascending=False)

top_n = 15
top_cost = cost_ranking.head(top_n).copy()

top_cost["Activity"] = top_cost["ID"].astype(str) + " — " + top_cost["Name"].astype(str)

top_cost["Share_Budget"] = top_cost["Total_Cost_Plan"] / bac if bac else 0

top_15_total = top_cost["Total_Cost_Plan"].sum()
top_15_share = top_15_total / bac if bac else 0

top_15_fixed = top_cost["Fixed_Cost"].sum()
top_15_variable = top_cost["Variable_Cost"].sum()
top_15_resource = top_cost["Resource_Cost"].sum()

# ------------------------------------------------------------
# Budget exposure indicators
# ------------------------------------------------------------

col1, col2, col3 = st.columns(3)

col1.metric(f"Top {top_n} activities", eur_millions(top_15_total))

col2.metric("Share of total budget", percentage(top_15_share))

col3.metric(
    "Fixed cost share within Top 15",
    percentage(top_15_fixed / top_15_total if top_15_total else 0),
)

# ------------------------------------------------------------

# ------------------------------------------------------------
# Cost composition by activity
# ------------------------------------------------------------

st.markdown("#### Cost composition by activity")

view_mode = st.radio(
    "View",
    [
        "Highest planned cost activities",
        "Budget concentration",
    ],
    horizontal=True,
    key="cost_exposure_view",
)

cost_components = top_cost.melt(
    id_vars=["ID", "Activity", "Total_Cost_Plan"],
    value_vars=[
        "Fixed_Cost",
        "Variable_Cost",
        "Resource_Cost",
    ],
    var_name="Cost_Component",
    value_name="Amount",
)

cost_components["Cost_Component"] = cost_components["Cost_Component"].map(
    {
        "Fixed_Cost": "Fixed costs",
        "Variable_Cost": "Variable costs",
        "Resource_Cost": "Resource costs",
    }
)

cost_components = cost_components[cost_components["Amount"] > 0].copy()

# Select absolute amounts or percentage of total budget
if view_mode == "Highest planned cost activities":

    cost_components["Display_Value"] = cost_components["Amount"]

    cost_components["Display_Label"] = cost_components["Amount"].apply(
        lambda x: (f"€{x / 1_000_000:.2f}M" if x >= 1_000_000 else f"€{x / 1_000:.0f}k")
    )

    x_title = "Planned cost (€)"
    hover_format = ":,.0f"

else:

    cost_components["Display_Value"] = (
        cost_components["Amount"] / bac * 100 if bac else 0
    )

    cost_components["Display_Label"] = cost_components["Display_Value"].apply(
        lambda x: f"{x:.2f}%"
    )

    x_title = "Share of total budget (%)"
    hover_format = ".2f"

# Plotly chart
fig_exposure = px.bar(
    cost_components.sort_values("Total_Cost_Plan"),
    x="Display_Value",
    y="Activity",
    color="Cost_Component",
    text="Display_Label",
    orientation="h",
    color_discrete_map={
        "Fixed costs": "#2980B9",
        "Variable costs": "#E67E22",
        "Resource costs": "#7F8C8D",
    },
    hover_data={
        "Amount": ":,.0f",
        "Total_Cost_Plan": ":,.0f",
        "Display_Value": False,
        "Display_Label": False,
    },
    labels={
        "Display_Value": x_title,
        "Activity": "",
        "Cost_Component": "Cost component",
        "Amount": "Component cost (€)",
        "Total_Cost_Plan": "Total activity cost (€)",
    },
)

fig_exposure.update_traces(
    textposition="inside",
    insidetextanchor="middle",
    textfont=dict(
        color="white",
        size=13,
    ),
    cliponaxis=False,
)

fig_exposure.update_layout(
    barmode="stack",
    height=570,
    margin=dict(l=10, r=30, t=15, b=10),
    xaxis_title=x_title,
    yaxis_title="",
    legend_title_text="",
    uniformtext_minsize=8,
    uniformtext_mode="hide",
)

st.plotly_chart(fig_exposure, use_container_width=True)

# ------------------------------------------------------------

# ------------------------------------------------------------
# Detailed activity cost breakdown
# ------------------------------------------------------------

with st.expander("Detailed activity cost breakdown"):

    display_cost = top_cost[
        [
            "ID",
            "Name",
            "WBS",
            "Fixed_Cost",
            "Variable_Cost",
            "Resource_Cost",
            "Total_Cost_Plan",
            "Share_Budget",
        ]
    ].rename(
        columns={
            "ID": "Activity ID",
            "Name": "Activity",
            "WBS": "WBS",
            "Fixed_Cost": "Fixed cost",
            "Variable_Cost": "Variable cost",
            "Resource_Cost": "Resource cost",
            "Total_Cost_Plan": "Total planned cost",
            "Share_Budget": "Budget share (%)",
        }
    )

    display_cost["Budget share (%)"] *= 100

    st.dataframe(
        display_cost,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Fixed cost": st.column_config.NumberColumn(format="€ %.0f"),
            "Variable cost": st.column_config.NumberColumn(format="€ %.0f"),
            "Resource cost": st.column_config.NumberColumn(format="€ %.0f"),
            "Total planned cost": st.column_config.NumberColumn(format="€ %.0f"),
            "Budget share (%)": st.column_config.NumberColumn(format="%.2f%%"),
        },
    )

# ------------------------------------------------------------
# Top 15 cost composition summary
# ------------------------------------------------------------

st.caption(
    f"Top {top_n} composition: "
    f"Fixed costs {eur_millions(top_15_fixed)} · "
    f"Variable costs {eur_millions(top_15_variable)} · "
    f"Resource costs {eur_millions(top_15_resource)}. "
    "All values represent planned costs."
)


# ============================================================
# 9. MANAGEMENT CONCLUSION
# ============================================================

st.divider()
st.subheader("Management Takeaways")

takeaways = []

if pd.notna(cpi) and cpi < 1:
    takeaways.append(
        f"**Cost efficiency:** CPI of {cpi:.3f} indicates "
        "unfavorable cost performance."
    )

if pd.notna(cv) and cv < 0:
    takeaways.append(
        f"**Economic exposure:** cumulative cost variance "
        f"stands at {eur_millions(cv)}."
    )

takeaways.append(
    f"**Budget concentration:** the {top_n} highest-cost activities "
    f"represent {top_15_share:.1%} of the planned budget."
)

takeaways.append(
    "**Cost visibility:** actual activity-level cost data "
    "is not available, limiting detailed attribution of overruns."
)

for item in takeaways:
    st.markdown(f"- {item}")

st.caption(
    "Economic performance is assessed using project-level EVM data. "
    "Activity cost exposure is based on planned costs, not actual costs."
)

print(
    sc.groupby("Execution_Status").agg(
        Activities=("ID", "nunique"), Planned_Cost=("Total_Cost_Plan", "sum")
    )
)

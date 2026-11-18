

import io

import numpy as np
import pandas as pd
import plotly.graph_objects as go
import streamlit as st


# ============================================================
# CONTEXTO GLOBAL
# ============================================================

data = st.session_state.get("project_data")

if data is None:
    st.error("Project data is not available.")
    st.stop()

tracking = data["project_tracking"].copy()

tracking["Status_Date"] = pd.to_datetime(
    tracking["Status_Date"]
)

tracking = (
    tracking
    .sort_values("TP")
    .reset_index(drop=True)
)

selected_tp = st.session_state["selected_tp"]

selected_row = tracking.loc[
    tracking["TP"] == selected_tp
].iloc[0]

selected_date = pd.to_datetime(
    st.session_state["selected_status_date"]
)

historical_data = tracking.loc[
    tracking["TP"] <= selected_tp
].copy()

cpm_summary = data["cpm_project_summary"].iloc[0]


# ============================================================
# FUNCIONES AUXILIARES
# ============================================================

def format_eur_millions(value):
    return f"{value / 1_000_000:,.2f} M€"


def format_index(value):
    return f"{value:.3f}"


def format_date(value):
    if pd.isna(value):
        return "N/D"
    return pd.to_datetime(value).strftime("%d/%m/%Y")


def format_days(value):
    if pd.isna(value):
        return "N/D"
    return f"{value:+.0f} days"


def render_activity_cards(frame, view):
    """
    Muestra un máximo de cinco actividades en tarjetas.
    """

    if frame.empty:
        st.info(
            "No pending supply-alert activities "
            "at the selected tracking period."
        )
        return

    cards = frame.head(5)

    for start in range(0, len(cards), 2):

        card_columns = st.columns(2)

        for column, (_, activity) in zip(
            card_columns,
            cards.iloc[start:start + 2].iterrows()
        ):

            with column:

                with st.container(border=True):

                    st.markdown(
                        f"**ID {int(activity['ID'])} · "
                        f"{activity['Name']}**"
                    )

                    st.caption(
                        f"{activity['Execution_State']} · "
                        f"{activity['Material_Alarm']} · "
                        f"Risk {activity['Supply_Risk_Score']}/100"
                    )

                    if view == "project":

                        st.write(
                            f"**Buffer excess:** "
                            f"{format_days(activity['Supply_Buffer_Excess_Days'])}"
                        )

                        st.write(
                            f"**CPM float:** "
                            f"{format_days(activity['Total_Float'])}"
                        )

                        st.write(
                            f"**Supply delay:** "
                            f"{format_days(activity['Supply_Delay_Days'])}"
                        )

                    elif view == "schedule":

                        st.write(
                            f"**CPM float:** "
                            f"{format_days(activity['Total_Float'])}"
                        )

                        st.write(
                            f"**Baseline start:** "
                            f"{format_date(activity['Baseline_Start'])}"
                        )

                        days_relative = int(
                            activity["Days_vs_Baseline_Start"]
                        )

                        if days_relative > 0:
                            st.write(
                                f"**Baseline start passed:** "
                                f"{days_relative} days ago"
                            )
                        elif days_relative < 0:
                            st.write(
                                f"**Time until baseline start:** "
                                f"{abs(days_relative)} days"
                            )
                        else:
                            st.write(
                                "**Baseline start:** Today"
                            )

                        st.write(
                            f"**Supply alarm:** "
                            f"{activity['Material_Alarm']}"
                        )

                    elif view == "supply":

                        st.write(
                            f"**Supply delay:** "
                            f"{format_days(activity['Supply_Delay_Days'])}"
                        )

                        st.write(
                            f"**Buffer excess:** "
                            f"{format_days(activity['Supply_Buffer_Excess_Days'])}"
                        )

                        st.write(
                            f"**CPM float:** "
                            f"{format_days(activity['Total_Float'])}"
                        )


# ============================================================
# CABECERA
# ============================================================

st.title("Executive Overview")

st.caption(
    f"Project status at {format_date(selected_date)} "
    f"· Tracking Period {int(selected_tp):03d}"
)

st.divider()


# ============================================================
# PROJECT PERFORMANCE
# ============================================================

st.subheader("Project Performance")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Schedule Performance Index",
    format_index(float(selected_row["SPI"]))
)

col2.metric(
    "Time-based SPI",
    format_index(float(selected_row["SPI_t"]))
)

sv_t = pd.to_numeric(
    str(selected_row["SV_t"]).strip().lower().replace("d", ""),
    errors="coerce"
)

col3.metric(
    "Schedule Variance (Time)",
    f"{sv_t:+.0f} days" if pd.notna(sv_t) else "N/D"
)

col4.metric(
    "Cost Performance Index",
    format_index(float(selected_row["CPI"]))
)


# ============================================================
# FINANCIAL PERFORMANCE
# ============================================================

st.subheader("Financial Performance")

col1, col2, col3 = st.columns(3)

col1.metric(
    "Planned Value (PV)",
    format_eur_millions(selected_row["PV"])
)

col2.metric(
    "Earned Value (EV)",
    format_eur_millions(selected_row["EV"])
)

col3.metric(
    "Actual Cost (AC)",
    format_eur_millions(selected_row["AC"])
)


# ============================================================
# PROJECT VARIANCES
# ============================================================

st.subheader("Project Variances")

var1, var2 = st.columns(2)

var1.metric(
    "Schedule Variance (SV)",
    format_eur_millions(selected_row["SV"])
)

var2.metric(
    "Cost Variance (CV)",
    format_eur_millions(selected_row["CV"])
)


st.divider()


# ============================================================
# EVM — HISTORICAL EVOLUTION
# ============================================================

st.subheader("Earned Value Management — Historical Evolution")

fig_evm = go.Figure()

fig_evm.add_trace(
    go.Scatter(
        x=historical_data["Status_Date"],
        y=historical_data["PV"],
        mode="lines",
        name="PV · Planned Value",
        line=dict(width=2)
    )
)

fig_evm.add_trace(
    go.Scatter(
        x=historical_data["Status_Date"],
        y=historical_data["EV"],
        mode="lines",
        name="EV · Earned Value",
        line=dict(width=2)
    )
)

fig_evm.add_trace(
    go.Scatter(
        x=historical_data["Status_Date"],
        y=historical_data["AC"],
        mode="lines",
        name="AC · Actual Cost",
        line=dict(width=2)
    )
)

fig_evm.update_layout(
    height=350,
    hovermode="x unified",
    xaxis_title="Tracking date",
    yaxis_title="Value (€)",
    yaxis=dict(tickformat=",.0f"),
    legend=dict(
        orientation="h",
        y=1.12,
        x=0
    ),
    margin=dict(l=20, r=20, t=35, b=20)
)

st.plotly_chart(
    fig_evm,
    use_container_width=True
)


# ============================================================
# PERFORMANCE INDICES — HISTORICAL EVOLUTION
# ============================================================

st.subheader("Performance Indices — Historical Evolution")

fig_indices = go.Figure()

fig_indices.add_trace(
    go.Scatter(
        x=historical_data["Status_Date"],
        y=historical_data["SPI"],
        mode="lines",
        name="SPI"
    )
)

fig_indices.add_trace(
    go.Scatter(
        x=historical_data["Status_Date"],
        y=historical_data["SPI_t"],
        mode="lines",
        name="SPI(t)"
    )
)

fig_indices.add_trace(
    go.Scatter(
        x=historical_data["Status_Date"],
        y=historical_data["CPI"],
        mode="lines",
        name="CPI"
    )
)

fig_indices.add_hline(
    y=1.0,
    line_dash="dash",
    annotation_text="Reference = 1.00"
)

fig_indices.update_layout(
    height=330,
    hovermode="x unified",
    xaxis_title="Tracking date",
    yaxis_title="Performance index",
    legend=dict(
        orientation="h",
        y=1.12,
        x=0
    ),
    margin=dict(l=20, r=20, t=35, b=20)
)

st.plotly_chart(
    fig_indices,
    use_container_width=True
)


st.divider()


# ============================================================
# BASELINE SCHEDULE — CPM REFERENCE
# ============================================================

st.subheader("Baseline Schedule — CPM Reference")

st.caption(
    "Static reference from the project CPM network. "
    "It is not recalculated historically for each tracking period."
)

base1, base2, base3, base4 = st.columns(4)

base1.metric(
    "Baseline Duration",
    f"{int(cpm_summary['Project_Duration_CPM_Days'])} days"
)

base2.metric(
    "Activities",
    f"{int(cpm_summary['Activities'])}"
)

base3.metric(
    "Dependencies",
    f"{int(cpm_summary['Dependencies'])}"
)

base4.metric(
    "Critical Activities",
    f"{int(cpm_summary['Critical_Activities'])}"
)


st.divider()


# ============================================================
# PROJECT ALERTS & MANAGEMENT ATTENTION
# ============================================================

st.subheader("Project Alerts & Management Attention")

# ------------------------------------------------------------
# 1. Consolidated supply exposure
# ------------------------------------------------------------

schedule = data["schedule_control"].copy()

supply = schedule.loc[
    schedule["Supply_Alert"] == True
].copy()

# ------------------------------------------------------------
# 2. Historical execution state at selected TP
# ------------------------------------------------------------

tracking_tp = data["activity_tracking"].loc[
    lambda x: x["TP"] == selected_tp
].copy()

tracking_tp["Status_Date"] = pd.to_datetime(
    tracking_tp["Status_Date"]
)

tracking_tp = tracking_tp[
    [
        "Activity_ID",
        "Pct_Complete",
        "Actual_Start",
        "Actual_Duration_Days",
        "Status_Date"
    ]
].rename(
    columns={
        "Actual_Start": "Tracking_Actual_Start"
    }
)

supply = supply.merge(
    tracking_tp,
    left_on="ID",
    right_on="Activity_ID",
    how="left"
)

# ------------------------------------------------------------
# 3. Execution classification
# ------------------------------------------------------------

supply["Execution_State"] = np.select(
    [
        supply["Pct_Complete"].isna(),
        supply["Pct_Complete"] >= 1,
        supply["Pct_Complete"].between(
            0.000001,
            0.999999
        )
    ],
    [
        "Unknown",
        "Completed",
        "In progress"
    ],
    default="Not started"
)

# Known pending activities
pending_supply = supply.loc[
    supply["Execution_State"].isin(
        ["Not started", "In progress"]
    )
].copy()

# Completed activities
completed_supply = supply.loc[
    supply["Execution_State"] == "Completed"
].copy()

# Unknown execution state
unknown_supply = supply.loc[
    supply["Execution_State"] == "Unknown"
].copy()

# ------------------------------------------------------------
# 4. Alarm hierarchy
# ------------------------------------------------------------

alarm_order = {
    "CRITICAL": 0,
    "WARNING": 1,
    "OK": 2
}

for frame in [pending_supply, supply]:

    frame["Alarm_Order"] = (
        frame["Material_Alarm"]
        .map(alarm_order)
        .fillna(3)
    )
    
# Temporal position relative to baseline start
selected_date_normalized = pd.Timestamp(selected_date).normalize()

pending_supply["Baseline_Start"] = pd.to_datetime(
    pending_supply["Baseline_Start"]
).dt.normalize()

pending_supply["Days_vs_Baseline_Start"] = (
    selected_date_normalized
    - pending_supply["Baseline_Start"]
).dt.days

schedule_ranking = pending_supply.sort_values(
    [
        "Days_vs_Baseline_Start",
        "Total_Float",
        "Supply_Risk_Score"
    ],
    ascending=[False, True, False]
).copy()

# ------------------------------------------------------------
# 5. Three operational rankings
# ------------------------------------------------------------

# Project Manager:
# Severity -> CPM float -> buffer excess -> risk score

project_ranking = pending_supply.sort_values(
    [
        "Alarm_Order",
        "Total_Float",
        "Supply_Buffer_Excess_Days",
        "Supply_Risk_Score"
    ],
    ascending=[
        True,
        True,
        False,
        False
    ]
).copy()


# Schedule Exposure:
# Activities whose baseline start date is closest or has passed.
# Secondary criterion: lowest available CPM float.

schedule_ranking = pending_supply.sort_values(
    [
        "Days_vs_Baseline_Start",
        "Total_Float",
        "Supply_Risk_Score"
    ],
    ascending=[
        False,
        True,
        False
    ]
).copy()


# Supply Escalation:
# Alarm -> buffer excess -> supply delay -> risk score

supply_ranking = pending_supply.sort_values(
    [
        "Alarm_Order",
        "Supply_Buffer_Excess_Days",
        "Supply_Delay_Days",
        "Supply_Risk_Score"
    ],
    ascending=[
        True,
        False,
        False,
        False
    ]
).copy()


# ------------------------------------------------------------
# 6. CPM criticality
# ------------------------------------------------------------

critical_supply_alerts = supply.loc[
    supply["Is_Critical"] == True
].copy()

pending_buffer_exceeded = pending_supply.loc[
    pending_supply["Supply_Buffer_Exceeded"] == True
].copy()


# ============================================================
# SUPPLY EXPOSURE — KPI
# ============================================================

alert1, alert2, alert3, alert4 = st.columns(4)

alert1.metric(
    "Consolidated Supply Alerts",
    len(supply)
)

alert2.metric(
    "Pending Activities",
    len(pending_supply)
)

alert3.metric(
    "Completed Activities",
    len(completed_supply)
)

alert4.metric(
    "CPM Critical Supply Alerts",
    len(critical_supply_alerts)
)

st.caption(
    "The consolidated supply-risk assessment is a reference snapshot. "
    "Pending and completed activity counts reflect actual execution "
    "progress at the selected tracking period."
)


# ============================================================
# SUPPLY RISK DISTRIBUTION — CONSOLIDATED SNAPSHOT
# ============================================================

risk_col, context_col = st.columns([1, 1])

with risk_col:

    st.markdown("#### Supply Risk Distribution")

    st.caption(
        "Consolidated risk classification across the project."
    )

    risk_counts = (
        schedule["Risk_Level"]
        .value_counts()
        .reindex(
            [
                "No Alert",
                "Preventive Alert",
                "Buffer Exceeded"
            ],
            fill_value=0
        )
    )

    fig_risk = go.Figure(
        go.Bar(
            x=risk_counts.index,
            y=risk_counts.values,
            text=risk_counts.values,
            textposition="outside"
        )
    )

    fig_risk.update_layout(
        height=350,
        xaxis_title="Risk classification",
        yaxis_title="Activities",
        showlegend=False,
        margin=dict(l=10, r=10, t=25, b=20)
    )

    st.plotly_chart(
        fig_risk,
        use_container_width=True
    )


with context_col:

    st.markdown("#### Exposure Status")

    st.metric(
        "Activities with buffer exceeded",
        len(buffer_exceeded := schedule.loc[
            schedule["Supply_Buffer_Exceeded"] == True
        ])
    )

    st.metric(
        "Preventive supply alerts",
        int(
            (schedule["Risk_Level"] == "Preventive Alert").sum()
        )
    )

    st.metric(
        "Activities with unknown execution state",
        len(unknown_supply)
    )

    st.caption(
        "Supply risk scores, alarms and buffer assessments are "
        "consolidated reference values. They are not historical "
        "measurements for each tracking period."
    )


# ============================================================
# THREE MANAGEMENT VIEWS
# ============================================================

st.markdown("#### Management Attention — Operational Views")

tab_project, tab_schedule, tab_supply = st.tabs(
    [
        "Project Manager",
        "Schedule Exposure",
        "Supply Escalation"
    ]
)


# ------------------------------------------------------------
# TAB 1 — PROJECT MANAGER
# ------------------------------------------------------------

with tab_project:

    st.markdown("##### Integrated Management Priority")

    st.caption(
        "Pending activities ranked by alarm severity, available "
        "CPM float, buffer excess and consolidated supply-risk score."
    )

    render_activity_cards(
        project_ranking,
        view="project"
    )


# ------------------------------------------------------------
# TAB 2 — SCHEDULE EXPOSURE
# ------------------------------------------------------------

with tab_schedule:

    st.caption(
        "Pending supply-alert activities ranked by their temporal "
        "position relative to baseline start. CPM total float is "
        "shown as schedule context."
    )

    st.info(
        "No supply-alert activity belongs to the baseline CPM critical path. "
        "The ranking prioritises activities whose baseline start date is "
        "closest or has already passed. CPM float is shown as additional "
        "schedule context; this ranking does not indicate a direct "
        "critical-path threat."
    )

    if schedule_ranking.empty:

        st.success(
            "No pending supply-alert activities at the selected reporting period."
        )

    else:

        render_activity_cards(
            schedule_ranking,
            view="schedule"
        )


# ------------------------------------------------------------
# TAB 3 — SUPPLY ESCALATION
# ------------------------------------------------------------

with tab_supply:

    st.markdown("##### Supplier and Material Intervention")

    st.caption(
        "Pending activities ranked by material alarm, buffer "
        "excess, supply delay and consolidated risk score."
    )

    render_activity_cards(
        supply_ranking,
        view="supply"
    )


# ============================================================
# EXCEL EXPORT — ALL CONSOLIDATED SUPPLY ALERTS
# ============================================================

st.markdown("#### Supply Exposure — Excel Export")

st.caption(
    "Download all consolidated supply-alert activities, "
    "including completed and pending activities, with their "
    "execution state at the selected tracking period."
)

export_data = supply.drop(
    columns=["Activity_ID", "Alarm_Order"],
    errors="ignore"
).copy()

export_data.insert(
    0,
    "Selected_TP",
    int(selected_tp)
)

export_data.insert(
    1,
    "Selected_Status_Date",
    selected_date
)

readme = pd.DataFrame(
    {
        "Field": [
            "Selected_TP",
            "Selected_Status_Date",
            "Execution_State",
            "Supply_Delay_Days",
            "Supply_Risk_Score",
            "Material_Alarm",
            "Supply_Buffer_Excess_Days",
            "Total_Float",
            "Material_Readiness_Date"
        ],
        "Interpretation": [
            "Selected historical tracking period.",
            "Historical project status date.",
            "Execution state derived from historical activity progress.",
            "Consolidated supply-delay assessment, not a historical time series.",
            "Consolidated supply-risk score, not a historical time series.",
            "Consolidated material alarm classification.",
            "Consolidated buffer assessment, not a historical time series.",
            "Baseline CPM total float.",
            "Planned material readiness date, not confirmed actual receipt."
        ]
    }
)

excel_buffer = io.BytesIO()

with pd.ExcelWriter(
    excel_buffer,
    engine="openpyxl"
) as writer:

    export_data.to_excel(
        writer,
        sheet_name="Supply Exposure",
        index=False
    )

    readme.to_excel(
        writer,
        sheet_name="Read Me",
        index=False
    )

st.download_button(
    label="Download Supply Exposure — Excel",
    data=excel_buffer.getvalue(),
    file_name=f"Supply_Exposure_TP{int(selected_tp):03d}.xlsx",
    mime=(
        "application/vnd.openxmlformats-officedocument."
        "spreadsheetml.sheet"
    )
)


# ============================================================
# MANAGEMENT INTERPRETATION
# ============================================================

st.markdown("#### Management Interpretation")

if pending_supply.empty:

    st.success(
        f"All {len(completed_supply)} activities with consolidated "
        f"supply alerts were completed by the selected tracking period."
    )

else:

    top_activity = project_ranking.iloc[0]

    st.warning(
        f"{len(pending_supply)} activities with supply alerts "
        f"remain not completed at the selected tracking period. "
        f"The highest-ranked activity is ID {int(top_activity['ID'])} "
        f"({top_activity['Name']}), with "
        f"{top_activity['Supply_Buffer_Excess_Days']:.0f} days "
        f"of consolidated buffer excess."
    )

if len(critical_supply_alerts) == 0:

    st.info(
        "None of the consolidated supply-alert activities "
        "is classified as critical in the baseline CPM network."
    )

if len(pending_buffer_exceeded) > 0:

    st.write(
        f"{len(pending_buffer_exceeded)} pending activities "
        f"have exceeded their consolidated supply buffer. "
        "Supplier intervention should be assessed alongside "
        "their remaining CPM float."
    )

if not unknown_supply.empty:

    st.warning(
        f"Execution status is unavailable for "
        f"{len(unknown_supply)} supply-alert activities. "
        "These activities are excluded from the pending rankings."
    )

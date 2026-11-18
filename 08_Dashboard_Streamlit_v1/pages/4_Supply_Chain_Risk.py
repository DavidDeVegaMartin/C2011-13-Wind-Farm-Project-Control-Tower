import pandas as pd
import streamlit as st
import plotly.express as px

# ============================================================
# 1. CONFIGURATION AND DATA
# ============================================================

st.title("Supply Chain & Risk")
st.caption(
    "Material readiness, supply exposure and potential " "schedule implications."
)

if "project_data" not in st.session_state:
    st.error(
        "Project data is not available. "
        "Please launch the application through app.py."
    )
    st.stop()

data = st.session_state["project_data"]

sc = data["schedule_control"].copy()

required_columns = [
    "ID",
    "Name",
    "Material_Type",
    "Material_Status",
    "Lead_Time_Days",
    "Buffer_Days",
    "Supply_Delay_Days",
    "Supply_Risk_Score",
    "Risk_Level",
    "Supply_Alert",
    "Is_Critical_Material",
    "Is_Critical",
    "Total_Float",
    "Material_Readiness_Date",
    "Baseline_Start",
    "Baseline_End",
    "Supply_Buffer_Excess_Days",
]

missing_columns = [col for col in required_columns if col not in sc.columns]

if missing_columns:
    st.error(
        "Missing required columns in schedule_control: " + ", ".join(missing_columns)
    )
    st.stop()

# Explicit type normalization
numeric_columns = [
    "Lead_Time_Days",
    "Buffer_Days",
    "Supply_Delay_Days",
    "Supply_Risk_Score",
    "Total_Float",
    "Supply_Buffer_Excess_Days",
]

for col in numeric_columns:
    sc[col] = pd.to_numeric(sc[col], errors="coerce")

for col in ["Material_Readiness_Date", "Baseline_Start", "Baseline_End"]:
    sc[col] = pd.to_datetime(sc[col], errors="coerce")

sc["Supply_Alert"] = sc["Supply_Alert"].fillna(False).astype(bool)

sc["Is_Critical"] = sc["Is_Critical"].fillna(False).astype(bool)

sc["Is_Critical_Material"] = sc["Is_Critical_Material"].fillna(False).astype(bool)

# Only activities with a material requirement
materials = sc[
    sc["Material_Type"].notna() & (sc["Material_Type"] != "Non-Critical")
].copy()

alerts = materials[materials["Supply_Alert"]].copy()

# Supply risk is a snapshot in the source data.
# It is not recalculated by the historical reporting-period selector.


# ============================================================
# 2. SUPPLY CHAIN OVERVIEW
# ============================================================

st.divider()
st.subheader("1. Supply Chain Overview")

total_activities = len(sc)
material_activities = len(materials)
alert_count = int(sc["Supply_Alert"].sum())

preventive_count = int((sc["Risk_Level"] == "Preventive Alert").sum())

buffer_exceeded_count = int((sc["Risk_Level"] == "Buffer Exceeded").sum())

critical_supply_alerts = int((sc["Supply_Alert"] & sc["Is_Critical"]).sum())

alert_rate = alert_count / material_activities if material_activities else 0

c1, c2, c3, c4, c5 = st.columns(5)

with c1:
    st.metric("Material activities", f"{material_activities} / {total_activities}")

with c2:
    st.metric("Supply alerts", alert_count, f"{alert_rate:.1%} of material activities")

with c3:
    st.metric("Preventive alerts", preventive_count)

with c4:
    st.metric("Buffer exceeded", buffer_exceeded_count)

with c5:
    st.metric("CPM critical alerts", critical_supply_alerts)

if buffer_exceeded_count > 0:
    st.warning(
        f"{buffer_exceeded_count} material activities have exceeded "
        "their supply buffer and require priority monitoring."
    )
else:
    st.success("No material activities have exceeded their supply buffer.")

if critical_supply_alerts == 0:
    st.info(
        "None of the activities with a supply alert is currently "
        "classified as critical in the CPM network. This does not "
        "eliminate supply risk: available schedule float must still "
        "be monitored."
    )


st.markdown("#### Supply alerts by material type")

alert_comparison = (
    materials.groupby("Material_Type")
    .agg(Activities=("ID", "count"), Alerts=("Supply_Alert", "sum"))
    .reset_index()
    .melt(
        id_vars="Material_Type",
        value_vars=["Activities", "Alerts"],
        var_name="Indicator",
        value_name="Number of activities",
    )
)

fig_alert_rate = px.bar(
    alert_comparison,
    x="Material_Type",
    y="Number of activities",
    color="Indicator",
    barmode="group",
    text="Number of activities",
    color_discrete_map={"Activities": "#AAB7B8", "Alerts": "#E67E22"},
    labels={
        "Material_Type": "Material type",
        "Number of activities": "Number of activities",
        "Indicator": "",
    },
)

fig_alert_rate.update_layout(
    height=320,
    xaxis_title="",
    yaxis_title="Number of activities",
    legend_title_text="",
    margin=dict(l=10, r=10, t=20, b=10),
)

st.plotly_chart(fig_alert_rate, use_container_width=True)


# ============================================================
# 4. SUPPLY RISK EXPOSURE
# ============================================================

st.divider()
st.subheader("3. Supply Risk Exposure")

st.markdown(
    "Activities ranked by the supply risk score. "
    "The ranking supports prioritisation; it does not represent "
    "a probability of project delay."
)

risk_ranking = alerts.copy()

risk_ranking = risk_ranking.sort_values(
    ["Supply_Risk_Score", "Supply_Buffer_Excess_Days", "Supply_Delay_Days"],
    ascending=[False, False, False],
)

if risk_ranking.empty:
    st.success("There are currently no supply alerts.")

else:
    top_risk = risk_ranking.head(15).copy()

    top_risk["Activity"] = (
        top_risk["ID"].astype(int).astype(str) + " — " + top_risk["Name"].astype(str)
    )

    # --------------------------------------------------------
    # 1. MAIN RISK RANKING
    # --------------------------------------------------------

    st.markdown("#### Highest-risk activities")

    fig_risk = px.bar(
        top_risk.sort_values("Supply_Risk_Score"),
        x="Supply_Risk_Score",
        y="Activity",
        orientation="h",
        color="Risk_Level",
        text="Supply_Risk_Score",
        color_discrete_map={
            "Preventive Alert": "#E67E22",
            "Buffer Exceeded": "#C0392B",
        },
        labels={
            "Supply_Risk_Score": "Supply risk score",
            "Activity": "",
            "Risk_Level": "Alert level",
        },
    )

    fig_risk.update_layout(
        height=520,
        margin=dict(l=10, r=30, t=15, b=10),
        xaxis_title="Supply risk score",
        yaxis_title="",
        legend_title_text="",
    )

    st.plotly_chart(fig_risk, use_container_width=True)

    # --------------------------------------------------------
    # 2. INCIDENT ANALYSIS
    # --------------------------------------------------------

    col1, col2 = st.columns(2)

    with col1:
        st.markdown("#### Supply delay vs. buffer excess")

        fig_incident_scatter = px.scatter(
            top_risk,
            x="Supply_Delay_Days",
            y="Supply_Buffer_Excess_Days",
            color="Risk_Level",
            hover_name="Activity",
            hover_data={
                "ID": True,
                "Material_Type": True,
                "Material_Status": True,
                "Supply_Delay_Days": True,
                "Buffer_Days": True,
                "Supply_Buffer_Excess_Days": True,
                "Supply_Risk_Score": True,
            },
            color_discrete_map={
                "Preventive Alert": "#E67E22",
                "Buffer Exceeded": "#C0392B",
            },
            labels={
                "Supply_Delay_Days": "Supply delay (days)",
                "Supply_Buffer_Excess_Days": "Buffer excess (days)",
                "Risk_Level": "Alert level",
            },
        )

        fig_incident_scatter.update_layout(
            height=400,
            xaxis_title="Supply delay (days)",
            yaxis_title="Buffer excess (days)",
            legend_title_text="",
            margin=dict(l=10, r=20, t=20, b=10),
        )

        st.plotly_chart(fig_incident_scatter, use_container_width=True)

    with col2:
        st.markdown("#### Incidents by material type")

        incident_by_material = (
            top_risk.groupby(["Material_Type", "Risk_Level"], dropna=False)
            .size()
            .reset_index(name="Incidents")
        )

        fig_incident_material = px.bar(
            incident_by_material,
            x="Material_Type",
            y="Incidents",
            color="Risk_Level",
            barmode="group",
            text="Incidents",
            color_discrete_map={
                "Preventive Alert": "#E67E22",
                "Buffer Exceeded": "#C0392B",
            },
            labels={
                "Material_Type": "Material type",
                "Incidents": "Number of incidents",
                "Risk_Level": "Alert level",
            },
        )

        fig_incident_material.update_layout(
            height=400,
            xaxis_title="",
            yaxis_title="Number of incidents",
            legend_title_text="",
            margin=dict(l=10, r=10, t=20, b=10),
        )

        st.plotly_chart(fig_incident_material, use_container_width=True)

    st.caption(
        "The analysis is based on the 15 highest-risk activities. "
        "Positive buffer excess indicates that the supply delay "
        "has exceeded the available buffer."
    )

    # --------------------------------------------------------
    # 3. DETAILED INCIDENT REGISTER
    # --------------------------------------------------------

    with st.expander("Priority incidents — detailed register"):

        priority_table = top_risk[
            [
                "ID",
                "Name",
                "Material_Type",
                "Material_Status",
                "Supply_Delay_Days",
                "Supply_Buffer_Excess_Days",
                "Supply_Risk_Score",
            ]
        ].rename(
            columns={
                "Name": "Activity",
                "Material_Type": "Material",
                "Material_Status": "Status",
                "Supply_Delay_Days": "Delay (d)",
                "Supply_Buffer_Excess_Days": "Buffer excess (d)",
                "Supply_Risk_Score": "Risk score",
            }
        )

        st.dataframe(
            priority_table,
            hide_index=True,
            use_container_width=True,
            column_config={
                "Risk score": st.column_config.NumberColumn(format="%.0f"),
                "Delay (d)": st.column_config.NumberColumn(format="%d"),
                "Buffer excess (d)": st.column_config.NumberColumn(format="%.0f"),
            },
        )


# ============================================================
# 5. SCHEDULE IMPACT
# ============================================================

st.divider()
st.subheader("4. Schedule Impact")

st.markdown(
    "Supply delays and available CPM total float are shown together "
    "to distinguish material exposure from actual schedule criticality."
)

impact = materials.dropna(subset=["Supply_Delay_Days", "Total_Float"]).copy()

st.markdown("#### Supply delay vs. CPM float")

if impact.empty:
    st.info("No activities have sufficient supply and CPM data for this analysis.")

else:
    fig_impact = px.scatter(
        impact,
        x="Total_Float",
        y="Supply_Delay_Days",
        color="Risk_Level",
        size="Supply_Risk_Score",
        size_max=18,
        hover_name="Name",
        hover_data={
            "ID": True,
            "Material_Type": True,
            "Material_Status": True,
            "Buffer_Days": True,
            "Supply_Buffer_Excess_Days": True,
            "Total_Float": True,
            "Supply_Risk_Score": True,
        },
        color_discrete_map={
            "No Alert": "#95A5A6",
            "Preventive Alert": "#E67E22",
            "Buffer Exceeded": "#C0392B",
        },
        labels={
            "Total_Float": "CPM total float (days)",
            "Supply_Delay_Days": "Supply delay (days)",
            "Risk_Level": "Supply alert level",
        },
    )

    fig_impact.update_layout(
        height=480,
        xaxis_title="CPM total float (days)",
        yaxis_title="Supply delay (days)",
        legend_title_text="",
        margin=dict(l=10, r=20, t=15, b=10),
    )

    st.plotly_chart(fig_impact, use_container_width=True)

# ------------------------------------------------------------
# EXPLICIT INTERPRETATION
# ------------------------------------------------------------

exceeded = alerts[alerts["Supply_Buffer_Excess_Days"] > 0]

reported_float_alerts = alerts.dropna(subset=["Total_Float"])

positive_float_alerts = reported_float_alerts[reported_float_alerts["Total_Float"] > 0]

st.info(
    f"{len(exceeded)} activities exceed their material buffer. "
    f"Among {len(reported_float_alerts)} alerted activities with "
    f"reported CPM float, {len(positive_float_alerts)} have "
    "positive total float. Supply buffer and CPM total float "
    "are different controls and must not be interpreted interchangeably."
)


# ============================================================
# 6. MANAGEMENT ATTENTION
# ============================================================

st.divider()
st.subheader("5. Management Attention")

st.markdown(
    "Priority list for operational follow-up, ordered by buffer "
    "excess, risk score and supply delay."
)

attention = alerts.copy()

attention["Priority_Order"] = (
    attention["Supply_Buffer_Excess_Days"].fillna(0) > 0
).astype(int)

attention = attention.sort_values(
    [
        "Priority_Order",
        "Supply_Buffer_Excess_Days",
        "Supply_Risk_Score",
        "Supply_Delay_Days",
    ],
    ascending=[False, False, False, False],
)

# ------------------------------------------------------------
# PRIORITY REGISTER
# ------------------------------------------------------------

attention_table = attention[
    [
        "ID",
        "Name",
        "Material_Type",
        "Material_Status",
        "Supply_Delay_Days",
        "Buffer_Days",
        "Supply_Buffer_Excess_Days",
        "Total_Float",
        "Is_Critical",
        "Supply_Risk_Score",
    ]
].rename(
    columns={
        "Name": "Activity",
        "Material_Type": "Material",
        "Material_Status": "Material status",
        "Supply_Delay_Days": "Supply delay (d)",
        "Buffer_Days": "Buffer (d)",
        "Supply_Buffer_Excess_Days": "Buffer excess (d)",
        "Total_Float": "CPM float (d)",
        "Is_Critical": "CPM critical",
        "Supply_Risk_Score": "Risk score",
    }
)

st.dataframe(
    attention_table,
    hide_index=True,
    use_container_width=True,
    column_config={
        "Supply delay (d)": st.column_config.NumberColumn(format="%d"),
        "Buffer (d)": st.column_config.NumberColumn(format="%.0f"),
        "Buffer excess (d)": st.column_config.NumberColumn(format="%.0f"),
        "CPM float (d)": st.column_config.NumberColumn(format="%d"),
        "Risk score": st.column_config.NumberColumn(format="%.0f"),
        "CPM critical": st.column_config.CheckboxColumn(disabled=True),
    },
)


# ------------------------------------------------------------
# PLANNED MATERIAL READINESS VS. ACTIVITY START
# ------------------------------------------------------------

st.markdown("#### Material readiness vs. activity start")

readiness = attention[
    [
        "ID",
        "Name",
        "Material_Type",
        "Material_Readiness_Date",
        "Baseline_Start",
        "Supply_Delay_Days",
        "Material_Status",
    ]
].copy()

readiness["Material_Readiness_Date"] = pd.to_datetime(
    readiness["Material_Readiness_Date"],
    errors="coerce",
)

readiness["Baseline_Start"] = pd.to_datetime(
    readiness["Baseline_Start"],
    errors="coerce",
)

# Activities with both dates available
valid_dates = readiness.dropna(
    subset=["Material_Readiness_Date", "Baseline_Start"]
).copy()

# Activities without one or both dates
missing_dates = len(readiness) - len(valid_dates)

if not valid_dates.empty:

    valid_dates["Readiness_Gap_Days"] = (
        valid_dates["Material_Readiness_Date"] - valid_dates["Baseline_Start"]
    ).dt.days

    ready_before = int((valid_dates["Readiness_Gap_Days"] < 0).sum())

    ready_on_start = int((valid_dates["Readiness_Gap_Days"] == 0).sum())

    ready_after = int((valid_dates["Readiness_Gap_Days"] > 0).sum())

else:
    ready_before = 0
    ready_on_start = 0
    ready_after = 0

# ------------------------------------------------------------
# READINESS KPIs
# ------------------------------------------------------------

col1, col2, col3, col4 = st.columns(4)

col1.metric("Ready before start", ready_before)
col2.metric("Ready on start date", ready_on_start)
col3.metric("Ready after start", ready_after)
col4.metric("Missing dates", missing_dates)

# ------------------------------------------------------------
# ACTIVITIES WITH LATE MATERIAL READINESS
# ------------------------------------------------------------

late_readiness = valid_dates[valid_dates["Readiness_Gap_Days"] > 0].copy()

late_readiness = late_readiness.sort_values(
    "Readiness_Gap_Days",
    ascending=False,
)

if late_readiness.empty:
    st.success(
        "No alerted activities have planned material readiness "
        "dates later than their baseline activity start."
    )

else:
    st.markdown("#### Activities with potential material readiness conflicts")

    late_readiness["Activity"] = (
        late_readiness["ID"].astype(int).astype(str)
        + " — "
        + late_readiness["Name"].astype(str)
    )

    late_table = late_readiness[
        [
            "ID",
            "Activity",
            "Material_Type",
            "Material_Readiness_Date",
            "Baseline_Start",
            "Readiness_Gap_Days",
            "Supply_Delay_Days",
            "Material_Status",
        ]
    ].rename(
        columns={
            "Material_Type": "Material",
            "Material_Readiness_Date": "Planned readiness",
            "Baseline_Start": "Baseline activity start",
            "Readiness_Gap_Days": "Readiness gap (d)",
            "Supply_Delay_Days": "Supply delay (d)",
            "Material_Status": "Material status",
        }
    )

    st.dataframe(
        late_table,
        hide_index=True,
        use_container_width=True,
        column_config={
            "Planned readiness": st.column_config.DateColumn(format="DD/MM/YYYY"),
            "Baseline activity start": st.column_config.DateColumn(format="DD/MM/YYYY"),
            "Readiness gap (d)": st.column_config.NumberColumn(format="%d"),
            "Supply delay (d)": st.column_config.NumberColumn(format="%d"),
        },
    )

st.caption(
    "Based on planned readiness dates, not confirmed physical receipts. "
    "A positive readiness gap means that planned material availability "
    "falls after the baseline activity start."
)


# ============================================================
# 7. MANAGEMENT TAKEAWAYS
# ============================================================

st.divider()
st.subheader("Management Takeaways")

if alerts.empty:

    st.success(
        "No supply alerts are currently recorded. "
        "No material-related management intervention is indicated "
        "by the current supply snapshot."
    )

else:

    # --------------------------------------------------------
    # MATERIAL EXPOSURE
    # --------------------------------------------------------

    material_counts = alerts["Material_Type"].fillna("Unspecified").value_counts()

    highest_count = int(material_counts.max())

    leading_materials = material_counts[material_counts == highest_count].index.tolist()

    other_materials = material_counts[~material_counts.index.isin(leading_materials)]

    if len(leading_materials) == 1:
        main_exposure = (
            f"**Main exposure:** {leading_materials[0]} "
            f"accounts for {highest_count} supply alerts, "
            "representing the largest material alert concentration."
        )
    else:
        main_exposure = (
            f"**Main exposure:** {', '.join(leading_materials)} "
            f"share the highest alert count, with {highest_count} "
            "alerts each."
        )

    st.markdown(f"- {main_exposure}")

    if not other_materials.empty:
        additional_exposure = ", ".join(
            f"{material}: {int(count)}" for material, count in other_materials.items()
        )

        st.markdown(f"- **Additional exposure:** {additional_exposure}.")
    else:
        st.markdown(
            "- **Additional exposure:** No other material categories "
            "have recorded alerts."
        )

    # --------------------------------------------------------
    # BUFFER MANAGEMENT
    # --------------------------------------------------------

    buffer_exceeded_count = int((alerts["Supply_Buffer_Excess_Days"] > 0).sum())

    st.markdown(
        f"- **Buffer management:** {buffer_exceeded_count} "
        "activities have exceeded their material supply buffer."
    )

    # --------------------------------------------------------
    # SCHEDULE POSITION
    # --------------------------------------------------------

    critical_supply_alerts = int(alerts["Is_Critical"].fillna(False).astype(bool).sum())

    st.markdown(
        f"- **Schedule position:** {critical_supply_alerts} "
        "alerted activities are CPM-critical in the current "
        "schedule snapshot."
    )

st.caption(
    "Supply risk indicators describe material exposure. "
    "CPM float describes schedule flexibility. "
    "Neither should be used as a substitute for the other."
)

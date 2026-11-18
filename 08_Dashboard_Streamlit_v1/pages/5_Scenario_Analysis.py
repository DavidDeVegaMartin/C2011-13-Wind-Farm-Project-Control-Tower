import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.title("Scenario Analysis")
st.caption(
    "Project scenario comparison, schedule impact and corrective "
    "intervention assessment."
)

data = st.session_state["project_data"]

scenario_summary = data["scenario_summary"].copy()
scenario_activity = data["scenario_activity_comparison"].copy()
scenario_supply = data["scenario_supply_impacts"].copy()
corrective_summary = data["corrective_decision_summary"].copy()
corrective_actions = data["corrective_actions"].copy()
corrective_supply = data["corrective_supply_risk"].copy()
corrective_cpm = data["corrective_cpm_comparison"].copy()
schedule_control = data["schedule_control"].copy()


# ============================================================
# 2. DATA PREPARATION
# ============================================================

numeric_columns = {
    "scenario_summary": [
        "Project_Duration_Days",
        "Project_Delay_Days",
        "Activity_Delay_Days",
        "Supply_Delay_Days",
        "Activities_With_Date_Changes",
        "Activities_With_Float_Consumption",
        "Critical_Activities",
    ],
    "corrective_summary": [
        "Duration_Before_Actions",
        "Delay_Before_Actions",
        "Activity_Impact_Before",
        "Supply_Impact_Before",
        "Duration_After_Actions",
        "Delay_After_Actions",
        "Activity_Impact_After",
        "Supply_Impact_After",
        "Project_Days_Recovered",
        "Delay_Reduction_Pct",
    ],
}

for col in numeric_columns["scenario_summary"]:
    scenario_summary[col] = pd.to_numeric(scenario_summary[col], errors="coerce")

for col in numeric_columns["corrective_summary"]:
    corrective_summary[col] = pd.to_numeric(corrective_summary[col], errors="coerce")

for df in [
    scenario_activity,
    scenario_supply,
    corrective_actions,
    corrective_supply,
    corrective_cpm,
    schedule_control,
]:
    for col in df.select_dtypes(include="object").columns:
        pass

# Baseline duration from reference CPM
baseline_duration = pd.to_numeric(schedule_control["EF"], errors="coerce").max()

if pd.isna(baseline_duration):
    baseline_duration = 299

baseline_duration = int(baseline_duration)


# Activity lookup
activity_lookup = (
    schedule_control[["ID", "Name"]]
    .drop_duplicates("ID")
    .set_index("ID")["Name"]
    .to_dict()
)


# Scenario labels
scenario_labels = {
    "SC01": "SC01 – Supply delay",
    "SC02": "SC02 – Activity delay",
    "SC03": "SC03 – Combined delay",
}


# ============================================================
# 3. SCENARIO OVERVIEW
# ============================================================

st.header("1. Scenario Overview")

st.caption(
    "Comparison against the reference CPM baseline. "
    "Scenario results are simulated, not historical execution results."
)

scenario_display = scenario_summary.copy()

baseline_critical_ids = (
    schedule_control.loc[
        schedule_control["Is_Critical"].fillna(False).astype(bool),
        "ID",
    ]
    .astype(int)
    .tolist()
)

baseline_row = pd.DataFrame(
    [
        {
            "Scenario_ID": "BASELINE",
            "Project_Duration_Days": baseline_duration,
            "Project_Delay_Days": 0,
            "Activity_Delay_Days": 0,
            "Supply_Delay_Days": 0,
            "Activities_With_Date_Changes": 0,
            "Activities_With_Float_Consumption": 0,
            "Critical_Activities": len(baseline_critical_ids),
            "New_Critical_Activities": "[]",
            "Activities_No_Longer_Critical": "[]",
            "Critical_Activity_IDs": str(baseline_critical_ids),
        }
    ]
)

scenario_display = pd.concat([baseline_row, scenario_display], ignore_index=True)

scenario_display["Scenario"] = (
    scenario_display["Scenario_ID"]
    .map(scenario_labels)
    .fillna(scenario_display["Scenario_ID"])
)

scenario_display.loc[scenario_display["Scenario_ID"] == "BASELINE", "Scenario"] = (
    "BASELINE – Reference"
)


scenario_duration = scenario_summary.set_index("Scenario_ID")["Project_Duration_Days"]

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Baseline duration",
    f"{baseline_duration} days",
)

for col, scenario_id in zip(
    [col2, col3, col4],
    ["SC01", "SC02", "SC03"],
):
    duration = int(scenario_duration.loc[scenario_id])
    delay = duration - baseline_duration

    col.metric(
        f"{scenario_id} duration",
        f"{duration} days",
        delta=f"{delay:+d} days" if delay != 0 else "No delay",
        delta_color="inverse",
    )


st.dataframe(
    scenario_display[
        [
            "Scenario",
            "Project_Duration_Days",
            "Project_Delay_Days",
            "Activity_Delay_Days",
            "Supply_Delay_Days",
            "Activities_With_Date_Changes",
            "Critical_Activities",
        ]
    ].rename(
        columns={
            "Project_Duration_Days": "Duration (days)",
            "Project_Delay_Days": "Project delay (days)",
            "Activity_Delay_Days": "Activity impact (days)",
            "Supply_Delay_Days": "Supply impact (days)",
            "Activities_With_Date_Changes": "Activities with date changes",
            "Critical_Activities": "Critical activities",
        }
    ),
    hide_index=True,
    use_container_width=True,
)


# ============================================================
# 4. SCHEDULE IMPACT
# ============================================================

st.divider()
st.header("2. Schedule Impact")

st.caption("Impact of simulated activity and supply delays on the project schedule.")

chart_data = scenario_display[["Scenario", "Project_Duration_Days"]].copy()

fig_duration = px.bar(
    chart_data,
    x="Scenario",
    y="Project_Duration_Days",
    text="Project_Duration_Days",
    title="Project duration by scenario",
    labels={
        "Scenario": "Scenario",
        "Project_Duration_Days": "Project duration (days)",
    },
)

fig_duration.add_hline(
    y=baseline_duration,
    line_dash="dash",
    line_color="gray",
    annotation_text=f"Baseline: {baseline_duration} days",
)

fig_duration.update_traces(textposition="outside")
fig_duration.update_layout(
    showlegend=False,
    yaxis_title="Duration (days)",
    xaxis_title="",
)

st.plotly_chart(fig_duration, use_container_width=True)


col1, col2 = st.columns(2)

with col1:
    impact_data = scenario_summary[
        ["Scenario_ID", "Activity_Delay_Days", "Supply_Delay_Days"]
    ].melt(
        id_vars="Scenario_ID",
        var_name="Impact_Type",
        value_name="Impact_Days",
    )

    impact_data["Impact_Type"] = impact_data["Impact_Type"].map(
        {
            "Activity_Delay_Days": "Activity delay",
            "Supply_Delay_Days": "Supply delay",
        }
    )

    fig_impact = px.bar(
        impact_data,
        x="Scenario_ID",
        y="Impact_Days",
        color="Impact_Type",
        barmode="group",
        title="Simulated delay inputs",
        labels={
            "Scenario_ID": "Scenario",
            "Impact_Days": "Delay (days)",
            "Impact_Type": "Impact type",
        },
    )

    st.plotly_chart(fig_impact, use_container_width=True)

with col2:
    activity_impact = scenario_summary[
        [
            "Scenario_ID",
            "Activities_With_Date_Changes",
            "Activities_With_Float_Consumption",
        ]
    ].melt(
        id_vars="Scenario_ID",
        var_name="Change_Type",
        value_name="Activities",
    )

    activity_impact["Change_Type"] = activity_impact["Change_Type"].map(
        {
            "Activities_With_Date_Changes": "Date changes",
            "Activities_With_Float_Consumption": "Float consumption",
        }
    )

    fig_changes = px.bar(
        activity_impact,
        x="Scenario_ID",
        y="Activities",
        color="Change_Type",
        barmode="group",
        title="Activities affected",
        labels={
            "Scenario_ID": "Scenario",
            "Activities": "Number of activities",
            "Change_Type": "Change type",
        },
    )

    st.plotly_chart(fig_changes, use_container_width=True)


# ============================================================
# 5. CORRECTIVE ACTIONS
# ============================================================

st.divider()
st.header("3. Corrective Actions")

st.info(
    "Corrective actions represent hypothetical interventions. "
    "Their effects are simulated assumptions, not confirmed recoveries."
)

action_display = corrective_actions.copy()

action_display["Target Activity"] = action_display["Target_Activity_ID"].map(
    activity_lookup
)

st.subheader("Intervention register")

st.dataframe(
    action_display[
        [
            "Action_ID",
            "Action_Name",
            "Target_Activity_ID",
            "Target Activity",
            "Action_Type",
            "Scenario_Impact_Before_Days",
            "Scenario_Impact_After_Days",
            "Recovered_Days",
            "Recovery_Rate_Pct",
            "CPM_Impact",
        ]
    ].rename(
        columns={
            "Action_ID": "Action",
            "Action_Name": "Intervention",
            "Target_Activity_ID": "Target ID",
            "Action_Type": "Type",
            "Scenario_Impact_Before_Days": "Impact before (days)",
            "Scenario_Impact_After_Days": "Impact after (days)",
            "Recovered_Days": "Days recovered",
            "Recovery_Rate_Pct": "Recovery rate (%)",
            "CPM_Impact": "CPM treatment",
        }
    ),
    hide_index=True,
    use_container_width=True,
)


# Corrective action assumptions
with st.expander("Intervention assumptions"):
    for _, row in corrective_actions.iterrows():
        st.markdown(f"**{row['Action_ID']} – {row['Action_Name']}**")
        st.write(row["Assumption"])


# ============================================================
# 6. BEFORE / AFTER COMPARISON
# ============================================================

st.subheader("Project impact before and after corrective actions")

corrective_display = corrective_summary.copy()

corrective_display["Scenario"] = (
    corrective_display["Scenario_ID"]
    .map(scenario_labels)
    .fillna(corrective_display["Scenario_ID"])
)

st.dataframe(
    corrective_display[
        [
            "Scenario",
            "Duration_Before_Actions",
            "Duration_After_Actions",
            "Delay_Before_Actions",
            "Delay_After_Actions",
            "Project_Days_Recovered",
            "Delay_Reduction_Pct",
        ]
    ]
    .rename(
        columns={
            "Duration_Before_Actions": "Duration before (days)",
            "Duration_After_Actions": "Duration after (days)",
            "Delay_Before_Actions": "Delay before (days)",
            "Delay_After_Actions": "Delay after (days)",
            "Project_Days_Recovered": "Days recovered",
            "Delay_Reduction_Pct": "Delay reduction (%)",
        }
    )
    .round(2),
    hide_index=True,
    use_container_width=True,
)


fig_before_after = go.Figure()

fig_before_after.add_trace(
    go.Bar(
        name="Before actions",
        x=corrective_display["Scenario"],
        y=corrective_display["Duration_Before_Actions"],
        text=corrective_display["Duration_Before_Actions"],
        textposition="outside",
    )
)

fig_before_after.add_trace(
    go.Bar(
        name="After actions",
        x=corrective_display["Scenario"],
        y=corrective_display["Duration_After_Actions"],
        text=corrective_display["Duration_After_Actions"],
        textposition="outside",
    )
)

fig_before_after.update_layout(
    title="Project duration: before vs after corrective actions",
    barmode="group",
    xaxis_title="Scenario",
    yaxis_title="Duration (days)",
)

st.plotly_chart(fig_before_after, use_container_width=True)


# ============================================================
# 7. RESIDUAL SUPPLY RISK
# ============================================================

st.divider()
st.header("4. Residual Supply Risk")

st.caption(
    "Supply mitigation reduces the additional scenario impact. "
    "The original baseline supply delay remains in place."
)

if not corrective_supply.empty:

    supply_display = corrective_supply.copy()

    supply_display["Activity"] = supply_display["Activity_ID"].map(activity_lookup)

    st.dataframe(
        supply_display[
            [
                "Scenario_ID",
                "Activity_ID",
                "Activity",
                "Baseline_Supply_Delay_Days",
                "Scenario_Supply_Impact_Days",
                "Residual_Scenario_Impact_Days",
                "Residual_Total_Supply_Delay_Days",
                "Buffer_Days",
                "Residual_Buffer_Excess_Days",
                "Supply_Risk_Reduction_Days",
                "Residual_Risk_Status",
            ]
        ].rename(
            columns={
                "Scenario_ID": "Scenario",
                "Activity_ID": "Activity ID",
                "Baseline_Supply_Delay_Days": "Baseline delay (days)",
                "Scenario_Supply_Impact_Days": "Scenario impact (days)",
                "Residual_Scenario_Impact_Days": "Residual scenario impact (days)",
                "Residual_Total_Supply_Delay_Days": "Residual total delay (days)",
                "Buffer_Days": "Buffer (days)",
                "Residual_Buffer_Excess_Days": "Residual buffer excess (days)",
                "Supply_Risk_Reduction_Days": "Risk reduction (days)",
                "Residual_Risk_Status": "Residual status",
            }
        ),
        hide_index=True,
        use_container_width=True,
    )

    residual_excess = pd.to_numeric(
        corrective_supply["Residual_Buffer_Excess_Days"], errors="coerce"
    )

    max_excess = residual_excess.max()

    if pd.isna(max_excess):
        st.info("Residual supply exposure could not be assessed.")

    elif max_excess > 0:
        st.warning(
            f"Residual supply exposure remains above the buffer. "
            f"Maximum residual buffer excess: {max_excess:.0f} days."
        )

    else:
        st.success("Residual supply exposure is within the available buffer.")

else:
    st.info("No residual supply risk records available.")


# ============================================================
# 8. CPM COMPARISON AFTER ACTIONS
# ============================================================

st.subheader("CPM impact of corrective interventions")

if not corrective_cpm.empty:

    cpm_change = corrective_cpm.copy()

    cpm_change["Activity"] = cpm_change["ID"].map(activity_lookup)

    critical_changes = cpm_change[
        cpm_change["Critical_Status_Changed"].fillna(False).astype(bool)
    ]

    col1, col2, col3 = st.columns(3)

    col1.metric("Activities evaluated", f"{cpm_change['ID'].nunique()}")

    col2.metric("Critical status changes", f"{len(critical_changes)}")

    col3.metric("Scenarios evaluated", f"{cpm_change['Scenario_ID'].nunique()}")

    selected_scenario = st.selectbox(
        "Select scenario for CPM comparison",
        options=sorted(cpm_change["Scenario_ID"].unique()),
        format_func=lambda x: scenario_labels.get(x, x),
        key="scenario_analysis_cpm",
    )

    selected_cpm = cpm_change[cpm_change["Scenario_ID"] == selected_scenario].copy()

    selected_cpm = selected_cpm[
        (selected_cpm["Duration_Simulated_Days_Change"] != 0)
        | (selected_cpm["ES_Change"] != 0)
        | (selected_cpm["EF_Change"] != 0)
        | (selected_cpm["Total_Float_Change"] != 0)
        | (selected_cpm["Critical_Status_Changed"].fillna(False))
    ]

    if selected_cpm.empty:
        st.success("No additional CPM changes are recorded for this scenario.")
    else:
        st.dataframe(
            selected_cpm[
                [
                    "ID",
                    "Activity",
                    "Duration_Simulated_Days_Change",
                    "ES_Change",
                    "EF_Change",
                    "Total_Float_Change",
                    "Critical_Status_Changed",
                ]
            ].rename(
                columns={
                    "ID": "Activity ID",
                    "Duration_Simulated_Days_Change": "Duration change (days)",
                    "ES_Change": "ES change (days)",
                    "EF_Change": "EF change (days)",
                    "Total_Float_Change": "Float change (days)",
                    "Critical_Status_Changed": "Critical status changed",
                }
            ),
            hide_index=True,
            use_container_width=True,
        )


# ============================================================
# 9. MANAGEMENT INSIGHTS
# ============================================================

st.divider()
st.header("5. Management Insights")

# Scenario results
scenario_results = scenario_summary.set_index("Scenario_ID")

sc01 = scenario_results.loc["SC01"]
sc02 = scenario_results.loc["SC02"]
sc03 = scenario_results.loc["SC03"]

# Corrective action results
corrective_results = corrective_summary.set_index("Scenario_ID")

ca01 = corrective_results.loc["SC01"]
ca02 = corrective_results.loc["SC02"]
ca03 = corrective_results.loc["SC03"]

# Supply residual exposure
if not corrective_supply.empty:
    residual_excess = pd.to_numeric(
        corrective_supply["Residual_Buffer_Excess_Days"],
        errors="coerce",
    )
    max_excess = residual_excess.max()
else:
    max_excess = 0

# ------------------------------------------------------------
# Scenario interpretation
# ------------------------------------------------------------

st.markdown("**Scenario interpretation**")

st.markdown(
    f"- **SC01 – Supply delay:** the supply impact is "
    f"{sc01['Supply_Delay_Days']:.0f} days, while project duration "
    f"remains at {sc01['Project_Duration_Days']:.0f} days."
)

st.markdown(
    f"- **SC02 – Activity delay:** the activity impact is "
    f"{sc02['Activity_Delay_Days']:.0f} days and the project duration "
    f"increases to {sc02['Project_Duration_Days']:.0f} days."
)

st.markdown(
    f"- **SC03 – Combined delay:** activity and supply impacts are "
    f"{sc03['Activity_Delay_Days']:.0f} and "
    f"{sc03['Supply_Delay_Days']:.0f} days respectively. "
    f"Project duration reaches {sc03['Project_Duration_Days']:.0f} days."
)

# ------------------------------------------------------------
# Corrective intervention interpretation
# ------------------------------------------------------------

st.markdown("**Corrective intervention interpretation**")

st.markdown(
    f"- **SC01:** project duration changes by "
    f"{ca01['Project_Days_Recovered']:.0f} days after interventions."
)

st.markdown(
    f"- **SC02:** interventions recover "
    f"{ca02['Project_Days_Recovered']:.0f} project days, "
    f"leaving a residual delay of {ca02['Delay_After_Actions']:.0f} days."
)

st.markdown(
    f"- **SC03:** interventions recover "
    f"{ca03['Project_Days_Recovered']:.0f} project days, "
    f"leaving a residual delay of {ca03['Delay_After_Actions']:.0f} days."
)

if max_excess > 0:
    st.markdown(
        f"- **Residual supply exposure:** the maximum remaining "
        f"buffer excess is {max_excess:.0f} days despite the mitigation."
    )
else:
    st.markdown(
        "- **Residual supply exposure:** no remaining buffer exceedance "
        "is recorded in the available results."
    )

st.info(
    "Decision principle: assess schedule recovery and supply risk separately. "
    "A project may recover schedule duration while retaining material "
    "exposure beyond its supply buffer."
)

st.caption(
    "Source: project scenario simulation, corrective action assessment "
    "and CPM recalculation outputs. All intervention benefits are "
    "scenario assumptions."
)

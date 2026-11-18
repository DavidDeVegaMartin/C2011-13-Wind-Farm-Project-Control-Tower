import pandas as pd
import plotly.express as px
import streamlit as st

from simulation_engine import run_custom_simulation

# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.title("Simulation Lab")
st.caption(
    "Test execution and supply delays, recalculate the project schedule "
    "and evaluate their impact."
)

data = st.session_state["project_data"]

catalog = data["activity_catalog"].copy()
baseline = data["activity_catalog"].copy()

catalog["ID"] = catalog["ID"].astype(int)
baseline["ID"] = baseline["ID"].astype(int)

catalog = catalog.sort_values("ID").reset_index(drop=True)

baseline_duration = float(baseline["EF"].max())
baseline_critical = int(baseline["Is_Critical"].sum())

activity_names = catalog.set_index("ID")["Name"].to_dict()

activity_options = catalog["ID"].tolist()

activity_labels = {
    activity_id: f"{activity_id} — {activity_names.get(activity_id, 'Unknown')}"
    for activity_id in activity_options
}

# Supply delays are only available for activities with material involvement.
supply_catalog = catalog[
    catalog["Material_Type"].notna() & (catalog["Material_Type"] != "Non-Critical")
].copy()

supply_options = supply_catalog["ID"].tolist()

supply_labels = {
    activity_id: activity_labels[activity_id] for activity_id in supply_options
}


# ============================================================
# 2. BASELINE REFERENCE
# ============================================================

st.subheader("Baseline reference")

col1, col2, col3 = st.columns(3)

col1.metric("Baseline project duration", f"{baseline_duration:.0f} days")
col2.metric("Critical activities", baseline_critical)
col3.metric("Activities available", len(activity_options))

st.divider()


# ============================================================
# 3. USER INPUTS
# ============================================================

st.subheader("Simulation parameters")

st.markdown(
    "Select the activities affected by execution delays and/or supply delays. "
    "You can configure several activities in each group."
)


col_activity, col_supply = st.columns(2)

activity_delays = {}
supply_delays = {}

with col_activity:
    with st.container(border=True):
        st.markdown("#### Execution delays")

        selected_activity_ids = st.multiselect(
            "Activities affected",
            options=activity_options,
            format_func=lambda x: activity_labels[x],
            key="simulation_activity_selection",
        )

        for activity_id in selected_activity_ids:
            delay = st.number_input(
                f"Execution delay — {activity_labels[activity_id]}",
                min_value=0,
                max_value=365,
                value=0,
                step=1,
                key=f"execution_delay_{activity_id}",
            )

            if delay > 0:
                activity_delays[activity_id] = int(delay)

with col_supply:
    with st.container(border=True):
        st.markdown("#### Supply delays")

        selected_supply_ids = st.multiselect(
            "Activities affected by supply delays",
            options=supply_options,
            format_func=lambda x: supply_labels[x],
            key="simulation_supply_selection",
        )

        for activity_id in selected_supply_ids:
            delay = st.number_input(
                f"Supply delay — {supply_labels[activity_id]}",
                min_value=0,
                max_value=365,
                value=0,
                step=1,
                key=f"supply_delay_{activity_id}",
            )

            if delay > 0:
                supply_delays[activity_id] = int(delay)


# ============================================================
# 4. RUN SIMULATION
# ============================================================

st.divider()

if st.button("Run simulation", type="primary", use_container_width=True):

    try:
        result = run_custom_simulation(
            data=data,
            activity_delays=activity_delays,
            supply_delays=supply_delays,
            scenario_id="CUSTOM",
        )

        st.session_state["custom_simulation_result"] = result
        st.session_state["custom_simulation_inputs"] = {
            "activity_delays": activity_delays.copy(),
            "supply_delays": supply_delays.copy(),
        }

        st.success("Simulation completed successfully.")

    except Exception as error:
        st.error(f"Simulation error: {error}")


# ============================================================
# 5. DISPLAY RESULTS
# ============================================================

result = st.session_state.get("custom_simulation_result")

if result is None:

    st.info(
        "Configure the delays above and run the simulation " "to display the results."
    )

else:

    summary = result["scenario_summary"].iloc[0]
    durations = result["scenario_durations"].copy()
    simulated_cpm = result["scenario_cpm"].copy()
    simulated_supply = result["scenario_supply"].copy()

    simulated_duration = float(summary["Project_Duration_Days"])
    simulated_critical = int(summary["Critical_Activities"])

    project_delay = simulated_duration - baseline_duration

    st.subheader("Simulation results")

    col1, col2, col3, col4 = st.columns(4)

    col1.metric(
        "Simulated duration",
        f"{simulated_duration:.0f} days",
        delta=f"{project_delay:+.0f} days",
        delta_color="inverse",
    )

    col2.metric(
        "Critical activities",
        simulated_critical,
        delta=f"{simulated_critical - baseline_critical:+d}",
        delta_color="inverse",
    )

    col3.metric(
        "Execution delay applied",
        f"{summary['Total_Activity_Delay_Days']:.0f} days",
    )

    col4.metric(
        "Supply delay recorded",
        f"{summary['Total_Supply_Delay_Days']:.0f} days",
    )

    # --------------------------------------------------------
    # 5.1 Duration comparison
    # --------------------------------------------------------

    st.markdown("#### Project duration comparison")

    duration_comparison = pd.DataFrame(
        {
            "Schedule": ["Baseline", "Custom simulation"],
            "Duration (days)": [
                baseline_duration,
                simulated_duration,
            ],
        }
    )

    fig_duration = px.bar(
        duration_comparison,
        x="Schedule",
        y="Duration (days)",
        text="Duration (days)",
        title="Baseline vs simulated project duration",
    )

    fig_duration.update_traces(textposition="outside")
    fig_duration.update_layout(
        showlegend=False,
        yaxis_title="Calendar days",
        xaxis_title="",
    )

    st.plotly_chart(fig_duration, use_container_width=True)

    # --------------------------------------------------------
    # 5.2 CPM comparison
    # --------------------------------------------------------

    st.markdown("#### CPM impact")

    cpm_comparison = baseline[
        ["ID", "Duration_Plan_Days", "ES", "EF", "Total_Float", "Is_Critical"]
    ].merge(
        simulated_cpm[
            ["ID", "Duration_Simulated_Days", "ES", "EF", "Total_Float", "Is_Critical"]
        ],
        on="ID",
        suffixes=("_Baseline", "_Simulated"),
        how="left",
    )

    cpm_comparison["Activity"] = cpm_comparison["ID"].map(activity_names)

    cpm_comparison["Duration_Change"] = (
        cpm_comparison["Duration_Simulated_Days"] - cpm_comparison["Duration_Plan_Days"]
    )

    cpm_comparison["ES_Change"] = (
        cpm_comparison["ES_Simulated"] - cpm_comparison["ES_Baseline"]
    )

    cpm_comparison["EF_Change"] = (
        cpm_comparison["EF_Simulated"] - cpm_comparison["EF_Baseline"]
    )

    cpm_comparison["Float_Change"] = (
        cpm_comparison["Total_Float_Simulated"] - cpm_comparison["Total_Float_Baseline"]
    )

    cpm_comparison["Critical_Status_Changed"] = (
        cpm_comparison["Is_Critical_Baseline"]
        != cpm_comparison["Is_Critical_Simulated"]
    )

    cpm_changed = cpm_comparison[
        (cpm_comparison["Duration_Change"] != 0)
        | (cpm_comparison["ES_Change"] != 0)
        | (cpm_comparison["EF_Change"] != 0)
        | (cpm_comparison["Critical_Status_Changed"])
    ].copy()

    col1, col2, col3 = st.columns(3)

    col1.metric("Activities with CPM changes", len(cpm_changed))

    col2.metric(
        "Activities becoming critical",
        (
            int(
                (
                    ~cpm_changed["Is_Critical_Baseline"]
                    & cpm_changed["Is_Critical_Simulated"]
                ).sum()
            )
            if not cpm_changed.empty
            else 0
        ),
    )

    col3.metric(
        "Critical status changes",
        (
            int(cpm_changed["Critical_Status_Changed"].sum())
            if not cpm_changed.empty
            else 0
        ),
    )

    if cpm_changed.empty:
        st.info("No CPM changes relative to the baseline.")
    else:
        display_cpm = cpm_changed[
            [
                "ID",
                "Activity",
                "Duration_Change",
                "ES_Change",
                "EF_Change",
                "Float_Change",
                "Is_Critical_Baseline",
                "Is_Critical_Simulated",
                "Critical_Status_Changed",
            ]
        ].rename(
            columns={
                "ID": "Activity ID",
                "Activity": "Activity",
                "Duration_Change": "Duration change (d)",
                "ES_Change": "Early start change (d)",
                "EF_Change": "Early finish change (d)",
                "Float_Change": "Total float change (d)",
                "Is_Critical_Baseline": "Critical baseline",
                "Is_Critical_Simulated": "Critical simulated",
                "Critical_Status_Changed": "Critical status changed",
            }
        )

        st.dataframe(
            display_cpm.sort_values(
                ["Critical status changed", "Early finish change (d)"],
                ascending=[False, False],
            ),
            use_container_width=True,
            hide_index=True,
        )

    # --------------------------------------------------------
    # 5.3 Simulated critical path
    # --------------------------------------------------------

    st.markdown("#### Simulated critical activities")

    critical_activities = simulated_cpm[simulated_cpm["Is_Critical"]].copy()

    critical_activities["Activity"] = critical_activities["ID"].map(activity_names)

    critical_activities = critical_activities[
        [
            "ID",
            "Activity",
            "Duration_Simulated_Days",
            "ES",
            "EF",
            "Total_Float",
        ]
    ].sort_values("ES")

    st.dataframe(
        critical_activities,
        use_container_width=True,
        hide_index=True,
    )

    # --------------------------------------------------------
    # 5.4 Supply delays
    # --------------------------------------------------------

    st.markdown("#### Supply delay assessment")

    if simulated_supply.empty:
        st.info("No supply delays were introduced in this simulation.")

    else:
        simulated_supply["Activity"] = simulated_supply["Activity_ID"].map(
            activity_names
        )

        supply_display = simulated_supply[
            [
                "Activity_ID",
                "Activity",
                "Supply_Delay_Days",
            ]
        ].rename(
            columns={
                "Activity_ID": "Activity ID",
                "Supply_Delay_Days": "Supply delay (days)",
            }
        )

        st.dataframe(
            supply_display,
            use_container_width=True,
            hide_index=True,
        )

        st.warning(
            "Supply delays are recorded separately by the current simulation "
            "engine. They do not modify activity durations or recalculate CPM. "
            "Do not interpret them as additional project delay."
        )

    # --------------------------------------------------------
    # 5.5 Management interpretation
    # --------------------------------------------------------

    st.divider()
    st.subheader("Management interpretation")

    col1, col2, col3 = st.columns(3)

    # Schedule impact
    with col1:
        st.markdown("#### Schedule impact")

        st.metric(
            "Project delay",
            f"{project_delay:+.0f} days",
            delta=(f"{project_delay:+.0f} days" if project_delay != 0 else "No delay"),
            delta_color="inverse",
        )

        st.caption(
            f"Baseline: {baseline_duration:.0f} days · "
            f"Simulated: {simulated_duration:.0f} days"
        )

    # CPM impact
    with col2:
        st.markdown("#### CPM impact")

        st.metric(
            "Activities with CPM changes",
            len(cpm_changed),
        )

        st.caption(
            f"Critical activities: {baseline_critical} → " f"{simulated_critical}"
        )

        st.caption(
            f"Critical status changes: "
            f"{int(cpm_changed['Critical_Status_Changed'].sum())}"
        )

    # Supply exposure
    with col3:
        st.markdown("#### Supply exposure")

        total_supply_delay = float(summary["Total_Supply_Delay_Days"])

        st.metric(
            "Supply delay recorded",
            f"{total_supply_delay:.0f} days",
        )

        if not simulated_supply.empty:
            st.caption(f"Activities affected: {len(simulated_supply)}")
        else:
            st.caption("No supply delays introduced.")

    st.info(
        "**Management principle:** interpret schedule impact, CPM changes "
        "and supply exposure separately. Supply delays are recorded "
        "independently and do not recalculate the project schedule "
        "in the current simulation engine."
    )

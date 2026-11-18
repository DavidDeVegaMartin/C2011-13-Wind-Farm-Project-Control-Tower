import pandas as pd
import plotly.express as px
import streamlit as st

# ============================================================
# 1. PAGE CONFIGURATION
# ============================================================

st.title("Decision Cockpit")
st.caption(
    "Economic evaluation of corrective actions, "
    "intervention scenarios and management decisions."
)

data = st.session_state["project_data"]

economic_summary = data["economic_summary"].copy()
economic_individual = data["economic_individual"].copy()
economic_combined = data["economic_combined"].copy()
economic_breakeven = data["economic_breakeven"].copy()
economic_decision = data["economic_decision_matrix"].copy()
economic_assumptions = data["economic_assumptions"].copy()


# ============================================================
# 2. FORMATTING FUNCTIONS
# ============================================================


def eur(value):
    if pd.isna(value):
        return "N/A"
    return f"€{value:,.0f}"


def pct(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:.2f}%"


scenario_order = ["Pessimistic", "Realistic", "Optimistic"]

available_scenarios = [
    scenario
    for scenario in scenario_order
    if scenario in economic_summary["Scenario"].unique()
]


# ============================================================
# 3. SCENARIO SELECTOR
# ============================================================

st.subheader("Economic scenario")

selected_scenario = st.selectbox(
    "Select economic scenario",
    options=available_scenarios,
    index=(
        available_scenarios.index("Realistic")
        if "Realistic" in available_scenarios
        else 0
    ),
)

summary_row = economic_summary[economic_summary["Scenario"] == selected_scenario].iloc[
    0
]

combined_row = economic_combined[
    economic_combined["Scenario"] == selected_scenario
].iloc[0]

individual = economic_individual[
    economic_individual["Scenario"] == selected_scenario
].copy()

breakeven = economic_breakeven[
    economic_breakeven["Scenario"] == selected_scenario
].copy()

decision = economic_decision[economic_decision["Scenario"] == selected_scenario].copy()

assumptions = economic_assumptions.copy()

# ============================================================
# 4. EXECUTIVE ECONOMIC SUMMARY
# ============================================================

st.divider()
st.subheader("Combined intervention — economic summary")

col1, col2, col3, col4 = st.columns(4)

col1.metric(
    "Intervention cost",
    eur(combined_row["Intervention_Cost_EUR"]),
)

col2.metric(
    "Avoided cost",
    eur(combined_row["Avoided_Cost_EUR"]),
)

col3.metric(
    "Net benefit",
    eur(combined_row["Net_Benefit_EUR"]),
)

col4.metric(
    "Combined ROI",
    pct(combined_row["ROI_Pct"]),
)

col1, col2, col3 = st.columns(3)

col1.metric(
    "Project days recovered",
    f"{summary_row['Project_Days_Recovered']:.0f}",
)

col2.metric(
    "Residual project delay",
    f"{summary_row['Residual_Project_Delay_Days']:.0f} days",
)

col3.metric(
    "Residual supply impact",
    f"{summary_row['Residual_Supply_Impact_Days']:.0f} days",
)

st.markdown(f"**Combined economic decision:** " f"{combined_row['Economic_Decision']}")


# ============================================================
# 5. INDIVIDUAL CORRECTIVE ACTIONS
# ============================================================

with st.expander("Individual corrective action assessment"):

    for action_id in ["CA01", "CA02"]:

        action = individual[individual["Action_ID"] == action_id]

        if action.empty:
            continue

        row = action.iloc[0]

        with st.container(border=True):

            st.markdown(f"#### {row['Action_ID']} — {row['Action']}")

            col1, col2, col3, col4 = st.columns(4)

            col1.metric(
                "Intervention cost",
                eur(row["Intervention_Cost_EUR"]),
            )

            col2.metric(
                "Avoided cost",
                eur(row["Avoided_Cost_EUR"]),
            )

            col3.metric(
                "Net benefit",
                eur(row["Net_Benefit_EUR"]),
            )

            col4.metric(
                "ROI",
                pct(row["ROI_Pct"]),
            )

            col1, col2, col3 = st.columns(3)

            col1.metric(
                "Impact before",
                f"{row['Impact_Before_Days']:.0f} days",
            )

            col2.metric(
                "Impact after",
                f"{row['Impact_After_Days']:.0f} days",
            )

            col3.metric(
                "Break-even intervention cost",
                eur(row["Break_Even_Intervention_EUR"]),
            )

            st.write(f"**Economic viability:** {row['Economic_Decision']}")


# ============================================================
# 6. COMBINED ECONOMIC COMPARISON
# ============================================================

st.divider()
st.subheader("Economic performance across scenarios")

comparison = economic_summary.copy()

comparison["Scenario"] = pd.Categorical(
    comparison["Scenario"],
    categories=scenario_order,
    ordered=True,
)

comparison = comparison.sort_values("Scenario")

# ------------------------------------------------------------
# Net benefit comparison
# ------------------------------------------------------------

fig_benefit = px.bar(
    comparison,
    x="Scenario",
    y="Combined_Net_Benefit_EUR",
    text="Combined_Net_Benefit_EUR",
    title="Combined net benefit by scenario",
    labels={
        "Combined_Net_Benefit_EUR": "Net benefit (€)",
        "Scenario": "Economic scenario",
    },
)

fig_benefit.add_hline(
    y=0,
    line_dash="dash",
    line_width=1,
)

fig_benefit.update_traces(
    texttemplate="€%{text:,.0f}",
    textposition="outside",
)

st.plotly_chart(
    fig_benefit,
    use_container_width=True,
)

# ------------------------------------------------------------
# Operational and financial comparison
# ------------------------------------------------------------

comparison_display = comparison[
    [
        "Scenario",
        "Combined_ROI_Pct",
    ]
].copy()

comparison_display = comparison_display.rename(
    columns={
        "Scenario": "Scenario",
        "Combined_ROI_Pct": "ROI (%)",
    }
)

st.dataframe(
    comparison_display,
    use_container_width=True,
    hide_index=True,
)

# ============================================================
# 7. BREAK-EVEN ANALYSIS
# ============================================================

with st.expander("Break-even analysis"):

    st.caption(
        "Economic thresholds calculated from the existing intervention "
        "cost and avoided-cost assumptions."
    )

    breakeven_display = breakeven[
        [
            "Action_ID",
            "Maximum_Intervention_Cost_EUR",
            "Minimum_Daily_Impact_Cost_EUR",
            "Minimum_Avoidable_Days",
            "Net_Benefit_EUR",
            "ROI_Pct",
        ]
    ].copy()

    breakeven_display = breakeven_display.rename(
        columns={
            "Action_ID": "Action",
            "Maximum_Intervention_Cost_EUR": "Maximum intervention cost (€)",
            "Minimum_Daily_Impact_Cost_EUR": "Minimum daily impact cost (€/day)",
            "Minimum_Avoidable_Days": "Minimum avoidable days",
            "Net_Benefit_EUR": "Net benefit (€)",
            "ROI_Pct": "ROI (%)",
        }
    )

    st.dataframe(
        breakeven_display,
        use_container_width=True,
        hide_index=True,
    )

# ============================================================
# 8. MANAGEMENT DECISION MATRIX
# ============================================================

st.divider()
st.subheader("Management decision matrix")

st.caption(
    "Recommended management decisions combining economic viability "
    "with residual supply and schedule exposure."
)

decision_display = decision[
    [
        "Action_ID",
        "Intervention_Cost_EUR",
        "Avoided_Cost_EUR",
        "Net_Benefit_EUR",
        "ROI_Pct",
        "Decision",
        "Residual_Supply_Risk",
        "Residual_Project_Delay_Days",
    ]
].copy()

decision_display = decision_display.rename(
    columns={
        "Action_ID": "Action",
        "Intervention_Cost_EUR": "Intervention cost (€)",
        "Avoided_Cost_EUR": "Avoided cost (€)",
        "Net_Benefit_EUR": "Net benefit (€)",
        "ROI_Pct": "ROI (%)",
        "Decision": "Management decision",
        "Residual_Supply_Risk": "Residual supply risk",
        "Residual_Project_Delay_Days": "Residual project delay (d)",
    }
)

st.dataframe(
    decision_display,
    use_container_width=True,
    hide_index=True,
)

# ============================================================
# 9. ECONOMIC ASSUMPTIONS
# ============================================================

st.divider()

with st.expander("Economic assumptions and model inputs"):

    assumption_display = assumptions[
        [
            "Action_ID",
            "Parameter",
            "Description",
            "Unit",
            "Pessimistic",
            "Realistic",
            "Optimistic",
        ]
    ].copy()

    assumption_display = assumption_display.rename(
        columns={
            "Action_ID": "Action",
            "Parameter": "Parameter",
            "Description": "Description",
            "Unit": "Unit",
            "Pessimistic": "Pessimistic",
            "Realistic": "Realistic",
            "Optimistic": "Optimistic",
        }
    )

    st.dataframe(
        assumption_display,
        use_container_width=True,
        hide_index=True,
    )

# ============================================================
# 10. MANAGEMENT INTERPRETATION
# ============================================================

st.divider()
st.subheader("Management interpretation")

st.info(
    "Economic results are scenario-based estimates derived from "
    "the intervention assumptions. They are not actual realised savings "
    "or costs attributed to individual activities. Management decisions "
    "should also consider residual schedule and supply risks."
)

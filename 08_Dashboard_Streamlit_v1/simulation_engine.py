
from graphlib import TopologicalSorter, CycleError

import pandas as pd


# ============================================================
# SIMULATION ENGINE
# C2011-13 WIND FARM
# ============================================================

ALLOWED_RELATIONS = {"FS", "SS", "FF", "SF"}
TOLERANCE = 1e-6


# ============================================================
# 1. BUILD DEPENDENCY NETWORK
# ============================================================

def build_dependency_network(df_activities, df_dependencies):

    activity_ids = set(df_activities["ID"].astype(int))

    if len(activity_ids) != len(df_activities):
        raise ValueError("Activity IDs must be unique.")

    required_columns = {
        "Predecessor_ID",
        "Successor_ID",
        "Relation_Type",
        "Lag"
    }

    missing = required_columns - set(df_dependencies.columns)

    if missing:
        raise ValueError(f"Missing dependency columns: {missing}")

    predecessors = {
        activity_id: set()
        for activity_id in activity_ids
    }

    incoming = {
        activity_id: []
        for activity_id in activity_ids
    }

    outgoing = {
        activity_id: []
        for activity_id in activity_ids
    }

    for row in df_dependencies.itertuples(index=False):

        predecessor = int(row.Predecessor_ID)
        successor = int(row.Successor_ID)

        relation = str(row.Relation_Type).upper().strip()
        lag = float(row.Lag)

        if predecessor not in activity_ids or successor not in activity_ids:
            raise ValueError(
                f"Dependency references an unknown activity: "
                f"{predecessor} -> {successor}"
            )

        if relation not in ALLOWED_RELATIONS:
            raise ValueError(f"Unsupported relationship: {relation}")

        edge = {
            "Predecessor": predecessor,
            "Successor": successor,
            "Relation": relation,
            "Lag": lag
        }

        predecessors[successor].add(predecessor)

        incoming[successor].append(edge)
        outgoing[predecessor].append(edge)

    try:
        execution_order = list(
            TopologicalSorter(predecessors).static_order()
        )

    except CycleError as exc:
        raise RuntimeError(
            "The dependency network contains a cycle."
        ) from exc

    return incoming, outgoing, execution_order


# ============================================================
# 2. CORRECTED CPM CALCULATION
# Based on NB_09 corrected implementation
# ============================================================

def calculate_scenario_cpm(
    durations,
    execution_order,
    incoming,
    outgoing
):

    durations = {
        activity_id: float(duration)
        for activity_id, duration in durations.items()
    }

    if set(durations) != set(execution_order):
        raise ValueError(
            "Duration activities do not match the dependency network."
        )

    if any(duration < 0 for duration in durations.values()):
        raise ValueError("Activity durations cannot be negative.")

    es = {}
    ef = {}

    # --------------------------------------------------------
    # FORWARD PASS
    # --------------------------------------------------------

    for activity_id in execution_order:

        duration = durations[activity_id]
        constraints = []

        for edge in incoming[activity_id]:

            predecessor = edge["Predecessor"]
            relation = edge["Relation"]
            lag = edge["Lag"]

            if relation == "FS":
                candidate = ef[predecessor] + lag

            elif relation == "SS":
                candidate = es[predecessor] + lag

            elif relation == "FF":
                candidate = ef[predecessor] + lag - duration

            elif relation == "SF":
                candidate = es[predecessor] + lag - duration

            constraints.append(candidate)

        es[activity_id] = max([0.0] + constraints)
        ef[activity_id] = es[activity_id] + duration

    project_duration = max(ef.values())

    # --------------------------------------------------------
    # BACKWARD PASS
    # Corrected global project-finish constraint
    # --------------------------------------------------------

    ls = {}
    lf = {}

    for activity_id in reversed(execution_order):

        duration = durations[activity_id]

        # Global constraint: every activity must finish
        # no later than the project completion date.
        constraints = [
            project_duration - duration
        ]

        for edge in outgoing[activity_id]:

            successor = edge["Successor"]
            relation = edge["Relation"]
            lag = edge["Lag"]

            if relation == "FS":
                candidate = ls[successor] - lag - duration

            elif relation == "SS":
                candidate = ls[successor] - lag

            elif relation == "FF":
                candidate = lf[successor] - lag - duration

            elif relation == "SF":
                candidate = lf[successor] - lag

            constraints.append(candidate)

        ls[activity_id] = min(constraints)
        lf[activity_id] = ls[activity_id] + duration

    # --------------------------------------------------------
    # RESULTS
    # --------------------------------------------------------

    results = pd.DataFrame({
        "ID": list(durations.keys()),
        "Duration_Simulated_Days": list(durations.values())
    })

    results["ES"] = results["ID"].map(es)
    results["EF"] = results["ID"].map(ef)
    results["LS"] = results["ID"].map(ls)
    results["LF"] = results["ID"].map(lf)

    results["Total_Float"] = (
        results["LS"] - results["ES"]
    )

    results["Is_Critical"] = (
        results["Total_Float"].abs() <= TOLERANCE
    )

    return results, project_duration


# ============================================================
# 3. RUN SCENARIO SIMULATIONS
# ============================================================

def run_scenario_simulation(data):

    df_baseline = data["cpm_activity"].copy()

    df_dependencies = data["cpm_dependencies"].copy()

    df_scenarios = data["scenario_configuration"].copy()

    required_baseline = {
        "ID",
        "Duration_Plan_Days"
    }

    if not required_baseline.issubset(df_baseline.columns):
        raise ValueError(
            "CPM activity data must contain ID and Duration_Plan_Days."
        )

    required_scenarios = {
        "Scenario_ID",
        "Activity_ID",
        "Impact_Type",
        "Delay_Days"
    }

    if not required_scenarios.issubset(df_scenarios.columns):
        raise ValueError(
            "Scenario configuration has missing columns."
        )

    # Normalize activity identifiers
    df_baseline["ID"] = df_baseline["ID"].astype(int)

    df_dependencies["Predecessor_ID"] = (
        df_dependencies["Predecessor_ID"].astype(int)
    )

    df_dependencies["Successor_ID"] = (
        df_dependencies["Successor_ID"].astype(int)
    )

    df_scenarios["Activity_ID"] = (
        df_scenarios["Activity_ID"].astype(int)
    )

    # Build network once
    incoming, outgoing, execution_order = (
        build_dependency_network(
            df_baseline,
            df_dependencies
        )
    )

    # --------------------------------------------------------
    # Prepare and run each scenario
    # --------------------------------------------------------

    activity_results = []
    supply_results = []
    cpm_results = []
    summary_results = []

    scenario_ids = sorted(
        df_scenarios["Scenario_ID"].dropna().unique()
    )

    for scenario_id in scenario_ids:

        scenario_rows = df_scenarios[
            df_scenarios["Scenario_ID"] == scenario_id
        ].copy()

        # Activity delays
        activity_impacts = (
            scenario_rows[
                scenario_rows["Impact_Type"] == "ACTIVITY_DELAY"
            ]
            .groupby("Activity_ID")["Delay_Days"]
            .sum()
        )

        # Supply delays are kept separate from CPM
        supply_impacts = scenario_rows[
            scenario_rows["Impact_Type"] == "SUPPLY_DELAY"
        ].copy()

        for row in supply_impacts.itertuples(index=False):

            supply_results.append({
                "Scenario_ID": scenario_id,
                "Activity_ID": int(row.Activity_ID),
                "Supply_Delay_Days": float(row.Delay_Days)
            })

        # Build simulated activity durations
        df_scenario = df_baseline[
            ["ID", "Duration_Plan_Days"]
        ].copy()

        df_scenario["Scenario_ID"] = scenario_id

        df_scenario["Activity_Delay_Applied"] = (
            df_scenario["ID"]
            .map(activity_impacts)
            .fillna(0.0)
        )

        df_scenario["Duration_Simulated_Days"] = (
            df_scenario["Duration_Plan_Days"]
            + df_scenario["Activity_Delay_Applied"]
        )

        activity_results.append(df_scenario)

        durations = (
            df_scenario
            .set_index("ID")["Duration_Simulated_Days"]
            .to_dict()
        )

        # Recalculate CPM
        df_result, project_duration = calculate_scenario_cpm(
            durations,
            execution_order,
            incoming,
            outgoing
        )

        df_result["Scenario_ID"] = scenario_id

        cpm_results.append(df_result)

        summary_results.append({
            "Scenario_ID": scenario_id,
            "Project_Duration_Days": project_duration,
            "Critical_Activities": int(
                df_result["Is_Critical"].sum()
            ),
            "Total_Activity_Delay_Days": float(
                df_scenario["Activity_Delay_Applied"].sum()
            ),
            "Total_Supply_Delay_Days": float(
                supply_impacts["Delay_Days"].sum()
            )
        })

    # --------------------------------------------------------
    # Consolidate results
    # --------------------------------------------------------

    df_scenario_durations = pd.concat(
        activity_results,
        ignore_index=True
    )

    df_scenario_supply = pd.DataFrame(
        supply_results,
        columns=[
            "Scenario_ID",
            "Activity_ID",
            "Supply_Delay_Days"
        ]
    )

    df_scenario_cpm = pd.concat(
        cpm_results,
        ignore_index=True
    )

    df_scenario_summary = pd.DataFrame(
        summary_results
    )

    # --------------------------------------------------------
    # Return results
    # --------------------------------------------------------

    return {
        "scenario_durations": df_scenario_durations,
        "scenario_supply": df_scenario_supply,
        "scenario_cpm": df_scenario_cpm,
        "scenario_summary": df_scenario_summary
    }



# ============================================================
# 4. CUSTOM SIMULATION
# User-defined activity and supply delays
# ============================================================

def run_custom_simulation(
    data,
    activity_delays=None,
    supply_delays=None,
    scenario_id="CUSTOM"
):
    """
    Runs a custom simulation using user-defined delays.

    Parameters
    ----------
    data : dict
        Dictionary returned by load_data().

    activity_delays : dict
        {Activity_ID: Delay_Days}
        These delays modify activity durations and recalculate CPM.

    supply_delays : dict
        {Activity_ID: Delay_Days}
        These delays are recorded separately and do not modify CPM.

    scenario_id : str
        Identifier assigned to the custom simulation.

    Returns
    -------
    dict
        scenario_durations
        scenario_supply
        scenario_cpm
        scenario_summary
    """

    activity_delays = activity_delays or {}
    supply_delays = supply_delays or {}

    df_baseline = data["cpm_activity"].copy()
    df_dependencies = data["cpm_dependencies"].copy()

    # --------------------------------------------------------
    # 1. Validate baseline
    # --------------------------------------------------------

    df_baseline["ID"] = df_baseline["ID"].astype(int)

    activity_ids = set(df_baseline["ID"])

    if df_baseline["ID"].duplicated().any():
        raise ValueError("Baseline contains duplicated activity IDs.")

    # --------------------------------------------------------
    # 2. Validate user parameters
    # --------------------------------------------------------

    def validate_delays(delays, parameter_name):

        validated = {}

        for activity_id, delay in delays.items():

            activity_id = int(activity_id)
            delay = float(delay)

            if activity_id not in activity_ids:
                raise ValueError(
                    f"{parameter_name}: unknown activity ID "
                    f"{activity_id}."
                )

            if not pd.notna(delay) or delay < 0:
                raise ValueError(
                    f"{parameter_name}: delays must be "
                    "non-negative numeric values."
                )

            validated[activity_id] = (
                validated.get(activity_id, 0.0) + delay
            )

        return validated

    activity_delays = validate_delays(
        activity_delays,
        "Activity delays"
    )

    supply_delays = validate_delays(
        supply_delays,
        "Supply delays"
    )

    # --------------------------------------------------------
    # 3. Build dependency network
    # --------------------------------------------------------

    incoming, outgoing, execution_order = (
        build_dependency_network(
            df_baseline,
            df_dependencies
        )
    )

    # --------------------------------------------------------
    # 4. Apply activity delays
    # --------------------------------------------------------

    df_scenario = df_baseline[
        ["ID", "Duration_Plan_Days"]
    ].copy()

    df_scenario["Scenario_ID"] = scenario_id

    df_scenario["Activity_Delay_Applied"] = (
        df_scenario["ID"]
        .map(activity_delays)
        .fillna(0.0)
    )

    df_scenario["Duration_Simulated_Days"] = (
        df_scenario["Duration_Plan_Days"]
        + df_scenario["Activity_Delay_Applied"]
    )

    durations = (
        df_scenario
        .set_index("ID")["Duration_Simulated_Days"]
        .to_dict()
    )

    # --------------------------------------------------------
    # 5. Recalculate CPM
    # --------------------------------------------------------

    df_cpm, project_duration = calculate_scenario_cpm(
        durations,
        execution_order,
        incoming,
        outgoing
    )

    df_cpm["Scenario_ID"] = scenario_id

    # --------------------------------------------------------
    # 6. Record supply delays separately
    # --------------------------------------------------------

    df_supply = pd.DataFrame(
        [
            {
                "Scenario_ID": scenario_id,
                "Activity_ID": activity_id,
                "Supply_Delay_Days": delay
            }
            for activity_id, delay in supply_delays.items()
            if delay > 0
        ],
        columns=[
            "Scenario_ID",
            "Activity_ID",
            "Supply_Delay_Days"
        ]
    )

    # --------------------------------------------------------
    # 7. Build summary
    # --------------------------------------------------------

    df_summary = pd.DataFrame([{
        "Scenario_ID": scenario_id,
        "Project_Duration_Days": project_duration,
        "Critical_Activities": int(
            df_cpm["Is_Critical"].sum()
        ),
        "Total_Activity_Delay_Days": float(
            df_scenario["Activity_Delay_Applied"].sum()
        ),
        "Total_Supply_Delay_Days": float(
            df_supply["Supply_Delay_Days"].sum()
        )
    }])

    # --------------------------------------------------------
    # 8. Return results
    # --------------------------------------------------------

    return {
        "scenario_durations": df_scenario,
        "scenario_supply": df_supply,
        "scenario_cpm": df_cpm,
        "scenario_summary": df_summary
    }


from pathlib import Path

import pandas as pd


# ============================================================
# PATHS
# ============================================================

APP_DIR = Path(__file__).resolve().parent
DATA_DIR = APP_DIR / "data"


# ============================================================
# DATA LOADER
# ============================================================

def load_data():

    data = {}

    # --------------------------------------------------------
    # PROJECT HISTORY
    # --------------------------------------------------------

    data["activity_master"] = pd.read_excel(
        DATA_DIR / "Activity_Master.xlsx"
    )

    data["activity_tracking"] = pd.read_excel(
        DATA_DIR / "Activity_Tracking.xlsx"
    )

    data["project_tracking"] = pd.read_excel(
        DATA_DIR / "Project_Tracking.xlsx"
    )

    # --------------------------------------------------------
    # PROJECT CONTROL AND CPM
    # --------------------------------------------------------

    data["schedule_control"] = pd.read_excel(
        DATA_DIR / "Schedule_Control.xlsx",
        sheet_name="Schedule Control"
    )

    data["cpm_activity"] = pd.read_csv(
        DATA_DIR / "cpm_activity_schedule.csv"
    )

    data["cpm_dependencies"] = pd.read_csv(
        DATA_DIR / "cpm_dependencies.csv"
    )

    data["cpm_project_summary"] = pd.read_csv(
        DATA_DIR / "cpm_project_summary.csv"
    )

    # --------------------------------------------------------
    # SCENARIOS
    # --------------------------------------------------------

    scenario_file = DATA_DIR / "Scenario_Configuration.xlsx"

    data["activity_catalog"] = pd.read_excel(
        scenario_file,
        sheet_name="Activity Catalog"
    )

    data["scenario_configuration"] = pd.read_excel(
        scenario_file,
        sheet_name="Scenarios"
    )

    simulation_file = DATA_DIR / "Scenario_Simulation_Results.xlsx"

    data["scenario_summary"] = pd.read_excel(
        simulation_file,
        sheet_name="Scenario Summary"
    )

    data["scenario_activity_comparison"] = pd.read_excel(
        simulation_file,
        sheet_name="Activity Comparison"
    )

    data["scenario_cpm"] = pd.read_excel(
        simulation_file,
        sheet_name="Scenario CPM"
    )

    data["scenario_supply_impacts"] = pd.read_excel(
        simulation_file,
        sheet_name="Supply Impacts"
    )

    # --------------------------------------------------------
    # CORRECTIVE ACTIONS
    # --------------------------------------------------------

    corrective_file = DATA_DIR / "Corrective_Action_Evaluation.xlsx"

    data["corrective_decision_summary"] = pd.read_excel(
        corrective_file,
        sheet_name="Decision Summary"
    )

    data["corrective_actions"] = pd.read_excel(
        corrective_file,
        sheet_name="Corrective Actions"
    )

    data["corrective_supply_risk"] = pd.read_excel(
        corrective_file,
        sheet_name="Supply Risk"
    )

    data["corrective_cpm_comparison"] = pd.read_excel(
        corrective_file,
        sheet_name="Activity CPM Comparison"
    )

    # --------------------------------------------------------
    # ECONOMIC IMPACT
    # --------------------------------------------------------

    economic_file = DATA_DIR / "Economic_Impact_Assessment.xlsx"

    data["economic_summary"] = pd.read_excel(
        economic_file,
        sheet_name="Executive Summary"
    )

    data["economic_assumptions"] = pd.read_excel(
        economic_file,
        sheet_name="Assumptions"
    )

    data["economic_individual"] = pd.read_excel(
        economic_file,
        sheet_name="Individual Results"
    )

    data["economic_combined"] = pd.read_excel(
        economic_file,
        sheet_name="Combined SC03"
    )

    data["economic_breakeven"] = pd.read_excel(
        economic_file,
        sheet_name="Break-even"
    )

    data["economic_decision_matrix"] = pd.read_excel(
        economic_file,
        sheet_name="Decision Matrix"
    )

    return data

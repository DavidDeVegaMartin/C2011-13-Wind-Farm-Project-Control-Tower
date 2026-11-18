from pathlib import Path
import json

import pandas as pd
import streamlit as st
import streamlit.components.v1 as components

# ============================================================
# 1. PATHS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
APP_DIR = BASE_DIR.parent
DATA_DIR = APP_DIR / "data"

CODEBASE = (
    BASE_DIR
    / "gantt_component"
    / "frontend"
    / "node_modules"
    / "dhtmlx-gantt"
    / "codebase"
)


# ============================================================
# 2. LOAD DATA
# ============================================================

master = pd.read_excel(DATA_DIR / "Activity_Master.xlsx")

schedule = pd.read_csv(DATA_DIR / "cpm_activity_schedule.csv")

dependencies = pd.read_csv(DATA_DIR / "cpm_dependencies.csv")

tracking = pd.read_excel(DATA_DIR / "Activity_Tracking.xlsx")


# ============================================================
# 3. SELECT TRACKING PERIOD
# ============================================================

selected_tp = int(tracking["TP"].max())

tracking_tp = tracking.loc[tracking["TP"] == selected_tp].drop_duplicates("Activity_ID")

progress_map = tracking_tp.set_index("Activity_ID")["Pct_Complete"].to_dict()


# ============================================================
# 4. BUILD WBS HIERARCHY
# ============================================================

master = master.copy()

master["ID"] = master["ID"].astype(int)
master["WBS"] = master["WBS"].astype(str)

master_by_wbs = {row["WBS"]: row for _, row in master.iterrows()}

children = {int(row["ID"]): [] for _, row in master.iterrows()}

parent_map = {}

for _, row in master.iterrows():

    wbs = row["WBS"]
    parts = wbs.split(".")

    if len(parts) == 1:
        continue

    parent_wbs = ".".join(parts[:-1])

    parent_row = master_by_wbs.get(parent_wbs)

    if parent_row is None:
        continue

    parent_id = int(parent_row["ID"])
    child_id = int(row["ID"])

    children[parent_id].append(child_id)
    parent_map[child_id] = parent_id


# ============================================================
# 5. PREPARE CPM DATA
# ============================================================

schedule = schedule.copy()

schedule["ID"] = schedule["ID"].astype(int)

schedule["CPM_Start_Date"] = pd.to_datetime(schedule["CPM_Start_Date"])

schedule["CPM_Finish_Date"] = pd.to_datetime(schedule["CPM_Finish_Date"])

schedule_by_id = schedule.set_index("ID").to_dict("index")

critical_ids = set(
    schedule.loc[
        schedule["Is_Critical"].astype(str).str.lower().isin(["true", "1"]), "ID"
    ].astype(int)
)


# ============================================================
# 6. CALCULATE PROJECT DATES FROM TERMINAL DESCENDANTS
# ============================================================


def get_terminal_schedule_ids(node_id):

    descendants = children.get(node_id, [])

    if not descendants:

        if node_id in schedule_by_id:
            return [node_id]

        return []

    result = []

    for child_id in descendants:
        result.extend(get_terminal_schedule_ids(child_id))

    return result


def get_node_dates(node_id):

    # WBS node with children:
    # derive dates from terminal CPM descendants.

    if children.get(node_id):

        terminal_ids = get_terminal_schedule_ids(node_id)

        if terminal_ids:

            dates = [schedule_by_id[i] for i in terminal_ids]

            start = min(x["CPM_Start_Date"] for x in dates)

            finish = max(x["CPM_Finish_Date"] for x in dates)

            duration = max(0, (finish - start).total_seconds() / 86400)

            return start, duration

        # Fallback to own CPM dates if available.
        if node_id in schedule_by_id:

            row = schedule_by_id[node_id]

            return (row["CPM_Start_Date"], float(row["Duration_Plan_Days"]))

        return None, None

    # Terminal activity.
    if node_id in schedule_by_id:

        row = schedule_by_id[node_id]

        return (row["CPM_Start_Date"], float(row["Duration_Plan_Days"]))

    return None, None


# ============================================================
# 7. BUILD DHTMLX TASKS
# ============================================================

tasks = []

for _, row in master.iterrows():

    node_id = int(row["ID"])
    name = str(row["Name"])

    parent_id = parent_map.get(node_id)

    has_children = bool(children.get(node_id))

    start, duration = get_node_dates(node_id)

    progress = float(progress_map.get(node_id, 0))

    task = {
        "id": f"task_{node_id}",
        "text": name,
        "parent": (f"task_{parent_id}" if parent_id is not None else 0),
        "open": True,
        "progress": progress,
    }

    if has_children:

        task["type"] = "project"

        if start is not None:
            task["start_date"] = start.strftime("%Y-%m-%d %H:%M")
            task["duration"] = duration

    elif start is not None:

        task["start_date"] = start.strftime("%Y-%m-%d %H:%M")

        task["duration"] = duration

        if duration == 0:
            task["type"] = "milestone"
        else:
            task["type"] = "task"

        if node_id in critical_ids:
            task["critical"] = True

    else:

        # Defensive fallback for a node without CPM data.
        task["type"] = "project"

    tasks.append(task)


# ============================================================
# 8. BUILD DEPENDENCIES
# ============================================================

relation_mapping = {
    "FS": "0",
    "SS": "1",
    "FF": "2",
    "SF": "3",
}

links = []

for idx, row in dependencies.iterrows():

    relation = str(row["Relation_Type"]).upper()

    if relation not in relation_mapping:
        continue

    links.append(
        {
            "id": int(idx) + 1,
            "source": f"task_{int(row['Predecessor_ID'])}",
            "target": f"task_{int(row['Successor_ID'])}",
            "type": relation_mapping[relation],
            "lag": float(row["Lag"]),
        }
    )


# ============================================================
# 9. SERIALIZE DATA
# ============================================================

gantt_data = json.dumps(
    {
        "data": tasks,
        "links": links,
    },
    ensure_ascii=False,
)


# ============================================================
# 10. LOAD DHTMLX ASSETS
# ============================================================

css_path = CODEBASE / "dhtmlxgantt.css"
js_path = CODEBASE / "dhtmlxgantt.js"

if not css_path.exists() or not js_path.exists():

    st.error("No se encuentran los archivos locales de DHTMLX.")

    st.stop()

css = css_path.read_text(encoding="utf-8")
js = js_path.read_text(encoding="utf-8")


# ============================================================
# 11. HTML
# ============================================================

html = r"""
<!DOCTYPE html>
<html>
<head>

<meta charset="utf-8">

<style>
__CSS__

html, body {
    margin: 0;
    padding: 0;
    width: 100%;
    height: 100%;
    overflow: hidden;
    font-family: Arial, sans-serif;
}

#gantt_here {
    width: 100%;
    height: 780px;
}

.gantt_task_line.critical_task {
    background-color: #d9534f;
    border-color: #b52b27;
}

.gantt_task_line.critical_task .gantt_task_progress {
    background-color: #8f1d19;
}

/* MEJORAS DE VISUALIZACIÓN DEL GANTT - PROGRESO DE ACTIVIDADES Y TAMAÑO TAREAS CORTAS*/

/* Mejorar visibilidad de actividades de corta duración */
.gantt_task_line:not(.gantt_project):not(.gantt_milestone) {
    min-width: 8px;
}

.gantt_tree_content {
    font-size: 12px;
}

/* Progreso de actividades normales */
.gantt_task_line .gantt_task_progress {
    background-color: #174f78;
}

/* Progreso de actividades críticas */
.gantt_task_line.critical_task .gantt_task_progress {
    background-color: #8f1d19;
}


</style>

</head>

<body>

<div id="gantt_here"></div>

<script>
__JS__
</script>

<script>

const ganttData = __DATA__;

gantt.config.date_format = "%Y-%m-%d %H:%i";

gantt.config.readonly = true;

gantt.config.grid_width = 390;

gantt.config.min_column_width = 45;

gantt.config.row_height = 28;

gantt.config.bar_height = 18;

// Escala temporal: meses y semanas
gantt.config.scales = [
    {
        unit: "month",
        step: 1,
        format: "%M %Y"
    },
    {
        unit: "week",
        step: 1,
        format: "S%W"
    }
];

// Altura y anchura de la escala
gantt.config.scale_height = 48;

gantt.config.min_column_width = 38;

gantt.config.fit_tasks = true;

gantt.config.show_progress = true;

gantt.config.open_tree_initially = true;

gantt.config.columns = [

    {
        name: "text",
        label: "WBS / Actividad",
        tree: true,
        width: "*",
        resize: true
    },

    {
        name: "start_date",
        label: "Inicio",
        align: "center",
        width: 105
    },

    {
        name: "duration",
        label: "Días",
        align: "center",
        width: 55
    }

];

gantt.templates.task_class = function(
    start,
    end,
    task
) {

    if (task.critical) {
        return "critical_task";
    }

    return "";
};


gantt.init("gantt_here");

gantt.parse(ganttData);

</script>

</body>
</html>
"""

html = (
    html.replace("__CSS__", css).replace("__JS__", js).replace("__DATA__", gantt_data)
)


# ============================================================
# 12. STREAMLIT
# ============================================================

st.set_page_config(page_title="Wind Farm - Real Gantt", layout="wide")

st.title("Wind Farm — Real WBS / CPM Gantt")

st.caption(
    f"167 WBS nodes | 135 CPM activities | "
    f"150 dependencies | Tracking TP {selected_tp}"
)

col1, col2, col3, col4 = st.columns(4)

col1.metric("WBS nodes", len(master))
col2.metric("CPM activities", len(schedule))
col3.metric("Dependencies", len(links))
col4.metric("Critical activities", len(critical_ids))

components.html(html, height=820, scrolling=True)

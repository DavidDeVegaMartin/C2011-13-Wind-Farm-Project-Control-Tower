import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
import numpy as np

import json
from pathlib import Path
import streamlit.components.v1 as components

# ============================================================
# 1. CONTEXTO COMPARTIDO
# ============================================================

data = st.session_state.get("project_data")

if data is None:
    st.error("No se han cargado los datos del proyecto.")
    st.stop()

selected_tp = int(st.session_state.get("selected_tp", 120))
selected_date = st.session_state.get("selected_status_date")

cpm = data["cpm_activity"].copy()
dependencies = data["cpm_dependencies"].copy()
summary = data["cpm_project_summary"].iloc[0]
schedule = data["schedule_control"].copy()
activity_master = data["activity_master"].copy()
tracking = data["activity_tracking"].copy()

cpm["CPM_Start_Date"] = pd.to_datetime(cpm["CPM_Start_Date"])
cpm["CPM_Finish_Date"] = pd.to_datetime(cpm["CPM_Finish_Date"])
cpm["Is_Critical"] = cpm["Is_Critical"].fillna(False).astype(bool)

if selected_date is not None:
    selected_date = pd.to_datetime(selected_date)

# ============================================================
# 2. FUNCIONES AUXILIARES
# ============================================================


def fmt_days(value):
    if pd.isna(value):
        return "N/A"
    return f"{value:,.0f} days"


def fmt_date(value):
    if pd.isna(value):
        return "N/A"
    return pd.to_datetime(value).strftime("%d/%m/%Y")


def display_value(value, suffix=""):
    if pd.isna(value):
        return "Not available"

    if isinstance(value, (int, float, np.integer, np.floating)):
        return f"{value:,.1f}{suffix}"

    return str(value)


def parent_wbs(wbs):
    parts = str(wbs).split(".")
    return ".".join(parts[:-1]) if len(parts) > 1 else None


# ============================================================
# 3. SEGUIMIENTO DEL TP SELECCIONADO
# ============================================================

tracking_tp = tracking.loc[
    tracking["TP"] == selected_tp,
    [
        "Activity_ID",
        "Pct_Complete",
        "Actual_Start",
        "Actual_Duration_Days",
        "Actual_Cost",
        "EV",
        "PV",
    ],
].copy()

tracking_tp = tracking_tp.drop_duplicates("Activity_ID")

tracking_tp = tracking_tp.rename(columns={"Activity_ID": "ID"})

tracking_tp["Pct_Complete"] = tracking_tp["Pct_Complete"].clip(0, 1)

# Registro de actividades CPM con avance semanal.
cpm = cpm.merge(tracking_tp, on="ID", how="left")

cpm["Pct_Complete"] = cpm["Pct_Complete"].fillna(0)

cpm["Progress_Pct"] = cpm["Pct_Complete"] * 100


# ============================================================
# 4. REGISTRO DE ACTIVIDADES Y SUMINISTRO
# ============================================================

schedule_columns = [
    "ID",
    "Total_Cost_Plan",
    "Fixed_Cost",
    "Variable_Cost",
    "Material_Type",
    "Is_Critical_Material",
    "Lead_Time_Days",
    "Buffer_Days",
    "Supply_Delay_Days",
    "Supply_Buffer_Excess_Days",
    "Supply_Risk_Score",
    "Material_Status",
    "Risk_Level",
    "Supply_Alert",
    "Supply_Buffer_Exceeded",
]

available_schedule_columns = [
    col for col in schedule_columns if col in schedule.columns
]

activity_register = cpm.merge(
    schedule[available_schedule_columns].drop_duplicates("ID"), on="ID", how="left"
)

successor_counts = dependencies.groupby("Predecessor_ID")["Successor_ID"].nunique()

predecessor_counts = dependencies.groupby("Successor_ID")["Predecessor_ID"].nunique()

activity_register["Successors"] = (
    activity_register["ID"].map(successor_counts).fillna(0).astype(int)
)

activity_register["Predecessors"] = (
    activity_register["ID"].map(predecessor_counts).fillna(0).astype(int)
)

activity_register["Total_Connections"] = (
    activity_register["Successors"] + activity_register["Predecessors"]
)

supply_alerts = schedule.loc[schedule["Supply_Alert"].fillna(False).astype(bool)].copy()

buffer_exceeded = supply_alerts.loc[
    supply_alerts["Supply_Buffer_Exceeded"].fillna(False).astype(bool)
].copy()

critical_supply_alerts = supply_alerts.loc[
    supply_alerts["ID"].isin(cpm.loc[cpm["Is_Critical"], "ID"])
].copy()


# ============================================================
# 5. CONSTRUCCIÓN DE LA JERARQUÍA WBS
# ============================================================

cpm_fields = [
    "ID",
    "ES_Days",
    "EF_Days",
    "LS_Days",
    "LF_Days",
    "Total_Float_Days",
    "Free_Float_Days",
    "Is_Critical",
    "CPM_Start_Date",
    "CPM_Finish_Date",
]

wbs = activity_master.merge(cpm[cpm_fields], on="ID", how="left")

wbs = wbs.merge(tracking_tp[["ID", "Pct_Complete"]], on="ID", how="left")

wbs["Pct_Complete"] = wbs["Pct_Complete"].fillna(0)
wbs["Is_Critical"] = wbs["Is_Critical"].fillna(False).astype(bool)

wbs["Parent_WBS"] = wbs["WBS"].apply(parent_wbs)

# Identificar nodos con descendientes.
all_wbs_codes = wbs["WBS"].astype(str).tolist()

wbs["Has_Children"] = wbs["WBS"].apply(
    lambda code: any(other.startswith(str(code) + ".") for other in all_wbs_codes)
)

# Las actividades terminales son las hojas de la jerarquía.
terminal_nodes = wbs.loc[~wbs["Has_Children"]].copy()

# Completar fechas CPM de nodos resumen a partir de descendientes.
for idx, node in wbs.sort_values("WBS_Level", ascending=False).iterrows():

    if pd.notna(node["CPM_Start_Date"]):
        continue

    descendants = wbs.loc[
        wbs["WBS"].astype(str).str.startswith(str(node["WBS"]) + ".")
        & wbs["CPM_Start_Date"].notna()
    ]

    if descendants.empty:
        continue

    wbs.at[idx, "CPM_Start_Date"] = descendants["CPM_Start_Date"].min()

    wbs.at[idx, "CPM_Finish_Date"] = descendants["CPM_Finish_Date"].max()

    wbs.at[idx, "ES_Days"] = descendants["ES_Days"].min()
    wbs.at[idx, "EF_Days"] = descendants["EF_Days"].max()

    wbs.at[idx, "Total_Float_Days"] = descendants["Total_Float_Days"].min()

    wbs.at[idx, "Free_Float_Days"] = descendants["Free_Float_Days"].min()

    wbs.at[idx, "Is_Critical"] = descendants["Is_Critical"].any()

# Calcular avance agregado de los nodos resumen.
# Se pondera por duración planificada de las actividades terminales.
for idx, node in wbs.iterrows():

    if not node["Has_Children"]:
        continue

    descendants = terminal_nodes.loc[
        terminal_nodes["WBS"].astype(str).str.startswith(str(node["WBS"]) + ".")
    ].copy()

    if descendants.empty:
        continue

    weights = (
        pd.to_numeric(descendants["Duration_Plan_Days"], errors="coerce")
        .fillna(0)
        .clip(lower=0)
    )

    if weights.sum() > 0:
        progress = np.average(descendants["Pct_Complete"], weights=weights)
    else:
        progress = descendants["Pct_Complete"].mean()

    wbs.at[idx, "Pct_Complete"] = progress

wbs["Progress_Pct"] = wbs["Pct_Complete"] * 100

# Duración visual de los nodos resumen.
wbs["Duration_Visual_Days"] = (
    wbs["CPM_Finish_Date"] - wbs["CPM_Start_Date"]
).dt.total_seconds() / 86400

# Mapa de nodos por código WBS.
wbs_lookup = wbs.set_index("WBS").to_dict("index")


# ============================================================
# 6. GANTT CON AVANCE Y RUTA CRÍTICA
# ============================================================


# ============================================================
# 5B. DHTMLX GANTT — DASHBOARD INTEGRATION
# ============================================================


def build_dhtmlx_gantt():

    # Assets locales de DHTMLX, reutilizando la instalación validada.
    app_dir = Path(__file__).resolve().parents[1]

    codebase = (
        app_dir
        / "gantt_component"
        / "gantt_component"
        / "frontend"
        / "node_modules"
        / "dhtmlx-gantt"
        / "codebase"
    )

    css_path = codebase / "dhtmlxgantt.css"
    js_path = codebase / "dhtmlxgantt.js"

    if not css_path.exists() or not js_path.exists():
        st.error(
            "No se encuentran los archivos locales de DHTMLX. "
            f"Ruta comprobada: {codebase}"
        )
        return

    css = css_path.read_text(encoding="utf-8")
    js = js_path.read_text(encoding="utf-8")

    # Relación WBS -> ID.
    id_by_wbs = {str(row["WBS"]): int(row["ID"]) for _, row in wbs.iterrows()}

    tasks = []

    for _, row in wbs.iterrows():

        node_id = int(row["ID"])
        code = str(row["WBS"])
        parent_code = row["Parent_WBS"]

        parent_id = id_by_wbs.get(str(parent_code)) if pd.notna(parent_code) else None

        has_children = bool(row["Has_Children"])

        start = row["CPM_Start_Date"]

        if pd.isna(start):
            continue

        # Los nodos resumen utilizan el intervalo de sus descendientes.
        # Las actividades terminales conservan su duración CPM.
        if has_children:
            duration = float(row["Duration_Visual_Days"])
        else:
            duration = float(row["Duration_Plan_Days"])

        progress = float(np.clip(row["Pct_Complete"], 0, 1))

        task = {
            "id": f"task_{node_id}",
            "text": str(row["Name"]),
            "parent": (f"task_{parent_id}" if parent_id is not None else 0),
            "open": True,
            "progress": progress,
            "start_date": pd.to_datetime(start).strftime("%Y-%m-%d %H:%M"),
            "duration": max(0, duration),
        }

        if has_children:
            task["type"] = "project"
        elif duration == 0:
            task["type"] = "milestone"
        else:
            task["type"] = "task"

        if bool(row["Is_Critical"]):
            task["critical"] = True

        tasks.append(task)

    # Dependencias CPM.
    relation_mapping = {
        "FS": "0",
        "SS": "1",
        "FF": "2",
        "SF": "3",
    }

    valid_task_ids = {task["id"] for task in tasks}

    links = []

    for idx, row in dependencies.iterrows():

        relation = str(row["Relation_Type"]).upper()

        if relation not in relation_mapping:
            continue

        source = f"task_{int(row['Predecessor_ID'])}"
        target = f"task_{int(row['Successor_ID'])}"

        if source not in valid_task_ids or target not in valid_task_ids:
            continue

        links.append(
            {
                "id": int(idx) + 1,
                "source": source,
                "target": target,
                "type": relation_mapping[relation],
                "lag": float(row["Lag"]),
            }
        )

    gantt_data = json.dumps(
        {
            "data": tasks,
            "links": links,
        },
        ensure_ascii=False,
    )

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

            .gantt_task_line .gantt_task_progress {
                background-color: #174f78;
            }

            .gantt_task_line.critical_task .gantt_task_progress {
                background-color: #8f1d19;
            }

            .gantt_tree_content {
                font-size: 12px;
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

            gantt.config.grid_width = 480;
            gantt.config.row_height = 28;
            gantt.config.bar_height = 18;

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

            gantt.config.scale_height = 48;
            gantt.config.min_column_width = 38;

            gantt.config.fit_tasks = true;
            gantt.config.show_progress = true;
            gantt.config.open_tree_initially = true;

            gantt.config.columns = [
                {
                    name: "text",
                    label: "WBS / Activity",
                    tree: true,
                    width: "*",
                    min_width: 250,
                    resize: true
                },
                {
                    name: "start_date",
                    label: "Start",
                    align: "center",
                    width: 100
                },
                {
                    name: "duration",
                    label: "Days",
                    align: "center",
                    width: 50
                },
                {
                    name: "progress",
                    label: "Progress",
                    align: "center",
                    width: 75,
                    template: function(task) {
                        return Math.round((task.progress || 0) * 100) + "%";
                    }
                }
            ];

            gantt.templates.task_class = function(
                start,
                end,
                task
            ) {
                return task.critical ? "critical_task" : "";
            };

            gantt.init("gantt_here");
            gantt.parse(ganttData);
        </script>
    </body>
    </html>
    """

    html = (
        html.replace("__CSS__", css)
        .replace("__JS__", js)
        .replace("__DATA__", gantt_data)
    )

    st.caption(
        f"{len(tasks)} WBS nodes · "
        f"{len(links)} dependencies · "
        f"{n_critical} critical activities · "
        f"TP {selected_tp:03d}"
    )

    components.html(html, height=820, scrolling=True)


def build_gantt(df, height=None):

    if df.empty:
        st.info("No activities available for this selection.")
        return

    plot_df = df.loc[
        df["CPM_Start_Date"].notna()
        & df["CPM_Finish_Date"].notna()
        & (df["CPM_Finish_Date"] > df["CPM_Start_Date"])
    ].copy()

    if plot_df.empty:
        st.info("No activities with valid CPM dates.")
        return

    plot_df["Activity"] = (
        plot_df["ID"].astype(str) + " · " + plot_df["Name"].astype(str)
    )

    plot_df["Path"] = np.where(plot_df["Is_Critical"], "Critical path", "Non-critical")

    plot_df["Progress_Pct"] = plot_df["Pct_Complete"].fillna(0).clip(0, 1) * 100

    # Barra de planificación.
    fig = px.timeline(
        plot_df,
        x_start="CPM_Start_Date",
        x_end="CPM_Finish_Date",
        y="Activity",
        color="Path",
        color_discrete_map={"Critical path": "#F1B4B4", "Non-critical": "#B7D0E8"},
        custom_data=[
            "ID",
            "Name",
            "Duration_Plan_Days",
            "Total_Float_Days",
            "Free_Float_Days",
            "Progress_Pct",
            "CPM_Start_Date",
            "CPM_Finish_Date",
        ],
        labels={"Path": "Schedule classification"},
    )

    # Relleno de avance sobre la duración planificada.
    progress_colors = [
        "#C62828" if critical else "#286090" for critical in plot_df["Is_Critical"]
    ]

    duration_ms = (
        plot_df["CPM_Finish_Date"] - plot_df["CPM_Start_Date"]
    ).dt.total_seconds() * 1000

    progress_ms = duration_ms * plot_df["Pct_Complete"].fillna(0).clip(0, 1)

    fig.add_trace(
        go.Bar(
            x=progress_ms,
            base=plot_df["CPM_Start_Date"],
            y=plot_df["Activity"],
            orientation="h",
            marker_color=progress_colors,
            opacity=0.95,
            showlegend=False,
            customdata=plot_df[["Progress_Pct", "Is_Critical"]].to_numpy(),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Progress: %{customdata[0]:.1f}%<br>"
                "Critical: %{customdata[1]}"
                "<extra></extra>"
            ),
        )
    )

    fig.update_yaxes(autorange="reversed", title="")

    fig.update_xaxes(title="Calendar date", tickformat="%b %Y")

    if height is None:
        height = max(260, min(650, len(plot_df) * 34))

    fig.update_layout(
        height=height,
        barmode="overlay",
        legend_title_text="Activity classification",
        margin=dict(l=10, r=10, t=25, b=10),
        hovermode="closest",
    )

    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# 7. CABECERA Y KPI
# ============================================================

st.title("Schedule & Critical Path")

st.caption(
    "Project schedule · Critical path · Weekly progress · "
    "Float analysis · Supply-related schedule exposure"
)

st.caption(
    f"Reporting period: TP {selected_tp:03d} · "
    f"Status date: {fmt_date(selected_date)}"
    if selected_date is not None
    else f"Reporting period: TP {selected_tp:03d}"
)

st.info(
    "The CPM represents the validated reference schedule. "
    "Weekly progress is taken from the selected reporting period. "
    "The reference CPM is not recalculated for historical reporting."
)

project_duration = float(summary["Project_Duration_CPM_Days"])
n_cpm_activities = int(summary["Activities"])
n_dependencies = int(summary["Dependencies"])
n_critical = int(summary["Critical_Activities"])

critical_activities = cpm.loc[cpm["Is_Critical"]].sort_values("ES_Days")

minimum_float = float(cpm["Total_Float_Days"].min())
median_float = float(cpm["Total_Float_Days"].median())

mean_progress = cpm["Pct_Complete"].mean() * 100

completed_activities = int((cpm["Pct_Complete"] >= 0.999).sum())

k1, k2, k3, k4, k5 = st.columns(5)

k1.metric("Project duration", fmt_days(project_duration))
k2.metric("Activities", f"{n_cpm_activities:,}")
k3.metric("Critical activities", f"{n_critical:,}")
k4.metric("Mean progress", f"{mean_progress:.1f}%")
k5.metric("Completed activities", f"{completed_activities}/{n_cpm_activities}")

st.divider()


# ============================================================
# 8. HIERARCHICAL PROJECT GANTT
# ============================================================

st.subheader("1. Project Schedule — Hierarchical Gantt")

st.caption(
    "Expand and collapse the WBS hierarchy to inspect the "
    "reference CPM schedule, critical path and execution progress "
    "at the selected reporting period."
)

st.info(
    "Planned dates and dependencies remain those of the validated "
    "CPM reference. The darker bar fill represents actual progress "
    "at the selected reporting period."
)

build_dhtmlx_gantt()


with st.expander("Complete dependency register", expanded=False):

    st.caption("Full predecessor-successor register used by the CPM network.")

    name_lookup = cpm.set_index("ID")["Name"].to_dict()

    dependency_display = dependencies.copy()

    dependency_display["Predecessor"] = dependency_display["Predecessor_ID"].map(
        name_lookup
    )

    dependency_display["Successor"] = dependency_display["Successor_ID"].map(
        name_lookup
    )

    dependency_display = dependency_display[
        [
            "Predecessor_ID",
            "Predecessor",
            "Successor_ID",
            "Successor",
            "Relation_Type",
            "Lag",
        ]
    ].rename(
        columns={
            "Predecessor_ID": "Predecessor ID",
            "Successor_ID": "Successor ID",
            "Relation_Type": "Relationship",
            "Lag": "Lag (days)",
        }
    )

    dependency_filter = st.selectbox(
        "Relationship type", ["All", "FS", "SS", "FF", "SF"], key="dependency_filter"
    )

    if dependency_filter != "All":
        dependency_display = dependency_display.loc[
            dependency_display["Relationship"] == dependency_filter
        ]

    st.caption(
        f"Displaying {len(dependency_display)} of " f"{len(dependencies)} dependencies."
    )

    st.dataframe(dependency_display, use_container_width=True, hide_index=True)


# ============================================================
# SCHEDULE EXPOSURE
# ============================================================

st.divider()

st.subheader("2. Schedule Exposure")

st.caption(
    "Ranks the 15 executable activities with the lowest total float, "
    "making schedule constraints and critical activities easier to identify."
)

# Trabajamos exclusivamente con actividades ejecutables.
exposure_df = cpm.loc[
    (cpm["Duration_Plan_Days"] > 0) & cpm["Total_Float_Days"].notna()
].copy()

# Actvidades criticas con holgura total negativa (retraso) se priorizan en el ranking.
critical_ids_expected = {12, 18, 20}

critical_ids_displayed = set(
    exposure_df.loc[exposure_df["Is_Critical"], "ID"].astype(int)
)

missing_critical = critical_ids_expected - critical_ids_displayed

if missing_critical:
    st.warning(
        f"Critical activities missing from exposure ranking: "
        f"{sorted(missing_critical)}"
    )

# Convertir columnas de holgura a numéricas, ignorando errores.

exposure_df["Total_Float_Days"] = pd.to_numeric(
    exposure_df["Total_Float_Days"], errors="coerce"
)

exposure_df["Free_Float_Days"] = pd.to_numeric(
    exposure_df["Free_Float_Days"], errors="coerce"
)

exposure_df = exposure_df.dropna(subset=["Total_Float_Days"])

# Ranking: las 15 actividades con menor holgura total.
exposure_df = exposure_df.sort_values(["Total_Float_Days", "ID"]).head(15).copy()

exposure_df["Activity"] = (
    exposure_df["ID"].astype(str) + " · " + exposure_df["Name"].astype(str)
)

exposure_df["Schedule_Status"] = np.where(
    exposure_df["Is_Critical"], "Critical", "Non-critical"
)

if exposure_df.empty:

    st.info("No activities available for schedule exposure analysis.")

else:
    # ---------------------------

    fig_exposure = px.bar(
        exposure_df.loc[~exposure_df["Is_Critical"]].sort_values(
            ["Total_Float_Days", "ID"], ascending=[False, True]
        ),
        x="Total_Float_Days",
        y="Activity",
        orientation="h",
        color_discrete_sequence=["#6C9BCF"],
        custom_data=[
            "ID",
            "Duration_Plan_Days",
            "Free_Float_Days",
            "CPM_Start_Date",
            "CPM_Finish_Date",
        ],
        labels={"Total_Float_Days": "Total float (days)", "Activity": ""},
    )

    fig_exposure.update_traces(
        name="Non-critical",
        showlegend=True,
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Total float: %{x:.0f} days<br>"
            "Duration: %{customdata[1]:.0f} days<br>"
            "Free float: %{customdata[2]:.0f} days<br>"
            "CPM start: %{customdata[3]|%d/%m/%Y}<br>"
            "CPM finish: %{customdata[4]|%d/%m/%Y}"
            "<extra>Non-critical activity</extra>"
        ),
    )

    # Marcadores específicos para actividades críticas (float = 0).
    critical_df = exposure_df.loc[exposure_df["Is_Critical"]].copy()

    fig_exposure.add_trace(
        go.Scatter(
            x=[0] * len(critical_df),
            y=critical_df["Activity"],
            mode="markers",
            name="Critical activity",
            marker=dict(
                symbol="diamond",
                size=13,
                color="#D9534F",
                line=dict(color="#8F1D19", width=1.5),
            ),
            customdata=critical_df[
                [
                    "ID",
                    "Duration_Plan_Days",
                    "Free_Float_Days",
                    "CPM_Start_Date",
                    "CPM_Finish_Date",
                ]
            ].to_numpy(),
            hovertemplate=(
                "<b>%{y}</b><br>"
                "Total float: 0 days<br>"
                "Duration: %{customdata[1]:.0f} days<br>"
                "Free float: %{customdata[2]:.0f} days<br>"
                "CPM start: %{customdata[3]|%d/%m/%Y}<br>"
                "CPM finish: %{customdata[4]|%d/%m/%Y}"
                "<extra>Critical activity</extra>"
            ),
        )
    )

    # ---------------------------
    fig_exposure.update_yaxes(autorange="reversed", title="")

    fig_exposure.update_xaxes(title="Total float (days)", rangemode="tozero")

    fig_exposure.update_layout(
        height=max(350, len(exposure_df) * 32),
        margin=dict(l=10, r=20, t=25, b=10),
        legend_title_text="Schedule status",
        hovermode="closest",
    )

    st.plotly_chart(fig_exposure, use_container_width=True)


# ============================================================
# SUPPLY CHAIN EXPOSURE MATRIX
# ============================================================

st.divider()

st.subheader("3. Supply Chain Exposure Analysis")

st.subheader("3.1 Supply Chain Exposure Matrix")

st.caption(
    "Exposure of material-associated activities combining supply risk "
    "and CPM schedule float."
)

# 1. Prepare supply and CPM data
supply_fields = [
    "ID",
    "Material_Type",
    "Is_Critical_Material",
    "Lead_Time_Days",
    "Buffer_Days",
    "Supply_Delay_Days",
    "Supply_Buffer_Excess_Days",
    "Supply_Risk_Score",
    "Material_Status",
    "Risk_Level",
    "Supply_Alert",
    "Supply_Buffer_Exceeded",
    "Total_Cost_Plan",
]

available_supply_fields = [col for col in supply_fields if col in schedule.columns]

supply_exposure = cpm[
    [
        "ID",
        "Name",
        "Total_Float_Days",
        "Is_Critical",
    ]
].merge(
    schedule[available_supply_fields].drop_duplicates("ID"),
    on="ID",
    how="inner",
    validate="one_to_one",
)

# Only activities with an actual material association
supply_exposure = supply_exposure.loc[
    supply_exposure["Material_Type"].notna()
    & supply_exposure["Material_Type"].ne("Non-Critical")
].copy()

# Numeric fields
numeric_fields = [
    "Total_Float_Days",
    "Supply_Buffer_Excess_Days",
    "Supply_Delay_Days",
    "Total_Cost_Plan",
]

for col in numeric_fields:
    if col in supply_exposure.columns:
        supply_exposure[col] = pd.to_numeric(supply_exposure[col], errors="coerce")

supply_exposure = supply_exposure.dropna(
    subset=["Total_Float_Days", "Supply_Buffer_Excess_Days", "Risk_Level"]
).copy()

# 2. Classify schedule exposure
# Zero float is an objective CPM condition.
# Positive float is split into three groups using its empirical distribution.

supply_exposure["Float_Category"] = "Critical"

positive_float = supply_exposure["Total_Float_Days"] > 0

if positive_float.any():

    float_rank = supply_exposure.loc[positive_float, "Total_Float_Days"].rank(
        method="average", pct=True
    )

    supply_exposure.loc[
        positive_float & (float_rank.reindex(supply_exposure.index).fillna(0) <= 1 / 3),
        "Float_Category",
    ] = "Very Low Float"

    supply_exposure.loc[
        positive_float
        & (
            (float_rank.reindex(supply_exposure.index).fillna(0) > 1 / 3)
            & (float_rank.reindex(supply_exposure.index).fillna(0) <= 2 / 3)
        ),
        "Float_Category",
    ] = "Low Float"

    supply_exposure.loc[
        positive_float & (float_rank.reindex(supply_exposure.index).fillna(0) > 2 / 3),
        "Float_Category",
    ] = "Comfortable Float"

float_order = [
    "Critical",
    "Very Low Float",
    "Low Float",
    "Comfortable Float",
]

risk_order = [
    "Buffer Exceeded",
    "Preventive Alert",
    "No Alert",
]

# 3. Material criticality selector
criticality_options = {
    "All materials": "all",
    "Critical materials": "critical",
    "Non-critical materials": "noncritical",
}

selected_criticality = st.selectbox(
    "Material criticality",
    options=list(criticality_options.keys()),
    index=0,
    key="supply_material_criticality",
)

selected_filter = criticality_options[selected_criticality]

if selected_filter == "critical":
    supply_view = supply_exposure.loc[
        supply_exposure["Is_Critical_Material"].fillna(False).astype(bool)
    ].copy()

elif selected_filter == "noncritical":
    supply_view = supply_exposure.loc[
        ~supply_exposure["Is_Critical_Material"].fillna(False).astype(bool)
    ].copy()

else:
    supply_view = supply_exposure.copy()

# ---------------------------------------------------------------------------------------------

# ============================================================
# 4. SUPPLY CHAIN EXPOSURE MATRIX
# ============================================================

# st.subheader("Supply Chain Exposure Matrix")

# 1. Build matrix from real activity counts and planned costs

matrix_count = (
    supply_view.groupby(["Risk_Level", "Float_Category"], observed=False)
    .size()
    .unstack(fill_value=0)
    .reindex(index=risk_order, columns=float_order, fill_value=0)
)

matrix_cost = (
    supply_view.groupby(["Risk_Level", "Float_Category"], observed=False)[
        "Total_Cost_Plan"
    ]
    .sum()
    .unstack(fill_value=0)
    .reindex(index=risk_order, columns=float_order, fill_value=0)
)

# 2. Summary indicators

n_material_activities = len(supply_view)

n_alerts = supply_view["Supply_Alert"].fillna(False).astype(bool).sum()

n_buffer_exceeded = (
    supply_view["Supply_Buffer_Exceeded"].fillna(False).astype(bool).sum()
)

k1, k2, k3 = st.columns(3)

k1.metric("Material activities", f"{n_material_activities}")
k2.metric("Supply alerts", f"{n_alerts}")
k3.metric("Buffer exceeded", f"{n_buffer_exceeded}")

# 3. Visual matrix

fig_supply_matrix = go.Figure(
    data=go.Heatmap(
        z=matrix_count.to_numpy(),
        x=float_order,
        y=risk_order,
        text=matrix_count.to_numpy(),
        texttemplate="%{text}",
        customdata=matrix_cost.to_numpy(),
        colorscale="Blues",
        zmin=0,
        showscale=True,
        colorbar=dict(title="Activities"),
        hovertemplate=(
            "<b>%{y}</b><br>"
            "Schedule exposure: %{x}<br>"
            "Activities: %{z:.0f}<br>"
            "Planned cost: €%{customdata:,.0f}"
            "<extra></extra>"
        ),
    )
)

fig_supply_matrix.update_layout(
    height=390,
    xaxis_title="CPM Schedule Float",
    yaxis_title="Supply Risk",
    margin=dict(l=15, r=15, t=20, b=50),
    font=dict(size=11),
)

st.plotly_chart(
    fig_supply_matrix, use_container_width=True, config={"displayModeBar": False}
)

st.caption(
    "Cell values represent the number of activities. "
    "Hover over a cell to see its planned cost."
)
# -------------------------------------------------------------------------


# ============================================================
# 5. ACTIVITY INVESTIGATION
# ============================================================

st.subheader("3.2 Activity Investigation")

st.caption("Filter the activities by supply risk and schedule exposure.")

filter_col1, filter_col2 = st.columns(2)

risk_filter_options = ["All supply risks"] + risk_order
float_filter_options = ["All schedule exposures"] + float_order

with filter_col1:
    selected_risk_filter = st.selectbox(
        "Supply risk", options=risk_filter_options, key="supply_risk_filter"
    )

with filter_col2:
    selected_float_filter = st.selectbox(
        "Schedule exposure", options=float_filter_options, key="supply_float_filter"
    )

# Apply filters

filtered_activities = supply_view.copy()

if selected_risk_filter != "All supply risks":
    filtered_activities = filtered_activities.loc[
        filtered_activities["Risk_Level"].astype(str) == selected_risk_filter
    ]

if selected_float_filter != "All schedule exposures":
    filtered_activities = filtered_activities.loc[
        filtered_activities["Float_Category"].astype(str) == selected_float_filter
    ]

# ------------------------------------------------------------
# Filtered activity register
# ------------------------------------------------------------

st.markdown("#### Activities found")

st.metric("Matching activities", len(filtered_activities))

if filtered_activities.empty:

    st.info(
        "No activities match the selected combination. "
        "Try changing one or both filters."
    )

else:

    filtered_activities = filtered_activities.sort_values(
        ["Supply_Buffer_Excess_Days", "Total_Float_Days"], ascending=[False, True]
    ).copy()

    detail_columns = [
        "ID",
        "Name",
        "Material_Type",
        "Risk_Level",
        "Float_Category",
        "Total_Float_Days",
        "Supply_Delay_Days",
        "Supply_Buffer_Excess_Days",
        "Total_Cost_Plan",
    ]

    available_detail_columns = [
        col for col in detail_columns if col in filtered_activities.columns
    ]

    st.dataframe(
        filtered_activities[available_detail_columns],
        use_container_width=True,
        hide_index=True,
        height=260,
    )

    # --------------------------------------------------------
    # Selected activity
    # --------------------------------------------------------

    st.markdown("#### Activity details")

    activity_names = filtered_activities.set_index("ID")["Name"].to_dict()

    selected_activity_id = st.selectbox(
        "Select an activity",
        options=filtered_activities["ID"].tolist(),
        format_func=lambda x: f"{x} · {activity_names.get(x, '')}",
        key=(
            f"supply_activity_"
            f"{selected_risk_filter}_{selected_float_filter}"
            f"_{selected_criticality}"
        ),
    )

    # Retrieve full activity information

    activity = activity_register.loc[
        activity_register["ID"] == selected_activity_id
    ].iloc[0]

    # --------------------------------------------------------
    # Focused Gantt with direct dependencies
    # --------------------------------------------------------

    incoming = dependencies.loc[
        dependencies["Successor_ID"] == selected_activity_id
    ].copy()

    outgoing = dependencies.loc[
        dependencies["Predecessor_ID"] == selected_activity_id
    ].copy()

    related_ids = {selected_activity_id}

    related_ids.update(incoming["Predecessor_ID"].tolist())
    related_ids.update(outgoing["Successor_ID"].tolist())

    focused_gantt = cpm.loc[cpm["ID"].isin(related_ids)].copy()

    focused_gantt = focused_gantt.sort_values(["ES_Days", "ID"])

    st.markdown("#### Schedule context")

    st.caption("Selected activity and its immediate predecessors and successors.")

    build_gantt(focused_gantt, height=max(280, min(500, len(focused_gantt) * 45)))

    # --------------------------------------------------------
    # Activity execution indicators
    # --------------------------------------------------------

    st.markdown("#### Execution overview")

    a1, a2, a3, a4, a5 = st.columns(5)

    a1.metric("Progress", f"{activity['Progress_Pct']:.1f}%")

    a2.metric("Duration", fmt_days(activity["Duration_Plan_Days"]))

    a3.metric("Total float", fmt_days(activity["Total_Float_Days"]))

    a4.metric("Free float", fmt_days(activity["Free_Float_Days"]))

    a5.metric("CPM status", "Critical" if activity["Is_Critical"] else "Non-critical")

    # --------------------------------------------------------
    # Schedule, cost and supply details
    # --------------------------------------------------------

    with st.expander("Schedule, cost and supply details", expanded=False):

        detail_left, detail_right = st.columns(2)

        with detail_left:

            st.markdown("**Schedule information**")

            st.write(f"Activity ID: {int(activity['ID'])}")
            st.write(f"Planned start: {fmt_date(activity['CPM_Start_Date'])}")
            st.write(f"Planned finish: {fmt_date(activity['CPM_Finish_Date'])}")
            st.write(f"Early start: {fmt_days(activity['ES_Days'])}")
            st.write(f"Early finish: {fmt_days(activity['EF_Days'])}")
            st.write(f"Late start: {fmt_days(activity['LS_Days'])}")
            st.write(f"Late finish: {fmt_days(activity['LF_Days'])}")

        with detail_right:

            st.markdown("**Cost and supply information**")

            cost_value = activity.get("Total_Cost_Plan", np.nan)

            cost_display = (
                f"€{cost_value:,.2f}" if pd.notna(cost_value) else "Not available"
            )

            st.write(f"Planned total cost: {cost_display}")
            st.write(f"Material type: {display_value(activity.get('Material_Type'))}")
            st.write(
                f"Supply delay: "
                f"{display_value(activity.get('Supply_Delay_Days'), ' days')}"
            )
            st.write(
                f"Supply buffer: "
                f"{display_value(activity.get('Buffer_Days'), ' days')}"
            )
            st.write(
                f"Buffer excess: "
                f"{display_value(activity.get('Supply_Buffer_Excess_Days'), ' days')}"
            )
            st.write(
                f"Material status: " f"{display_value(activity.get('Material_Status'))}"
            )
            st.write(f"Supply risk: {display_value(activity.get('Risk_Level'))}")

    # --------------------------------------------------------
    # Direct dependencies
    # --------------------------------------------------------

    with st.expander("Direct dependencies", expanded=False):

        name_lookup = cpm.set_index("ID")["Name"].to_dict()

        rel1, rel2 = st.columns(2)

        with rel1:

            st.markdown("**Predecessors**")

            if incoming.empty:
                st.caption("No direct predecessors.")
            else:
                for _, row in incoming.iterrows():

                    name = name_lookup.get(row["Predecessor_ID"], "Unknown")

                    st.write(
                        f"• {int(row['Predecessor_ID'])} · {name} "
                        f"({row['Relation_Type']}, "
                        f"lag {row['Lag']} days)"
                    )

        with rel2:

            st.markdown("**Successors**")

            if outgoing.empty:
                st.caption("No direct successors.")
            else:
                for _, row in outgoing.iterrows():

                    name = name_lookup.get(row["Successor_ID"], "Unknown")

                    st.write(
                        f"• {int(row['Successor_ID'])} · {name} "
                        f"({row['Relation_Type']}, "
                        f"lag {row['Lag']} days)"
                    )

# Reference snapshot notice

st.caption(
    "Supply information is a non-time-indexed reference snapshot. "
    "Changing the selected tracking period (TP) does not recalculate "
    "the supply risk."
)


# ============================================================
# 6. MANAGEMENT ACTIONS
# ============================================================

st.subheader("4. Management Actions")

# ------------------------------------------------------------
# Dynamic schedule priorities
# ------------------------------------------------------------

critical_now = cpm.loc[cpm["Is_Critical"].fillna(False).astype(bool)].sort_values(
    "ES_Days"
)

critical_sequence_text = " → ".join(critical_now["Name"].tolist())

non_critical_exposure = cpm.loc[
    (~cpm["Is_Critical"].fillna(False).astype(bool)) & (cpm["Total_Float_Days"] > 0)
].sort_values("Total_Float_Days")

if not non_critical_exposure.empty:
    lowest_float = non_critical_exposure.iloc[0]
    lowest_float_text = (
        f"**{lowest_float['Name']} "
        f"(ID {int(lowest_float['ID'])})** "
        f"with **{lowest_float['Total_Float_Days']:.0f} days** "
        "of total float"
    )
else:
    lowest_float_text = "No non-critical activities with positive float are available."

# ------------------------------------------------------------
# Dynamic supply priorities
# ------------------------------------------------------------

supply_breaches_now = activity_register.loc[
    activity_register["Supply_Buffer_Exceeded"].fillna(False).astype(bool)
].copy()

supply_breaches_now = supply_breaches_now.sort_values(
    ["Total_Float_Days", "Supply_Buffer_Excess_Days"], ascending=[True, False]
)

critical_supply_now = supply_breaches_now.loc[
    supply_breaches_now["Is_Critical"].fillna(False).astype(bool)
]

if not supply_breaches_now.empty:
    top_breach = supply_breaches_now.iloc[0]

    top_breach_text = (
        f"**{top_breach['Name']} (ID {int(top_breach['ID'])})** "
        f"has exceeded its buffer by "
        f"**{top_breach['Supply_Buffer_Excess_Days']:.0f} days** "
        f"and retains **{top_breach['Total_Float_Days']:.0f} days "
        "of CPM total float**."
    )
else:
    top_breach_text = "No supply buffer breaches are currently recorded."

# ------------------------------------------------------------
# Management interpretation
# ------------------------------------------------------------

st.markdown(f"""
##### 1. Protect the critical path

The validated CPM reference duration is **{project_duration:.0f} days**.

The current critical sequence contains **{len(critical_now)} activities**:

**{critical_sequence_text if critical_sequence_text else "No critical activities identified."}**

Critical activities have zero total float and require close schedule
control.

The nearest non-critical schedule constraint is {lowest_float_text}.
Monitor its remaining float for any deterioration.

##### 2. Prioritise supply recovery by schedule exposure

The current supply snapshot identifies **{len(supply_alerts)} supply-alert
activities**, including **{len(supply_breaches_now)} buffer breaches**.

Of the current buffer breaches, **{len(critical_supply_now)}**
belong to the CPM critical path.

{top_breach_text}

Prioritise supplier follow-up and recovery measures according to
buffer excess, remaining CPM float and downstream schedule impact.
A buffer breach alone does not automatically justify expediting:
available schedule flexibility must also be considered.

##### 3. Coordinate schedule and supply decisions

Where supply delays affect critical or low-float activities,
evaluate recovery options and potential downstream consequences.

Where substantial CPM float remains, maintain supplier follow-up
and reassess the situation as delivery dates and schedule exposure
change.

##### 4. Monitor execution progress

At **TP {selected_tp:03d}**, mean recorded progress across CPM
activities is **{mean_progress:.2f}%**.

**{completed_activities} of {n_cpm_activities} activities**
are recorded as completed.

Interpret these indicators in the context of the selected reporting
period. Progress and completion figures should be assessed alongside
the schedule position and supply exposure, rather than in isolation.
""")

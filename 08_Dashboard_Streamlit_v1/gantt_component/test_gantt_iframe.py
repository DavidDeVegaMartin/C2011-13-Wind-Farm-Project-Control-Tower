
from pathlib import Path

import streamlit as st
import streamlit.components.v1 as components


# --------------------------------------------------
# 1. CARGA DE RECURSOS LOCALES
# --------------------------------------------------

BASE_DIR = Path(__file__).resolve().parent

CODEBASE = (
    BASE_DIR
    / "gantt_component"
    / "frontend"
    / "node_modules"
    / "dhtmlx-gantt"
    / "codebase"
)

css = (CODEBASE / "dhtmlxgantt.css").read_text(encoding="utf-8")
js = (CODEBASE / "dhtmlxgantt.js").read_text(encoding="utf-8")


# --------------------------------------------------
# 2. HTML AUTÓNOMO
# --------------------------------------------------

html = """
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
    overflow: hidden;
}

#gantt_here {
    width: 100%;
    height: 660px;
}
</style>

</head>

<body>

<div id="gantt_here"></div>

<script>
__JS__
</script>

<script>

gantt.config.date_format = "%Y-%m-%d";
gantt.config.readonly = true;

gantt.config.grid_width = 420;
gantt.config.row_height = 32;
gantt.config.bar_height = 20;

gantt.config.scale_unit = "month";
gantt.config.date_scale = "%M %Y";
gantt.config.subscales = [
    { unit: "week", step: 1, date: "%d" }
];

gantt.config.fit_tasks = true;

gantt.config.columns = [
    {
        name: "text",
        label: "Actividad / WBS",
        tree: true,
        width: "*",
        resize: true
    },
    {
        name: "start_date",
        label: "Inicio",
        align: "center",
        width: 100
    },
    {
        name: "duration",
        label: "Días",
        align: "center",
        width: 55
    }
];

gantt.init("gantt_here");

gantt.parse({

    data: [

        {
            id: 1,
            text: "Wind Farm",
            type: "project",
            open: true
        },

        {
            id: 2,
            text: "Development",
            type: "project",
            parent: 1,
            open: true
        },

        {
            id: 12,
            text: "orientatiestudie",
            start_date: "2008-10-20",
            duration: 105,
            parent: 2,
            progress: 0.75
        },

        {
            id: 18,
            text: "extra vergunningen",
            start_date: "2009-02-02",
            duration: 180,
            parent: 2,
            progress: 0.50
        },

        {
            id: 20,
            text: "Roads and hardstands",
            start_date: "2009-08-01",
            duration: 14,
            parent: 2,
            progress: 0.25
        }
    ],

    links: [

        {
            id: 1,
            source: 12,
            target: 18,
            type: "0"
        },

        {
            id: 2,
            source: 18,
            target: 20,
            type: "0"
        }
    ]

});

</script>

</body>
</html>
"""

html = html.replace("__CSS__", css).replace("__JS__", js)


# --------------------------------------------------
# 3. STREAMLIT
# --------------------------------------------------

st.set_page_config(
    page_title="Wind Farm - Gantt Test",
    layout="wide"
)

st.title("Wind Farm — Gantt Prototype")

st.caption(
    "DHTMLX Gantt 10.0.3 | WBS jerárquico | Solo lectura"
)

components.html(
    html,
    height=700,
    scrolling=True
)

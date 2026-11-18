from collections.abc import Mapping, Sequence
from typing import Any

import streamlit as st

# Registro del componente Streamlit v2
_out = st.components.v2.component(
    "wind-farm-gantt-component.gantt",
    js="index-*.js",
    css="index-*.css",
    html='<div id="gantt-root"></div>',
)


def gantt_component(
    tasks: Sequence[Mapping[str, Any]],
    links: Sequence[Mapping[str, Any]] | None = None,
    *,
    height: int = 700,
    key: str | None = None,
):
    """
    Renderiza el Gantt jerárquico.

    Parameters
    ----------
    tasks : actividades y nodos WBS
    links : dependencias entre actividades
    height : altura del componente en píxeles
    key : identificador único de la instancia
    """

    payload = {
        "tasks": [dict(task) for task in tasks],
        "links": [dict(link) for link in (links or [])],
        "height": int(height),
    }

    return _out(
        data=payload,
        key=key,
    )

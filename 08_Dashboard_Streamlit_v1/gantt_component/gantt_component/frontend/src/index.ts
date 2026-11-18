
import type {
  FrontendRenderer,
  FrontendRendererArgs,
} from "@streamlit/component-v2-lib";

import { gantt } from "dhtmlx-gantt";
import "dhtmlx-gantt/codebase/dhtmlxgantt.css";


interface GanttData {
  tasks: Record<string, unknown>[];
  links: Record<string, unknown>[];
  height: number;
}


const GanttComponent: FrontendRenderer<
  Record<string, never>,
  GanttData
> = (args: FrontendRendererArgs<Record<string, never>, GanttData>) => {

  const { parentElement, data } = args;

  const root = parentElement.querySelector("#gantt-root");

  if (!root) {
    throw new Error("No se encuentra el contenedor #gantt-root");
  }

  const container = root as HTMLElement;

  container.style.width = "100%";
  container.style.height = `${data.height || 700}px`;

  // Configuración inicial
  gantt.config.date_format = "%Y-%m-%d";
  gantt.config.readonly = true;
  gantt.config.grid_width = 420;
  gantt.config.row_height = 32;
  gantt.config.bar_height = 20;

  gantt.config.columns = [
    {
      name: "text",
      label: "Actividad / WBS",
      tree: true,
      width: "*",
      resize: true,
    },
    {
      name: "start_date",
      label: "Inicio",
      align: "center",
      width: 90,
    },
    {
      name: "duration",
      label: "Días",
      align: "center",
      width: 55,
    },
  ];

  // Inicializar y cargar datos
  gantt.init(container);

  gantt.parse({
    data: data.tasks,
    links: data.links,
  } as Parameters<typeof gantt.parse>[0]);

  // Liberar recursos al desmontar el componente
  return () => {
    gantt.clearAll();
    gantt.destructor();
  };
};

export default GanttComponent;

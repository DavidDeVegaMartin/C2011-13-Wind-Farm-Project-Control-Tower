# C2011-13 Wind Farm — Project Planning & Data Analytics

## Part I. Data Preparation & Transformation

### 1. Project overview

This project develops an integrated data preparation, project monitoring and decision-support workflow based on the C2011-13 Wind Farm case study.

The work addresses a central challenge in Project Planning and Project Control: transforming dispersed project information into a structured analytical environment that makes it possible to monitor progress, identify deviations, understand their impact and assess potential corrective actions.

The project combines project management knowledge with data analytics to connect schedule control, cost monitoring, material readiness, scenario simulation and economic assessment.

### 2. Data source and selection

The starting point is **DSLIB / PSLIB – Dynamic Scheduling Empirical Project Library**, developed by Ghent University (Belgium).

This research library contains more than 230 real project datasets, including baseline schedules, activity networks, resources, execution progress, risk and project control information.

It was selected because its structure is particularly suitable for analysing the relationship between initial planning and actual project performance. It provides the information needed to work with activity dependencies, schedule deviations, progress monitoring and project performance.

The C2011-13 Wind Farm case was selected as the basis for developing the analytical workflow.

**Original data source:**
- [DSLIB / PSLIB – GitHub repository](https://github.com/MarioVanhoucke/DSLIB-Dynamic-Scheduling-Empirical-Project-Library)
- [Ghent University – Project Management Research](https://www.projectmanagement.ugent.be/research/data)

### 3. Data preparation and analytical workflow

The preparation and transformation process is organised into a sequence of 13 notebooks. Each stage addresses a specific analytical requirement and produces structured datasets or intermediate results for subsequent stages.

The workflow follows six main stages:

**1. Data exploration and structuring (NB01–NB03)**

The original project files are explored, their structure is analysed and the information is reorganised into consistent datasets. The resulting data model separates the project activity structure from global and activity-level progress tracking, providing a common basis for subsequent analysis.

**2. Project monitoring and material control (NB04–NB06)**

Project performance indicators are integrated with schedule and cost information to identify deviations and generate monitoring alerts. Material readiness and supply risks are also incorporated, connecting project activities with the availability of critical resources. The stage concludes by preparing the information required to identify potential decision points.

**3. Schedule analysis and scenario simulation (NB07–NB09)**

A Critical Path Method (CPM) model is developed to analyse activity dependencies, early and late dates, float and critical activities. On this basis, hypothetical scenarios are executed to assess how selected delays or duration changes may affect the project schedule and completion date.

**4. Corrective actions and decision evaluation (NB10)**

Potential corrective measures are evaluated against the simulated scenarios. Their effects on schedule performance and residual supply risk are analysed, allowing alternative responses to be compared.

**5. Economic impact assessment (NB11–NB12)**

The economic dimension of corrective decisions is incorporated by estimating intervention costs, potential costs of not intervening, residual impacts and expected financial benefits. Different assumptions are considered to assess the sensitivity and economic viability of the alternatives.

**6. Integrated exploration and validation (NB13)**

The information produced throughout the workflow is examined from a cross-project perspective. Historical performance, cost deviations, material incidents and simulation results are explored to identify relevant patterns and verify the consistency of the analytical outputs.

### 4. Scenario simulation and decision support

A key component of the workflow is the development of a scenario simulator designed to evaluate the potential consequences of project disruptions and corrective actions.

Three initial cases are defined:

- **Critical supply delay:** evaluates the impact of a delay affecting a material supply.
- **Critical activity delay:** analyses the effect of an increase in the duration of an activity on the critical path.
- **Combined scenario:** examines the interaction between both types of disruption.

The simulated results are used to compare schedule impacts, changes in float and critical path, residual risks and the economic implications of potential corrective measures.

These three cases constitute an initial set of scenarios rather than an exhaustive catalogue. The workflow is structured to accommodate additional disruptions, affected activities and combinations of assumptions.

### 5. Outputs and integration

The notebooks produce intermediate datasets, analytical results, validation files and a final set of 11 data files prepared for consumption by the Streamlit application.

This separation between data preparation and application functionality allows the analytical process to be developed, checked and updated independently of the user interface.

The result is a structured and integrated data foundation that connects project planning, performance monitoring, material control, schedule simulation and economic assessment.

*The application and its main monitoring and decision-support functionalities are described in Part II of this README.*

## Part II. Project Control Tower — Interactive Application

### 6. Application overview

The Project Control Tower is an interactive Streamlit application developed to bring together the information and analytical outputs generated during Part I.

Its purpose is to provide an integrated environment for project monitoring, schedule analysis, supply chain risk assessment, scenario simulation and corrective action evaluation.

Rather than presenting isolated performance indicators, the application connects project execution with its schedule, cost performance, material availability and potential management interventions.

The application is organised into seven modules, each addressing a specific dimension of Project Planning and Project Control.

### 7. Application modules

**1. Executive Overview**

Provides a consolidated view of the project's overall performance and current status.

The module brings together key Earned Value Management indicators, including PV, EV, AC, SPI, SPI(t) and CPI, alongside schedule and cost variances.

Time-series visualisations allow the evolution of project performance to be examined across tracking periods. Monitoring alerts help identify relevant issues from different management perspectives, including overall project performance, schedule exposure and supply escalation.

The alert register can also be exported for further analysis.

**2. Schedule & Critical Path — Hierarchical Gantt**

The interactive hierarchical Gantt is one of the central components of the application.

It represents the project through its Work Breakdown Structure (WBS), allowing users to navigate from higher-level work packages to individual activities and milestones.

The visualisation integrates CPM schedule dates, activity durations, recorded progress and logical dependencies. Critical activities are visually distinguished from non-critical activities, while the schedule network supports Finish-to-Start, Start-to-Start, Finish-to-Finish and Start-to-Finish relationships.

The module also provides access to schedule performance indicators, activity records, total and free float, criticality and supply-related exposure.

By combining project structure, scheduling logic and execution information, the Gantt provides a common visual reference for reviewing the project schedule and investigating potential deviations.

**3. Cost & Performance**

Focuses on the financial dimension of project control.

It presents budget and performance indicators, including BAC, AC, EV, CPI and CV, together with the evolution of planned value, earned value and actual cost.

Budget information can also be examined at activity level, including the available breakdown of planned cost components.

The module helps identify cost performance deviations and understand their relationship with overall project progress.

**4. Supply Chain & Risk**

Connects material availability with project execution and schedule exposure.

It provides visibility into activities associated with material requirements, supply alerts, readiness dates, lead times and schedule buffers.

Risk rankings and detailed activity information help identify potential supply constraints, with particular attention to activities on or close to the critical path.

This allows supply-related issues to be examined in the context of their potential impact on project delivery.

**5. Scenario Analysis**

Provides a comparative view of predefined disruption scenarios and corrective actions.

The initial configuration includes three cases:

- **SC01 — Critical Supply Delay:** evaluates the consequences of a material supply delay.
- **SC02 — Critical Activity Delay:** examines the impact of an increase in activity duration.
- **SC03 — Combined Scenario:** combines both types of disruption.

The module compares their effects on project duration, activity dates, criticality, schedule exposure and supply risk.

It also examines the potential effects of the corrective actions defined in the analytical workflow, allowing users to compare initial disruption scenarios with intervention outcomes.

**6. Simulation Lab**

Allows users to configure and test additional hypothetical disruptions beyond the predefined scenarios.

Execution delays can be introduced for individual or multiple activities, while supply delays can be configured separately.

The simulation engine reconstructs the schedule network and recalculates CPM results when execution durations are modified. The resulting analysis includes changes in project duration, critical activities, dates, float and activity status.

Supply delays are evaluated separately and do not automatically modify the CPM schedule.

This module provides a practical environment for exploring alternative assumptions and understanding how different disruptions may affect project delivery.

**7. Decision Cockpit**

Brings together schedule and economic information to support the evaluation of corrective actions.

The module assesses intervention costs, potential avoided costs, estimated net benefits and Return on Investment (ROI) under pessimistic, realistic and optimistic assumptions.

It also examines recovered days, residual project delays and remaining supply impacts.

Break-even analysis identifies the economic conditions under which an intervention may become viable, including the maximum intervention cost and the minimum impact reduction required.

A decision matrix combines economic viability, residual supply exposure and project delay to provide a consolidated view of the alternatives.

### 8. Integrated project control workflow

The seven modules are designed to support a connected management process:

**Monitor → Investigate → Prioritise → Compare → Simulate → Evaluate**

The workflow starts with the monitoring of project performance and schedule status. Relevant deviations and supply risks can then be investigated at activity level and prioritised according to their potential impact.

Predefined scenarios and additional simulations allow alternative situations to be examined. Finally, the Decision Cockpit connects the operational effects of corrective actions with their estimated economic implications.

This approach links project monitoring with forward-looking analysis and decision evaluation, moving beyond descriptive reporting towards a more integrated Project Control environment.

### 9. Technical architecture and data integration

The application is developed using Python and Streamlit, with Pandas for data processing and Plotly for interactive data visualisation.

Its architecture separates data loading, simulation logic and user interface components:

- **app.py:** application entry point and navigation.
- **data_loader.py:** loading and preparation of the analytical datasets.
- **simulation_engine.py:** schedule simulation and recalculation logic.
- **Application pages:** seven functional modules covering monitoring, planning, simulation and decision support.
- **Gantt component:** interactive hierarchical schedule visualisation.

The application consumes 11 structured output files generated by the data preparation workflow described in Part I.

This separation allows the analytical notebooks, data outputs and interactive application to operate as distinct but connected components.

### 10. Scope and methodological considerations

The application combines historical project information, consolidated datasets, simulated scenarios and conditional economic estimates. These different types of information should be interpreted according to their respective origins.

The CPM network represents the validated reference schedule and is not recalculated for each historical tracking period. The execution simulation engine recalculates the schedule when activity durations are modified, whereas supply delays are evaluated separately.

Actual cost information is available at project level and is not allocated to individual activities. Activity-level budget exposure therefore represents planned budget information rather than actual expenditure.

Economic assessments are based on configurable assumptions and should be interpreted as estimates rather than observed savings or confirmed intervention costs.

The application is a demonstrative Project Control environment built around the selected case study. Its application to a live industrial project would require updated execution data, working calendars, resource constraints, actual procurement information and validated cost assumptions.

### 11. Overall contribution

The Project Control Tower brings together the analytical work developed throughout the project in a single interactive environment.

It demonstrates how project data can be transformed into practical capabilities for monitoring performance, understanding schedule dependencies, identifying supply-related exposure, testing alternative scenarios and evaluating corrective actions.

The combination of hierarchical planning visualisation, CPM analysis, interactive simulation and economic decision support provides an integrated approach to Project Planning and Project Control.

The result is not simply a collection of dashboards, but a decision-support application connecting project information with the analysis of deviations and the evaluation of potential management responses.

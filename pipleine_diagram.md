# Smart Energy AI Current Runtime Diagram

This Mermaid chart shows the current runtime topology for the local Smart Energy AI stack. It summarizes the active runtime surfaces around Dagster, the dashboard, data persistence, and observability instead of reproducing the low-level asset graph.

For detailed Dagster asset dependencies and job wiring, see [docs/technical/DAGSTER_PIPELINE_DEPENDENCY_MAP.md](docs/technical/DAGSTER_PIPELINE_DEPENDENCY_MAP.md).

```mermaid
architecture-beta
    group sources(cloud)[External Data Sources]
    service oree(internet)[OREE market prices] in sources
    service weather(internet)[Open Meteo weather API] in sources

    group runtime(cloud)[Current Runtime]
    group orchestrator(cloud)[Dagster Orchestration] in runtime
    service dagster(server)[Dagster defs in src definitions] in orchestrator
    service daily(server)[daily data refresh job] in orchestrator
    service checks(server)[contract checks job] in orchestrator
    service benchmark(server)[benchmark engines job] in orchestrator
    service multi(server)[multi tenant analytics job] in orchestrator

    group data(cloud)[Data and Observability] in runtime
    service postgres(database)[PostgreSQL metadata and snapshots] in data
    service mlflow(server)[MLflow tracking] in data
    service files(disk)[Filesystem IO fallback] in data

    group surfaces(cloud)[User Interfaces and Operators] in runtime
    service dagsterui(server)[Dagster UI port 3000] in surfaces
    service dashboard(server)[Nuxt dashboard and API port 3600] in surfaces
    service streamlit(server)[Streamlit app legacy internal] in surfaces

    oree:B --> T:dagster
    weather:B --> T:dagster

    dagster:B --> T:daily
    dagster:R --> L:checks
    dagster:L --> R:benchmark
    dagster:T --> B:multi

    dagster:R --> L:postgres
    dagster:R --> L:files
    benchmark:R --> L:mlflow

    dagster:B --> T:dagsterui
    dagster:B --> T:dashboard
    dagster:B --> T:streamlit
```

Notes:
- Scope is the current runtime stack described by the active workspace, local launcher, and compose services.
- The AWS free tier target deployment remains documented separately in the technical architecture docs and is intentionally omitted here.
- Streamlit is shown as a secondary legacy or internal surface because it still exists in the repo, but the current local runtime guidance centers on Dagster and the Nuxt dashboard.
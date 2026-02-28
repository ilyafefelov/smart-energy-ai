### Technical Specification: Autonomous Energy Arbitrage System (Ukraine 2026\)

##### 1\. Architectural Blueprint: Software-Defined Assets (SDA)

In the hyper-volatile 2026 Ukrainian energy market, operational reliability is a function of data integrity. This system transition from traditional task-based scheduling to a  **Software-Defined Asset (SDA)**  framework via Dagster. Unlike imperative scripts, SDAs are declarative; they represent the desired state of the world. This approach is mission-critical for maintaining rigorous data lineage, ensuring that every arbitrage decision is traceable to a specific version of market prices or battery telemetry. Furthermore, by offloading the heavy computational lifting to the AWS cloud, we mitigate the hardware constraints of local Victron CCGX and Cerbo GX devices, which are prone to reboots and processing exhaustion when managing high-frequency mods.**Asset Lineage Mapping**  Implement the following core Dagster Assets to represent the system state:

* **Market\_Data\_Asset** : Ingest hourly pricing from Ukrenergo and ENTSO-E, covering both the Day-Ahead Market (DAM) and Intraday Market (IDM).  
* **Weather\_Asset** : Generate localized high-resolution forecasts for solar insolation and wind speed. This asset requires gps\_coords to anchor meteorological precision.  
* **Client\_State\_Asset (stage 2, beyond this current  stage 1 \- only user manual config)** : Ingest real-time hardware telemetry via MQTT. To maintain architectural precision, subscribe to the following Victron paths:  
* N/{portalId}/system/0/Dc/Battery/Soc (State of Charge)  
* N/{portalId}/system/0/Dc/Battery/Power (Current Load)  
* N/{portalId}/system/0/Dc/Battery/Temperature (Thermal monitoring)  
* N/{portalId}/solarcharger/289/State (Charger status: Bulk/Absorption/Float)  
* **Feature\_Matrix** : Synthesize raw market, weather, and telemetry data. This asset employs the dual-engine approach to balance latency and throughput.  
* **Decision\_Model** : Execute XGBoost for price forecasting and Optuna for cycle optimization to produce the "Actionable Advice."**Lineage Visualization and Connectivity**  Enforce data persistence using the S3PickleIOManager. This ensures that the flow from raw ingestion to the final action is backed by S3-stored state, allowing for re-hydration of the pipeline at any node. This structural foundation enables the high-performance compute engines to operate on versioned, immutable data snapshots.

##### 2\. Dual-Engine Feature Engineering: The Benchmarking Framework

Strategic computational flexibility requires balancing "Free Tier" local development with "Terabyte-Scale" production demands. This dual-engine strategy ensures that engineers can iterate on t3.micro instances using memory-efficient lazy evaluation before scaling to GPU-accelerated clusters for high-frequency characterization.**Engine Differentiators**| Feature | Backend A: Polars | Backend B: NVTabular || \------ | \------ | \------ || **Compute Environment** | CPU-bound (Multi-threaded Rust) | GPU-bound (CUDA-optimized) || **Execution Logic** | Lazy Evaluation / Vectorization | Massively Parallel Tensors (RAPIDS) || **Scalability** | High (Efficient on t3.micro RAM) | Ultra-high (H100/A10 instances) || **Strategic Use Case** | Local Dev / Edge Fallback | Production Training / IDM Arbitrage |  
**Defense Import Logic**  Implement a robust fallback mechanism to ensure system uptime regardless of hardware availability. Use the following structured technical pattern:  
try:  
    import nvtabular as nvt  
    import torch  
    if torch.cuda.is\_available():  
        ENGINE \= "NVTabular"  
    else:  
        raise ImportError("CUDA not detected")  
except ImportError:  
    import polars as pl  
    ENGINE \= "Polars"

**MLflow Observability**  Mandate the logging of the following parameters for every execution to ensure performance transparency:

* engine\_type: (Polars | NVTabular)  
* processing\_seconds: Total transformation time.  
* MAE (Mean Absolute Error): Model accuracy validation.  
* inference\_latency: Critical for execution in the Intraday Market (IDM) window.

##### 3\. Physical & Economic Modeling: The Battery Intelligence Layer

Long-term profitability in energy arbitrage is not driven by revenue alone, but by the management of Solid Electrolyte Interphase (SEI) growth. Every cycle incurs a non-linear cost; the system must optimize for the "Knee Point"—the threshold where SEI resistance surpasses a critical value, leading to rapid, irreversible capacity fade.**Optimizer Equations (Optuna)**  The system shall solve for the Pareto-front of revenue vs. degradation using the following mathematical models:

1. **Levelized Cost of Storage (LCOS):**   $$LCOS \= \\frac{CAPEX \+ \\sum\_{t=1}^{n} \\frac{Maint\_t}{(1+r)^t}}{\\sum\_{t=1}^{n} \\frac{Discharge\_t}{(1+r)^t}}$$   *Calculates the total cost per kWh throughput over the asset's lifecycle.*  
2. **Marginal Cost of Degradation (**  **$MC\_{deg}**$  **):**   $$MC\_{deg} \= \\frac{\\partial (\\text{Asset Value Loss})}{\\partial (\\text{Cycle Energy})} \\times f(T, SoC, R\_{sei})$$   *Where*  *$f*$  *is a non-linear penalty function increasing as SEI resistance (*  *$R\_{sei}*$  *) approaches the critical "Knee Point."***Chemistry Benchmarking**  
* **LFP (Lithium Iron Phosphate):**  Preferred for the 2026 Ukrainian market. Its  **olivine structure**  and stable phase-change characteristics result in significantly lower  $MC\_{deg}$  and higher cycle life compared to NMC or Lead-Acid.  
* **Lead-Acid:**  Low CAPEX but high wear. Rapid "Knee Point" arrival makes it unsuitable for the high-frequency cycling required for IDM/DAM arbitrage.

##### 4\. AWS Free Tier Deployment & Infrastructure Strategy

Minimize Operational Overhead (OPEX) by exploiting the AWS Free Tier while maintaining 2026-market readiness through stateless scalability.**Hybrid Infrastructure Components**

1. **Management Plane:**  EC2 (t3.micro) for the Dagster Webserver and Daemon.  
2. **Compute Plane:**  AWS Lambda for Dask workers and Optuna trials. To bypass the 15-minute Lambda execution limit, implement a  **Task Partitioning Strategy**  using Dagster Partitions to chunk 2026 market data into discrete 15-minute windows or specific Client IDs.  
3. **Metadata Plane:**  RDS PostgreSQL (db.t3.micro). This instance serves as both the Dagster run storage and the  **Optuna RDB Backend** , facilitating parallel optimization trials across multiple Lambda instances.  
4. **Storage Plane:**  Amazon S3 utilizing S3PickleIOManager for inter-asset communication and persistence of the feature matrix.

##### 5\. SaaS Architecture: Multi-tenancy & Asset Factories

Scaling to hundreds of shopping centers (ТЦ) requires an "Asset Factory" pattern to programmatically generate pipelines without manual code changes.**Dynamic Asset Generation**  Implement dg.Component to scaffold client-specific definitions. Use the build\_defs logic to map YAML configurations to SDA instances. The defs.yaml for a new client must include:

* client\_id: Unique identifier (e.g., TC\_Kyiv\_01).  
* battery\_chemistry: (LFP | NMC) to load specific  $MC\_{deg}$  penalty functions.  
* gps\_coords: For the Weather\_Asset localized forecast.  
* hardware\_portal\_id: For the Victron MQTT path interpolation.**Client Insights Dashboard**  Surface the following metrics:  
* **Daily Arbitrage Savings (UAH):**  Net financial gain.  
* **Current SoC:**  Real-time state from system/0/Dc/Battery/Soc.  
* **Projected SoH (State of Health):**  Remaining useful life based on the SEI resistance curve.

##### 6\. System Reliability, Observability, and Implementation

"Idempotency" is the primary engineering safeguard against catastrophic hardware wear.**Core Engineering Principles**

* **Idempotency (Check-Before-Write):**  Before issuing a BUY/SELL command, the protocol must query the Client\_State\_Asset to verify if the hardware state already reflects the intended action (e.g., verifying Charger\_Status before re-issuing a charge command).  
* **Observability (Lineage of Advice):**  Attach a JSON blob to the final Actionable\_Advice asset metadata. This blob must contain the upstream price\_forecast and predicted\_weather\_impact used to generate the command.**Project Deliverables Summary**  
* README.md: Setup and operational guide.  
* **C4 Model:**  Architectural diagram of Management (EC2), Compute (Lambda), and Metadata (RDS) planes.  
* **Folder Structure:**  
* **MLflow Integration:**  Automated tracking for engine\_type, MAE, and inference\_latency.


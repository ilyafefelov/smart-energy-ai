# Diploma Literature Tracker

This is the human-readable companion to `diploma_bibliography.bib`.

Use the `.bib` file for citation tooling.
Use this tracker for ranking, reading status, thesis placement, and MVP upgrade decisions.

## Status Legend

- `planned`: tracked but not yet finished for that field.
- `partial`: partly reviewed or partly incorporated, but not finished.
- `done`: finished for that field.
- `n/a`: not applicable for that source.

Field meaning:

- `Read`: the paper or source has been reviewed beyond title-only triage.
- `Cited`: the source has been placed into the working thesis bibliography or draft citation set.
- `Discussed`: the source is explicitly discussed in diploma text, not only listed in references.
- `Implemented`: the source already changed the MVP code, evaluation, or planned implementation slice.

## Curation Rules

- `core`: directly helps replace the current `RandomForest` forecast or improve the forecast-to-schedule logic.
- `methodology`: changes how model quality is judged, even if it is not a new forecast architecture.
- `supporting`: useful for the literature review and system context, but not the center of the arbitrage MVP.
- `appendix`: regulatory, market, vendor, or tooling context that should stay out of the main peer-reviewed bibliography.

## Update Protocol

1. Add or update the source in `diploma_bibliography.bib`.
2. Add one row here with rank, role, workflow status, and next action.
3. If a source is not peer reviewed, move it to the appendix section instead of the core list.
4. Update `Read`, `Cited`, `Discussed`, and `Implemented` whenever the source advances.
5. If a paper changes the implementation plan, update the `MVP action` column before adding more reading notes.

## Core Sources

| Key | Rank | Priority | Origin | Read | Cited | Discussed | Implemented | Why keep it | MVP action |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| `Lago2021ForecastingDayAhead` | 1 | P1 | earlier sweep | partial | done | planned | planned | Best benchmark and evaluation discipline anchor | Build leakage-safe walk-forward benchmark harness |
| `OConnor2025ElectricityPriceForecastingReview` | 2 | P1 | earlier sweep | partial | done | planned | planned | Best recent cross-market review for day-ahead, intraday, and balancing | Keep day-ahead scope now, but design data/model interfaces so intraday and balancing can be added |
| `Smets2025ValueOrientedPriceForecasting` | 3 | P1 | earlier sweep | partial | done | planned | planned | Strongest paper for judging forecasts by arbitrage value instead of only RMSE | Add value-based model selection or weighted loss tuning |
| `Finhold2023OptimizingMarketingFlexibility` | 4 | P1 | earlier sweep | partial | done | planned | planned | Best optimizer-side paper in the current set | Replace one-shot deterministic schedule with rolling-horizon re-optimization |
| `Olivares2023NBEATSx` | 5 | P1 | earlier sweep | partial | done | planned | planned | Strong near-term candidate to replace RF without overcomplicating the stack | Implement LEAR and NBEATSx as the first two serious RF replacements |
| `Jiang2024ProbabilisticTFT` | 6 | P2 | earlier sweep | partial | done | planned | planned | Best uncertainty-aware forecasting source in the set | Add quantile outputs such as P10, P50, and P90 |
| `Alghumayjan2024TwoSettlementArbitrage` | 7 | P2 | earlier sweep | partial | done | planned | planned | Direct bridge between transformer forecasting and storage dispatch economics | Add a later two-settlement market branch after the rolling-horizon scheduler lands |
| `Weber2024OpenSourceEnergyArbitrage` | 8 | P2 | Stage 2 market note | partial | done | planned | planned | Open and implementable risk-aware arbitrage model | Add conservative forecast bands or scenario bands around price forecasts |
| `Kampker2025BatteryEnergyStorageModelling` | 9 | P2 | Stage 2 finance and EPRI notes | partial | done | planned | planned | Best battery-realism paper carried into the audit | Add degradation penalties for high SOC windows, deep cycles, and throughput |
| `Zhang2025BatteryStateEstimationReview` | 10 | P3 | Stage 2 EPRI note | partial | done | planned | planned | Battery-state context source, useful for credibility rather than first implementation | Add richer battery state proxies after degradation penalties are in place |

## Methodology Anchors

| Key | Priority | Read | Cited | Discussed | Implemented | Why keep it | MVP action |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Sang2022DecisionFocusedArbitrage` | P1 | partial | done | planned | planned | Directly ties forecast training to storage arbitrage decisions | Evaluate models on schedule value, not only forecast error |
| `ElmachtoubGrigas2022SmartPredictThenOptimize` | P1 | partial | done | planned | planned | Formal predict-then-optimize foundation for the thesis argument | Use as the theoretical justification for decision-aware model selection |

## Supporting Academic Context

| Key | Priority | Read | Cited | Discussed | Implemented | Why keep it | Thesis placement |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `Aslam2021DeepLearningSurvey` | P2 | partial | done | planned | planned | Broad review of deep learning in load and renewable forecasting | Background chapter on AI in smart energy systems |
| `BediToshniwal2019DeepLearningFramework` | P2 | partial | done | planned | planned | Older but still useful load-forecasting architecture reference | Supporting literature review, not core arbitrage evidence |
| `Zhang2023CNNLSTMMultiTaskLoad` | P3 | partial | done | planned | planned | Concrete hybrid load-forecasting architecture from the new report-derived set | Background section on advanced load forecasting |
| `Shareef2018HomeEnergyManagementReview` | P3 | partial | done | planned | planned | Good HEMS and demand-response framing source | System context and related work, not main bibliography center |
| `Mischos2023IntelligentEMSReview` | P1 | partial | done | planned | planned | Strongest broad intelligent EMS review surfaced by the new MDPI paper | Literature review anchor for EMS architecture, AI methods, and system components |
| `Kwon2022AIBasedHomeEMS` | P1 | partial | done | planned | planned | Strong peer-reviewed HEMS paper tying energy efficiency to resident satisfaction | Related work for AI HEMS with explicit user-centered objectives |
| `Wei2023DeepReinforcementLearningSmartHome` | P1 | partial | done | planned | planned | Stronger smart-home RL control reference than the weaker building-only paper already tracked | Future-work bridge for RL control in residential EMS |
| `Hu2024IncentiveBasedIntegratedDemandResponse` | P2 | partial | done | planned | planned | Direct RL-based demand-response incentive paper with coupling effects | Demand-response incentives and adaptive control discussion |
| `Dey2025IntelligentIncentiveBasedDR` | P2 | partial | done | planned | planned | Useful incentive-based DR paper with techno-economic framing beyond the home-only case | Supporting DR literature and broader system context |
| `Ikram2024SmartHomeLoadScheduling` | P2 | partial | done | planned | planned | Strong recent smart-home load scheduling reference surfaced through the new MDPI paper | Related work on residential load scheduling and appliance coordination |
| `Liu2025DistributedSmartHomeNILM` | P2 | partial | done | planned | planned | Strong deterministic SHEM scheduling reference with MILP + GA, comfort, carbon, and DR incentives | Related work for multi-objective deterministic scheduling and household EMS |

## Appendix Candidates

| Key | Category | Read | Cited | Discussed | Implemented | Why keep it | Where to use it |
| --- | --- | --- | --- | --- | --- | --- | --- |
| `CMSMarketCoupling` | Regulatory | partial | done | planned | n/a | Useful for Ukrainian market-coupling context | Normative appendix |
| `EnergyCommunity2026WinterReport` | Regulatory | partial | done | planned | n/a | Useful for current reform and crisis-management context | Normative appendix |
| `ESSNews2026SolarStorageAuctions` | Industry news | partial | done | planned | n/a | Tracks current auction direction for solar plus storage | Practical appendix |
| `PVMagazine2026SolarStorageAuctions` | Industry news | partial | done | planned | n/a | Corroborating market media source | Practical appendix |
| `EPRIDERIntegrationTools` | Tooling | partial | done | planned | n/a | Useful to cite comparable industry planning tools | Practical appendix |
| `EPRIDERVET` | Tooling | partial | done | planned | n/a | Comparable implementation tool, not a thesis method source | Practical appendix |
| `EPRIDERVETGuide` | Tooling | partial | done | planned | n/a | Useful for engineering comparison or feature ideas | Practical appendix |
| `SolarForecastArbiterCalculatingCosts` | Evaluation tooling | partial | done | planned | n/a | Useful for forecast-cost framing | Practical appendix |
| `Kavya2025HybridAIDrivenEMS` | Conference paper | partial | done | planned | n/a | Compact AI-EMS architecture source, but the short conference format keeps it out of the strict main thesis bibliography | Provisional academic appendix |
| `Farhana2023EfficientDeepReinforcementLearning` | Provisional journal article | partial | done | planned | n/a | RL-plus-storage smart-building paper; useful signal, but weaker as a thesis anchor than the stronger smart-home RL sources added later | Provisional academic appendix |
| `Kanna2025UrbanSmartGridsPreprint` | Preprint | partial | done | planned | n/a | Strong quantitative EMS claims from the new report, but preprint status keeps it out of the core academic set | Directional appendix evidence only |
| `Aleemoddin2025AIBasedEMS` | Provisional overview | partial | done | planned | n/a | General AI-EMS overview from the new report, but not strong enough to anchor the thesis argument | Practical appendix and replacement target for stronger peer-reviewed evidence |

## Read Order

1. `OConnor2025ElectricityPriceForecastingReview`
2. `Smets2025ValueOrientedPriceForecasting`
3. `Finhold2023OptimizingMarketingFlexibility`
4. `Olivares2023NBEATSx`
5. `Jiang2024ProbabilisticTFT`
6. `Alghumayjan2024TwoSettlementArbitrage`
7. `Weber2024OpenSourceEnergyArbitrage`
8. `Mischos2023IntelligentEMSReview`
9. `Kwon2022AIBasedHomeEMS`
10. `Wei2023DeepReinforcementLearningSmartHome`
11. `Hu2024IncentiveBasedIntegratedDemandResponse`
12. `Liu2025DistributedSmartHomeNILM`
13. `Ikram2024SmartHomeLoadScheduling`

## Top 5 New Sources for MVP Upgrade

These are the five strongest newly elevated sources from the second-pass literature sweep when the goal is to upgrade the current RandomForest plus deterministic-optimization MVP.

| Source with url link | Upgrade Type | Concrete MVP Change | What to implement in practice | Expected payoff |
| --- | --- | --- | --- | --- |
| [Mischos2023IntelligentEMSReview](https://doi.org/10.1007/s10462-023-10441-3) | System architecture and method selection | Replace the current loosely coupled forecast-plus-scheduler logic with a clearer HEMS architecture split into forecasting, decision, device, and user-objective layers | Refactor the MVP pipeline into explicit modules for forecasting, optimization, user constraints, and battery/device control; use the review as the thesis anchor for the target architecture | Cleaner diploma narrative, better extensibility, and lower risk of ad hoc MVP growth |
| [Kwon2022AIBasedHomeEMS](https://doi.org/10.1109/JIOT.2021.3104830) | User-aware multi-objective HEMS | Extend the optimizer objective beyond simple price arbitrage to include resident comfort or satisfaction proxies | Add configurable comfort penalties, preference weights, and household-level objective terms into the optimization layer and evaluation metrics | More realistic household EMS behavior and a stronger practical justification for the diploma MVP |
| [Wei2023DeepReinforcementLearningSmartHome](https://doi.org/10.1109/JSYST.2023.3247592) | Adaptive control beyond deterministic scheduling | Add an RL-based controller baseline or experiment track alongside the deterministic optimizer | Build an offline training environment from historical price, load, and battery-state trajectories; compare PPO or DQN-style control against the current deterministic scheduler | Evidence on whether adaptive control outperforms the fixed optimization policy under volatile conditions |
| [Hu2024IncentiveBasedIntegratedDemandResponse](https://doi.org/10.1016/j.energy.2024.132997) | Incentive-aware demand response | Expand the MVP from pure arbitrage to tariff or incentive response logic | Add incentive signals, demand-response event flags, and coupled demand-side constraints to the optimization inputs and scenario evaluation | Broader business relevance and a better fit to real demand-response programs instead of arbitrage-only evaluation |
| [Liu2025DistributedSmartHomeNILM](https://doi.org/10.3390/electronics14091719) | Stronger deterministic residential scheduler | Upgrade the deterministic part of the MVP from a simple battery arbitrage optimizer to a multi-objective household scheduler with appliance or load-state awareness | Add appliance/load categories, carbon or comfort penalties, and multi-objective scheduling experiments using MILP-style formulations or constrained heuristics | Stronger baseline results, better realism, and a clearer comparison point before introducing RL |

## Implementation Order

The phased code-facing roadmap that turns this literature tracker into concrete repository work now lives in [codebase_implementation_roadmap.md](codebase_implementation_roadmap.md).

1. Benchmark harness from `Lago2021ForecastingDayAhead`
2. RF replacements from `Olivares2023NBEATSx`
3. Rolling-horizon scheduler from `Finhold2023OptimizingMarketingFlexibility`
4. Decision-aware model selection from `Smets2025ValueOrientedPriceForecasting` and `Sang2022DecisionFocusedArbitrage`
5. Probabilistic forecasts from `Jiang2024ProbabilisticTFT`
6. Battery degradation realism from `Kampker2025BatteryEnergyStorageModelling`

## Known Gaps

- `AI-Driven Smart Energy Management in Ukraine.pdf` was present in the Stage 2 folder but not reliably text-parsable through the available toolchain.
- `AI-oriented_smart_energy_management_systems_and_lo (1).pdf` exposed only limited metadata and was not treated as a verified source-bearing artifact.
- `Weber2024OpenSourceEnergyArbitrage` has an online-first timing quirk in Crossref. The DOI is stable, but some exporters may surface a 2023 online publication date instead of the volume-year view.
- `Kavya2025HybridAIDrivenEMS` was recoverable by DOI and title, but the precise IEEE proceedings title could not be resolved through the available fetch path, so the BibTeX entry is deliberately conservative.
- `Kanna2025UrbanSmartGridsPreprint` remains a Research Square preprint and should not be used as core peer-reviewed evidence even though the report cites strong quantitative results from it.
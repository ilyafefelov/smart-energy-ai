# Тиждень 1. Щотижневий звіт

- Період: `2026-04-13 - 2026-04-19`
- Статус: `чернетка`
- Формат: `текстовий звіт`
- Фокус тижня: зробити активний Stage 2 forecast-to-schedule контур пояснюваним та простежуваним: явна промоція моделі, uncertainty contract, provenance у schedule та dashboard API.

## 1. Попередній аналіз проблеми та підходів до її розв'язання

### Проблема

- У поточному MVP прогноз ціни, benchmark-результати та downstream schedule-рішення існували, але між ними не зберігався повний контекст: яка модель була активною, чому вона була promoted, який uncertainty regime використовувався, і як цей контекст дійшов до schedule та dashboard.
- Через це було складно обґрунтувати якість рішень у дипломі та показати, що optimizer діє не як «чорна скринька», а як відтворюваний predict-then-optimize контур.

### Чому це важливо

- Для дипломної роботи це критично, бо без явного provenance важко захистити вибір моделі, логіку benchmark promotion та пояснити, чому schedule рекомендує конкретну дію.
- Для технічної якості MVP це важливо, бо без стабільного контракту uncertainty і provenance губляться на межах `forecast -> benchmark -> optimizer -> dashboard`.
- Для подальшого розвитку це важливо, бо richer UI, decision audit і rolling-horizon experiments залежать від того, що metadata та reasoning стабільно проходять через runtime.

### Розглянуті підходи

1. Окремо збагачувати dashboard-дані тільки на фронтенді — відхилено, бо це дублює логіку, створює різні джерела істини і не вирішує проблему на runtime boundary.
2. Протягнути явний contract через існуючий Dagster + Nuxt runtime — обрано, бо це найменша зміна з максимальною користю для traceability.
3. Робити ширший рефакторинг scheduler/UI одночасно — відкладено, бо це збільшило б ризик і змішало б кілька slice в один великий блок без чіткої валідації.

## 2. Чітко визначені цілі проєкту на цей тиждень

- Зробити active forecast model selection і promotion metadata явними.
- Додати explicit uncertainty contract і навчити optimization inputs використовувати conservative horizon.
- Зберегти provenance від forecast asset до schedule rows і dashboard API.
- Залишити deterministic MVP production-safe, але зробити його більш пояснюваним та захищеним від metadata loss.

## 3. Початковий варіант MVP або опис методології дослідження

- Архітектурна рамка: активний локальний стек `Dagster + Python pipeline + Nuxt dashboard`, без greenfield-переписування.
- Методологія: маленькі локальні slice-правки з focused validation після кожної зміни: unit tests, Dagster materialization, runtime smoke, API contract checks.
- Дослідницький принцип: не оцінювати forecasting лише через RMSE/MAE, а зв'язувати його з value-oriented arbitrage quality і predict-then-optimize логікою.
- Поточний MVP залишається deterministic-by-default, а richer probabilistic / rolling-horizon behavior вводиться через контрактні розширення, а не через одночасний повний redesign.

## 4. Виконані завдання, досягнення і зміни у проєкті

| Завдання | Що зроблено | Артефакт |
| --- | --- | --- |
| Explicit forecast promotion | Додано явну promoted-model metadata path для runtime forecast selection | commit `3321659`, `src/data_pipeline/forecast_model_registry.py`, `src/assets/core/price_forecast.py` |
| Forecast uncertainty contract | Додано explicit low/base/high scenario fields і uncertainty metadata | commit `e84ccbd`, `src/assets/core/price_forecast.py` |
| Conservative optimization input | Optimizer input layer почав використовувати uncertainty-aware conservative horizon | commit `4751afd`, `src/data_pipeline/optimization_schedule_inputs.py`, `src/assets/core/optimization_schedule.py` |
| Benchmark + MLflow alignment | Збережено uncertainty summary у benchmark scorecards, promotion metadata та MLflow rows | commits `13f39a9`, `6894e30`, `src/data_pipeline/benchmark_helpers.py`, `src/assets/benchmarks/performance.py` |
| Forecast provenance in runtime output | Forecast rows тепер несуть `promotion_*` provenance fields | commit `ab79a64`, `src/assets/core/price_forecast.py` |
| Schedule provenance | Forecast model / horizon / uncertainty / promotion context протягнуто в `optimization_schedule_asset` і Python schedule reader | commit `cfe25aa`, `src/assets/core/optimization_schedule.py`, `src/data_pipeline/dagster_schedule_loader.py`, `scripts/read_dagster_schedule.py` |
| Dashboard API provenance | Dagster-backed schedule rows і `source_metadata` зберігають forecast provenance у recommendation та schedule-24h routes | commits `906e71a`, `6af5339`, `dashboard/server/api/dagster/recommendation.ts`, `dashboard/server/api/dagster/schedule-24h.ts` |
| Runtime import repair | Виправлено `src.definitions`, щоб Dagster materialization знову проходив через прямі модульні імпорти | commit `8c1358c`, `src/definitions.py` |

## 5. Оновлені або релевантні безпекові аспекти

- Поточний тижневий slice не був безпосередньо cybersecurity-oriented.
- Проте traceability та provenance metadata зменшують audit ambiguity: тепер легше побачити, яка модель і який uncertainty regime вплинули на рішення scheduler-а.
- Нових security-механізмів, SAST/DAST-артефактів або змін threat model цього тижня не додавалося.

## 6. Ризики та виклики

| Проблема | Чому це важливо | План розв'язання |
| --- | --- | --- |
| `dashboard/app/pages/index.vue` має pre-existing syntax/typecheck errors | Це блокує повний `nuxi typecheck` і ускладнює broad dashboard validation для нових API-змін | Наступного тижня локально виправити template syntax у `pages/index.vue` і повторно прогнати `nuxi typecheck` |
| Локальний Nuxt server на `127.0.0.1:3600` був нестабільний під час перевірок | Через це частина live endpoint validation залежала від середовища, а не від коду slice | Підняти локальний stack через існуючий start-local flow і повторно прогнати endpoint smoke для `recommendation` та `schedule-24h` |
| Provenance вже дійшов до API, але ще не відображається у user-facing UI | Без UI supervisor не побачить практичну користь explainability improvements | Додати provenance summary і uncertainty context у dashboard cards/timeline поверх існуючих API payloads |

## 7. План роботи на наступний тиждень

1. Виправити pre-existing dashboard syntax break у `dashboard/app/pages/index.vue` і повернути зелений `nuxi typecheck`.
2. Підняти локальний dashboard server і повторно smoke-перевірити `/api/dagster/recommendation` та `/api/dagster/schedule-24h`.
3. Вивести Dagster forecast provenance та uncertainty summary у dashboard UI, а не лише в API contracts.
4. Продовжити Phase 2/3 roadmap у напрямку richer decision audit та rolling-horizon-oriented optimizer reasoning.
5. Дофіналізувати weekly report артефакти: додати скріншоти або screencast перед подачею.

## 8. Артефакти, що підтверджують виконану роботу

### Код

- `src/assets/core/price_forecast.py`
- `src/data_pipeline/benchmark_helpers.py`
- `src/data_pipeline/forecast_model_registry.py`
- `src/assets/core/optimization_schedule.py`
- `src/data_pipeline/dagster_schedule_loader.py`
- `scripts/read_dagster_schedule.py`
- `dashboard/server/api/dagster/recommendation.ts`
- `dashboard/server/api/dagster/schedule-24h.ts`

### Документація

- `docs/Stage 2/codebase_implementation_roadmap.md`
- `docs/Stage 2/plan.md`
- `docs/Stage 2/diploma_literature_tracker.md`
- `docs/Stage 2/weekly_reports/weekly_progress_report_template.md`
- `docs/Stage 2/weekly_reports/week-01-progress-report.md`

### Демонстраційні матеріали

- Скріншоти: `pending before submission`
- Відео: `optional / pending`

### Тестування

- Focused pytest slices for forecast, benchmark, registry, schedule, and Python schedule reader
- Real Dagster materialization of the optimization chain with `RUN_SUCCESS`
- Local diagnostics: touched dashboard route files report no editor errors
- Known limitation: full `nuxi typecheck` currently fails because of unrelated pre-existing syntax errors in `dashboard/app/pages/index.vue`

## 9. Огляд літератури для цього slice роботи (мінімум 5 джерел)

| Джерело | Теоретична ідея | Як це використано в поточному slice | Посилання |
| --- | --- | --- | --- |
| `ElmachtoubGrigas2022SmartPredictThenOptimize` | Predict-then-optimize потрібно оцінювати не лише через prediction quality, а через decision boundary | Вибраний slice сфокусовано на тому, щоб model metadata та provenance не губилися на межі `forecast -> optimizer -> dashboard`, тобто decision layer отримував прозорий контекст | https://doi.org/10.1287/mnsc.2020.3922 |
| `Sang2022DecisionFocusedArbitrage` | Forecasting для storage arbitrage має бути decision-focused, а не лише error-focused | У benchmark path збережено value-oriented forecast summaries і downstream decision relevance через promotion metadata та schedule attribution | https://doi.org/10.1109/TSG.2022.3166791 |
| `Smets2025ValueOrientedPriceForecasting` | Value-oriented price forecasting вимагає зберігати метрики, які відображають arbitrage value, а не тільки RMSE/MAE | У scorecards, MLflow logging і promotion metadata було збережено uncertainty/value context для runtime forecast promotion | https://doi.org/10.1016/j.energy.2025.137112 |
| `Weber2024OpenSourceEnergyArbitrage` | Risk-aware arbitrage потребує price bands або conservative interpretation imperfect price signals | Це напряму використано для explicit uncertainty contract і conservative horizon у optimization inputs | https://doi.org/10.3390/en17010013 |
| `Finhold2023OptimizingMarketingFlexibility` | Rolling-horizon dispatch та market-facing flexibility повинні бути відтворюваними і пояснюваними | Поточний schedule provenance slice готує optimizer outputs до richer rolling-horizon/dispatch reasoning, зберігаючи model/horizon/uncertainty context на schedule boundary | https://doi.org/10.1016/j.apenergy.2023.121667 |

## 10. Очікуваний результат на кінець тижня

- [x] Попередній аналіз проблеми та підходів готовий.
- [x] Цілі проєкту визначені.
- [x] Початковий MVP / методологія описані.
- [x] Перший звіт про прогрес підготовлено.
- [x] Щонайменше 5 джерел літератури пов'язані з поточним slice роботи.

## 11. Готовність до подачі

- Посилання на текстовий документ: `fill before submission`
- Посилання на відео: `optional`
- Коментар для керівника: поточний тижневий slice сфокусований на traceability forecast-to-schedule logic, а не на broad UI polish; next week main risk burn-down — відновити full dashboard validation surface.
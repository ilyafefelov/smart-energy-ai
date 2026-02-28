# Energy Dashboard Visualization Strategy

**Created:** Feb 6, 2026  
**Research:** Academic + Industry Best Practices  
**Status:** Implemented

---

## Executive Summary

Based on research into energy management dashboards (Tesla Powerwall, Sunrun), battery management systems, and academic papers on energy visualization, we've identified 7 critical visualization types that help users make optimal trading decisions.

---

## Core Visualization Recommendations

### 1. **Hourly Price Line Chart + Solar Area + Demand Bars**
**Purpose:** When to buy/sell energy  
**Current Implementation:** ✅ DEPLOYED in dashboard index.vue

- **Line:** Real-time price overlay (₴/kWh)
- **Area:** Solar generation curve (free energy availability)
- **Bars:** Factory demand (kWh consumption)
- **Zones:** Buy (low), Hold (medium), Sell (high) highlighted

**Why it works:** Shows optimal action at each hour. Users see instantly which hours to charge (low price + low demand) vs sell (high price + high solar).

---

### 2. **Battery State of Charge (SOC) Trajectory**
**Purpose:** Battery charge/discharge scheduling  
**Recommended for Control page**

- **Line chart:** Hourly SOC % over 24h period
- **Shaded regions:** Min safe level, optimal charging band, max capacity
- **Color:** Green (healthy), Yellow (caution), Red (critical)
- **Interaction:** Click to see what trading action caused each change

**Why it works:** Users see the "battery journey" - when they're charging, when they're selling, when they're at capacity. Prevents overcharging or over-discharging.

---

### 3. **Cumulative Savings Chart**
**Purpose:** Cost savings visualization  
**Current Implementation:** ✅ Partially (need time-series version)

**Recommendation:** 
- **X-axis:** Time (hourly, daily, weekly, monthly selector)
- **Line:** Cumulative ₴ saved vs baseline
- **Shaded area:** 7-day rolling average
- **Key metrics:** Daily rate (₴/day), monthly projection, annual run rate

**Psychology:** Shows money accumulating. More motivating than static numbers.

---

### 4. **Time-of-Use Heatmap**
**Purpose:** Pattern discovery (when prices are high/low)  
**Recommended for Analytics page**

- **Grid:** Hours (columns) × Days (rows)
- **Color intensity:** Price level (blue=cheap, red=expensive)
- **Overlays:** Solar generation pattern, demand pattern

**Why it works:** Users spot patterns visually:
- "Prices always spike 11-13h" → Sell window
- "Solar peaks 10-14h" → Charge window
- Helps with manual intervention if needed

---

### 5. **Real-Time Cost Gauge**
**Purpose:** Current hour decision indicator  
**Recommended for Control page**

- **Gauge:** Current price against daily min/max
- **Zones:** 
  - 🟢 BUY CHEAP (0-33% of range)
  - 🟡 HOLD (33-66% of range)
  - 🔴 SELL PREMIUM (66-100% of range)
- **Action prompt:** "Good time to charge" / "Premium sell opportunity"

**Why it works:** Real-time guidance. User knows what to do RIGHT NOW.

---

### 6. **Anomaly Detection Alerts**
**Purpose:** Catch unusual patterns (grid issues, price spikes)  
**Recommended for Notifications system**

- **Alert cards:** Distinct from normal data
- **Types:**
  - ⚠️ Unusual price spike (+50% above normal)
  - ⚡ Grid outage detected
  - 🔋 Battery critically low
  - ❄️ Extreme weather affecting solar

**Why it works:** Draws attention to exceptional situations requiring intervention.

---

### 7. **Sankey Diagram: Energy Flow**
**Purpose:** Understand source-to-use journey  
**Recommended for Analytics page**

- **Left side:** Sources (Grid bought, Solar free, Battery stored)
- **Right side:** Uses (Factory load, Sold to grid, Stored)
- **Flow width:** Proportional to energy quantity
- **Color:** Green (renewable), Blue (grid), Yellow (stored)

**Example:**
```
Solar (15 kWh) ──┐
                 ├→ Factory Load (25 kWh) ──→ Direct use
Battery (8 kWh) ─┤
                 └→ Sold to Grid (6 kWh) ──→ Revenue
Grid (5 kWh) ────┘
```

**Why it works:** Holistic energy balance. Users understand input vs output.

---

## Per-Page Implementation Roadmap

### Dashboard (index.vue) - DONE ✅
- ✅ Hourly price chart with solar + demand
- ✅ Weekly OREE price table
- ✅ Cost comparison (baseline vs PPO)
- ✅ Financial projections
- 🔜 Add cumulative savings trend

### Control (control.vue) - TO BUILD
- 🔜 Battery SOC trajectory (24h)
- 🔜 Real-time cost gauge
- 🔜 Manual trading buttons (charge now, sell now, hold)
- 🔜 Hourly price/solar/demand forecast

### Analytics (analytics.vue) - TO BUILD
- 🔜 Time-of-use heatmap (7-30 day view)
- 🔜 Pattern analysis (peak hours, valley hours)
- 🔜 Sankey diagram (energy flow)
- 🔜 Monthly/quarterly/annual trend lines
- 🔜 Anomaly history log

### Settings (settings.vue) - DONE ✅
- ✅ Battery configuration
- ✅ Model retraining UI
- ✅ Notification preferences
- ✅ Real-time save feedback

---

## Model Strategy: Per-User vs Shared

### Decision: **PER-USER MODELS** ✅

**Why each user needs their own trained model:**

1. **Different demand patterns**
   - Factory: 9-17h peak load
   - Residential: 7-9h + 18-22h peaks
   - Seasonal: Summer vs winter demand curves

2. **Solar availability varies**
   - Latitude affects peak generation time
   - Roof angle/orientation impacts yield
   - Weather patterns region-specific

3. **Electricity prices differ by zone**
   - Ukraine has regional OREE zones
   - Germany has regional DA/IDM prices
   - Time-of-use rates vary by provider

4. **Battery constraints are unique**
   - Different brands have different efficiency curves
   - Degradation patterns vary
   - Charge/discharge rates different

**Scaling approach:**
- **Daily quick update** (1 min): Retrain on yesterday's data, optimize parameters
- **Weekly full retraining** (10 min): Full model optimization with latest data
- **On settings change**: Immediate quick update + proposal for full retrain

**Storage:**
- Model size: ~2-5 MB per user (PPO weights + metadata)
- Scalable to 1,000s of users (simple file storage)
- Can migrate to cloud later if needed

---

## Retraining Workflow

### Automatic Triggers
1. **Settings updated** → Propose retraining
2. **Anomaly detected** → Alert user, suggest quick update
3. **Weekly schedule** → Auto-run full retraining at 2 AM

### User Controls (Settings page)
- **Quick Daily Update** button (1 min, incremental)
- **Full Weekly Retraining** button (10 min, comprehensive)
- Progress bar with time remaining
- Real-time status notifications
- Auto-save confirmation before retraining

### Notification on Save
- ✅ Green banner: "Settings saved successfully"
- 💡 Blue banner: "Retraining recommended. Your model will be optimized for new settings."
- Two buttons: "Start Now" or "Skip"
- Auto-dismiss if user skips

---

## Color Scheme & Visual Hierarchy

### Energy States
- 🟢 **Green** (Emerald): Savings, solar, profit, good decision
- 🔴 **Red**: Costs, grid purchase, price spikes
- 🟡 **Yellow**: Battery, caution, neutral
- 🔵 **Blue**: Grid, pricing, information
- ⚫ **Slate**: Background, neutral

### Interactive Elements
- **Buttons:** Emerald-600 (primary), Blue-700 (secondary), Slate-700 (tertiary)
- **Alerts:** Green (success), Red (urgent), Yellow (warning), Blue (info)
- **Badges:** Animated pulse for real-time status

---

## Research Sources

### Academic
- "Energy Management Systems for Smart Grids" (MDPI Energies, 2023)
- "Real-Time Visualization of Battery State Estimation" (IEEE 2021)
- "User Interface Design for Energy Trading Platforms" (Sage, 2023)

### Industry
- Tesla Powerwall dashboard (real-time SOC, price awareness)
- Sunrun battery management (cost savings highlighting)
- AESO (Alberta) electricity market interface (heatmaps for TOU patterns)
- EPEX SPOT energy exchange (price visualization)

### Principles Applied
- **Information density:** Show must-know, hide nice-to-know
- **Action clarity:** Every visual tells user what to do
- **Pattern recognition:** Spatial layout aids mental models
- **Real-time feedback:** Confirmation of actions immediately

---

## Next Steps

1. ✅ Settings page with model retraining UI
2. ✅ Navigation menu across all pages
3. 🔜 Build Control page with SOC trajectory + cost gauge
4. 🔜 Build Analytics page with heatmap + Sankey diagram
5. 🔜 Add cumulative savings trend to dashboard
6. 🔜 Implement anomaly detection alerts
7. 🔜 Test with multi-site scenarios
8. 🔜 Mobile responsiveness optimization

---

## Metrics for Success

- Users can identify cheapest trading hours in <5 seconds (heatmap helps)
- Users understand when model last retrained (Settings page)
- Users see real-time savings accumulate (cumulative chart)
- Users get actionable alerts (anomaly detection)
- Users never lose unsaved settings (real-time feedback)


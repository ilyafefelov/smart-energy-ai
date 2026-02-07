# Dashboard Issues: Sequential Fix Plan

**Date:** 2026-02-07 10:34 GMT+2  
**Status:** Working through issues one at a time  
**Project:** Smart Energy AI Dashboard (Nuxt 4 + @nuxt/ui 4.4.0)

---

## Issues to Fix (In Order)

### ✅ Issue #1: Zoom/Pan buttons not working
**Status:** COMPLETE  
**Solution:** Added chart interactivity with zoom (1x → 3x), pan (translate left), reset
**Result:** All buttons functional with visual feedback
**Verified:** Yes

---

### ✅ Issue #2: Good buying/selling zones not showing
**Status:** COMPLETE  
**Solution:** Added SVG background rectangles - green for buying, red for selling
**Result:** Visual zones now visible on chart
**Verified:** Yes

---

### ⏳ Issue #3: Hover tooltips - descriptions & formulas not showing
**Status:** IN PROGRESS - MOSTLY DONE  
**What was fixed:**
- Improved `InfoTooltip.vue` styling and positioning (top-right → bottom-full)
- Added proper spacing and separators
- Color-coded text for better readability
- All data already exists in metricsStore.ts

**Current status:**
- Data layer: ✅ Complete (8 metrics with title + description + formula)
- Component: ✅ Fixed (improved styling)
- Positioning: ✅ Fixed (above cards instead of to the right)
- Testing: ⏳ Pending browser reconnect

**Next:** Verify tooltip display with browser screenshot

---

### ⏳ Issue #4: Export button doesn't work
**Status:** IN PROGRESS  
**What needs to be done:**
- Price History Export: Download CSV with 8 hours of data
- Savings Breakdown Export: Download CSV with arbitrage/peak/efficiency data
- Use CSV blob + URL.createObjectURL for download

**Codex agent:** Currently working on implementation

**Next:** Complete export, test, commit

---

### ⏳ Issue #5: Refresh button doesn't work
**Status:** NOT STARTED  
**What needs to be done:**
- Refresh button should fetch latest price data from API
- Update chart and metrics on dashboard
- Show loading state while refreshing

**Next:** After Export button is done

---

## Version Status

✅ **Nuxt 4.3.0** - Upgraded successfully  
✅ **Node 24** - Using via NVM  
✅ **@nuxt/ui 4.4.0** - Now properly compatible  
✅ **Dev server:** Running on http://localhost:3001 with hot reload

---

## File Locations

**Main files being modified:**
- `pages/index.vue` - Dashboard page with all sections
- `components/DashboardCards/MetricCard.vue` - Metric cards
- `components/Tooltips/InfoTooltip.vue` - Tooltip component
- `stores/metricsStore.ts` - Metrics data + tooltips

**New features added:**
- Chart interactivity (zoom, pan, reset)
- Buy/sell zone visualization
- Button action handlers
- Tooltip styling improvements

---

## Work Session Plan

1. ✅ Issue #1 & #2: Complete
2. ⏳ Issue #3: Tooltip - 80% done (styling fixed, testing pending)
3. ⏳ Issue #4: Export button - Codex agent working
4. ⏳ Issue #5: Refresh button - Waiting for #4 to complete

**Approach:** One issue at a time, fully test before moving to next

---

## Notes

- Browser control service went offline - will reconnect for testing
- Codex agent has improved Windows PowerShell compatibility
- All interactive features are now implemented (from yesterday)
- Focus: Getting button actions and tooltips fully working

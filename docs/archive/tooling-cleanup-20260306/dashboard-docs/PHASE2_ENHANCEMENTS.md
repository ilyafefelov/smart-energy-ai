# Phase 2: Enhancements & Bug Fixes

**Branch:** `feature/nuxt-ui-enhancements-and-fixes`  
**Status:** Ready to start  
**Created:** 2026-02-07 13:11 GMT+2

---

## Issues to Fix

### 1. Data Refresh Instability (CRITICAL)
**Problem:** Clicking refresh on "Price History" table causes numbers to change dramatically
```
Before refresh: Daily Savings ₴125.50, Peak ₴0.00, etc.
After refresh: Different values entirely
Expected: Data should only change if market changed, not randomly
```

**Root cause:** Likely API endpoint returning different values each call
**Options:**
- A) Check if data is being cached between calls
- B) Verify API endpoint is deterministic (same input = same output)
- C) Add timestamp check - only refresh if new data available
- D) Check if scraping is re-running each time instead of using cached results

**Files to investigate:**
- `server/api/prices/*.ts` - Price endpoints
- `server/api/battery/*.ts` - Battery status endpoint
- `stores/pricesStore.ts` - Price store logic

### 2. Current Price vs Peak Price Anomaly
**Problem:** Current price (0.00 ₴) is LOWER than peak price (0.00 ₴)
```
Current Price: 0.00 ₴
Peak Price Today: 0.00 ₴
Off-Peak Price: 0.00 ₴
Logic: Current should be between off-peak and peak, or >= one of them
```

**Root cause:** Test data or API returning zeros
**Fix:** Validate all price endpoints return non-zero realistic values

**Files to investigate:**
- `data/prices/` - Test data
- `server/api/` - API endpoints
- Data scraping scripts

### 3. Lost Navigation Menu
**Problem:** NavigationMenu component not showing on any page
```
Before: Menu visible on dashboard, settings, control, analytics pages
Now: All pages blank header
```

**Files:**
- `app/components/Navigation/PageMenu.vue` - Component exists
- `app/app.vue` - Layout file needs to include it
- Check if route changes broke the menu

**Fix:** Wire navigation component back into layout

### 4. Missing Hover Tooltips
**Problem:** Metric cards don't show tooltips on hover
```
Expected: Hover over "Daily Savings" card → shows explanation
Actual: Nothing happens
```

**Component exists:**
- `app/components/Tooltips/InfoTooltip.vue` - Component ready
- `app/pages/index.vue` - Uses MetricCard components

**Fix:** Wire tooltips to metric cards in dashboard

### 5. Missing Documentation on Dashboard
**Problem:** Users don't understand how forecasting/zones work
**Need to add:**

a) **Price Forecasting Methodology Card**
   - How prices are predicted (algorithm/model used)
   - Formula or calculation method
   - Data sources used
   - Confidence level/accuracy

b) **Buy/Sell Zone Explanation**
   - Green zone: price < 85% of average (BUY signal)
   - Red zone: price > 115% of average (SELL signal)
   - How these thresholds were chosen
   - Historical performance

c) **Last Data Update Timestamp**
   - Show when prices were last updated
   - Show when forecast was generated
   - Show data source freshness

d) **Data Source Citations**
   - Where prices come from
   - Update frequency
   - Reliability rating

**Implementation:** Add info cards or info modals to dashboard

---

## Enhancement Tasks

### Task 1: Setup @nuxt/ui Properly
**What:** Install and configure @nuxt/ui with NUXT-UI MCP server
```json
{
  "nuxt-ui": {
    "command": "npx",
    "args": ["mcp-remote", "https://ui.nuxt.com/mcp"]
  }
}
```

**Steps:**
1. Add @nuxt/ui to package.json and modules
2. Consult NUXT-UI MCP for best practices
3. Use UI components where appropriate
4. Replace custom styling with @nuxt/ui components
5. Test all pages render correctly

**Files to modify:**
- `nuxt.config.ts` - Add @nuxt/ui module
- `package.json` - Add @nuxt/ui dependency

### Task 2: Fix Navigation Menu
**Steps:**
1. Check if NavigationMenu is imported in app.vue
2. Verify route detection in NavigationMenu
3. Fix active route highlighting
4. Test on all pages (dashboard, settings, control, analytics)

**Files:**
- `app/app.vue` - Add NavigationMenu component
- `app/components/Navigation/PageMenu.vue` - Menu component

### Task 3: Wire Hover Tooltips
**Steps:**
1. Import InfoTooltip component in MetricCard
2. Add tooltip text for each metric
3. Style tooltip positioning
4. Test hover on all cards

**Files:**
- `app/components/DashboardCards/MetricCard.vue` - Add tooltip wrapper
- `app/components/Tooltips/InfoTooltip.vue` - Use existing component

### Task 4: Fix Data Refresh & Stability
**Steps:**
1. Check API endpoints for caching
2. Verify data scraping logic
3. Add timestamp validation
4. Ensure prices are realistic (non-zero)
5. Test refresh stability (10+ clicks = same results if market unchanged)

**Files:**
- `server/api/prices/*.ts` - All price endpoints
- `server/api/battery/*.ts` - Battery endpoints
- `stores/pricesStore.ts` - Store logic
- `data/prices/` - Test data

### Task 5: Add Documentation to Dashboard
**Steps:**
1. Create info cards with methodology explanations
2. Add "How it works" modal or expandable section
3. Show last update timestamp
4. Add data source and accuracy info
5. Explain buy/sell zone calculations

**Files to create/modify:**
- `app/components/Documentation/MethodologyCard.vue` - NEW
- `app/components/Documentation/DataSourceInfo.vue` - NEW
- `app/pages/index.vue` - Add documentation section

---

## Testing Checklist (After Each Fix)

- [ ] Navigation menu shows on all pages
- [ ] Hover tooltips appear on metric cards
- [ ] Refresh button clicks 10x - data stable if market unchanged
- [ ] All prices are non-zero and realistic
- [ ] Current price makes sense (between off-peak and peak)
- [ ] Documentation clearly explains forecasting method
- [ ] Buy/Sell zones explained with calculation
- [ ] Last update timestamp visible
- [ ] Data sources cited
- [ ] @nuxt/ui components rendering
- [ ] No console errors
- [ ] Responsive on mobile
- [ ] Dark theme consistent

---

## Success Criteria

✅ All 5 issues fixed  
✅ Documentation added and clear  
✅ @nuxt/ui integrated properly  
✅ No console errors  
✅ Data refresh stable (same results for same market state)  
✅ All interactive features working (tooltips, navigation, export, refresh, zoom)  
✅ Ready to merge back to feature/v2-software-defined-assets  

---

## Estimated Timeline

| Task | Est. Time | Priority |
|------|-----------|----------|
| Fix navigation menu | 15 min | HIGH |
| Wire tooltips | 20 min | MEDIUM |
| Fix data refresh | 45 min | CRITICAL |
| Add documentation | 30 min | MEDIUM |
| Setup @nuxt/ui | 30 min | MEDIUM |
| Testing | 20 min | HIGH |
| **Total** | **2.5 hours** | - |

---

**Start:** Ready to begin  
**Branch:** `feature/nuxt-ui-enhancements-and-fixes`  
**Will merge to:** `feature/v2-software-defined-assets`

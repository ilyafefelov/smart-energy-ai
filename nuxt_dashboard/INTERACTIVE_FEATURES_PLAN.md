# Interactive Chart Implementation Plan

## Issues to Fix

1. **Zoom/Pan not working** - Buttons click but chart doesn't transform
2. **"Good buying/selling time" not visible** - Legend shows but zones not highlighted
3. **Hover tooltips missing** - No hover effects showing price details
4. **Export/Show 24h buttons not functional** - Button clicks not handled
5. **Card hover effects missing** - No hover styling on metric cards

## Solution Strategy

### 1. Chart Interactivity (Price Forecast)
- Add zoom transform to SVG
- Add pan transform to SVG
- Highlight buying zones (green) when price < avg * 0.85
- Highlight selling zones (red) when price > avg * 1.15
- Add hover tooltip showing hour + price

### 2. Hover Effects & Tooltips
- Add card hover styles (scale + shadow)
- Show tooltip on hover with:
  - Metric name + definition
  - Current value
  - Trend information
  - Formula or calculation method

### 3. Button Actions
- Price History: "Show 24 hours" → Scroll to full table
- Savings: "Export" → Download CSV
- All buttons should have hover states and feedback

### 4. Consider Nuxt 4 Upgrade
- Current: Nuxt 3.10.0 + @nuxt/ui 4.4.0 (mismatch!)
- Target: Nuxt 4.x + @nuxt/ui 4.4.0 (compatible)
- Benefits: Better hydration, component support, TypeScript

## Implementation Priority

1. **HIGH** - Chart interactive features (zoom, pan, zones)
2. **HIGH** - Card hover effects + tooltips
3. **MEDIUM** - Button actions (export, show 24h)
4. **MEDIUM** - Nuxt 4 upgrade

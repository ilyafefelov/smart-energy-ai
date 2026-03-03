<template>
  <div class="min-h-screen bg-slate-950 text-white p-8">
    <div class="max-w-7xl mx-auto space-y-8">
      <!-- Header -->
      <div class="flex justify-between items-start">
        <div>
          <h1 class="text-4xl font-bold text-energy-400 mb-2">⚡ Energy Dashboard</h1>
          <p class="text-slate-400">Real-time AI-powered battery optimization</p>
        </div>
        <div class="text-right">
          <select
            v-model="selectedTenantId"
            class="mb-2 px-3 py-2 rounded-md border border-slate-700 bg-slate-900 text-sm"
          >
            <option v-for="tenant in tenantOptions" :key="tenant.id" :value="tenant.id">
              {{ tenant.name || tenant.id }}
            </option>
          </select>
          <p class="text-sm text-slate-400">{{ currentDate }}</p>
          <p class="text-energy-400 font-semibold">{{ liveStatus }}</p>
        </div>
      </div>

      <!-- Error handling -->
      <div v-if="metricsStore.error" class="bg-red-900 bg-opacity-30 border border-red-700 rounded-lg p-4">
        <p class="text-red-300 font-semibold">⚠️ {{ metricsStore.error }}</p>
        <button @click="metricsStore.clearError" class="text-xs text-red-400 hover:text-red-300 mt-2">Dismiss</button>
      </div>

      <!-- Key Metrics Grid (4 cols) -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <!-- Daily Savings Card -->
        <MetricCard
          label="Daily Savings"
          :value="metricsStore.savingsToday.value"
          icon="💰"
          :color="metricsStore.savingsToday.color as any"
          :trend="metricsStore.savingsToday.trend as any"
          :trendValue="metricsStore.savingsToday.trendValue"
          :tooltipInfo="metricsStore.getTooltip('savingsToday')"
        />

        <!-- Current Price Card -->
        <MetricCard
          label="Current Price"
          :value="pricesStore.currentPriceFormatted"
          icon="📊"
          :color="pricesStore.priceStatus.color as any"
          :tooltipInfo="metricsStore.getTooltip('currentPrice')"
        />

        <!-- Battery SOC Card -->
        <MetricCard
          label="Battery SOC"
          :value="batteryStore.socPercentage"
          icon="🔋"
          color="yellow"
          :description="`${batteryStore.power.toFixed(2)} kW • ${batteryStore.temperature.toFixed(1)}°C`"
          :tooltipInfo="metricsStore.getTooltip('batteryHealth')"
        >
          <div class="mt-4">
            <div class="w-full bg-slate-700 rounded-full h-2">
              <div 
                class="h-full bg-gradient-to-r from-green-500 to-yellow-500 rounded-full transition-all"
                :style="{ width: batteryStore.soc + '%' }"
              ></div>
            </div>
            <p class="text-xs text-slate-400 mt-2">{{ batteryStore.capacity }} kWh capacity</p>
          </div>
        </MetricCard>

        <!-- Forecast Accuracy Card -->
        <MetricCard
          label="Forecast Accuracy"
          :value="metricsStore.accuracy.value"
          icon="🎯"
          color="blue"
          :tooltipInfo="metricsStore.getTooltip('forecastAccuracy')"
        />
      </div>

      <!-- Documentation / Methodology -->
      <MethodologyCard />

      <!-- ML Recommendations Section -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- AI Recommendation Card -->
        <MLRecommendationCard />
        
        <!-- 24-Hour Forecast Chart -->
        <MLForecastChart />
      </div>

      <!-- Secondary Metrics Grid (3 cols) -->
      <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
        <MetricCard
          label="Peak Price Today"
          :value="pricesStore.peakPrice.toFixed(2) + ' ₴/kWh'"
          icon="📈"
          color="red"
          :tooltipInfo="metricsStore.getTooltip('peakPrice')"
        />

        <MetricCard
          label="Off-Peak Price"
          :value="pricesStore.offPeakPrice.toFixed(2) + ' ₴/kWh'"
          icon="📉"
          color="green"
          :tooltipInfo="metricsStore.getTooltip('offPeakPrice')"
        />

        <MetricCard
          label="Next Cycle In"
          :value="metricsStore.metrics.nextCycleIn.value"
          icon="⏱️"
          color="purple"
          :tooltipInfo="metricsStore.getTooltip('nextCycleIn')"
        />
      </div>

      <!-- Battery Control Section -->
      <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
        <div class="flex items-center justify-between mb-6">
          <div>
            <h2 class="text-2xl font-bold text-white mb-2">🔋 Battery Control System</h2>
            <p class="text-sm text-slate-400">Real-time battery physics simulation and control</p>
          </div>
          <NuxtLink 
            to="/settings?tab=control" 
            class="px-4 py-2 bg-energy-400 hover:bg-cyan-300 text-slate-950 font-semibold rounded-lg transition"
          >
            ⚙️ Full Control
          </NuxtLink>
        </div>

        <!-- Compact Battery Status -->
        <div class="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-5 gap-4 mb-6">
          <!-- SOC -->
          <div class="bg-slate-900 bg-opacity-50 rounded-lg p-4 text-center">
            <div class="text-2xl font-bold mb-2" :class="batteryPhysicsStore.socColor">
              {{ batteryPhysicsStore.state.socPercentage.toFixed(1) }}%
            </div>
            <div class="text-sm text-slate-400">State of Charge</div>
          </div>

          <!-- Power -->
          <div class="bg-slate-900 bg-opacity-50 rounded-lg p-4 text-center">
            <div class="text-2xl font-bold mb-2" :class="getPowerColor(batteryPhysicsStore.state.power)">
              {{ batteryPhysicsStore.state.power.toFixed(1) }} kW
            </div>
            <div class="text-sm text-slate-400">
              {{ batteryPhysicsStore.state.power > 0 ? 'Charging' : batteryPhysicsStore.state.power < 0 ? 'Discharging' : 'Idle' }}
            </div>
          </div>

          <!-- Health -->
          <div class="bg-slate-900 bg-opacity-50 rounded-lg p-4 text-center">
            <div class="text-2xl font-bold mb-2" :class="batteryPhysicsStore.healthStatus.color">
              {{ batteryPhysicsStore.state.health }}%
            </div>
            <div class="text-sm text-slate-400">Battery Health</div>
          </div>

          <!-- Temperature -->
          <div class="bg-slate-900 bg-opacity-50 rounded-lg p-4 text-center">
            <div class="text-2xl font-bold mb-2" :class="getTemperatureColor(batteryPhysicsStore.state.temperature)">
              {{ batteryPhysicsStore.state.temperature.toFixed(1) }}°C
            </div>
            <div class="text-sm text-slate-400">Temperature</div>
          </div>

          <!-- Status -->
          <div class="bg-slate-900 bg-opacity-50 rounded-lg p-4 text-center">
            <div class="text-2xl mb-2">{{ batteryPhysicsStore.powerStatus.icon }}</div>
            <div class="text-sm font-semibold" :class="batteryPhysicsStore.powerStatus.color">
              {{ batteryPhysicsStore.powerStatus.text }}
            </div>
          </div>
        </div>

        <!-- Quick Control Buttons -->
        <div class="grid grid-cols-2 md:grid-cols-5 gap-3">
          <button 
            @click="quickCharge"
            :disabled="!batteryPhysicsStore.canCharge"
            class="px-4 py-2 bg-green-600 hover:bg-green-500 text-white font-semibold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            ⚡ Quick Charge
          </button>
          
          <button 
            @click="quickDischarge"
            :disabled="!batteryPhysicsStore.canDischarge"
            class="px-4 py-2 bg-orange-600 hover:bg-orange-500 text-white font-semibold rounded-lg transition disabled:opacity-50 disabled:cursor-not-allowed"
          >
            🔋 Quick Discharge
          </button>
          
          <button 
            @click="stopPower"
            class="px-4 py-2 bg-slate-600 hover:bg-slate-500 text-white font-semibold rounded-lg transition"
          >
            ⏸️ Stop
          </button>
          
          <button 
            @click="autoOptimize"
            class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-semibold rounded-lg transition"
          >
            🤖 Auto Mode
          </button>
          
          <button 
            @click="emergencyStop"
            class="px-4 py-2 bg-red-600 hover:bg-red-500 text-white font-semibold rounded-lg transition"
          >
            🛑 Emergency Stop
          </button>
        </div>
      </div>

      <!-- Price Forecast Chart (Interactive) -->
      <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
        <div class="flex justify-between items-start mb-4">
          <div>
            <h2 class="text-xl font-bold text-white mb-1">24h Price Forecast</h2>
            <p class="text-sm text-slate-400">
              <span v-if="hoverPrice">{{ hoverPrice.hour }}:00 → {{ hoverPrice.price.toFixed(2) }}₴/kWh</span>
              <span v-else>Hover for details • Zoom: {{ chartZoom.toFixed(1) }}x</span>
            </p>
          </div>
          <div class="flex gap-2">
            <button 
              @click="refreshChartData" 
              class="px-3 py-1 text-xs bg-slate-700 hover:bg-energy-400 hover:text-slate-900 rounded transition font-semibold disabled:opacity-50 disabled:cursor-not-allowed"
              :disabled="isRefreshingChart"
            >
              {{ isRefreshingChart ? '⏳ Loading...' : '🔄 Refresh' }}
            </button>
            <button 
              @click="zoomChart" 
              class="px-3 py-1 text-xs bg-slate-700 hover:bg-energy-400 hover:text-slate-900 rounded transition font-semibold"
              :disabled="chartZoom >= 3"
              :class="{ 'opacity-50 cursor-not-allowed': chartZoom >= 3 }"
            >
              🔍+ Zoom
            </button>
            <button 
              @click="panChart" 
              class="px-3 py-1 text-xs bg-slate-700 hover:bg-energy-400 hover:text-slate-900 rounded transition font-semibold"
              :disabled="chartPanX <= -600"
              :class="{ 'opacity-50 cursor-not-allowed': chartPanX <= -600 }"
            >
              ◀ Pan
            </button>
            <button 
              @click="resetChart" 
              class="px-3 py-1 text-xs bg-slate-700 hover:bg-energy-400 hover:text-slate-900 rounded transition font-semibold"
              v-show="chartZoom > 1 || chartPanX < 0"
            >
              ↺ Reset
            </button>
          </div>
        </div>

        <!-- Simple SVG Chart -->
        <div v-if="pricesStore.forecast.length > 0" class="relative overflow-hidden">
          <div class="overflow-x-auto">
            <svg 
              viewBox="0 0 1200 400" 
              class="w-full h-64 mb-4 transition-transform"
              :style="{ 
                transform: `scale(${chartZoom}) translateX(${chartPanX}px)`,
                transformOrigin: 'top left',
                minWidth: `${(chartZoom - 1) * 100}%`
              }"
              @mousemove="onChartHover"
              @mouseleave="onChartLeave"
            >
              <!-- Good buying zones (light green background) -->
              <g v-for="(f, i) in pricesStore.forecast" :key="`buy-${i}`">
                <rect
                  v-if="f.price < (pricesStore.todayAvg * 0.85)"
                  :x="(i / pricesStore.forecast.length) * 1200 - 15"
                  y="0"
                  width="30"
                  height="400"
                  fill="#22c55e"
                  opacity="0.15"
                />
              </g>

              <!-- Good selling zones (light red background) -->
              <g v-for="(f, i) in pricesStore.forecast" :key="`sell-${i}`">
                <rect
                  v-if="f.price > (pricesStore.todayAvg * 1.15)"
                  :x="(i / pricesStore.forecast.length) * 1200 - 15"
                  y="0"
                  width="30"
                  height="400"
                  fill="#ef4444"
                  opacity="0.15"
                />
              </g>

              <!-- Grid lines -->
              <line x1="0" y1="50" x2="1200" y2="50" stroke="#475569" stroke-width="1" stroke-dasharray="4" />
              <line x1="0" y1="150" x2="1200" y2="150" stroke="#475569" stroke-width="1" stroke-dasharray="4" />
              <line x1="0" y1="250" x2="1200" y2="250" stroke="#475569" stroke-width="1" stroke-dasharray="4" />
              <line x1="0" y1="350" x2="1200" y2="350" stroke="#475569" stroke-width="1" stroke-dasharray="4" />

              <!-- Price line chart -->
              <polyline
                :points="chartPoints"
                fill="none"
                stroke="#22d3ee"
                stroke-width="3"
                stroke-linecap="round"
                stroke-linejoin="round"
              />

              <!-- Fill under line -->
              <polygon
                :points="`0,350 ${chartPoints} 1200,350`"
                fill="url(#priceGradient)"
                opacity="0.3"
              />

              <!-- Gradient definition -->
              <defs>
                <linearGradient id="priceGradient" x1="0%" y1="0%" x2="0%" y2="100%">
                  <stop offset="0%" style="stop-color: #22d3ee; stop-opacity: 0.5" />
                  <stop offset="100%" style="stop-color: #22d3ee; stop-opacity: 0" />
                </linearGradient>
              </defs>

              <!-- Axis labels -->
              <text x="10" y="25" font-size="12" fill="#94a3b8">{{ pricesStore.peakPrice.toFixed(1) }}₴</text>
              <text x="10" y="375" font-size="12" fill="#94a3b8">{{ pricesStore.offPeakPrice.toFixed(1) }}₴</text>
            </svg>
          </div>

          <!-- Legend -->
          <div class="flex justify-center gap-6 text-sm">
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 bg-cyan-400 rounded-full"></div>
              <span class="text-slate-300">Price forecast</span>
            </div>
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 bg-green-500 rounded-full"></div>
              <span class="text-slate-300">Good buying time (< 85% avg)</span>
            </div>
            <div class="flex items-center gap-2">
              <div class="w-3 h-3 bg-red-500 rounded-full"></div>
              <span class="text-slate-300">Good selling time (> 115% avg)</span>
            </div>
          </div>
        </div>

        <!-- Loading state -->
        <div v-else class="flex items-center justify-center h-64">
          <p class="text-slate-400">Loading forecast...</p>
        </div>
      </div>

      <!-- Arbitrage Opportunities -->
      <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
        <h2 class="text-xl font-bold text-white mb-4">💡 Arbitrage Opportunities</h2>
        
        <div v-if="pricesStore.arbitrageOpportunity" class="grid grid-cols-1 md:grid-cols-3 gap-4">
          <div class="bg-slate-900 rounded-lg p-4">
            <p class="text-sm text-slate-400 mb-1">Price Spread</p>
            <p class="text-2xl font-bold text-energy-400">{{ pricesStore.arbitrageOpportunity.spread.toFixed(2) }} ₴</p>
            <p class="text-xs text-slate-400 mt-1">{{ pricesStore.arbitrageOpportunity.spreadPercent }}% variance</p>
          </div>

          <div class="bg-slate-900 rounded-lg p-4">
            <p class="text-sm text-slate-400 mb-1">Opportunity Status</p>
            <p v-if="pricesStore.arbitrageOpportunity.opportunity" class="text-xl font-bold text-green-400">✓ Profitable</p>
            <p v-else class="text-xl font-bold text-yellow-400">⚠ Limited</p>
            <p class="text-xs text-slate-400 mt-1">Minimum 2₴ spread required</p>
          </div>

          <div class="bg-slate-900 rounded-lg p-4">
            <p class="text-sm text-slate-400 mb-1">Recommended Action</p>
            <p v-if="pricesStore.arbitrageOpportunity.opportunity" class="text-lg font-bold text-energy-400">Buy Low → Sell High</p>
            <p v-else class="text-lg font-bold text-slate-400">Hold</p>
            <p class="text-xs text-slate-400 mt-1">Based on forecast</p>
          </div>
        </div>
      </div>

      <!-- Battery Trajectory Simulation -->
      <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
        <h2 class="text-xl font-bold text-white mb-4">🔋 Battery Trajectory (Next 24h)</h2>
        <p class="text-sm text-slate-400 mb-4">Projected SOC trajectory derived from live prices and current battery limits</p>

        <svg viewBox="0 0 1200 300" class="w-full h-48 mb-4">
          <!-- Grid -->
          <line x1="0" y1="50" x2="1200" y2="50" stroke="#475569" stroke-width="1" stroke-dasharray="4" />
          <line x1="0" y1="150" x2="1200" y2="150" stroke="#475569" stroke-width="1" stroke-dasharray="4" />
          <line x1="0" y1="250" x2="1200" y2="250" stroke="#475569" stroke-width="1" stroke-dasharray="4" />

          <!-- Data-driven trajectory -->
          <polyline
            :points="batteryTrajectoryPoints"
            fill="none"
            stroke="#fbbf24"
            stroke-width="3"
            stroke-linecap="round"
            stroke-linejoin="round"
          />

          <!-- Min/Max bounds -->
          <line :x1="0" :y1="batteryUpperBoundY" :x2="1200" :y2="batteryUpperBoundY" stroke="#ef4444" stroke-width="2" stroke-dasharray="8" opacity="0.5" />
          <line :x1="0" :y1="batteryLowerBoundY" :x2="1200" :y2="batteryLowerBoundY" stroke="#22c55e" stroke-width="2" stroke-dasharray="8" opacity="0.5" />

          <!-- Labels -->
          <text x="10" :y="Math.max(16, batteryUpperBoundY - 6)" font-size="12" fill="#ef4444">Max (100%)</text>
          <text x="10" :y="Math.min(296, batteryLowerBoundY + 18)" font-size="12" fill="#22c55e">Min ({{ batteryStore.minSOC }}%)</text>
        </svg>

        <p class="text-xs text-slate-400">Hover to see predicted SOC at specific hour • Drag to adjust forecast</p>
      </div>

      <!-- Price History Table -->
      <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6" id="price-history-table">
        <div class="flex justify-between items-center mb-4">
          <div>
            <h2 class="text-xl font-bold text-white">📊 Price History (Today)</h2>
            <p class="text-sm text-slate-400 mt-1">24-hour pricing data with peak/off-peak classification</p>
          </div>
          <div class="flex gap-2">
            <button @click="exportPriceData" class="px-3 py-1 text-xs bg-slate-700 hover:bg-energy-400 hover:text-slate-900 rounded transition font-semibold cursor-pointer">📥 Export</button>
            <button @click="refreshPriceData" class="px-3 py-1 text-xs bg-slate-700 hover:bg-energy-400 hover:text-slate-900 rounded transition font-semibold cursor-pointer">🔄 Refresh</button>
          </div>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-700">
                <th class="text-left py-3 px-4 text-slate-400 font-semibold">Hour</th>
                <th class="text-right py-3 px-4 text-slate-400 font-semibold">Price (₴/kWh)</th>
                <th class="text-left py-3 px-4 text-slate-400 font-semibold">Status</th>
                <th class="text-right py-3 px-4 text-slate-400 font-semibold">vs Avg</th>
                <th class="text-center py-3 px-4 text-slate-400 font-semibold">Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(price, idx) in pricesStore.forecast.slice(0, 8)" :key="idx" class="border-b border-slate-800 hover:bg-slate-900 bg-opacity-30 transition">
                <td class="py-3 px-4 text-white font-medium">{{ (new Date().getHours() + idx) % 24 }}:00</td>
                <td class="text-right py-3 px-4">
                  <span class="font-bold text-cyan-400">{{ price.price.toFixed(2) }}</span>
                </td>
                <td class="py-3 px-4">
                  <span v-if="price.price > (pricesStore.todayAvg * 1.15)" class="px-2 py-1 bg-red-900 bg-opacity-40 text-red-300 rounded text-xs">📈 Peak</span>
                  <span v-else-if="price.price < (pricesStore.todayAvg * 0.85)" class="px-2 py-1 bg-green-900 bg-opacity-40 text-green-300 rounded text-xs">📉 Off-Peak</span>
                  <span v-else class="px-2 py-1 bg-yellow-900 bg-opacity-40 text-yellow-300 rounded text-xs">➡️ Normal</span>
                </td>
                <td class="text-right py-3 px-4" :class="price.price > pricesStore.todayAvg ? 'text-red-400' : 'text-green-400'">
                  {{ ((price.price - pricesStore.todayAvg) / pricesStore.todayAvg * 100).toFixed(0) }}%
                </td>
                <td class="text-center py-3 px-4">
                  <span v-if="price.price < (pricesStore.todayAvg * 0.85)" class="text-lg">💰 Buy</span>
                  <span v-else-if="price.price > (pricesStore.todayAvg * 1.15)" class="text-lg">⚡ Sell</span>
                  <span v-else class="text-lg">—</span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>

        <p class="text-xs text-slate-400 mt-4">Showing first 8 hours • <button @click="scrollToPriceTable" class="text-energy-400 hover:text-cyan-300 cursor-pointer transition">View all 24 hours</button></p>
      </div>

      <!-- Daily Savings Trend -->
      <div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <!-- Savings Breakdown -->
        <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
          <div class="flex justify-between items-center mb-4">
            <h2 class="text-xl font-bold text-white">💰 Daily Savings Breakdown</h2>
            <button @click="exportSavingsData" class="px-3 py-1 text-xs bg-slate-700 hover:bg-energy-400 hover:text-slate-900 rounded transition font-semibold cursor-pointer">📥 Export</button>
          </div>
          
          <div class="space-y-3">
            <div v-for="entry in savingsBreakdownRows" :key="entry.key">
              <div class="flex justify-between items-center mb-2">
                <span class="text-sm text-slate-300">{{ entry.label }}</span>
                <span class="font-bold" :class="entry.textColor">₴ {{ Math.round(entry.value).toLocaleString() }}</span>
              </div>
              <div class="w-full bg-slate-700 rounded-full h-2">
                <div class="h-full rounded-full" :class="entry.barColor" :style="{ width: `${entry.percent}%` }"></div>
              </div>
            </div>

            <div class="pt-4 mt-4 border-t border-slate-700">
              <div class="flex justify-between items-center">
                <span class="font-bold text-white">Total Daily Savings</span>
                <span class="text-2xl font-bold text-energy-400">₴ {{ Math.round(totalDailySavings).toLocaleString() }}</span>
              </div>
            </div>
          </div>
        </div>

        <!-- Weekly Trend -->
        <div class="bg-slate-800 bg-opacity-40 border border-slate-700 rounded-lg p-6">
          <h2 class="text-xl font-bold text-white mb-4">📈 7-Day Savings Trend</h2>
          
          <svg viewBox="0 0 600 250" class="w-full h-full">
            <!-- Grid -->
            <line x1="0" y1="50" x2="600" y2="50" stroke="#475569" stroke-width="1" stroke-dasharray="4" />
            <line x1="0" y1="100" x2="600" y2="100" stroke="#475569" stroke-width="1" stroke-dasharray="4" />
            <line x1="0" y1="150" x2="600" y2="150" stroke="#475569" stroke-width="1" stroke-dasharray="4" />
            <line x1="0" y1="200" x2="600" y2="200" stroke="#475569" stroke-width="1" stroke-dasharray="4" />

            <!-- Bar chart for 7 days -->
            <g v-for="point in weeklySavingsSeries" :key="point.label">
              <rect 
                :x="point.x"
                :y="point.y"
                width="60"
                :height="point.height"
                fill="#10b981"
                opacity="0.7"
              />
              <text :x="point.x + 30" y="230" font-size="11" fill="#94a3b8" text-anchor="middle">
                {{ point.label }}
              </text>
            </g>

            <!-- Y-axis labels -->
            <text x="545" y="55" font-size="11" fill="#94a3b8">₴{{ Math.round(weeklyPeakDay.value).toLocaleString() }}</text>
            <text x="545" y="155" font-size="11" fill="#94a3b8">₴{{ Math.round(weeklyPeakDay.value / 2).toLocaleString() }}</text>
            <text x="575" y="205" font-size="11" fill="#94a3b8">₴0</text>
          </svg>

          <p class="text-xs text-slate-400 mt-4">
            Average: <span class="text-green-400 font-bold">₴ {{ Math.round(weeklyAverageSavings).toLocaleString() }}/day</span>
            • Peak: <span class="text-green-400 font-bold">₴ {{ Math.round(weeklyPeakDay.value).toLocaleString() }} ({{ weeklyPeakDay.label }})</span>
          </p>
        </div>
      </div>

      <!-- Active Retraining Section -->
      <div v-if="retrainingStore.isRunning" class="bg-yellow-900 bg-opacity-30 border border-yellow-700 rounded-lg p-6">
        <div class="flex items-center gap-3 mb-4">
          <div class="animate-spin text-2xl">⚙️</div>
          <div>
            <h2 class="text-xl font-bold text-yellow-300">Model Retraining in Progress</h2>
            <p class="text-sm text-yellow-200">{{ retrainingStore.job.message }}</p>
          </div>
        </div>

        <div class="w-full bg-slate-800 rounded-full h-3 mb-2">
          <div 
            class="h-full bg-gradient-to-r from-yellow-500 to-orange-500 rounded-full transition-all"
            :style="{ width: retrainingStore.progressPercent + '%' }"
          ></div>
        </div>

        <div class="flex justify-between text-sm text-yellow-300">
          <span>{{ retrainingStore.progressPercentFormatted }}</span>
          <span>{{ retrainingStore.timeRemaining }}</span>
        </div>

        <button 
          @click="cancelRetraining"
          class="mt-4 px-4 py-2 bg-red-600 hover:bg-red-500 rounded-lg text-sm font-semibold transition"
        >
          ✕ Cancel Retraining
        </button>
      </div>

      <!-- Retraining Complete Alert -->
      <div v-if="retrainingStore.isCompleted" class="bg-green-900 bg-opacity-30 border border-green-700 rounded-lg p-6">
        <h2 class="text-xl font-bold text-green-300 mb-2">✅ Model Retraining Complete!</h2>
        <p class="text-green-200 mb-4">Your personal PPO model has been optimized and is now active.</p>

        <div v-if="retrainingStore.job.metricsImprovement" class="grid grid-cols-3 gap-4 mb-4">
          <div class="bg-slate-800 rounded-lg p-3">
            <p class="text-xs text-slate-400">Previous Accuracy</p>
            <p class="text-lg font-bold text-green-400">{{ retrainingStore.job.metricsImprovement.previousAccuracy }}%</p>
          </div>
          <div class="bg-slate-800 rounded-lg p-3">
            <p class="text-xs text-slate-400">New Accuracy</p>
            <p class="text-lg font-bold text-green-300">{{ retrainingStore.job.metricsImprovement.newAccuracy }}%</p>
          </div>
          <div class="bg-slate-800 rounded-lg p-3">
            <p class="text-xs text-slate-400">Improvement</p>
            <p class="text-lg font-bold text-cyan-400">+{{ retrainingStore.job.metricsImprovement.improvementPercent }}%</p>
          </div>
        </div>

        <button 
          @click="dismissRetrainingComplete"
          class="px-4 py-2 bg-slate-700 hover:bg-slate-600 rounded-lg text-sm font-semibold transition"
        >
          Dismiss
        </button>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, watch } from 'vue'
import { useMetricsStore } from '~/stores/metricsStore'
import { useBatteryStore } from '~/stores/batteryStore'
import { usePricesStore } from '~/stores/pricesStore'
import { useRetrainingStore } from '~/stores/retrainingStore'
import { useSettingsStore } from '~/stores/settingsStore'
import { useMLStore } from '~/stores/mlStore'
import { useBatteryPhysicsStore } from '~/stores/batteryPhysicsStore'
import { useTenantContext } from '~/composables/useTenantContext'
import MetricCard from '~/components/DashboardCards/MetricCard.vue'
import MethodologyCard from '~/components/Documentation/MethodologyCard.vue'
import MLRecommendationCard from '~/components/ML/RecommendationCard.vue'
import MLForecastChart from '~/components/ML/ForecastChart.vue'

const metricsStore = useMetricsStore()
const batteryStore = useBatteryStore()
const batteryPhysicsStore = useBatteryPhysicsStore()
const pricesStore = usePricesStore()
const retrainingStore = useRetrainingStore()
const settingsStore = useSettingsStore()
const mlStore = useMLStore()
const tenantContext = useTenantContext()

const tenantOptions = computed(() => tenantContext.tenants.value)
const selectedTenantId = computed({
  get: () => tenantContext.currentTenantId.value,
  set: (tenantId: string) => tenantContext.setTenant(tenantId),
})

const showRetrainingComplete = ref(false)
const chartZoom = ref(1)
const chartPanX = ref(0)
const hoverPrice = ref<{ hour: number; price: number } | null>(null)
const isRefreshingChart = ref(false)

// Chart interactivity
const zoomChart = () => {
  chartZoom.value = Math.min(chartZoom.value + 0.5, 3)
}

const panChart = () => {
  chartPanX.value = Math.max(chartPanX.value - 100, -600)
}

const resetChart = () => {
  chartZoom.value = 1
  chartPanX.value = 0
}

// Hover tooltip
const onChartHover = (event: MouseEvent) => {
  const svg = event.currentTarget as SVGElement
  const rect = svg.getBoundingClientRect()
  const x = event.clientX - rect.left

  // Calculate which hour is being hovered
  const dataPoints = pricesStore.forecast.length
  const pointWidth = 1200 / dataPoints
  const hoverIndex = Math.floor(x / pointWidth)

  if (hoverIndex >= 0 && hoverIndex < dataPoints) {
    hoverPrice.value = {
      hour: (new Date().getHours() + hoverIndex) % 24,
      price: pricesStore.forecast[hoverIndex].price
    }
  }
}

const onChartLeave = () => {
  hoverPrice.value = null
}

const currentDate = computed(() => {
  return new Date().toLocaleDateString('en-US', {
    year: 'numeric',
    month: 'short',
    day: 'numeric'
  })
})

const liveStatus = computed(() => {
  const trainingStatus = metricsStore.rawMetrics?.trainingStatus
  if (trainingStatus === 'running') return 'RETRAINING IN PROGRESS'
  return new Date().getHours() >= 8 && new Date().getHours() < 20 ? 'TRADING HOURS' : 'OFF-PEAK'
})

const parseCurrencyValue = (value: string | number): number => {
  if (typeof value === 'number') {
    return Number.isFinite(value) ? value : 0
  }

  const normalized = value.replace(/[^0-9.,-]/g, '').replace(/,/g, '')
  const parsed = Number(normalized)
  return Number.isFinite(parsed) ? parsed : 0
}

const weeklySavingsSeries = computed(() => {
  const labels = ['Sun', 'Mon', 'Tue', 'Wed', 'Thu', 'Fri', 'Sat']
  const base = parseCurrencyValue(metricsStore.savingsToday.value)
  const trend = metricsStore.savingsToday.trend || 'stable'

  const factorsByTrend: Record<string, number[]> = {
    up: [0.78, 0.84, 0.92, 1.0, 1.08, 1.14, 1.2],
    down: [1.2, 1.14, 1.08, 1.0, 0.92, 0.86, 0.8],
    stable: [0.94, 0.98, 1.01, 1.0, 1.03, 0.99, 1.02],
  }

  const factors = factorsByTrend[trend] || factorsByTrend.stable
  const values = factors.map((factor) => Number((base * factor).toFixed(2)))
  const maxValue = Math.max(...values, 1)

  return labels.map((label, idx) => {
    const value = values[idx] || 0
    const normalized = Math.max(0, Math.min(1, value / maxValue))
    const rawHeight = normalized * 150
    const height = value > 0 ? Math.max(rawHeight, 4) : 0

    return {
      label,
      value,
      x: idx * 85 + 10,
      y: 200 - height,
      height,
    }
  })
})

const weeklyAverageSavings = computed(() => {
  if (weeklySavingsSeries.value.length === 0) return 0
  const total = weeklySavingsSeries.value.reduce((sum, point) => sum + point.value, 0)
  return total / weeklySavingsSeries.value.length
})

const weeklyPeakDay = computed(() => {
  if (weeklySavingsSeries.value.length === 0) {
    return { label: '—', value: 0 }
  }

  return weeklySavingsSeries.value.reduce((peak, current) => {
    return current.value > peak.value ? current : peak
  }, weeklySavingsSeries.value[0])
})

const savingsBreakdownRows = computed(() => {
  const breakdown = metricsStore.rawMetrics?.savingsBreakdown || {}
  const arbitrage = Number(breakdown.arbitrage || 0)
  const peakAvoidance = Number(breakdown.peak_avoidance || 0)
  const efficiency = Number(breakdown.efficiency || 0)

  const fallbackTotal = parseCurrencyValue(metricsStore.savingsToday.value)
  const fallbackArbitrage = fallbackTotal * 0.6
  const fallbackPeakAvoidance = fallbackTotal * 0.25
  const fallbackEfficiency = fallbackTotal * 0.15

  const rows = [
    {
      key: 'arbitrage',
      label: 'Arbitrage Profit',
      value: arbitrage > 0 ? arbitrage : fallbackArbitrage,
      barColor: 'bg-green-500',
      textColor: 'text-green-400',
    },
    {
      key: 'peak_avoidance',
      label: 'Avoided Peak Charges',
      value: peakAvoidance > 0 ? peakAvoidance : fallbackPeakAvoidance,
      barColor: 'bg-blue-500',
      textColor: 'text-blue-400',
    },
    {
      key: 'efficiency',
      label: 'Efficiency Gains',
      value: efficiency > 0 ? efficiency : fallbackEfficiency,
      barColor: 'bg-purple-500',
      textColor: 'text-purple-400',
    },
  ]

  const total = rows.reduce((sum, row) => sum + row.value, 0)
  return rows.map((row) => ({
    ...row,
    percent: total > 0 ? Number(((row.value / total) * 100).toFixed(1)) : 0,
  }))
})

const totalDailySavings = computed(() => {
  return savingsBreakdownRows.value.reduce((sum, row) => sum + row.value, 0)
})

const projectTrajectory = computed(() => {
  const prices = pricesStore.forecast.slice(0, 24)
  if (prices.length === 0) {
    return [batteryStore.soc]
  }

  const avgPrice = prices.reduce((sum, row) => sum + row.price, 0) / prices.length
  const minSoc = batteryStore.minSOC
  const maxSoc = 100
  let soc = Number(batteryStore.soc)

  const trajectory = [soc]
  for (const row of prices) {
    if (row.price <= avgPrice * 0.9) {
      soc = Math.min(maxSoc, soc + 4)
    } else if (row.price >= avgPrice * 1.1) {
      soc = Math.max(minSoc, soc - 5)
    } else {
      soc = Math.max(minSoc, Math.min(maxSoc, soc - 0.5))
    }
    trajectory.push(Number(soc.toFixed(2)))
  }

  return trajectory
})

const mapSocToY = (socPercent: number) => {
  const clamped = Math.max(0, Math.min(100, socPercent))
  return 270 - ((clamped / 100) * 240)
}

const batteryTrajectoryPoints = computed(() => {
  const series = projectTrajectory.value
  const maxIndex = Math.max(1, series.length - 1)
  return series
    .map((soc, index) => {
      const x = (index / maxIndex) * 1200
      return `${x},${mapSocToY(soc)}`
    })
    .join(' ')
})

const batteryUpperBoundY = computed(() => mapSocToY(100))
const batteryLowerBoundY = computed(() => mapSocToY(batteryStore.minSOC))

// Chart points for price forecast
const chartPoints = computed(() => {
  if (pricesStore.forecast.length === 0) return ''

  const minPrice = Math.min(...pricesStore.forecast.map(f => f.price))
  const maxPrice = Math.max(...pricesStore.forecast.map(f => f.price))
  const range = maxPrice - minPrice || 1

  return pricesStore.forecast.map((f, i) => {
    const x = (i / pricesStore.forecast.length) * 1200
    const y = 350 - ((f.price - minPrice) / range) * 300
    return `${x},${y}`
  }).join(' ')
})

const cancelRetraining = async () => {
  await retrainingStore.cancelRetraining()
}

// Scroll to price history table
const scrollToPriceTable = () => {
  const element = document.getElementById('price-history-table')
  if (element) {
    element.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }
}

// CSV Export utility
const downloadCSV = (csvContent: string, filename: string) => {
  const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' })
  const link = document.createElement('a')
  const url = URL.createObjectURL(blob)
  
  link.setAttribute('href', url)
  link.setAttribute('download', filename)
  link.style.visibility = 'hidden'
  
  document.body.appendChild(link)
  link.click()
  document.body.removeChild(link)
  
  console.log(`✅ Downloaded: ${filename}`)
}

// Export Price History Data (last 8 hours)
const exportPriceData = () => {
  const now = new Date()
  const dateStr = now.toISOString().split('T')[0]
  const filename = `price-history-${dateStr}.csv`
  
  // Get the last 8 hours of price data
  const priceData = pricesStore.forecast.slice(0, 8)
  
  // Build CSV header
  let csv = 'Hour,Price(₴/kWh),Status,vs Average,Action\n'
  
  // Build CSV rows
  priceData.forEach((price, idx) => {
    const hour = (new Date().getHours() + idx) % 24
    const priceValue = price.price.toFixed(2)
    
    // Determine status
    let status = 'Normal'
    if (price.price > (pricesStore.todayAvg * 1.15)) {
      status = 'Peak'
    } else if (price.price < (pricesStore.todayAvg * 0.85)) {
      status = 'Off-Peak'
    }
    
    // Calculate vs Average percentage
    const vsAvg = ((price.price - pricesStore.todayAvg) / pricesStore.todayAvg * 100).toFixed(0)
    
    // Determine action
    let action = '-'
    if (price.price < (pricesStore.todayAvg * 0.85)) {
      action = 'Buy'
    } else if (price.price > (pricesStore.todayAvg * 1.15)) {
      action = 'Sell'
    }
    
    csv += `${hour}:00,${priceValue},${status},${vsAvg}%,${action}\n`
  })
  
  downloadCSV(csv, filename)
}

// Export Savings Breakdown Data
const exportSavingsData = () => {
  const now = new Date()
  const dateStr = now.toISOString().split('T')[0]
  const filename = `savings-breakdown-${dateStr}.csv`
  
  const rows = savingsBreakdownRows.value
  const arbitrage = rows.find((row) => row.key === 'arbitrage')?.value || 0
  const peakAvoidance = rows.find((row) => row.key === 'peak_avoidance')?.value || 0
  const efficiency = rows.find((row) => row.key === 'efficiency')?.value || 0
  const total = rows.reduce((sum, row) => sum + row.value, 0)
  
  // Build CSV header
  let csv = 'Category,Amount(₴),Percentage\n'
  
  // Build CSV rows
  const safeTotal = total > 0 ? total : 1
  csv += `Arbitrage Profit,${arbitrage},${((arbitrage / safeTotal) * 100).toFixed(1)}%\n`
  csv += `Avoided Peak Charges,${peakAvoidance},${((peakAvoidance / safeTotal) * 100).toFixed(1)}%\n`
  csv += `Efficiency Gains,${efficiency},${((efficiency / safeTotal) * 100).toFixed(1)}%\n`
  csv += `Total Daily Savings,${total},100%\n`
  
  downloadCSV(csv, filename)
}

const refreshPriceData = async () => {
  console.log('Refresh clicked - Price Data')
  await pricesStore.fetchPrices()
}


const refreshChartData = async () => {
  console.log('🔄 Refreshing price forecast chart...')
  isRefreshingChart.value = true

  try {
    await pricesStore.fetchPrices()
    console.log('✅ Price forecast updated successfully')
  } catch (e) {
    console.error('❌ Failed to refresh chart:', e)
  } finally {
    isRefreshingChart.value = false
  }
}


// Battery Physics Control Functions
const getPowerColor = (power: number) => {
  if (power > 0) return 'text-green-400'
  if (power < 0) return 'text-orange-400'
  return 'text-slate-400'
}

const getTemperatureColor = (temp: number) => {
  if (temp > 40) return 'text-red-400'
  if (temp > 30) return 'text-yellow-400'
  if (temp < 0) return 'text-blue-400'
  return 'text-green-400'
}

const quickCharge = () => {
  const chargePower = batteryPhysicsStore.state.maxChargePower * 0.8
  batteryPhysicsStore.charge(chargePower)
}

const quickDischarge = () => {
  const dischargePower = batteryPhysicsStore.state.maxDischargePower * 0.8
  batteryPhysicsStore.discharge(dischargePower)
}

const stopPower = () => {
  batteryPhysicsStore.idle()
}

const autoOptimize = () => {
  batteryPhysicsStore.startBalancedOperation()
}

const emergencyStop = () => {
  batteryPhysicsStore.idle()
  // In a real system, this would trigger additional safety protocols
}

onMounted(async () => {
  await tenantContext.loadTenants()

  // Load settings FIRST so battery capacity is available
  await settingsStore.loadSettings()
  
  // Then fetch all data in parallel
  await Promise.all([
    metricsStore.fetchMetrics(),
    batteryStore.fetchBatteryStatus(),
    pricesStore.fetchPrices()
  ])

  // Start real-time updates
  batteryStore.startRealTimeUpdates(5000)
  batteryPhysicsStore.startRealTimeUpdates(5000)
  pricesStore.startRealTimeUpdates(60000)
  metricsStore.startRealTimeUpdates(30000)
})

// Cleanup on unmount
onUnmounted(() => {
  batteryStore.stopRealTimeUpdates()
  batteryPhysicsStore.stopRealTimeUpdates()
  pricesStore.stopRealTimeUpdates()
  metricsStore.stopRealTimeUpdates()
})

watch(
  () => tenantContext.currentTenantId.value,
  async () => {
    await settingsStore.loadSettings()
    await Promise.all([
      metricsStore.fetchMetrics(),
      batteryStore.fetchBatteryStatus(),
      pricesStore.fetchPrices(),
      batteryPhysicsStore.fetchBatteryData(),
    ])
  },
)
</script>

<style scoped>
.animate-spin {
  animation: spin 1s linear infinite;
}

@keyframes spin {
  from {
    transform: rotate(0deg);
  }
  to {
    transform: rotate(360deg);
  }
}
</style>

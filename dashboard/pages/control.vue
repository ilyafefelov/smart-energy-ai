<template>
  <div class="min-h-screen bg-slate-950 text-white p-8">
    <div class="max-w-6xl mx-auto space-y-8">
      <!-- Header -->
      <div class="mb-8">
        <NuxtLink to="/" class="text-blue-400 hover:text-blue-300 text-sm mb-2 inline-block">
          ← Back to Dashboard
        </NuxtLink>
        <h1 class="text-4xl font-bold text-energy-400 mt-2">🔋 Control</h1>
        <p class="text-slate-400 mt-2">Real-time battery optimization & manual trading</p>
      </div>

      <!-- Real-Time Status Row -->
      <div class="grid grid-cols-1 md:grid-cols-4 gap-4">
        <!-- Current Price Gauge -->
        <div class="bg-slate-900 border border-slate-800 rounded-lg p-4 group relative">
          <p class="text-slate-400 text-sm mb-3">Current Price</p>
          <div class="text-center">
            <div class="relative w-32 h-32 mx-auto mb-3">
              <svg class="w-full h-full" viewBox="0 0 100 100">
                <!-- Background arc -->
                <circle cx="50" cy="50" r="40" fill="none" stroke="#334155" stroke-width="8" 
                        stroke-dasharray="251.3" stroke-dashoffset="0" transform="rotate(-90 50 50)" />
                <!-- Value arc (green to yellow to red) -->
                <circle cx="50" cy="50" r="40" fill="none" 
                        :stroke="priceColor" stroke-width="8"
                        :stroke-dasharray="priceDashArray"
                        stroke-dashoffset="0" transform="rotate(-90 50 50)" />
                <!-- Center circle -->
                <circle cx="50" cy="50" r="28" fill="#0f172a" />
                <!-- Price text -->
                <text x="50" y="48" text-anchor="middle" class="text-2xl font-bold" fill="#10b981">
                  {{ currentPrice.toFixed(2) }}
                </text>
                <text x="50" y="58" text-anchor="middle" class="text-xs" fill="#94a3b8">
                  ₴/kWh
                </text>
              </svg>
            </div>
            <p class="text-energy-400 font-semibold text-sm">{{ priceAction }}</p>
          </div>
          <!-- Hover tooltip -->
          <div class="hidden group-hover:block absolute top-0 right-0 bg-slate-950 border border-slate-700 rounded p-3 text-xs text-slate-400 w-56 z-10">
            <p class="font-semibold text-white mb-1">💰 Current Market Price</p>
            <p>Market price from OREE real-time data. Green &lt;9₴ is optimal for charging. Red &gt;13₴ is optimal for selling.</p>
          </div>
        </div>

        <!-- Battery SOC -->
        <div class="bg-slate-900 border border-slate-800 rounded-lg p-4 group relative">
          <p class="text-slate-400 text-sm mb-3">Battery SOC</p>
          <div class="text-center">
            <div class="text-4xl font-bold text-energy-400 mb-2">75%</div>
            <div class="w-full bg-slate-700 rounded-full h-3 mb-3">
              <div class="h-full bg-gradient-to-r from-green-500 via-yellow-500 to-red-500 rounded-full" 
                   style="width: 75%"></div>
            </div>
            <p class="text-slate-400 text-xs">112.5 / 150 kWh</p>
          </div>
          <!-- Hover tooltip -->
          <div class="hidden group-hover:block absolute top-0 right-0 bg-slate-950 border border-slate-700 rounded p-3 text-xs text-slate-400 w-56 z-10">
            <p class="font-semibold text-white mb-1">🔋 State of Charge</p>
            <p>Current battery charge level. Optimal range is 50-80%. Below 20% is unsafe for deep discharge.</p>
          </div>
        </div>

        <!-- Today's Cost -->
        <div class="bg-slate-900 border border-slate-800 rounded-lg p-4 group relative">
          <p class="text-slate-400 text-sm mb-3">Today's Cost</p>
          <div class="text-center">
            <div class="text-3xl font-bold text-red-400 mb-2">287₴</div>
            <p class="text-slate-400 text-xs mb-2">vs baseline 495₴</p>
            <p class="text-green-400 text-xs font-semibold">↓ 42% saved</p>
          </div>
          <!-- Hover tooltip -->
          <div class="hidden group-hover:block absolute top-0 right-0 bg-slate-950 border border-slate-700 rounded p-3 text-xs text-slate-400 w-56 z-10">
            <p class="font-semibold text-white mb-1">💵 Daily Cost Tracking</p>
            <p>Today's electricity cost vs. baseline (no optimization). Shows AI savings in real-time.</p>
          </div>
        </div>

        <!-- AI Status -->
        <div class="bg-slate-900 border border-slate-800 rounded-lg p-4 group relative">
          <p class="text-slate-400 text-sm mb-3">AI Optimization</p>
          <div class="text-center">
            <div class="inline-block">
              <span class="inline-flex items-center gap-2 px-3 py-1 bg-green-900 bg-opacity-30 border border-green-700 rounded-full">
                <span class="w-2 h-2 bg-green-400 rounded-full animate-pulse"></span>
                <span class="text-xs text-green-400 font-semibold">Active</span>
              </span>
            </div>
            <p class="text-slate-400 text-xs mt-3">Retraining in 5h 23m</p>
          </div>
          <!-- Hover tooltip -->
          <div class="hidden group-hover:block absolute top-0 right-0 bg-slate-950 border border-slate-700 rounded p-3 text-xs text-slate-400 w-56 z-10">
            <p class="font-semibold text-white mb-1">🤖 AI Status</p>
            <p>Personal PPO model actively optimizing battery operations. Weekly retraining scheduled.</p>
          </div>
        </div>
      </div>

      <!-- Manual Control Buttons -->
      <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h2 class="text-xl font-bold text-white mb-4">Manual Controls</h2>
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3">
          <!-- Charge Button -->
          <button @click="executeAction('charge')"
                  :disabled="batterySOC > 80"
                  class="px-4 py-3 bg-blue-600 hover:bg-blue-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-semibold rounded-lg transition text-sm">
            🔋 CHARGE NOW
          </button>

          <!-- Sell Button -->
          <button @click="executeAction('sell')"
                  :disabled="batterySOC < 30"
                  class="px-4 py-3 bg-green-600 hover:bg-green-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-semibold rounded-lg transition text-sm">
            ⚡ SELL TO GRID
          </button>

          <!-- Hold Button -->
          <button @click="executeAction('hold')"
                  class="px-4 py-3 bg-slate-700 hover:bg-slate-600 text-white font-semibold rounded-lg transition text-sm">
            ⏸️ HOLD
          </button>

          <!-- Discharge Button -->
          <button @click="executeAction('discharge')"
                  :disabled="batterySOC < 50 || currentPrice < 12"
                  class="px-4 py-3 bg-red-600 hover:bg-red-500 disabled:bg-slate-700 disabled:text-slate-500 text-white font-semibold rounded-lg transition text-sm">
            💨 DISCHARGE
          </button>
        </div>
        <p class="text-xs text-slate-500 mt-3">Note: Manual actions override AI optimization for the selected period</p>
      </div>

      <!-- Battery SOC Trajectory -->
      <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h2 class="text-xl font-bold text-white mb-4">Battery Trajectory (Next 48 Hours) - HOVER FOR DETAILS</h2>
        <div class="h-80 bg-slate-800 rounded-lg p-4 relative" @mouseleave="activeBatteryHour = null">
          <!-- SVG Chart -->
          <svg class="w-full h-full" viewBox="0 0 1000 300" preserveAspectRatio="xMidYMid meet">
            <!-- Grid background -->
            <defs>
              <pattern id="grid" width="100" height="30" patternUnits="userSpaceOnUse">
                <path d="M 100 0 L 0 0 0 30" fill="none" stroke="#334155" stroke-width="0.5" />
              </pattern>
            </defs>
            <rect width="1000" height="300" fill="url(#grid)" />

            <!-- Min safe zone (red, 0-20%) -->
            <rect x="50" y="220" width="900" height="60" fill="#dc26262e" />
            <text x="20" y="250" font-size="12" fill="#94a3b8">20%</text>

            <!-- Optimal zone (green, 50-80%) -->
            <rect x="50" y="70" width="900" height="90" fill="#10b98166" />
            <text x="20" y="120" font-size="12" fill="#94a3b8">80%</text>
            <text x="20" y="145" font-size="12" fill="#94a3b8">50%</text>

            <!-- Max capacity line (orange, 100%) -->
            <line x1="50" y1="10" x2="950" y2="10" stroke="#f97316" stroke-width="2" />
            <text x="20" y="20" font-size="12" fill="#f97316">100%</text>

            <!-- Actual SOC line (blue) -->
            <polyline points="50,140 150,130 250,120 350,130 450,150 550,140 650,130 750,120 850,110 950,100" 
                      fill="none" stroke="#3b82f6" stroke-width="3" />

            <!-- Optimal band (shaded green) -->
            <polygon points="50,140 150,135 250,132 350,138 450,145 550,140 650,135 750,132 850,125 950,118 950,200 850,200 750,200 650,200 550,200 450,200 350,200 250,200 150,200 50,200"
                     fill="#10b98144" />

            <!-- Hour labels -->
            <text x="50" y="290" font-size="11" fill="#94a3b8" text-anchor="middle">0h</text>
            <text x="250" y="290" font-size="11" fill="#94a3b8" text-anchor="middle">12h</text>
            <text x="450" y="290" font-size="11" fill="#94a3b8" text-anchor="middle">24h</text>
            <text x="650" y="290" font-size="11" fill="#94a3b8" text-anchor="middle">36h</text>
            <text x="950" y="290" font-size="11" fill="#94a3b8" text-anchor="middle">48h</text>

            <!-- Interactive layer (invisible rects for each hour) -->
            <g class="cursor-pointer">
              <rect v-for="(hour, idx) in 48"
                    :key="`hour-battery-${idx}`"
                    :x="50 + idx * 18.75"
                    y="0"
                    width="20"
                    height="300"
                    fill="transparent"
                    @mouseenter="activeBatteryHour = idx"
              />
            </g>

            <!-- Tooltip for battery chart -->
            <g v-if="activeBatteryHour !== null">
              <!-- Vertical line at cursor -->
              <line
                :x1="50 + activeBatteryHour * 18.75 + 10"
                y1="0"
                :x2="50 + activeBatteryHour * 18.75 + 10"
                y2="300"
                stroke="#64748b"
                stroke-width="1"
                stroke-dasharray="5,5"
              />
              
              <!-- Tooltip box -->
              <rect
                :x="Math.max(100, 50 + activeBatteryHour * 18.75 - 80)"
                :y="30"
                width="160"
                height="110"
                fill="#1e293b"
                stroke="#64748b"
                stroke-width="1"
                rx="4"
              />
              
              <!-- Tooltip text -->
              <text
                :x="Math.max(110, 50 + activeBatteryHour * 18.75 - 70)"
                :y="55"
                fill="#10b981"
                font-weight="bold"
                font-size="14"
              >
                Hour {{ activeBatteryHour }}: {{ getBatteryTooltipTime(activeBatteryHour) }}
              </text>
              
              <text
                :x="Math.max(110, 50 + activeBatteryHour * 18.75 - 70)"
                :y="75"
                fill="#fff"
                font-size="13"
              >
                SOC: {{ getBatterySocForHour(activeBatteryHour) }}%
              </text>
              
              <text
                :x="Math.max(110, 50 + activeBatteryHour * 18.75 - 70)"
                :y="95"
                fill="#94a3b8"
                font-size="12"
              >
                Status: {{ getBatteryStatusForHour(activeBatteryHour) }}
              </text>

              <text
                :x="Math.max(110, 50 + activeBatteryHour * 18.75 - 70)"
                :y="115"
                fill="#94a3b8"
                font-size="12"
              >
                Confidence: 82%
              </text>
            </g>
          </svg>
        </div>
        
        <!-- Legend explanations -->
        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 text-sm">
          <div class="bg-slate-800 rounded p-3 border border-slate-700 group relative cursor-help hover:border-green-600 transition">
            <p class="text-white font-semibold flex items-center gap-2">
              <span class="text-lg">🟢</span>
              Optimal Zone
            </p>
            <p class="text-slate-400 text-xs mt-1">50-80% SOC</p>
            <!-- Hover tooltip -->
            <div class="hidden group-hover:block absolute bottom-full left-0 bg-slate-950 border border-slate-700 rounded p-3 text-xs text-slate-400 w-48 z-10 mb-2">
              <p class="font-semibold text-green-400 mb-1">Optimal Battery Zone</p>
              <p>Keep battery between 50-80% for maximum lifespan and trading flexibility.</p>
            </div>
          </div>

          <div class="bg-slate-800 rounded p-3 border border-slate-700 group relative cursor-help hover:border-red-600 transition">
            <p class="text-white font-semibold flex items-center gap-2">
              <span class="text-lg">🔴</span>
              Low Safe Zone
            </p>
            <p class="text-slate-400 text-xs mt-1">0-20% SOC</p>
            <!-- Hover tooltip -->
            <div class="hidden group-hover:block absolute bottom-full left-0 bg-slate-950 border border-slate-700 rounded p-3 text-xs text-slate-400 w-48 z-10 mb-2">
              <p class="font-semibold text-red-400 mb-1">Critical Safety Zone</p>
              <p>Below 20% SOC is unsafe. Battery won't discharge further to protect hardware.</p>
            </div>
          </div>

          <div class="bg-slate-800 rounded p-3 border border-slate-700 group relative cursor-help hover:border-orange-600 transition">
            <p class="text-white font-semibold flex items-center gap-2">
              <span class="text-lg">🟠</span>
              Max Capacity
            </p>
            <p class="text-slate-400 text-xs mt-1">100% Limit</p>
            <!-- Hover tooltip -->
            <div class="hidden group-hover:block absolute bottom-full left-0 bg-slate-950 border border-slate-700 rounded p-3 text-xs text-slate-400 w-48 z-10 mb-2">
              <p class="font-semibold text-orange-400 mb-1">Maximum Capacity</p>
              <p>Battery cannot exceed 100% charge. Used for peak demand periods.</p>
            </div>
          </div>

          <div class="bg-slate-800 rounded p-3 border border-slate-700 group relative cursor-help hover:border-blue-600 transition">
            <p class="text-white font-semibold flex items-center gap-2">
              <span class="text-lg">🔵</span>
              Actual Trajectory
            </p>
            <p class="text-slate-400 text-xs mt-1">Forecasted path</p>
            <!-- Hover tooltip -->
            <div class="hidden group-hover:block absolute bottom-full left-0 bg-slate-950 border border-slate-700 rounded p-3 text-xs text-slate-400 w-48 z-10 mb-2">
              <p class="font-semibold text-blue-400 mb-1">SOC Trajectory</p>
              <p>AI's predicted battery charge path over next 48 hours based on prices and solar.</p>
            </div>
          </div>
        </div>

        <div class="grid grid-cols-2 md:grid-cols-4 gap-3 mt-4 text-sm">
          <div class="bg-slate-800 rounded p-2">
            <p class="text-slate-400">Current SOC</p>
            <p class="text-energy-400 font-bold">75%</p>
          </div>
          <div class="bg-slate-800 rounded p-2">
            <p class="text-slate-400">Min Forecast</p>
            <p class="text-blue-400 font-bold">45%</p>
          </div>
          <div class="bg-slate-800 rounded p-2">
            <p class="text-slate-400">Max Forecast</p>
            <p class="text-orange-400 font-bold">88%</p>
          </div>
          <div class="bg-slate-800 rounded p-2">
            <p class="text-slate-400">Peak Hour</p>
            <p class="text-yellow-400 font-bold">3:00 PM (35h)</p>
          </div>
        </div>
      </div>

      <!-- Hourly Forecast Table -->
      <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h2 class="text-xl font-bold text-white mb-4">Hourly Price Forecast (Next 12 Hours) - HOVER FOR DETAILS</h2>
        <div class="h-80 bg-slate-800 rounded-lg p-4 relative mb-4" @mouseleave="activePriceHour = null">
          <!-- SVG Price Chart -->
          <svg class="w-full h-full" viewBox="0 0 1000 300" preserveAspectRatio="xMidYMid meet">
            <!-- Grid background -->
            <defs>
              <pattern id="grid-price" width="100" height="30" patternUnits="userSpaceOnUse">
                <path d="M 100 0 L 0 0 0 30" fill="none" stroke="#334155" stroke-width="0.5" />
              </pattern>
            </defs>
            <rect width="1000" height="300" fill="url(#grid-price)" />

            <!-- Price zones -->
            <!-- Red zone (expensive, >13₴) -->
            <rect x="50" y="0" width="900" height="60" fill="#dc26262e" />
            <text x="20" y="30" font-size="12" fill="#ef4444">13₴</text>

            <!-- Yellow zone (moderate, 9-13₴) -->
            <rect x="50" y="60" width="900" height="120" fill="#eab30844" />
            <text x="20" y="120" font-size="12" fill="#eab308">9₴</text>

            <!-- Green zone (cheap, <9₴) -->
            <rect x="50" y="180" width="900" height="100" fill="#10b98166" />
            <text x="20" y="240" font-size="12" fill="#10b981">0₴</text>

            <!-- Price line -->
            <polyline points="50,140 150,120 250,100 350,90 450,80 550,120 650,140 750,160 850,180 950,200" 
                      fill="none" stroke="#3b82f6" stroke-width="3" />

            <!-- Hour labels -->
            <text x="50" y="290" font-size="11" fill="#94a3b8" text-anchor="middle">14:00</text>
            <text x="250" y="290" font-size="11" fill="#94a3b8" text-anchor="middle">16:00</text>
            <text x="450" y="290" font-size="11" fill="#94a3b8" text-anchor="middle">18:00</text>
            <text x="650" y="290" font-size="11" fill="#94a3b8" text-anchor="middle">20:00</text>
            <text x="950" y="290" font-size="11" fill="#94a3b8" text-anchor="middle">01:00</text>

            <!-- Interactive layer (invisible rects for each hour) -->
            <g class="cursor-pointer">
              <rect v-for="(hour, idx) in 12"
                    :key="`hour-price-${idx}`"
                    :x="50 + idx * 75"
                    y="0"
                    width="75"
                    height="300"
                    fill="transparent"
                    @mouseenter="activePriceHour = idx"
              />
            </g>

            <!-- Tooltip for price chart -->
            <g v-if="activePriceHour !== null">
              <!-- Vertical line at cursor -->
              <line
                :x1="50 + activePriceHour * 75 + 37.5"
                y1="0"
                :x2="50 + activePriceHour * 75 + 37.5"
                y2="300"
                stroke="#64748b"
                stroke-width="1"
                stroke-dasharray="5,5"
              />
              
              <!-- Tooltip box -->
              <rect
                :x="Math.max(100, 50 + activePriceHour * 75 - 60)"
                :y="30"
                width="160"
                height="130"
                fill="#1e293b"
                stroke="#64748b"
                stroke-width="1"
                rx="4"
              />
              
              <!-- Tooltip text -->
              <text
                :x="Math.max(110, 50 + activePriceHour * 75 - 50)"
                :y="55"
                fill="#10b981"
                font-weight="bold"
                font-size="14"
              >
                {{ getPriceTooltipTime(activePriceHour) }}
              </text>
              
              <text
                :x="Math.max(110, 50 + activePriceHour * 75 - 50)"
                :y="75"
                fill="#fff"
                font-size="13"
              >
                Price: {{ getPriceForHour(activePriceHour) }}₴/kWh
              </text>
              
              <text
                :x="Math.max(110, 50 + activePriceHour * 75 - 50)"
                :y="95"
                fill="#94a3b8"
                font-size="12"
              >
                Action: {{ getActionForHour(activePriceHour) }}
              </text>

              <text
                :x="Math.max(110, 50 + activePriceHour * 75 - 50)"
                :y="115"
                fill="#94a3b8"
                font-size="12"
              >
                Confidence: 78%
              </text>

              <text
                :x="Math.max(110, 50 + activePriceHour * 75 - 50)"
                :y="135"
                fill="#94a3b8"
                font-size="11"
              >
                Est. Gain: {{ getEstimatedGain(activePriceHour) }}₴
              </text>
            </g>
          </svg>
        </div>

        <div class="overflow-x-auto">
          <table class="w-full text-sm">
            <thead>
              <tr class="border-b border-slate-700">
                <th class="text-left py-2 px-3 text-slate-400 font-semibold">Hour</th>
                <th class="text-right py-2 px-3 text-slate-400 font-semibold">Price (₴/kWh)</th>
                <th class="text-right py-2 px-3 text-slate-400 font-semibold">Solar (kW)</th>
                <th class="text-right py-2 px-3 text-slate-400 font-semibold">Demand (kW)</th>
                <th class="text-center py-2 px-3 text-slate-400 font-semibold">AI Action</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="(hour, idx) in forecastHours" :key="idx" 
                  :class="['border-b border-slate-800 hover:bg-slate-800 transition', 
                           idx === 0 ? 'bg-slate-800' : '']">
                <td class="py-2 px-3 font-semibold">{{ hour.time }}</td>
                <td class="py-2 px-3 text-right" :class="hour.priceColor">{{ hour.price }}</td>
                <td class="py-2 px-3 text-right text-yellow-400">{{ hour.solar }}</td>
                <td class="py-2 px-3 text-right text-red-400">{{ hour.demand }}</td>
                <td class="py-2 px-3 text-center">
                  <span :class="['px-2 py-1 rounded-full text-xs font-semibold', hour.actionColor]">
                    {{ hour.action }}
                  </span>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      <!-- 7-Day Summary -->
      <div class="bg-slate-900 border border-slate-800 rounded-lg p-6">
        <h2 class="text-xl font-bold text-white mb-4">7-Day Cost Summary</h2>
        <div class="h-64 bg-slate-800 rounded-lg p-4 flex items-end justify-around">
          <!-- Daily bars -->
          <div v-for="day in dailySummary" :key="day.date" class="flex flex-col items-center gap-2">
            <div class="text-xs text-slate-400">{{ day.savings }}</div>
            <div class="flex gap-1 items-end" style="height: 180px;">
              <!-- Cost bar (gray) -->
              <div class="w-4 bg-slate-600 rounded-t" :style="{ height: (day.cost / 5) + 'px' }"></div>
              <!-- Savings bar (green) -->
              <div class="w-4 bg-green-500 rounded-t" :style="{ height: (day.savings / 5) + 'px' }"></div>
            </div>
            <div class="text-xs font-semibold text-slate-400">{{ day.date }}</div>
          </div>
        </div>
        <div class="grid grid-cols-3 gap-3 mt-4 text-sm">
          <div class="flex items-center gap-2 px-3 py-2 bg-slate-800 rounded">
            <div class="w-3 h-3 bg-slate-600 rounded"></div>
            <span class="text-slate-400">Cost (₴)</span>
          </div>
          <div class="flex items-center gap-2 px-3 py-2 bg-slate-800 rounded">
            <div class="w-3 h-3 bg-green-500 rounded"></div>
            <span class="text-slate-400">Savings (₴)</span>
          </div>
          <div class="text-right px-3 py-2 bg-slate-800 rounded">
            <p class="text-energy-400 font-bold">7-day: 55,316₴</p>
          </div>
        </div>
      </div>

      <!-- Footer navigation -->
      <div class="flex gap-4 justify-center text-center mt-12 pt-8 border-t border-slate-800">
        <NuxtLink to="/" class="bg-blue-700 hover:bg-blue-600 px-6 py-2 rounded-lg transition text-sm">
          📊 Dashboard
        </NuxtLink>
        <NuxtLink to="/analytics" class="bg-blue-700 hover:bg-blue-600 px-6 py-2 rounded-lg transition text-sm">
          📈 Analytics
        </NuxtLink>
        <NuxtLink to="/settings" class="bg-blue-700 hover:bg-blue-600 px-6 py-2 rounded-lg transition text-sm">
          ⚙️ Settings
        </NuxtLink>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed } from 'vue'

definePageMeta({
  layout: 'default'
})

// Battery state
const batterySOC = ref(75)

// Current price (from real OREE data)
const currentPrice = ref(11.63)

// Tooltip tracking
const activePriceHour = ref<number | null>(null)
const activeBatteryHour = ref<number | null>(null)

// Price color and action based on range
const priceColor = computed(() => {
  const percent = (currentPrice.value / 20) * 100
  if (percent < 33) return '#10b981' // Green
  if (percent < 66) return '#eab308' // Yellow
  return '#ef4444' // Red
})

const priceDashArray = computed(() => {
  const percent = (currentPrice.value / 20) * 100
  return (percent / 100) * 251.3
})

const priceAction = computed(() => {
  const percent = (currentPrice.value / 20) * 100
  if (percent < 33) return '🟢 Good for CHARGING'
  if (percent < 66) return '🟡 HOLD Position'
  return '🔴 SELL PREMIUM'
})

// Forecast data for next 12 hours
const forecastHours = computed(() => [
  { time: '14:00 (now)', price: '11.63₴', priceColor: 'text-yellow-400', solar: '12.5', demand: '42', action: 'HOLD', actionColor: 'bg-yellow-600 bg-opacity-30 text-yellow-400' },
  { time: '15:00', price: '12.81₴', priceColor: 'text-red-400', solar: '14.2', demand: '45', action: 'SELL', actionColor: 'bg-green-600 bg-opacity-30 text-green-400' },
  { time: '16:00', price: '13.44₴', priceColor: 'text-red-400', solar: '15.0', demand: '48', action: 'SELL', actionColor: 'bg-green-600 bg-opacity-30 text-green-400' },
  { time: '17:00', price: '14.21₴', priceColor: 'text-red-400', solar: '12.8', demand: '50', action: 'SELL', actionColor: 'bg-green-600 bg-opacity-30 text-green-400' },
  { time: '18:00', price: '12.95₴', priceColor: 'text-red-400', solar: '8.2', demand: '52', action: 'DISCHARGE', actionColor: 'bg-red-600 bg-opacity-30 text-red-400' },
  { time: '19:00', price: '11.44₴', priceColor: 'text-yellow-400', solar: '2.1', demand: '48', action: 'DISCHARGE', actionColor: 'bg-red-600 bg-opacity-30 text-red-400' },
  { time: '20:00', price: '10.12₴', priceColor: 'text-yellow-400', solar: '0.0', demand: '42', action: 'HOLD', actionColor: 'bg-slate-600 bg-opacity-30 text-slate-400' },
  { time: '21:00', price: '8.76₴', priceColor: 'text-green-400', solar: '0.0', demand: '35', action: 'CHARGE', actionColor: 'bg-blue-600 bg-opacity-30 text-blue-400' },
  { time: '22:00', price: '7.44₴', priceColor: 'text-green-400', solar: '0.0', demand: '30', action: 'CHARGE', actionColor: 'bg-blue-600 bg-opacity-30 text-blue-400' },
  { time: '23:00', price: '6.89₴', priceColor: 'text-green-400', solar: '0.0', demand: '25', action: 'CHARGE', actionColor: 'bg-blue-600 bg-opacity-30 text-blue-400' },
  { time: '00:00', price: '5.44₴', priceColor: 'text-green-400', solar: '0.0', demand: '20', action: 'CHARGE', actionColor: 'bg-blue-600 bg-opacity-30 text-blue-400' },
  { time: '01:00', price: '5.12₴', priceColor: 'text-green-400', solar: '0.0', demand: '18', action: 'CHARGE', actionColor: 'bg-blue-600 bg-opacity-30 text-blue-400' },
])

// 7-day summary
const dailySummary = [
  { date: 'Feb 1', cost: 95.5, savings: 55.3 },
  { date: 'Feb 2', cost: 87.2, savings: 52.1 },
  { date: 'Feb 3', cost: 92.1, savings: 54.8 },
  { date: 'Feb 4', cost: 98.3, savings: 58.2 },
  { date: 'Feb 5', cost: 94.6, savings: 56.4 },
  { date: 'Feb 6', cost: 91.2, savings: 54.9 },
  { date: 'Feb 7', cost: 96.8, savings: 57.1 },
]

// Tooltip helper functions for PRICE CHART
const getPriceTooltipTime = (idx: number): string => {
  const baseHour = 14
  const hour = (baseHour + idx) % 24
  return `${hour.toString().padStart(2, '0')}:00`
}

const getPriceForHour = (idx: number): string => {
  const prices = ['11.63', '12.81', '13.44', '14.21', '12.95', '11.44', '10.12', '8.76', '7.44', '6.89', '5.44', '5.12']
  return prices[idx] || '0.00'
}

const getActionForHour = (idx: number): string => {
  const actions = ['HOLD', 'SELL', 'SELL', 'SELL', 'DISCHARGE', 'DISCHARGE', 'HOLD', 'CHARGE', 'CHARGE', 'CHARGE', 'CHARGE', 'CHARGE']
  return actions[idx] || 'HOLD'
}

const getEstimatedGain = (idx: number): string => {
  const gains = ['0', '+15.2', '+18.5', '+22.8', '+14.5', '+8.2', '0', '+12.3', '+15.8', '+18.2', '+22.5', '+24.1']
  return gains[idx] || '0'
}

// Tooltip helper functions for BATTERY CHART
const getBatteryTooltipTime = (idx: number): string => {
  const baseHour = 0
  const hour = (baseHour + idx) % 24
  return `${hour.toString().padStart(2, '0')}:00`
}

const getBatterySocForHour = (idx: number): string => {
  // Simulate SOC changes throughout 48 hours
  const baseSOC = 75
  let soc = baseSOC
  
  // Linear decrease by ~0.6% per hour on average
  soc = soc - (idx * 0.6)
  
  // Add some realistic variation
  const variance = Math.sin(idx / 12) * 5
  soc = soc + variance
  
  return Math.max(20, Math.round(soc)).toString()
}

const getBatteryStatusForHour = (idx: number): string => {
  const soc = parseInt(getBatterySocForHour(idx))
  if (soc >= 80) return '🟠 High'
  if (soc >= 50) return '🟢 Optimal'
  if (soc >= 20) return '🟡 Low'
  return '🔴 Critical'
}

// Manual action handler
const executeAction = (action: string) => {
  console.log(`Executing action: ${action}`)
  // In real implementation, this would trigger API call to change battery mode
}
</script>

<style scoped>
.energy-400 {
  @apply text-emerald-400;
}
</style>

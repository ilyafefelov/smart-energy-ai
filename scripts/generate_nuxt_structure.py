#!/usr/bin/env python3
"""
Generate Nuxt3 + Nitro dashboard for Smart Energy AI

This script generates the complete project structure for the frontend
"""

import json
from pathlib import Path

DASHBOARD_DIR = Path("dashboard")
SRC_DIR = DASHBOARD_DIR / "src"

# Project structure
STRUCTURE = {
    "dashboard": {
        ".gitignore": ["node_modules/", ".nuxt/", ".output/", "dist/", ".env.local"],
        "nuxt.config.ts": "Nuxt configuration with UI and TailwindCSS",
        "tsconfig.json": "TypeScript configuration",
        "package.json": "Dependencies and scripts",
        "tailwind.config.ts": "TailwindCSS configuration",
        ".env.example": "Environment variables template",
        "README.md": "Setup and development guide",
        
        "app.vue": "Root app component",
        "app.config.ts": "App-level configuration",
        
        "public": {
            "favicon.ico": "Favicon"
        },
        
        "server": {
            "api": {
                "prices.ts": "GET /api/prices - Real-time OREE prices",
                "battery.ts": "GET/POST /api/battery - Battery status and control",
                "metrics.ts": "GET /api/metrics - Cost metrics and savings",
                "history.ts": "GET /api/history - Optimization history",
            }
        },
        
        "pages": {
            "index.vue": "Dashboard homepage",
            "analytics.vue": "Price analytics and trends",
            "control.vue": "Battery control panel",
            "settings.vue": "Configuration and settings",
        },
        
        "components": {
            "EnergyHeader.vue": "Top navigation",
            "PriceCard.vue": "Real-time price display",
            "BatteryStatus.vue": "Battery SOC and performance",
            "CostMetrics.vue": "Cost savings display",
            "PriceChart.vue": "Price history chart",
            "ControlPanel.vue": "Battery control interface",
        },
        
        "composables": {
            "usePrices.ts": "Composable for price data",
            "useBattery.ts": "Composable for battery control",
            "useMetrics.ts": "Composable for cost metrics",
        },
        
        "stores": {
            "energy.ts": "Pinia store for energy state",
        },
        
        "types": {
            "index.ts": "TypeScript type definitions",
        },
        
        "utils": {
            "formatters.ts": "Data formatting utilities",
            "calculations.ts": "Energy calculations",
        }
    }
}

def print_structure(d: dict, indent: int = 0) -> str:
    """Pretty print directory structure"""
    result = []
    for key, value in d.items():
        prefix = "  " * indent + "├─ "
        if isinstance(value, dict):
            result.append(f"{prefix}📁 {key}/")
            result.append(print_structure(value, indent + 1))
        elif isinstance(value, list):
            result.append(f"{prefix}📝 {key}")
            for item in value:
                result.append("  " * (indent + 1) + f"  • {item}")
        else:
            result.append(f"{prefix}📝 {key}")
    return "\n".join(result)

if __name__ == "__main__":
    print("="*70)
    print("🚀 NUXT3 + NITRO DASHBOARD - PROJECT STRUCTURE")
    print("="*70)
    print("\n📁 Directory Structure:\n")
    print(print_structure(STRUCTURE))
    
    print("\n" + "="*70)
    print("📋 FILES TO CREATE:")
    print("="*70)
    print("""
1. Dashboard Root:
   - nuxt.config.ts (Nuxt 3 configuration)
   - tsconfig.json (TypeScript setup)
   - package.json (dependencies)
   - tailwind.config.ts (styling)
   
2. API Routes (/server/api):
   - prices.ts - OREE price data endpoint
   - battery.ts - Battery status and control
   - metrics.ts - Cost metrics calculations
   - history.ts - Optimization history
   
3. Pages:
   - index.vue - Main dashboard
   - analytics.vue - Price analysis
   - control.vue - Battery control
   - settings.vue - Configuration
   
4. Components:
   - EnergyHeader.vue
   - PriceCard.vue
   - BatteryStatus.vue
   - CostMetrics.vue
   - PriceChart.vue
   - ControlPanel.vue
   
5. Composables:
   - usePrices.ts
   - useBattery.ts
   - useMetrics.ts
   
6. Store (Pinia):
   - energy.ts
   
7. Types & Utilities:
   - types/index.ts
   - utils/formatters.ts
   - utils/calculations.ts
    """)
    
    print("\n" + "="*70)
    print("🎯 SETUP COMMANDS:")
    print("="*70)
    print("""
# 1. Create project with Nuxt scaffolding
cd C:\\Users\\ilyaf\\clawd\\projects\\smart-energy-ai
npx nuxi@latest init dashboard

# 2. Install additional dependencies
cd dashboard
npm install -D @nuxtjs/tailwindcss nuxt-ui pinia @pinia/nuxt chart.js vue-chartjs

# 3. Start development server
npm run dev
# Will be available at: http://localhost:3000

# 4. Build for production
npm run build
npm run preview
    """)

    print("\n" + "="*70)
    print("✅ READY FOR CODEX IMPLEMENTATION")
    print("="*70)

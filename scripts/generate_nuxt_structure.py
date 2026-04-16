#!/usr/bin/env python3
"""Generate the legacy Nuxt3 + Nitro dashboard scaffolding layout."""

SECTION_WIDTH = 70

DASHBOARD_ROOT_FILES = {
    ".gitignore": ["node_modules/", ".nuxt/", ".output/", "dist/", ".env.local"],
    "nuxt.config.ts": "Nuxt configuration with UI and TailwindCSS",
    "tsconfig.json": "TypeScript configuration",
    "package.json": "Dependencies and scripts",
    "tailwind.config.ts": "TailwindCSS configuration",
    ".env.example": "Environment variables template",
    "README.md": "Setup and development guide",
    "app.vue": "Root app component",
    "app.config.ts": "App-level configuration",
}

PUBLIC_STRUCTURE = {
    "favicon.ico": "Favicon",
}

SERVER_API_STRUCTURE = {
    "prices.ts": "GET /api/prices - Real-time OREE prices",
    "battery.ts": "GET/POST /api/battery - Battery status and control",
    "metrics.ts": "GET /api/metrics - Cost metrics and savings",
    "history.ts": "GET /api/history - Optimization history",
}

PAGES_STRUCTURE = {
    "index.vue": "Dashboard homepage",
    "analytics.vue": "Price analytics and trends",
    "control.vue": "Battery control panel",
    "settings.vue": "Configuration and settings",
}

COMPONENTS_STRUCTURE = {
    "EnergyHeader.vue": "Top navigation",
    "PriceCard.vue": "Real-time price display",
    "BatteryStatus.vue": "Battery SOC and performance",
    "CostMetrics.vue": "Cost savings display",
    "PriceChart.vue": "Price history chart",
    "ControlPanel.vue": "Battery control interface",
}

COMPOSABLES_STRUCTURE = {
    "usePrices.ts": "Composable for price data",
    "useBattery.ts": "Composable for battery control",
    "useMetrics.ts": "Composable for cost metrics",
}

STORES_STRUCTURE = {
    "energy.ts": "Pinia store for energy state",
}

TYPES_STRUCTURE = {
    "index.ts": "TypeScript type definitions",
}

UTILS_STRUCTURE = {
    "formatters.ts": "Data formatting utilities",
    "calculations.ts": "Energy calculations",
}

STRUCTURE = {
    "dashboard": {
        **DASHBOARD_ROOT_FILES,
        "public": PUBLIC_STRUCTURE,
        "server": {"api": SERVER_API_STRUCTURE},
        "pages": PAGES_STRUCTURE,
        "components": COMPONENTS_STRUCTURE,
        "composables": COMPOSABLES_STRUCTURE,
        "stores": STORES_STRUCTURE,
        "types": TYPES_STRUCTURE,
        "utils": UTILS_STRUCTURE,
    }
}

FILES_TO_CREATE_TEXT = """
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
"""

SETUP_COMMANDS_TEXT = """
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
"""

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


def print_section(title: str) -> None:
     print("=" * SECTION_WIDTH)
     print(title)
     print("=" * SECTION_WIDTH)


def main() -> None:
     print_section("🚀 NUXT3 + NITRO DASHBOARD - PROJECT STRUCTURE")
     print("\n📁 Directory Structure:\n")
     print(print_structure(STRUCTURE))

     print("\n")
     print_section("📋 FILES TO CREATE:")
     print(FILES_TO_CREATE_TEXT)

     print("\n")
     print_section("🎯 SETUP COMMANDS:")
     print(SETUP_COMMANDS_TEXT)

     print("\n")
     print_section("✅ READY FOR CODEX IMPLEMENTATION")

if __name__ == "__main__":
     main()

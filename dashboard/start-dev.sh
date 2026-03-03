#!/usr/bin/env bash
# Start Nuxt Dashboard with Real Data

SCRIPT_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" >/dev/null 2>&1 && pwd)"
cd "$SCRIPT_DIR" || exit 1

echo "🚀 Starting Smart Energy AI Dashboard"
echo "═══════════════════════════════════════"
echo ""

# Check if node_modules exists
if [ ! -d "node_modules" ]; then
  echo "📦 Installing dependencies..."
  npm install --legacy-peer-deps || {
    echo "❌ npm install failed"
    exit 1
  }
fi

echo ""
echo "🔄 Starting Nuxt dev server..."
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""
echo "📊 Dashboard will be available at:"
echo "   → http://localhost:3600"
echo ""
echo "📚 Pages:"
echo "   → http://localhost:3600/ (Dashboard)"
echo "   → http://localhost:3600/analytics (Analytics)"
echo "   → http://localhost:3600/control (Control)"
echo "   → http://localhost:3600/settings (Settings)"
echo ""
echo "📈 Real Data Sources:"
echo "   → OREE Feb 2026 prices"
echo "   → PPO ML validation results"
echo "   → Battery status metrics"
echo "   → Historical performance data"
echo ""
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo ""

npm run dev

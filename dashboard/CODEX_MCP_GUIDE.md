# Codex CLI + MCP Integration for Nuxt3 Dashboard

## 🎯 What is MCP?

**Model Context Protocol (MCP)** allows Codex CLI to:
- Access your file system with context
- Understand Nuxt framework structure
- Integrate with GitHub
- Perform web searches
- Run tools and execute tests
- All while maintaining code context

---

## 🚀 Quick Start

### 1. Verify Codex Configuration

Your MCP config is at: `~/.codex/config.toml`

```toml
[[mcp.servers]]
name = "nuxt-mcp"
command = "npx"
args = ["nuxt-mcp"]
enabled = true

[[mcp.servers]]
name = "filesystem"
command = "npx"
args = ["@modelcontextprotocol/server-filesystem", "C:\\Users\\ilyaf\\clawd\\projects\\smart-energy-ai"]
enabled = true
```

### 2. Start Development Server

```bash
cd C:\Users\ilyaf\clawd\projects\smart-energy-ai\dashboard
npm install
npm run dev
# http://localhost:3000
```

### 3. Use Codex with MCP

```bash
# Navigate to dashboard directory
cd dashboard

# Now use Codex - it will have Nuxt context via MCP
codex "Create a component for real-time price display"
codex "Add dark mode toggle to settings page"
codex "Fix responsive layout on mobile"
codex "Implement battery charge/discharge animation"
```

---

## 💡 Example Use Cases

### 1. Generate New Components
```bash
codex "Create a Vue 3 component called <ChargingStrategy> with:
- Charge/discharge controls
- Target SOC slider
- Rate selection dropdown
- Dark theme with tailwind
- Make it production-ready"
```

**Result:** Codex generates complete component with:
- TypeScript types
- Event handlers
- Tailwind styling
- Accessibility features
- Dark mode support

### 2. Refactor Existing Code
```bash
codex "Refactor all API routes in server/api/ to use consistent error handling and logging"
```

**Result:** Updates all 4 endpoints with:
- Unified error patterns
- Request logging
- Response validation
- Type safety

### 3. Debug Issues
```bash
codex "The battery control panel layout breaks on mobile. Fix the responsive design"
```

**Result:** Analyzes the component and:
- Identifies responsive issues
- Suggests grid/flex changes
- Tests on mobile sizes
- Provides working fix

### 4. Add Features
```bash
codex "Add a new page at /advanced-settings with:
- Model tuning parameters
- Risk tolerance slider
- Data export options
- Make it match the existing UI theme"
```

**Result:** Creates complete page with:
- Routing setup
- Component structure
- Styling consistency
- API integration

---

## 🔗 MCP Servers Available

### ✅ Enabled

**filesystem** - File system access
```bash
codex "Show me all .vue files in the pages directory"
codex "How many lines of code in dashboard/pages/index.vue?"
```

**nuxt-mcp** - Nuxt-specific context
```bash
codex "Generate a Nuxt composable for real-time price updates"
codex "Create a Pinia store for battery status management"
```

### 🔲 Disabled (Can Enable)

**github** - GitHub integration
- Requires: `$env:GITHUB_TOKEN`
- Features: Issue creation, PR automation, commit history
- Enable in `~/.codex/config.toml`

**brave-search** - Web search
- Requires: `$env:BRAVE_SEARCH_API_KEY`
- Features: Search documentation, find examples
- Enable in `~/.codex/config.toml`

---

## 📋 Pro Tips

### Tip 1: Combine MCP Tools
```bash
# Use filesystem + nuxt context together
codex "Create a complete feature:
1. New API endpoint for battery forecasting
2. Vue component to display forecast
3. Pinia store for state management
4. Add route to navigation menu"
```

### Tip 2: Local Context Matters
```bash
# Go to dashboard directory first
cd dashboard

# Now Codex has Nuxt context from MCP
codex "your task"  # More accurate than from root
```

### Tip 3: Chain Requests
```bash
# First: Understand structure
codex "Show me the architecture of the energy store"

# Then: Improve it
codex "Refactor the energy store to add real-time price updates"

# Finally: Test
codex "Write unit tests for the energy store"
```

### Tip 4: Use for CI/CD Automation
```bash
codex "Create a GitHub Actions workflow that:
1. Runs on push to main
2. Installs dependencies
3. Runs tests
4. Builds Nuxt
5. Deploys to production"
```

---

## 🔐 Environment Variables

To enable more MCP servers, set:

```powershell
# Enable GitHub integration
$env:GITHUB_TOKEN = "your-github-token"

# Enable web search
$env:BRAVE_SEARCH_API_KEY = "your-api-key"

# Then enable in ~/.codex/config.toml
# [[mcp.servers]]
# name = "github"
# enabled = true
```

---

## 🎓 Learning Path

### Beginner
1. Generate simple components with Codex
2. Fix CSS/responsive issues
3. Create utility functions

### Intermediate
1. Generate complete features (page + API + store)
2. Refactor existing code
3. Write tests for components

### Advanced
1. Complex multi-file refactoring
2. Automated feature generation
3. CI/CD pipeline setup
4. Cross-cutting concerns

---

## 🚀 Workflow Example: Add Price Forecasting to Dashboard

```bash
# 1. Start dev server
cd dashboard
npm run dev

# 2. Open new terminal, navigate to dashboard
cd dashboard

# 3. Ask Codex to add forecasting
codex "Create a price forecasting feature:
1. New API endpoint /api/forecast that returns predicted prices for next 7 days
2. New page /forecasting with chart showing predictions
3. Update dashboard to show 'predicted savings'
4. All with dark theme, TypeScript, production-ready

Requirements:
- Use Chart.js for charts
- Integrate with existing API
- Add to navigation menu
- Type-safe with full TypeScript"

# 4. Apply generated code
# Review -> Copy -> Paste into files

# 5. Test
npm run dev
# Visit http://localhost:3000/forecasting
```

---

## 📚 Resources

- **MCP Protocol:** https://modelcontextprotocol.io/
- **Nuxt Docs:** https://nuxt.com/
- **Codex CLI:** `codex --help`
- **Config File:** `~/.codex/config.toml`

---

## ✅ Status

- ✅ MCP configured in `~/.codex/config.toml`
- ✅ filesystem server enabled
- ✅ nuxt-mcp server enabled
- ✅ Ready to use `codex` command
- ⏳ npm install in progress (MCP servers)

**Next:** Once npm finishes, run `codex "your task"` in dashboard directory!

---

**Happy coding with Codex + MCP! 🚀**

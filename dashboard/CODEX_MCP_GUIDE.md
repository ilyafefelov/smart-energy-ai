# Codex CLI + MCP Integration for Nuxt3 Dashboard

## 🎯 What is MCP?

**Model Context Protocol (MCP)** allows Codex CLI to:
- Access your file system with context
- Understand Nuxt UI framework structure
- Integrate with GitHub
- Perform web searches
- Run tools and execute tests
- All while maintaining code context

---

## 🚀 Quick Start

### 1. Verify Codex Configuration

Your MCP config is at: `~/.codex/config.toml`

```toml
# Remote: Nuxt UI MCP Server
[[mcp.servers]]
name = "nuxt-ui"
command = "npx"
args = ["mcp-remote", "https://ui.nuxt.com/mcp"]
enabled = true

# Local: Filesystem access
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

# Now use Codex - it will have Nuxt UI context via MCP
codex "Create a component for real-time price display"
codex "Add dark mode toggle to settings page"
codex "Fix responsive layout on mobile"
codex "Implement battery charge/discharge animation"
```

---

## 💡 Example Use Cases

### 1. Generate New Components
```bash
codex "Create a Vue 3 component called <PriceChart> with:
- Real-time price data visualization
- Chart.js for smooth animations
- Dark theme with tailwind
- Responsive on mobile
- Full TypeScript types
- Production-ready code"
```

**Result:** Codex generates complete component with:
- TypeScript types
- Event handlers
- Tailwind styling
- Accessibility features
- Dark mode support
- Chart integration

### 2. Refactor Existing Code
```bash
codex "Refactor all API routes in server/api/ to:
- Use consistent error handling
- Add request logging
- Validate all inputs
- Return typed responses"
```

**Result:** Updates all 4 endpoints with:
- Unified error patterns
- Request logging
- Response validation
- Type safety

### 3. Debug Issues
```bash
codex "The battery control panel layout breaks on mobile. 
Analyze the responsive design and provide a fix using Tailwind"
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
- Match the existing dark theme UI"
```

**Result:** Creates complete page with:
- Routing setup
- Component structure
- Styling consistency
- API integration

### 5. Use Nuxt UI Components
```bash
codex "Create a settings form using Nuxt UI components:
- UInput for text fields
- UToggle for boolean settings
- USelect for dropdowns
- UButton for submit
- Dark theme styling"
```

**Result:** Uses Nuxt UI components with:
- Proper Nuxt UI API
- Dark theme integration
- Form validation
- Accessibility built-in

---

## 🔗 MCP Servers Available

### ✅ Enabled

**nuxt-ui** (Remote) - Nuxt UI framework context
```bash
# Generate components using Nuxt UI
codex "Create a UCard-based component for battery status"
codex "Use UButton and UInput from Nuxt UI in settings"
codex "Generate a Nuxt UI form with validation"
```

**filesystem** (Local) - File system access
```bash
codex "Show me all .vue files in the pages directory"
codex "How many lines of code in dashboard/pages/index.vue?"
codex "List all TypeScript files in the project"
```

### 🔲 Disabled (Can Enable)

**github** (Remote) - GitHub integration
- Features: Issue creation, PR automation, commit history
- Enable in `~/.codex/config.toml`

**brave-search** (Remote) - Web search
- Features: Search documentation, find examples
- Enable in `~/.codex/config.toml`

---

## 📋 Pro Tips

### Tip 1: Combine MCP Context
```bash
# Use nuxt-ui + filesystem context together
codex "Create a complete feature:
1. New API endpoint for battery forecasting
2. Vue component using Nuxt UI to display forecast
3. Pinia store for state management
4. Add route to navigation menu"
```

### Tip 2: Nuxt UI Specific
```bash
# Leverage Nuxt UI components
codex "Build a dashboard using Nuxt UI:
- UCard for metric cards
- UButton for actions
- UInput for forms
- UToggle for settings
- Dark theme throughout"
```

### Tip 3: Local Context Matters
```bash
# Go to dashboard directory first
cd dashboard

# Now Codex has Nuxt context from remote MCP
codex "your task"  # More accurate than from root
```

### Tip 4: Chain Requests
```bash
# First: Understand structure
codex "Explain the Nuxt UI component architecture"

# Then: Generate code
codex "Create a custom UCard variant for energy metrics"

# Finally: Integrate
codex "Add the new component to the dashboard"
```

### Tip 5: Remote MCP Benefits
```bash
# No need to install - already hosted
# Always up-to-date
# No permission issues
# Works everywhere
codex "I want to use the latest Nuxt UI features"
```

---

## 🔐 Environment Variables

Remote MCP servers don't require env vars (hosted online).

For GitHub integration (optional):
```powershell
# Enable GitHub if needed
$env:GITHUB_TOKEN = "your-github-token"

# Then enable in ~/.codex/config.toml
# [[mcp.servers]]
# name = "github"
# enabled = true
```

---

## 🎓 Learning Path

### Beginner
1. Generate components with Nuxt UI
2. Use Tailwind for styling
3. Add Vue interactivity

### Intermediate
1. Generate complete features (page + API + store)
2. Use Nuxt UI for consistent design
3. Refactor existing code

### Advanced
1. Complex multi-file features
2. Automated component generation
3. CI/CD pipeline setup
4. Performance optimization

---

## 🚀 Workflow Example: Add Forecasting with Nuxt UI

```bash
# 1. Start dev server
cd dashboard
npm run dev

# 2. Open new terminal, navigate to dashboard
cd dashboard

# 3. Ask Codex to add forecasting using Nuxt UI
codex "Create a price forecasting feature:
1. New API endpoint /api/forecast (returns 7-day predictions)
2. New page /forecasting with:
   - UCard component for header
   - UButton actions
   - Chart.js for visualization
   - Dark theme styling
3. Update dashboard to show 'predicted savings'
4. All production-ready, TypeScript, Nuxt UI styled"

# 4. Apply generated code
# Review -> Copy -> Paste into files

# 5. Test
npm run dev
# Visit http://localhost:3000/forecasting
```

---

## 🌐 Remote MCP vs Local

| Feature | Remote (Nuxt UI) | Local (Filesystem) |
|---------|------------------|-------------------|
| Installation | ✓ None needed | ✗ Requires npm |
| Updates | ✓ Always latest | ✗ Manual updates |
| Permissions | ✓ No issues | ✗ May require sudo |
| Network | ✗ Requires internet | ✓ Offline capable |
| Speed | ~ 1-2s overhead | ✓ Instant |
| Content | ✓ Official docs | ✓ Your files |

**Best practice:** Use both!
- Remote for frameworks (Nuxt UI)
- Local for project files (filesystem)

---

## 📚 Resources

- **MCP Protocol:** https://modelcontextprotocol.io/
- **Nuxt UI:** https://ui.nuxt.com/
- **Nuxt Docs:** https://nuxt.com/
- **Codex CLI:** `codex --help`
- **Config File:** `~/.codex/config.toml`

---

## ✅ Status

- ✅ MCP configured in `~/.codex/config.toml`
- ✅ nuxt-ui remote server enabled
- ✅ filesystem server enabled
- ✅ Ready to use `codex` command
- ✅ No npm install needed for remote servers

**Next:** Run `codex "your task"` in dashboard directory!

---

**Happy coding with Codex + MCP! 🚀**
**Remote Nuxt UI server = instant Nuxt UI context! 🎨**

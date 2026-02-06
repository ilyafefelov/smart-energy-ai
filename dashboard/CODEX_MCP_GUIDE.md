# Codex CLI + MCP Integration for Nuxt3 Dashboard

## 🎯 What is MCP?

**Model Context Protocol (MCP)** allows Codex CLI to:
- Access your **file system** with context
- Understand **Nuxt framework** architecture & best practices
- Access **Nuxt UI component** library
- Integrate with GitHub
- Perform web searches
- Run tools and execute tests
- All while maintaining full code context

---

## 🚀 Quick Start

### 1. Verify Codex Configuration

Your MCP config is at: `~/.codex/config.toml`

```toml
# Remote: Nuxt Framework (docs, patterns, best practices)
[[mcp.servers]]
name = "nuxt"
command = "npx"
args = ["mcp-remote", "https://nuxt.com/mcp"]
enabled = true

# Remote: Nuxt UI Components (UCard, UButton, etc.)
[[mcp.servers]]
name = "nuxt-ui"
command = "npx"
args = ["mcp-remote", "https://ui.nuxt.com/mcp"]
enabled = true

# Local: Filesystem (your project files)
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

# Now Codex has FULL CONTEXT:
# - Nuxt framework knowledge
# - Nuxt UI components
# - Your project files
# - Best practices

codex "Create a composable for real-time price updates"
codex "Build a page using Nuxt server routes"
codex "Generate Nuxt UI components for battery control"
```

---

## 💡 Example Use Cases

### 1. Generate Components with Nuxt Best Practices
```bash
codex "Create a Vue 3 component using Nuxt patterns:
- Use Nuxt composable for logic
- Nuxt UI components (UCard, UButton)
- Chart.js for price visualization
- Dark theme with tailwind
- TypeScript throughout
- Production-ready"
```

**Result:** Component with:
- Proper Nuxt composable pattern
- Nuxt UI integration
- Type safety
- Tailwind styling
- Best practices

### 2. Create Nuxt Pages with Auto-Routing
```bash
codex "Create new Nuxt page /pages/forecasting.vue:
- Fetch predictions from /server/api/forecast
- Display with Nuxt UI
- Use Pinia store for state
- Add to nav automatically
- Dark theme"
```

**Result:**
- Auto-routed page
- Server integration
- Store setup
- Full styling

### 3. Build Nuxt Server Routes
```bash
codex "Create server route /server/api/predictions.ts:
- Validates input params
- Calls ML endpoint
- Returns typed response
- Error handling
- Following Nuxt conventions"
```

**Result:** Production-ready API route

### 4. Create Nuxt Composables
```bash
codex "Create composable useBatteryStatus:
- Fetches battery data
- Real-time updates
- Pinia store integration
- Error handling
- Reactive state"
```

**Result:** Reusable composable

### 5. Refactor with Nuxt Patterns
```bash
codex "Refactor all pages to use:
- Nuxt composables for shared logic
- Auto-imported components
- Proper Nuxt directory structure
- Server routes instead of API layer
- Full TypeScript types"
```

**Result:** Code following Nuxt best practices

---

## 🔗 MCP Servers Available

### ✅ Enabled (3 Servers)

**nuxt** (Remote) - Nuxt Framework Documentation
- Official Nuxt documentation
- Framework patterns & best practices
- Composition API patterns
- Server routes, middleware, etc.
- Auto-imports & directory structure

```bash
codex "How do Nuxt composables work?"
codex "What's the difference between middleware and plugins?"
codex "Create a Nuxt server middleware for logging"
```

**nuxt-ui** (Remote) - Nuxt UI Component Library
- 50+ ready-made components
- UCard, UButton, UInput, UForm, etc.
- Dark mode support
- Tailwind integration
- Accessibility built-in

```bash
codex "What Nuxt UI components exist for forms?"
codex "Create a data table with Nuxt UI"
codex "Build dashboard using UCard components"
```

**filesystem** (Local) - Project File Access
- Your project structure
- Current code analysis
- File-aware recommendations
- Cross-file refactoring

```bash
codex "Show me the project structure"
codex "How many Vue components do we have?"
codex "Refactor all pages at once"
```

### 🔲 Disabled (Can Enable)

**github** (Remote) - GitHub Integration
- Issue/PR automation
- Commit message generation
- Repository analysis

**brave-search** (Remote) - Web Search
- Documentation lookup
- Example finding
- Package research

---

## 🎓 Codex + MCP Workflows

### Workflow 1: Add New Feature with Full Nuxt Context

```bash
cd dashboard

# 1. Ask about Nuxt pattern
codex "How should I structure a new feature in Nuxt?"

# 2. Generate the page
codex "Create /pages/advanced-settings.vue with:
- Nuxt composables for data
- Nuxt UI forms
- Server routes for API
- Store for state
- Dark theme"

# 3. Create composable
codex "Create composable for advanced settings logic"

# 4. Create API route
codex "Create /server/api/settings/save.ts"

# 5. Test
npm run dev
# Visit http://localhost:3000/advanced-settings
```

### Workflow 2: Refactor Existing Code

```bash
cd dashboard

# Understand current structure
codex "Analyze the current project structure"

# Plan refactor
codex "How should we restructure using Nuxt best practices?"

# Execute refactor
codex "Refactor all pages to use composables"
codex "Move logic from components to server routes"
codex "Update API layer to use proper Nuxt patterns"
```

### Workflow 3: Build Complete Feature

```bash
# Start with feature request
codex "Build price forecasting feature:
1. /pages/forecasting.vue page
2. usePriceForecast composable
3. /server/api/forecast endpoint
4. Nuxt UI components for display
5. Pinia store for state
6. Tests for API"
```

---

## 📚 MCP + Nuxt Context Examples

### Understanding Nuxt Patterns
```bash
codex "Explain Nuxt's auto-import system and give examples"
codex "How do server routes differ from client API calls?"
codex "Show me the recommended project structure"
```

### Building with Nuxt UI
```bash
codex "List all Nuxt UI form components"
codex "Create a complex form with validation using Nuxt UI"
codex "How do I customize Nuxt UI components?"
```

### Nuxt Best Practices
```bash
codex "What are Nuxt middleware and when should I use them?"
codex "Explain composables vs useAsync"
codex "How should I handle authentication in Nuxt?"
```

---

## 🌐 Remote MCP vs Local

| Feature | Remote Nuxt | Remote Nuxt UI | Local Filesystem |
|---------|-------------|----------------|------------------|
| **Source** | nuxt.com | ui.nuxt.com | Your files |
| **Content** | Framework docs | Components | Project code |
| **Updates** | Always latest | Always latest | Real-time |
| **Internet** | Required | Required | Not needed |
| **Setup** | Zero | Zero | npm install |
| **Speed** | 1-2s overhead | 1-2s overhead | Instant |

**Best Practice:** Use all 3!
- Remote Nuxt for framework knowledge
- Remote Nuxt UI for components
- Local filesystem for your code

---

## 🚀 Performance Tips

1. **Navigate to project first:**
   ```bash
   cd dashboard
   codex "your task"  # Better context
   ```

2. **Be specific in requests:**
   ```bash
   # Good
   codex "Create /pages/settings.vue with Nuxt composable pattern"
   
   # Less specific
   codex "Create settings page"
   ```

3. **Ask about patterns first:**
   ```bash
   codex "How should I structure this feature?"
   # Then use the answer for generation
   ```

4. **Chain requests for complex features:**
   ```bash
   codex "Create page..."
   codex "Create composable..."
   codex "Create API route..."
   # Build incrementally
   ```

---

## 📖 Resources

- **Nuxt:** https://nuxt.com/
- **Nuxt UI:** https://ui.nuxt.com/
- **MCP Protocol:** https://modelcontextprotocol.io/
- **Codex CLI:** `codex --help`

---

## ✅ Status

- ✅ **nuxt** MCP enabled (Nuxt framework context)
- ✅ **nuxt-ui** MCP enabled (Component library)
- ✅ **filesystem** MCP enabled (Project access)
- ✅ Ready to use `codex` command
- ✅ Full Nuxt context available

**Start developing:**
```bash
cd dashboard
npm install
npm run dev

# In new terminal:
cd dashboard
codex "your task here"
```

---

**Happy coding with Codex + Nuxt! 🚀**
**Three MCP servers = full framework context! 🎉**

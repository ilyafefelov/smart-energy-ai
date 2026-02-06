#!/usr/bin/env node
/**
 * Codex CLI + MCP Integration Script
 * 
 * Demonstrates how to use Codex with MCP servers for:
 * - Nuxt development with full context
 * - GitHub integration
 * - File system access
 * - Web search
 */

const { spawn } = require('child_process');
const path = require('path');
const fs = require('fs');

const projectRoot = 'C:\\Users\\ilyaf\\clawd\\projects\\smart-energy-ai';
const dashboardDir = path.join(projectRoot, 'dashboard');

console.log('🚀 Codex CLI + MCP Integration');
console.log('================================\n');

console.log('📋 Available MCP Servers:');
console.log('  ✓ filesystem - Project file access');
console.log('  ✓ nuxt-mcp - Nuxt framework support');
console.log('  ○ github - GitHub integration (disabled)');
console.log('  ○ brave-search - Web search (disabled)\n');

console.log('🎯 Usage Examples:\n');

console.log('1. Code Generation with Nuxt Context:');
console.log('   codex "Create a Vue component for battery status display"\n');

console.log('2. File System Operations:');
console.log('   codex "List all TypeScript files in pages/ directory"\n');

console.log('3. Project-Wide Refactoring:');
console.log('   codex "Update all API endpoints to use v2 naming"\n');

console.log('4. Debug & Fix:');
console.log('   codex "Fix the battery control layout on mobile devices"\n');

console.log('📝 Configuration Path:');
console.log(`   ~/.codex/config.toml\n`);

console.log('🔧 Current MCP Servers Enabled:');
console.log('   - filesystem (project root)');
console.log('   - nuxt-mcp (framework support)\n');

console.log('📦 To Enable More Servers:');
console.log('   1. Set GITHUB_TOKEN env variable');
console.log('   2. Set BRAVE_SEARCH_API_KEY env variable');
console.log('   3. Edit ~/.codex/config.toml');
console.log('   4. Set enabled = true for desired servers\n');

console.log('💡 Tips:');
console.log('   - Use "codex" in dashboard/ for local context');
console.log('   - Use "codex --help" for all options');
console.log('   - MCP servers provide enhanced code generation');
console.log('   - Combine with OpenClaw for autonomous workflows\n');

console.log('🚀 Next: Run "npm run dev" in dashboard/ to start Nuxt server');
console.log('   Then use: codex "your task here"\n');

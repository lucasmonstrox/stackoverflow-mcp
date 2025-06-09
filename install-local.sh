#!/bin/bash
# StackOverflow MCP Server - Local Installation Script

set -e

echo "🔧 StackOverflow MCP Server - Local Setup"
echo "=========================================="

# Check if we're in the right directory
if [[ ! -f "package.json" ]] || [[ ! -f "pyproject.toml" ]]; then
    echo "❌ Error: Please run this script from the stackoverflow-mcp project root directory"
    exit 1
fi

echo "📍 Current directory: $(pwd)"

# Install Python dependencies
echo ""
echo "📦 Installing Python dependencies..."
if command -v uv >/dev/null 2>&1; then
    echo "Using uv package manager..."
    uv sync
else
    echo "Using pip..."
    pip install -e .
fi

# Install Node.js dependencies (if any)
echo ""
echo "📦 Installing Node.js dependencies..."
npm install

# Create config file if it doesn't exist
if [[ ! -f ".stackoverflow-mcp.json" ]]; then
    echo ""
    echo "📝 Creating default configuration file..."
    cp .stackoverflow-mcp.example.json .stackoverflow-mcp.json
    echo "✓ Created .stackoverflow-mcp.json"
else
    echo "✓ Configuration file already exists"
fi

# Test installations
echo ""
echo "🧪 Testing installations..."

echo "Testing Python FastMCP version..."
if python -m src.stackoverflow_mcp.fastmcp_main --help >/dev/null 2>&1; then
    echo "✓ FastMCP version working"
else
    echo "❌ FastMCP version failed"
fi

echo "Testing Node.js wrapper..."
if node cli.js --help >/dev/null 2>&1; then
    echo "✓ Node.js wrapper working"
else
    echo "❌ Node.js wrapper failed"
fi

echo ""
echo "🎉 Setup complete!"
echo ""
echo "📋 Available commands:"
echo "  FastMCP version: python -m src.stackoverflow_mcp.fastmcp_main"
echo "  Traditional:     python -m src.stackoverflow_mcp.main"
echo "  Node.js wrapper: node cli.js"
echo ""
echo "📝 Cursor MCP Configuration:"
echo "  Check cursor-mcp-config.json for example configurations"
echo "  Remember to update the 'cwd' path to your project directory!"
echo ""
echo "📖 For more details, see FIXES.md" 
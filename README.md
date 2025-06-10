# StackOverflow MCP Server

[![npm version](https://badge.fury.io/js/@notalk-tech%2Fstackoverflow-mcp.svg)](https://badge.fury.io/js/@notalk-tech%2Fstackoverflow-mcp)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

A Model Context Protocol (MCP) server that provides seamless access to StackOverflow's programming Q&A database using the FastMCP framework. This package serves as an NPX-compatible wrapper for the Python-based StackOverflow MCP server.

## Quick Start

### Using NPX (Recommended)

```bash
# Run directly with npx (no installation required)
npx @notalk/stackoverflow-mcp

# Skip installation prompts (useful for automation)
npx -y @notalk/stackoverflow-mcp

# Or install globally
npm install -g @notalk/stackoverflow-mcp
stackoverflow-mcp
```

### Using Python Module Directly

```bash
# If you have the Python package installed
python -m stackoverflow_mcp

# Using uv (recommended for Python development)
uv run python -m stackoverflow_mcp
```

## 📋 Prerequisites

- **Node.js** 14.0.0 or higher
- **Python** 3.12 or higher
- **uv** (recommended) or **pip** (Python package manager)

The NPX wrapper will automatically:
- Detect your Python installation
- Install the required Python package (`stackoverflow-mcp`)
- Handle environment setup and configuration

## Installation

### Option 1: NPX (No Installation)
```bash
npx @notalk/stackoverflow-mcp --help
```

### Option 2: Global NPM Installation
```bash
npm install -g @notalk/stackoverflow-mcp
stackoverflow-mcp --help
```

### Option 3: Local Development
```bash
git clone https://github.com/NoTalkTech/stackoverflow-mcp.git
cd stackoverflow-mcp
npm install
node cli.js --help
```

## 🎯 Features

- **🔍 Question Search**: Search StackOverflow questions by keywords
- **📖 Question Details**: Get detailed question content, answers, and metadata
- **🏷️ Tag-based Search**: Find questions by programming language tags
- **⚡ Rate Limit Management**: Automatic detection and handling of API limits
- **🔐 API Authentication**: Support for StackOverflow API keys
- **🚀 Auto-deployment**: NPX-compatible with automatic Python environment setup
- **📁 Smart Configuration**: Auto-discovery of config files and working directories
- **🔧 Development Mode**: Enhanced logging and debugging features
- **⚡ FastMCP Implementation**: Simplified, elegant server using FastMCP framework (only implementation)

## Usage

### Basic Usage

```bash
# Start the MCP server with default settings
npx @notalk/stackoverflow-mcp

# Auto-confirm installation (useful for scripts/CI)
npx -y @notalk/stackoverflow-mcp

# Start on a specific port
npx @notalk/stackoverflow-mcp --port 8080

# Development mode with debug logging
npx @notalk/stackoverflow-mcp --dev --log-level DEBUG

# Use custom configuration file
npx @notalk/stackoverflow-mcp --config-file ./my-config.json
```

### Python Development with uv

For Python development, we recommend using uv for faster dependency management:

```bash
# Install dependencies with uv
uv sync

# Run the server with uv
uv run python -m stackoverflow_mcp

# Development mode with uv
uv run python -m stackoverflow_mcp --log-level DEBUG
```

**FastMCP Benefits:**
- 🔥 **Simplified Code**: Clean, maintainable implementation
- 🎯 **Decorator-based**: Clean tool registration with `@mcp.tool()`
- 🚀 **Auto-schema**: Type hints automatically generate schemas  
- 🛡️ **Built-in Error Handling**: Consistent error responses
- 📦 **Better Separation**: Clean architecture with focused responsibilities

### Configuration

Create a `.stackoverflow-mcp.json` file in your project directory:

```json
{
  "host": "localhost",
  "port": 3000,
  "log_level": "INFO",
  "stackoverflow_api_key": "your_api_key_here"
}
```

### Command Line Options

```
Options:
  --host TEXT                     Host to bind the server to
  --port INTEGER                  Port to bind the server to (auto-detect if not specified)
  --log-level [DEBUG|INFO|WARNING|ERROR]
                                  Logging level
  --config-file PATH              Path to configuration file (auto-discover if not specified)
  --working-dir DIRECTORY         Working directory (auto-detect if not specified)
  --auto-port / --no-auto-port    Automatically find an available port if specified port is in use
  --dev / --prod                  Run in development mode (more verbose logging, auto-reload)
  --health-check / --no-health-check
                                  Enable startup health checks
  --version                       Show the version and exit.
  --help                          Show this message and exit.
```

## 🔧 Configuration Files

The server automatically discovers configuration files in the following order:

1. `.stackoverflow-mcp.json`
2. `stackoverflow-mcp.config.json`
3. `config/stackoverflow-mcp.json`
4. `.config/stackoverflow-mcp.json`

### Example Configuration

```json
{
  "host": "localhost",
  "port": 3000,
  "log_level": "INFO",
  "stackoverflow_api_key": "your_optional_api_key",
  "max_requests_per_minute": 30,
  "enable_caching": true
}
```

## 🌐 API Endpoints

Once running, the MCP server provides the following tools:

- `search_questions`: Search StackOverflow questions by keywords
- `get_question_details`: Get detailed information about a specific question
- `search_by_tags`: Find questions filtered by programming language tags
- `get_user_info`: Get information about StackOverflow users

## 🧪 Testing

```bash
# Test the npm package
npm test

# Test npm packaging
npm run test:npm

# Test global installation
npm run test:install

# Test Python module directly
python -m pytest tests/ -v
```

## 🚀 Development

### Local Development Setup

```bash
# Clone the repository
git clone https://github.com/NoTalkTech/stackoverflow-mcp.git
cd stackoverflow-mcp

# Install Node.js dependencies
npm install

# Install Python dependencies
pip install -e .

# Run in development mode
npm start -- --dev
```

### Project Structure

```
@notalk/stackoverflow-mcp/
├── cli.js                          # NPX wrapper (Node.js)
├── package.json                    # NPM package configuration
├── src/stackoverflow_mcp/          # Python MCP server
│   ├── __main__.py                 # Python module entry point
│   ├── main.py                     # CLI and server management
│   ├── server.py                   # MCP server implementation
│   └── stackoverflow_client.py     # StackOverflow API client
├── tests/                          # Test files
└── README.md                       # This file
```

## 📦 Publishing

### Semantic Versioning

This package follows [Semantic Versioning](https://semver.org/):

- **MAJOR**: Breaking changes
- **MINOR**: New features (backward compatible)
- **PATCH**: Bug fixes (backward compatible)

### Release Process

```bash
# Update version
npm version patch|minor|major

# Publish to npm
npm publish

# Create GitHub release
git push --tags
```

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🆘 Support

- **Issues**: [GitHub Issues](https://github.com/NoTalkTech/stackoverflow-mcp/issues)
- **Documentation**: [GitHub Wiki](https://github.com/NoTalkTech/stackoverflow-mcp/wiki)
- **Discussions**: [GitHub Discussions](https://github.com/NoTalkTech/stackoverflow-mcp/discussions)

## 🙏 Acknowledgments

- [Model Context Protocol](https://github.com/modelcontextprotocol) for the MCP specification
- [StackOverflow](https://stackoverflow.com/) for providing the API
- The open-source community for inspiration and contributions

---

**Made with ❤️ for the developer community**

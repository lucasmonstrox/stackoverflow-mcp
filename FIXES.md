# StackOverflow MCP Server - 修复说明

## 问题总结

这个 MCP 服务器之前存在几个关键问题，导致无法正确识别工作路径并在 Cursor 的 MCP 配置中正常工作：

## 修复的问题

### 1. 缺少 `ServerConfig.from_file()` 方法

**问题**: `fastmcp_main.py` 调用了 `ServerConfig.from_file()` 方法，但 `config.py` 中没有定义这个方法。

**修复**: 在 `ServerConfig` 类中添加了 `from_file()` 类方法：

```python
@classmethod
def from_file(cls, config_path: Path) -> "ServerConfig":
    """Load configuration from a JSON config file."""
    if not config_path.exists():
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    
    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # Create config with loaded data, allowing extra fields to be ignored
        return cls(**{k: v for k, v in config_data.items() if k in cls.__fields__})
        
    except json.JSONDecodeError as e:
        raise ValueError(f"Invalid JSON in config file {config_path}: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to load config from {config_path}: {e}")
```

### 2. 工作目录切换问题

**问题**: 虽然工作目录检测逻辑正确，但 Python 进程没有正确切换到检测到的工作目录。

**修复**: 
- 在 `fastmcp_main.py` 中添加了显式的工作目录切换
- 在 `cli.js` 中改进了工作目录处理和错误处理
- 确保 `--working-dir` 参数正确传递给 Python 进程

### 3. AsyncIO 事件循环冲突

**问题**: 在某些环境中（如 Jupyter、IDE）已经有运行中的 asyncio 事件循环，导致 "Already running asyncio in this thread" 错误。

**修复**: 添加了 asyncio 事件循环冲突处理：

```python
try:
    asyncio.run(run_server(config))
except RuntimeError as e:
    if "already running" in str(e).lower():
        logger.warning("AsyncIO loop already running, creating new event loop")
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_server(config))
        finally:
            loop.close()
    else:
        raise
```

### 4. 配置文件路径处理

**修复**: 改进了配置文件路径处理，支持相对路径和绝对路径：

```python
if config_file:
    config_path = Path(config_file)
    if not config_path.is_absolute():
        config_path = work_dir / config_path
else:
    config_path = discover_config_file(work_dir)
```

## 验证修复

运行测试脚本验证所有组件正常工作：

```bash
python test_server.py
```

预期输出：
```
StackOverflow MCP Server - Test Suite
==================================================
Testing configuration loading...
✓ Working directory detected: /Users/biyu.huang/code/stackoverflow-mcp
✓ Config file discovered: /Users/biyu.huang/code/stackoverflow-mcp/.stackoverflow-mcp.json
✓ Config loaded from file: host=localhost, port=3000

Testing server imports...
✓ FastMCP server imports successful
✓ Server instance created
✓ FastMCP app created

✓ All tests passed! Server should work correctly.
✓ Configuration: localhost:3000
✓ Log level: DEBUG
```

## Cursor MCP 配置

⚠️ **重要提示**: npm 包 `stackoverflow-mcp` 尚未发布到 npm registry，因此无法使用 `npx` 命令。请使用以下本地配置方案：

### 选项 1: 使用 FastMCP 版本（推荐，更简洁）
```json
{
  "mcpServers": {
    "stackoverflow-fastmcp": {
      "command": "python",
      "args": ["-m", "src.stackoverflow_mcp.fastmcp_main", "--port", "3001", "--log-level", "INFO"],
      "cwd": "/Users/biyu.huang/code/stackoverflow-mcp",
      "env": {
        "STACKOVERFLOW_API_KEY": ""
      }
    }
  }
}
```

### 选项 2: 使用 Node.js 包装器
```json
{
  "mcpServers": {
    "stackoverflow-local": {
      "command": "node",
      "args": ["cli.js", "--port", "3002", "--log-level", "INFO"],
      "cwd": "/Users/biyu.huang/code/stackoverflow-mcp",
      "env": {
        "STACKOVERFLOW_API_KEY": ""
      }
    }
  }
}
```

### 选项 3: 使用传统版本
```json
{
  "mcpServers": {
    "stackoverflow-main": {
      "command": "python",
      "args": ["-m", "src.stackoverflow_mcp.main", "--port", "3003", "--log-level", "INFO"],
      "cwd": "/Users/biyu.huang/code/stackoverflow-mcp",
      "env": {
        "STACKOVERFLOW_API_KEY": ""
      }
    }
  }
}
```

**配置要点**:
- 必须指定 `"cwd"` 为项目根目录的绝对路径
- 使用 `src.stackoverflow_mcp` 模块路径（注意 `src.` 前缀）
- 每个选项使用不同端口避免冲突

## 关键改进

1. **工作路径识别**: 现在能正确检测和切换到项目工作目录
2. **配置文件加载**: 支持从 JSON 文件加载配置
3. **错误处理**: 改进了错误处理和日志记录
4. **环境兼容性**: 解决了 asyncio 事件循环冲突问题
5. **参数传递**: 确保命令行参数正确传递给 Python 进程

## 测试命令

```bash
# 测试 FastMCP 版本
python -m src.stackoverflow_mcp.fastmcp_main --help

# 测试 Node.js 包装器
node cli.js --help

# 测试配置加载
python -c "from src.stackoverflow_mcp.config import ServerConfig; from pathlib import Path; config = ServerConfig.from_file(Path('.stackoverflow-mcp.json')); print(f'Config: {config.host}:{config.port}')"
```

现在这个 MCP 服务器应该能够在 Cursor 中正确工作了！ 
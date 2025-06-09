# StackOverflow MCP Server - 本地设置指南

## 📋 问题说明

npm 包 `stackoverflow-mcp` 尚未发布到 npm registry，因此无法通过 `npx stackoverflow-mcp` 直接使用。

## 🚀 快速设置

### 1. 运行自动安装脚本

```bash
./install-local.sh
```

### 2. 手动设置（可选）

如果自动脚本失败，可以手动执行以下步骤：

```bash
# 安装 Python 依赖
pip install -e .

# 安装 Node.js 依赖
npm install

# 创建配置文件
cp .stackoverflow-mcp.example.json .stackoverflow-mcp.json
```

## 🔧 Cursor MCP 配置

将以下配置添加到你的 Cursor 设置中（记得更新 `cwd` 路径）：

### 推荐配置（FastMCP 版本）

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

### 替代配置（Node.js 包装器）

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

## ✅ 测试安装

```bash
# 测试 FastMCP 版本
python -m src.stackoverflow_mcp.fastmcp_main --help

# 测试 Node.js 包装器
node cli.js --help

# 测试配置加载
python -c "import sys; sys.path.insert(0, 'src'); from stackoverflow_mcp.config import ServerConfig; from pathlib import Path; print('Config test:', ServerConfig.from_file(Path('.stackoverflow-mcp.json')).host)"
```

## 🔑 配置要点

1. **必须指定 `cwd`**: Cursor MCP 配置中必须包含项目根目录的绝对路径
2. **模块路径**: 使用 `src.stackoverflow_mcp` 前缀
3. **端口冲突**: 每个服务器使用不同端口
4. **工作目录**: 确保当前工作目录在项目根目录

## 🐛 常见问题

### "Already running asyncio in this thread"
这个错误已经修复，服务器会自动处理 asyncio 事件循环冲突。

### "Module not found"
确保：
- 当前目录在项目根目录
- 使用正确的模块路径 `src.stackoverflow_mcp`
- Python 依赖已正确安装

### "Config file not found"
确保：
- `.stackoverflow-mcp.json` 文件存在于项目根目录
- Cursor MCP 配置中指定了正确的 `cwd` 路径

## 📚 更多信息

- 详细修复说明：[FIXES.md](FIXES.md)
- 完整配置示例：[cursor-mcp-config.json](cursor-mcp-config.json)
- 原始 README：[README.md](README.md) 
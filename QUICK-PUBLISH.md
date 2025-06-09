# 🚀 快速发布指南

## 📋 发布前检查清单

✅ **包名可用**: `stackoverflow-mcp` 未被占用  
✅ **打包测试**: 通过 `npm pack --dry-run`  
✅ **文件结构**: 包含 cli.js, README.md, LICENSE 等必要文件  

## 🔥 一键发布

```bash
# 运行自动发布脚本
./publish.sh
```

## 📝 手动发布步骤

### 1. 登录NPM

```bash
# 登录npm账户
npm login

# 验证登录
npm whoami
```

### 2. 运行测试

```bash
# 确保所有测试通过
npm test

# 检查打包内容
npm pack --dry-run
```

### 3. 更新版本并发布

```bash
# 更新版本号（选择一个）
npm version patch   # 0.1.0 → 0.1.1
npm version minor   # 0.1.0 → 0.2.0  
npm version major   # 0.1.0 → 1.0.0

# 发布到npm
npm publish --access public

# 推送标签到GitHub
git push origin main --tags
```

### 4. 验证发布

```bash
# 检查包信息
npm view stackoverflow-mcp

# 测试npx安装
npx stackoverflow-mcp --help
```

## 🎯 发布成功后

### 更新文档

发布成功后，用户就可以使用 `npx stackoverflow-mcp` 了！

更新 Cursor MCP 配置示例：

```json
{
  "mcpServers": {
    "stackoverflow": {
      "command": "npx",
      "args": ["stackoverflow-mcp", "--port", "3000", "--log-level", "INFO"],
      "env": {
        "STACKOVERFLOW_API_KEY": ""
      }
    }
  }
}
```

### 创建 GitHub Release

1. 访问: https://github.com/NoTalkTech/stackoverflow-mcp/releases/new
2. 选择刚创建的版本标签
3. 填写 Release 说明
4. 发布 Release

## 🔧 常见问题

### npm login 问题

```bash
# 如果登录失败，先登出再登录
npm logout
npm login
```

### 权限问题

```bash
# 确保使用 --access public
npm publish --access public
```

### 版本冲突

```bash
# 如果版本已存在，更新版本号
npm version patch
npm publish --access public
```

## 📊 当前状态

- **包名**: `stackoverflow-mcp` ✅ 可用
- **版本**: `0.1.0` 
- **Registry**: https://registry.npmjs.org/
- **访问权限**: public
- **文件大小**: ~6.7 kB (打包后)

准备好了就运行 `./publish.sh` 开始发布！🎉 
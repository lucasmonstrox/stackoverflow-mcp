# NPM 包发布指南

## 📋 发布前准备

### 1. 检查项目状态

```bash
# 确保所有文件已提交
git status

# 确保在main分支
git branch

# 拉取最新代码
git pull origin main
```

### 2. 运行测试

```bash
# 运行所有测试
npm test

# 测试npm包打包
npm run test:npm

# 测试Python模块
python -m pytest tests/ -v
```

## 🔐 NPM 账户设置

### 1. 注册/登录NPM账户

```bash
# 如果没有账户，先注册
npm adduser

# 如果已有账户，登录
npm login
```

### 2. 验证登录状态

```bash
# 检查当前登录用户
npm whoami

# 检查发布权限
npm access list packages
```

## 📦 发布流程

### 1. 版本管理

```bash
# 查看当前版本
npm version

# 更新版本号 (选择一个)
npm version patch    # 0.1.0 → 0.1.1 (bug修复)
npm version minor    # 0.1.0 → 0.2.0 (新功能)
npm version major    # 0.1.0 → 1.0.0 (重大更改)

# 或手动指定版本
npm version 0.1.1
```

### 2. 最终检查

```bash
# 打包预览（不会实际打包）
npm pack --dry-run

# 检查将要发布的文件
npm pack
tar -tzf stackoverflow-mcp-*.tgz
rm stackoverflow-mcp-*.tgz
```

### 3. 发布到NPM

```bash
# 发布到npm registry
npm publish

# 如果是第一次发布，可能需要指定访问权限
npm publish --access public
```

## 🏷️ 标签和分发标签

```bash
# 发布为latest (默认)
npm publish

# 发布为beta版本
npm publish --tag beta

# 发布为alpha版本  
npm publish --tag alpha

# 查看所有标签
npm dist-tag ls stackoverflow-mcp
```

## ✅ 验证发布

### 1. 检查npm registry

```bash
# 查看包信息
npm view stackoverflow-mcp

# 查看包的所有版本
npm view stackoverflow-mcp versions --json

# 在浏览器中查看
open https://www.npmjs.com/package/stackoverflow-mcp
```

### 2. 测试安装

```bash
# 在临时目录测试安装
mkdir /tmp/test-install
cd /tmp/test-install

# 测试npx使用
npx stackoverflow-mcp --help

# 测试全局安装
npm install -g stackoverflow-mcp
stackoverflow-mcp --help

# 清理
npm uninstall -g stackoverflow-mcp
cd -
rm -rf /tmp/test-install
```

## 🔄 发布后更新

### 1. 更新README配置

发布成功后，更新文档中的NPX使用说明：

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

### 2. 创建GitHub Release

```bash
# 推送版本标签
git push origin main --tags

# 在GitHub上创建Release
# https://github.com/NoTalkTech/stackoverflow-mcp/releases/new
```

## 🐛 常见问题

### 发布权限错误

```bash
# 错误：403 Forbidden
# 解决：检查包名是否已被占用
npm view stackoverflow-mcp

# 如果包名被占用，需要更改package.json中的name
```

### 版本冲突

```bash
# 错误：版本已存在
# 解决：更新版本号
npm version patch
npm publish
```

### 登录问题

```bash
# 清除npm缓存
npm logout
npm login

# 检查npm registry
npm config get registry
# 应该是：https://registry.npmjs.org/
```

## 📋 发布检查清单

- [ ] 所有代码已提交并推送到GitHub
- [ ] 测试通过（`npm test`）
- [ ] 版本号已更新
- [ ] README.md已更新
- [ ] 已登录npm账户
- [ ] 运行`npm pack --dry-run`检查文件
- [ ] 执行`npm publish`
- [ ] 验证发布成功
- [ ] 测试`npx stackoverflow-mcp`
- [ ] 更新文档中的安装说明
- [ ] 创建GitHub Release

## 🎯 快速发布命令

```bash
# 一键发布脚本
./publish.sh
```

或手动执行：

```bash
# 1. 运行测试
npm test

# 2. 更新版本
npm version patch

# 3. 发布
npm publish

# 4. 推送标签
git push origin main --tags

# 5. 测试
npx stackoverflow-mcp --help
``` 
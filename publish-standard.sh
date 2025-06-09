#!/bin/bash
# StackOverflow MCP Server - 标准NPM发布脚本
# 遵循npm发布最佳实践和规范

set -e

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 日志函数
log_info() { echo -e "${BLUE}ℹ️  $1${NC}"; }
log_success() { echo -e "${GREEN}✅ $1${NC}"; }
log_warning() { echo -e "${YELLOW}⚠️  $1${NC}"; }
log_error() { echo -e "${RED}❌ $1${NC}"; }

echo "📦 StackOverflow MCP Server - 标准NPM发布脚本"
echo "=============================================="
echo "遵循npm发布最佳实践和规范"
echo ""

# 1. 环境检查
log_info "检查发布环境..."

# 检查必要工具
command -v npm >/dev/null 2>&1 || { log_error "npm未安装"; exit 1; }
command -v git >/dev/null 2>&1 || { log_error "git未安装"; exit 1; }
command -v node >/dev/null 2>&1 || { log_error "node未安装"; exit 1; }

# 检查Node.js版本
node_version=$(node --version | cut -d'v' -f2)
required_version="14.0.0"
if ! node -e "process.exit(require('semver').gte('$node_version', '$required_version') ? 0 : 1)" 2>/dev/null; then
    log_error "Node.js版本过低，需要 >= $required_version，当前: $node_version"
    exit 1
fi

log_success "环境检查通过"

# 2. 项目结构检查
log_info "检查项目结构..."

if [[ ! -f "package.json" ]]; then
    log_error "package.json文件不存在"
    exit 1
fi

if [[ ! -f "cli.js" ]]; then
    log_error "cli.js文件不存在"
    exit 1
fi

# 检查必要文件
required_files=("README.md" "LICENSE")
for file in "${required_files[@]}"; do
    if [[ ! -f "$file" ]]; then
        log_error "必要文件不存在: $file"
        exit 1
    fi
done

log_success "项目结构检查通过"

# 3. package.json验证
log_info "验证package.json配置..."

# 检查必要字段
required_fields=("name" "version" "description" "main" "author" "license")
for field in "${required_fields[@]}"; do
    if ! node -e "const pkg = require('./package.json'); if (!pkg.$field) process.exit(1);" 2>/dev/null; then
        log_error "package.json缺少必要字段: $field"
        exit 1
    fi
done

# 检查版本格式
if ! node -e "const pkg = require('./package.json'); require('semver').valid(pkg.version) || process.exit(1);" 2>/dev/null; then
    log_error "package.json中的版本号格式不正确"
    exit 1
fi

log_success "package.json验证通过"

# 4. Git状态检查
log_info "检查Git状态..."

if [[ ! -d ".git" ]]; then
    log_error "不是Git仓库"
    exit 1
fi

if [[ -n $(git status --porcelain) ]]; then
    log_error "工作目录不干净，请先提交所有更改"
    git status --short
    exit 1
fi

current_branch=$(git branch --show-current)
if [[ "$current_branch" != "main" && "$current_branch" != "master" ]]; then
    log_warning "当前不在主分支 (当前: $current_branch)"
    read -p "是否继续? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

log_success "Git状态检查通过"

# 5. 拉取最新代码
log_info "拉取最新代码..."
git pull origin $current_branch
log_success "代码已更新"

# 6. NPM认证检查
log_info "检查NPM认证..."

if ! npm whoami >/dev/null 2>&1; then
    log_error "未登录NPM，请先运行 'npm login'"
    exit 1
fi

current_user=$(npm whoami)
log_success "已登录NPM，用户: $current_user"

# 7. 依赖检查
log_info "检查依赖..."

# 创建package-lock.json（如果不存在）
if [[ ! -f "package-lock.json" ]]; then
    log_info "创建package-lock.json..."
    npm install --package-lock-only
fi

# 安全审计
log_info "运行安全审计..."
if npm audit --audit-level=high; then
    log_success "安全审计通过"
else
    log_warning "发现安全问题，建议运行 'npm audit fix'"
    read -p "是否继续发布? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 8. 运行测试
log_info "运行测试..."

if npm test; then
    log_success "所有测试通过"
else
    log_error "测试失败，请修复后再发布"
    exit 1
fi

# 9. 包内容检查
log_info "检查包内容..."

# 打包预览
npm pack --dry-run > /tmp/npm-pack-preview.txt
package_size=$(grep "package size:" /tmp/npm-pack-preview.txt | awk '{print $3, $4}')
unpacked_size=$(grep "unpacked size:" /tmp/npm-pack-preview.txt | awk '{print $3, $4}')

log_info "包大小: $package_size"
log_info "解压后大小: $unpacked_size"

# 检查包大小（警告如果超过1MB）
size_bytes=$(grep "package size:" /tmp/npm-pack-preview.txt | awk '{print $3}' | sed 's/[^0-9.]//g')
if (( $(echo "$size_bytes > 1000" | bc -l) )); then
    log_warning "包大小较大 ($package_size)，考虑优化"
fi

# 显示将要包含的文件
echo ""
log_info "将要发布的文件:"
npm pack --dry-run | grep -A 100 "Tarball Contents" | grep -B 100 "Tarball Details" | grep -v "Tarball"

echo ""
read -p "确认包内容正确? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_error "用户取消发布"
    exit 1
fi

log_success "包内容检查通过"

# 10. 版本管理
log_info "版本管理..."

current_version=$(node -e "console.log(require('./package.json').version)")
log_info "当前版本: $current_version"

echo ""
echo "选择版本更新类型:"
echo "1) patch (修复)      - $current_version → $(npm version patch --no-git-tag-version --dry-run 2>/dev/null || echo 'N/A')"
echo "2) minor (功能)      - $current_version → $(npm version minor --no-git-tag-version --dry-run 2>/dev/null || echo 'N/A')"
echo "3) major (重大更改)  - $current_version → $(npm version major --no-git-tag-version --dry-run 2>/dev/null || echo 'N/A')"
echo "4) prerelease (预发布)"
echo "5) 自定义版本"
echo "6) 跳过版本更新"

read -p "请选择 (1-6): " version_choice

case $version_choice in
    1)
        log_info "更新patch版本..."
        new_version=$(npm version patch)
        ;;
    2)
        log_info "更新minor版本..."
        new_version=$(npm version minor)
        ;;
    3)
        log_info "更新major版本..."
        new_version=$(npm version major)
        ;;
    4)
        read -p "输入预发布标识符 (alpha/beta/rc): " prerelease_id
        log_info "更新prerelease版本..."
        new_version=$(npm version prerelease --preid=$prerelease_id)
        ;;
    5)
        read -p "输入自定义版本 (例: 1.2.3): " custom_version
        if ! node -e "require('semver').valid('$custom_version') || process.exit(1);" 2>/dev/null; then
            log_error "版本号格式不正确"
            exit 1
        fi
        log_info "设置自定义版本..."
        new_version=$(npm version $custom_version)
        ;;
    6)
        log_info "跳过版本更新"
        new_version="v$current_version"
        ;;
    *)
        log_error "无效选择"
        exit 1
        ;;
esac

final_version=${new_version#v}
log_success "版本: $final_version"

# 11. 发布标签选择
if [[ $version_choice == "4" ]]; then
    # 预发布版本
    if [[ $prerelease_id == "alpha" ]]; then
        publish_tag="alpha"
    elif [[ $prerelease_id == "beta" ]]; then
        publish_tag="beta"
    else
        publish_tag="next"
    fi
else
    publish_tag="latest"
fi

log_info "发布标签: $publish_tag"

# 12. 最终确认
echo ""
log_info "发布信息确认:"
echo "  包名: $(node -e "console.log(require('./package.json').name)")"
echo "  版本: $final_version"
echo "  标签: $publish_tag"
echo "  用户: $current_user"
echo "  注册表: $(npm config get registry)"
echo ""

read -p "确认发布? (y/N): " -n 1 -r
echo
if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    log_error "用户取消发布"
    # 如果更新了版本，回滚
    if [[ $version_choice != "6" ]]; then
        git reset --hard HEAD~1
        log_info "已回滚版本更改"
    fi
    exit 1
fi

# 13. 执行发布
log_info "发布到NPM..."

if [[ $publish_tag == "latest" ]]; then
    npm publish --access public
else
    npm publish --access public --tag $publish_tag
fi

if [[ $? -eq 0 ]]; then
    log_success "发布成功: $(node -e "console.log(require('./package.json').name)")@$final_version"
else
    log_error "发布失败"
    # 回滚版本更改
    if [[ $version_choice != "6" ]]; then
        git reset --hard HEAD~1
        log_info "已回滚版本更改"
    fi
    exit 1
fi

# 14. 推送Git标签
if [[ $version_choice != "6" ]]; then
    log_info "推送Git标签..."
    git push origin $current_branch --tags
    log_success "Git标签已推送"
fi

# 15. 发布后验证
log_info "验证发布..."
sleep 3

if npm view $(node -e "console.log(require('./package.json').name)")@$final_version >/dev/null 2>&1; then
    log_success "包已在NPM注册表中可用"
    echo "🌐 查看: https://www.npmjs.com/package/$(node -e "console.log(require('./package.json').name)")"
else
    log_warning "包可能还未在注册表中可见（可能需要几分钟）"
fi

# 16. 测试安装
log_info "测试安装..."
temp_dir=$(mktemp -d)
cd $temp_dir

package_name=$(node -e "console.log(require('$OLDPWD/package.json').name)")

if timeout 30 npx $package_name@$final_version --help >/dev/null 2>&1; then
    log_success "npx测试成功"
else
    log_warning "npx测试失败或超时（包可能需要时间传播）"
fi

cd - >/dev/null
rm -rf $temp_dir

# 17. 完成
echo ""
log_success "🎉 发布完成!"
echo ""
echo "📋 后续步骤:"
echo "1. 创建GitHub Release: https://github.com/$(git config --get remote.origin.url | sed 's/.*github.com[:/]\([^.]*\).*/\1/')/releases/new"
echo "2. 更新文档中的安装说明"
echo "3. 通知用户新版本发布"
echo ""
echo "✨ 用户现在可以使用:"
echo "   npx $package_name"
echo "   npm install -g $package_name"

# 清理临时文件
rm -f /tmp/npm-pack-preview.txt

log_success "发布脚本执行完成" 
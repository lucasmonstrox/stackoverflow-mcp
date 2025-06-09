#!/bin/bash
# StackOverflow MCP Server - NPM发布脚本

set -e

# Task 4: 错误回滚机制
# 记录发布前状态
initial_version=""
current_tag=""
rollback_needed=false

# 错误处理函数
cleanup_and_rollback() {
    local exit_code=$?
    
    if [[ $rollback_needed == true ]] && [[ $exit_code -ne 0 ]]; then
        echo ""
        echo "💥 Publishing failed! Attempting rollback..."
        
        # 回滚版本号
        if [[ -n "$initial_version" ]]; then
            echo "🔄 Restoring package.json version to $initial_version..."
            npm version "$initial_version" --no-git-tag-version >/dev/null 2>&1 || true
        fi
        
        # 删除可能创建的Git标签
        if [[ -n "$current_tag" ]]; then
            echo "🔄 Removing Git tag $current_tag..."
            git tag -d "$current_tag" >/dev/null 2>&1 || true
        fi
        
        # 重置Git状态（如果有未推送的提交）
        echo "🔄 Checking for unpushed commits..."
        if git log @{u}.. --oneline 2>/dev/null | grep -q "^"; then
            echo "🔄 Resetting to last pushed commit..."
            git reset --hard @{u} >/dev/null 2>&1 || true
        fi
        
        echo "✅ Rollback completed"
    fi
    
    exit $exit_code
}

# 设置错误陷阱
trap cleanup_and_rollback ERR INT TERM

# Task 7: 脚本结构优化 - 命令行参数解析
show_help() {
    echo "📦 StackOverflow MCP Server - NPM Publishing Script"
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --skip-tests     Skip running tests"
    echo "  --skip-audit     Skip security audit"
    echo "  --force          Skip confirmations (use with caution)"
    echo "  --dry-run        Show what would be done without actually publishing"
    echo "  --help, -h       Show this help message"
    echo ""
    exit 0
}

# 解析命令行参数
skip_tests=false
skip_audit=false
force_publish=false
dry_run=false

while [[ $# -gt 0 ]]; do
    case $1 in
        --skip-tests)
            skip_tests=true
            shift
            ;;
        --skip-audit)
            skip_audit=true
            shift
            ;;
        --force)
            force_publish=true
            shift
            ;;
        --dry-run)
            dry_run=true
            shift
            ;;
        --help|-h)
            show_help
            ;;
        *)
            echo "❌ Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

echo "📦 StackOverflow MCP Server - NPM Publishing Script"
echo "=================================================="
if [[ $dry_run == true ]]; then
    echo "🔍 DRY RUN MODE - No actual changes will be made"
    echo "=================================================="
fi

# Task 1: 环境检查功能
echo ""
echo "🔧 Checking environment requirements..."

# 检查 Node.js 版本
if ! command -v node >/dev/null 2>&1; then
    echo "❌ Error: Node.js is not installed"
    exit 1
fi

node_version=$(node --version | sed 's/v//')
required_node="14.0.0"

# 简化版本比较 - 检查主版本号
node_major=$(echo "$node_version" | cut -d. -f1)
required_major=$(echo "$required_node" | cut -d. -f1)

if [[ $node_major -lt $required_major ]]; then
    echo "❌ Error: Node.js version $node_version is below required $required_node"
    exit 1
fi
echo "✓ Node.js version: $node_version"

# 检查 npm 版本
if ! command -v npm >/dev/null 2>&1; then
    echo "❌ Error: npm is not installed"
    exit 1
fi

npm_version=$(npm --version)
echo "✓ npm version: $npm_version"

# 验证当前工作目录是否为 Git 仓库根目录
if [[ ! -d ".git" ]]; then
    echo "❌ Error: Current directory is not a Git repository root"
    exit 1
fi
echo "✓ Git repository detected"

# 检查是否在正确的目录
if [[ ! -f "package.json" ]] || [[ ! -f "cli.js" ]]; then
    echo "❌ Error: Please run this script from the project root directory"
    exit 1
fi
echo "✓ Project structure validated"

# 检查Git状态
echo ""
echo "🔍 Checking Git status..."
if [[ -n $(git status --porcelain) ]]; then
    echo "❌ Error: Working directory is not clean. Please commit all changes first."
    git status --short
    exit 1
fi

# 检查是否在main分支
current_branch=$(git branch --show-current)
if [[ "$current_branch" != "main" ]]; then
    echo "⚠️  Warning: You are not on the main branch (current: $current_branch)"
    read -p "Continue anyway? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# 拉取最新代码
echo ""
echo "📥 Pulling latest changes..."
git pull origin $current_branch

# 检查npm登录状态
echo ""
echo "🔐 Checking NPM authentication..."
if ! npm whoami >/dev/null 2>&1; then
    echo "❌ Error: Not logged in to NPM. Please run 'npm login' first."
    exit 1
fi

current_user=$(npm whoami)
echo "✓ Logged in as: $current_user"

# Task 2: 安全审计功能
if [[ $skip_audit != true ]]; then
    echo ""
    echo "🔒 Running security audit..."
else
    echo ""
    echo "⏭️  Skipping security audit (--skip-audit specified)"
fi

if [[ $skip_audit != true ]] && command -v npm >/dev/null 2>&1; then
    # 检查是否存在 package-lock.json 或 npm-shrinkwrap.json
    if [[ ! -f "package-lock.json" ]] && [[ ! -f "npm-shrinkwrap.json" ]]; then
        echo "⚠️  Warning: No package-lock.json found. Generating one for audit..."
        npm install --package-lock-only
    fi
    
    # 运行安全审计
    echo "Running npm audit..."
    if npm audit --audit-level=moderate; then
        echo "✓ Security audit passed"
    else
        audit_exit_code=$?
        if [[ $audit_exit_code -eq 1 ]]; then
            echo "❌ Error: Security vulnerabilities found (moderate or higher)"
            echo ""
            echo "💡 To fix vulnerabilities, try:"
            echo "   npm audit fix"
            echo "   npm audit fix --force  (for breaking changes)"
            echo ""
            read -p "Continue anyway? (y/N): " -n 1 -r
            echo
            if [[ ! $REPLY =~ ^[Yy]$ ]]; then
                exit 1
            fi
        else
            echo "⚠️  Warning: npm audit failed with code $audit_exit_code"
        fi
    fi
fi

# 运行测试
if [[ $skip_tests != true ]]; then
    echo ""
    echo "🧪 Running tests..."
    if [[ $dry_run == true ]]; then
        echo "🔍 DRY RUN: Would run 'npm test'"
    elif ! npm test; then
        echo "❌ Error: Tests failed. Please fix before publishing."
        exit 1
    fi
else
    echo ""
    echo "⏭️  Skipping tests (--skip-tests specified)"
fi

# 检查打包
echo ""
echo "📋 Checking package contents..."
npm pack --dry-run

# Task 3: 包质量检查
echo ""
echo "📊 Running package quality checks..."

# 检查 package.json 必要字段
echo "Validating package.json structure..."
required_fields=("name" "version" "main" "files" "description" "keywords" "author" "license")
missing_fields=()

for field in "${required_fields[@]}"; do
    if ! jq -e ".$field" package.json >/dev/null 2>&1; then
        missing_fields+=("$field")
    fi
done

if [[ ${#missing_fields[@]} -gt 0 ]]; then
    echo "⚠️  Warning: Missing recommended package.json fields: ${missing_fields[*]}"
fi

# 检查包大小
echo "Checking package size..."
# 创建临时打包文件来检查大小
pack_output=$(npm pack 2>/dev/null | tail -n 1)
if [[ -f "$pack_output" ]]; then
    pack_size=$(stat -f%z "$pack_output" 2>/dev/null || stat -c%s "$pack_output" 2>/dev/null || echo "0")
    pack_size_mb=$((pack_size / 1024 / 1024))
    
    echo "✓ Package size: $(ls -lh "$pack_output" | awk '{print $5}') ($pack_size bytes)"
    
    if [[ $pack_size_mb -gt 1 ]]; then
        echo "⚠️  Warning: Package size is large (${pack_size_mb}MB+). Consider:"
        echo "   - Updating .npmignore to exclude unnecessary files"
        echo "   - Checking 'files' field in package.json"
    fi
    
    rm -f "$pack_output"
else
    echo "⚠️  Warning: Could not determine package size"
fi

# 检查重要文件存在性
echo "Checking required files..."
if [[ ! -f "README.md" ]]; then
    echo "⚠️  Warning: README.md not found"
fi

if [[ ! -f "LICENSE" ]] && [[ ! -f "LICENSE.md" ]] && [[ ! -f "LICENSE.txt" ]]; then
    echo "⚠️  Warning: LICENSE file not found"
fi

# 检查入口文件
main_file=$(jq -r '.main // "index.js"' package.json)
if [[ ! -f "$main_file" ]]; then
    echo "❌ Error: Main file '$main_file' not found"
    exit 1
fi
echo "✓ Main file verified: $main_file"

echo "✓ Package quality checks completed"

# 询问版本类型
echo ""
initial_version=$(npm version --json | jq -r '.["stackoverflow-mcp"]')
echo "📊 Current version: $initial_version"
# Task 5: 增强版本管理
echo "Select version bump type:"
echo "1) patch (bug fixes)     - e.g., 0.1.0 → 0.1.1"
echo "2) minor (new features)  - e.g., 0.1.0 → 0.2.0" 
echo "3) major (breaking)      - e.g., 0.1.0 → 1.0.0"
echo "4) prerelease alpha      - e.g., 0.1.0 → 0.1.1-alpha.0"
echo "5) prerelease beta       - e.g., 0.1.0 → 0.1.1-beta.0"
echo "6) prerelease rc         - e.g., 0.1.0 → 0.1.1-rc.0"
echo "7) custom version"
echo "8) skip version bump"

read -p "Enter choice (1-8): " version_choice

npm_tag="latest"  # Default npm tag

case $version_choice in
    1)
        echo "Bumping patch version..."
        rollback_needed=true
        if [[ $dry_run == true ]]; then
            echo "🔍 DRY RUN: Would run 'npm version patch'"
            new_version="${initial_version%.*}.$((${initial_version##*.} + 1))"
        else
            npm version patch
        fi
        ;;
    2)
        echo "Bumping minor version..."
        rollback_needed=true
        if [[ $dry_run == true ]]; then
            echo "🔍 DRY RUN: Would run 'npm version minor'"
            new_version="${initial_version%.*.*}.$((${initial_version#*.} + 1)).0"
        else
            npm version minor
        fi
        ;;
    3)
        echo "Bumping major version..."
        rollback_needed=true
        if [[ $dry_run == true ]]; then
            echo "🔍 DRY RUN: Would run 'npm version major'"
            new_version="$((${initial_version%%.*} + 1)).0.0"
        else
            npm version major
        fi
        ;;
    4)
        echo "Creating alpha prerelease..."
        rollback_needed=true
        npm_tag="alpha"
        if [[ $dry_run == true ]]; then
            echo "🔍 DRY RUN: Would run 'npm version prerelease --preid=alpha'"
            new_version="${initial_version}-alpha.0"
        else
            npm version prerelease --preid=alpha
        fi
        ;;
    5)
        echo "Creating beta prerelease..."
        rollback_needed=true
        npm_tag="beta"
        if [[ $dry_run == true ]]; then
            echo "🔍 DRY RUN: Would run 'npm version prerelease --preid=beta'"
            new_version="${initial_version}-beta.0"
        else
            npm version prerelease --preid=beta
        fi
        ;;
    6)
        echo "Creating release candidate..."
        rollback_needed=true
        npm_tag="rc"
        if [[ $dry_run == true ]]; then
            echo "🔍 DRY RUN: Would run 'npm version prerelease --preid=rc'"
            new_version="${initial_version}-rc.0"
        else
            npm version prerelease --preid=rc
        fi
        ;;
    7)
        read -p "Enter custom version (e.g., 1.2.3 or 1.2.3-alpha.1): " custom_version
        rollback_needed=true
        if [[ $dry_run == true ]]; then
            echo "🔍 DRY RUN: Would run 'npm version $custom_version'"
            new_version="$custom_version"
        else
            npm version $custom_version
        fi
        # Detect prerelease tag from version
        if [[ "$custom_version" =~ -alpha ]]; then
            npm_tag="alpha"
        elif [[ "$custom_version" =~ -beta ]]; then
            npm_tag="beta"
        elif [[ "$custom_version" =~ -rc ]]; then
            npm_tag="rc"
        fi
        ;;
    8)
        echo "Skipping version bump..."
        ;;
    *)
        echo "❌ Invalid choice. Exiting."
        exit 1
        ;;
esac

if [[ $dry_run != true ]]; then
    new_version=$(npm version --json | jq -r '.["stackoverflow-mcp"]')
fi
if [[ $rollback_needed == true ]]; then
    current_tag="v$new_version"
fi
echo "✓ Version: $new_version"

# Task 6: 发布前确认和日志
echo ""
echo "🚀 Ready to publish!"
echo "================================="
echo "Package: stackoverflow-mcp@$new_version"
echo "User: $current_user"
echo "Registry: $(npm config get registry)"
echo "NPM Tag: $npm_tag"
if [[ $rollback_needed == true ]]; then
    echo "Version changed: $initial_version → $new_version"
fi
echo "Timestamp: $(date)"
echo "================================="

# 记录到日志文件
log_file="publish.log"
echo "$(date): Attempting to publish stackoverflow-mcp@$new_version (tag: $npm_tag) by $current_user" >> "$log_file"

if [[ $force_publish != true ]]; then
    read -p "Proceed with publishing? (y/N): " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        echo "Publishing cancelled by user."
        echo "$(date): Publishing cancelled by user" >> "$log_file"
        exit 0
    fi
else
    echo "🚀 Force mode enabled - proceeding without confirmation"
fi

# 发布到NPM
echo ""
if [[ $dry_run == true ]]; then
    echo "🔍 DRY RUN: Would publish to NPM..."
    if [[ "$npm_tag" != "latest" ]]; then
        echo "🔍 DRY RUN: Would run 'npm publish --access public --tag $npm_tag'"
    else
        echo "🔍 DRY RUN: Would run 'npm publish --access public'"
    fi
    publish_success=true  # Simulate success for dry run
else
    echo "📤 Publishing to NPM..."
    if [[ "$npm_tag" != "latest" ]]; then
        echo "Publishing with tag: $npm_tag"
        npm publish --access public --tag $npm_tag
        publish_success=$?
    else
        npm publish --access public
        publish_success=$?
    fi
fi

if [[ $publish_success -eq 0 ]] || [[ $dry_run == true ]]; then
    if [[ $dry_run == true ]]; then
        echo "🔍 DRY RUN: Publishing would have succeeded"
    else
        echo "✅ Successfully published stackoverflow-mcp@$new_version"
        echo "$(date): Successfully published stackoverflow-mcp@$new_version (tag: $npm_tag)" >> "$log_file"
        rollback_needed=false  # 发布成功后禁用回滚
    fi
else
    echo "❌ Publishing failed!"
    echo "$(date): Publishing failed for stackoverflow-mcp@$new_version" >> "$log_file"
    exit 1
fi

# 推送Git标签
if [[ $version_choice != "5" ]]; then
    echo ""
    echo "📤 Pushing Git tags..."
    git push origin $current_branch --tags
fi

# 验证发布
echo ""
echo "🔍 Verifying publication..."
sleep 5  # Wait for NPM to update

if npm view stackoverflow-mcp@$new_version >/dev/null 2>&1; then
    echo "✅ Package verified on NPM registry"
    echo "🌐 View at: https://www.npmjs.com/package/stackoverflow-mcp"
else
    echo "⚠️  Warning: Package not yet visible on registry (may take a few minutes)"
fi

# 测试npx
echo ""
echo "🧪 Testing npx installation..."
temp_dir=$(mktemp -d)
cd $temp_dir

if timeout 30 npx stackoverflow-mcp@$new_version --help >/dev/null 2>&1; then
    echo "✅ npx test successful"
else
    echo "⚠️  npx test failed or timed out (may take time to propagate)"
fi

cd - >/dev/null
rm -rf $temp_dir

echo ""
echo "🎉 Publishing complete!"
echo ""
echo "📋 Next steps:"
echo "1. Update documentation to use 'npx stackoverflow-mcp'"
echo "2. Create GitHub Release: https://github.com/NoTalkTech/stackoverflow-mcp/releases/new"
echo "3. Update Cursor MCP configurations to use the published package"
echo ""
echo "✨ Users can now install with:"
echo "   npx stackoverflow-mcp"
echo "   npm install -g stackoverflow-mcp" 
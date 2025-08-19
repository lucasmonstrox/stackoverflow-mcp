#!/bin/bash
# StackOverflow MCP Server - 统一发布脚本
# 同时发布 NPM 包和 Python 包

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

# PyPI authentication functions
setup_pypi_auth() {
    echo "Setting up PyPI authentication..."
    
    # Check for .pypirc file first
    local pypirc_file="$HOME/.pypirc"
    local pypirc_supported=false
    
    if [[ -f "$pypirc_file" ]]; then
        echo "✓ Found .pypirc file at $pypirc_file"
        
        # Check if it has the required sections
        if [[ $use_test_pypi == true ]]; then
            if grep -q "\[testpypi\]" "$pypirc_file"; then
                echo "✓ Test PyPI configuration found in .pypirc"
                pypirc_supported=true
            fi
        else
            if grep -q "\[pypi\]" "$pypirc_file"; then
                echo "✓ PyPI configuration found in .pypirc"
                pypirc_supported=true
            fi
        fi
    fi
    
    # If .pypirc is not available or doesn't have required sections, check environment variables
    if [[ $pypirc_supported != true ]]; then
        if [[ $use_test_pypi == true ]]; then
            if [[ -z "$TEST_PYPI_API_TOKEN" ]]; then
                echo "⚠️  Warning: TEST_PYPI_API_TOKEN not set and no .pypirc configuration found."
                echo ""
                echo "To set up Test PyPI authentication, choose one of:"
                echo ""
                echo "1. Environment variable (current session):"
                echo "   export TEST_PYPI_API_TOKEN=pypi-your-token"
                echo ""
                echo "2. Create .pypirc file (persistent):"
                echo "   cat > ~/.pypirc << EOF"
                echo "   [distutils]"
                echo "   index-servers = testpypi"
                echo "   "
                echo "   [testpypi]"
                echo "   repository = https://test.pypi.org/legacy/"
                echo "   username = __token__"
                echo "   password = pypi-your-token"
                echo "   EOF"
                echo ""
                echo "3. Get Test PyPI token at: https://test.pypi.org/manage/account/token/"
                echo ""
                return 1
            else
                # Validate token format
                if ! validate_pypi_token "$TEST_PYPI_API_TOKEN"; then
                    echo "❌ Error: Invalid TEST_PYPI_API_TOKEN format"
                    return 1
                fi
                echo "✓ Test PyPI token configured via environment variable"
            fi
        else
            if [[ -z "$PYPI_API_TOKEN" ]]; then
                echo "❌ Error: PYPI_API_TOKEN not set and no .pypirc configuration found."
                echo ""
                echo "To set up PyPI authentication, choose one of:"
                echo ""
                echo "1. Environment variable (current session):"
                echo "   export PYPI_API_TOKEN=pypi-your-token"
                echo ""
                echo "2. Create .pypirc file (persistent):"
                echo "   cat > ~/.pypirc << EOF"
                echo "   [distutils]"
                echo "   index-servers = pypi"
                echo "   "
                echo "   [pypi]"
                echo "   repository = https://upload.pypi.org/legacy/"
                echo "   username = __token__"
                echo "   password = pypi-your-token"
                echo "   EOF"
                echo ""
                echo "3. Get PyPI token at: https://pypi.org/manage/account/token/"
                echo "   - Recommended: Create a project-scoped token for 'stackoverflow-fastmcp'"
                echo ""
                return 1
            else
                # Validate token format
                if ! validate_pypi_token "$PYPI_API_TOKEN"; then
                    echo "❌ Error: Invalid PYPI_API_TOKEN format"
                    return 1
                fi
                echo "✓ PyPI token configured via environment variable"
            fi
        fi
    fi
    
    return 0
}

validate_pypi_token() {
    local token="$1"
    
    # PyPI tokens should start with 'pypi-' and be base64-like
    if [[ ! "$token" =~ ^pypi-[A-Za-z0-9_-]{32,}$ ]]; then
        echo "❌ Invalid token format. PyPI tokens should:"
        echo "   - Start with 'pypi-'"
        echo "   - Be followed by base64-like characters"
        echo "   - Be at least 36 characters long"
        echo ""
        echo "Example: pypi-AgEIcHlwaS5vcmcCJGFiY2RlZi0xMjM0LTU2NzgtOWFiYy1kZWYwMTIzNDU2Nzg"
        return 1
    fi
    
    return 0
}

# Python package build and test functions
build_python_package() {
    echo ""
    echo "🔨 Building Python package..."
    
    # Clean previous builds
    if [[ -d "dist" ]]; then
        echo "Cleaning previous build artifacts..."
        rm -rf dist/
    fi
    
    # Build package
    echo "Building package with uv..."
    if [[ $dry_run == true ]]; then
        echo "[DRY RUN] Would run: uv build"
    else
        if ! uv build; then
            echo "❌ Error: Failed to build Python package"
            return 1
        fi
    fi
    
    # Verify build artifacts
    if [[ $dry_run != true ]]; then
        if [[ ! -d "dist" ]] || [[ -z "$(ls -A dist/)" ]]; then
            echo "❌ Error: No build artifacts found in dist/"
            return 1
        fi
        
        echo "✓ Build artifacts created:"
        ls -la dist/
        
        # Basic package validation
        local wheel_file=$(find dist/ -name "*.whl" | head -1)
        local tar_file=$(find dist/ -name "*.tar.gz" | head -1)
        
        if [[ -n "$wheel_file" ]]; then
            echo "✓ Wheel package: $(basename "$wheel_file")"
        fi
        
        if [[ -n "$tar_file" ]]; then
            echo "✓ Source package: $(basename "$tar_file")"
        fi
    fi
    
    return 0
}

test_python_package() {
    echo ""
    echo "🧪 Testing Python package..."
    
    if [[ $dry_run == true ]]; then
        echo "[DRY RUN] Would run basic import tests"
        return 0
    fi
    
    # Test basic import
    echo "Testing package import..."
    if ! python -c "import sys; sys.path.insert(0, 'src'); import stackoverflow_mcp; print('✓ Package import successful')"; then
        echo "❌ Error: Failed to import package"
        return 1
    fi
    
    # Test CLI entry point
    echo "Testing CLI entry point..."
    if ! python -m stackoverflow_mcp --help >/dev/null 2>&1; then
        echo "⚠️  Warning: CLI entry point test failed (this might be expected in some environments)"
    else
        echo "✓ CLI entry point working"
    fi
    
    return 0
}

# PyPI package status check functions
check_pypi_package_status() {
    echo ""
    echo "🔍 Checking PyPI package status..."
    
    # Get package name and version from pyproject.toml
    local package_name=$(grep '^name = ' pyproject.toml | sed 's/name = "\(.*\)"/\1/')
    local package_version=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
    
    if [[ -z "$package_name" ]] || [[ -z "$package_version" ]]; then
        echo "❌ Error: Could not extract package name or version from pyproject.toml"
        return 1
    fi
    
    echo "Package: $package_name"
    echo "Version: $package_version"
    
    # Determine PyPI URL based on test mode
    local pypi_url
    if [[ $use_test_pypi == true ]]; then
        pypi_url="https://test.pypi.org/pypi"
        echo "Target: Test PyPI"
    else
        pypi_url="https://pypi.org/pypi"
        echo "Target: Production PyPI"
    fi
    
    # Check if package exists
    echo "Checking package existence..."
    local package_info
    if package_info=$(curl -s "$pypi_url/$package_name/json" 2>/dev/null); then
        if echo "$package_info" | grep -q '"message": "Not Found"'; then
            echo "✓ Package does not exist yet - ready for first release"
            return 0
        else
            echo "✓ Package exists on PyPI"
            
            # Check if this version already exists
            if echo "$package_info" | grep -q "\"$package_version\""; then
                echo "❌ Error: Version $package_version already exists on PyPI"
                echo ""
                echo "Available options:"
                echo "1. Bump version in pyproject.toml"
                echo "2. Use --test-pypi for testing"
                echo "3. Delete the version (if it's on Test PyPI)"
                echo ""
                return 1
            else
                echo "✓ Version $package_version is available"
                
                # Show latest version
                local latest_version=$(echo "$package_info" | python3 -c "
import sys, json
data = json.load(sys.stdin)
print(data['info']['version'])
" 2>/dev/null || echo "unknown")
                echo "Latest version on PyPI: $latest_version"
            fi
        fi
    else
        echo "⚠️  Warning: Could not check package status (network issue?)"
        echo "Proceeding with caution..."
    fi
    
    return 0
}

# Secure PyPI publishing function
secure_publish_python() {
    echo ""
    echo "📦 Publishing Python package to PyPI..."
    
    # Set up environment for uv publish
    local publish_env=""
    
    # Determine which token to use
    if [[ $use_test_pypi == true ]]; then
        if [[ -n "$TEST_PYPI_API_TOKEN" ]]; then
            publish_env="UV_PUBLISH_TOKEN=$TEST_PYPI_API_TOKEN"
            echo "Using Test PyPI with environment token"
        else
            echo "Using Test PyPI with .pypirc configuration"
        fi
    else
        if [[ -n "$PYPI_API_TOKEN" ]]; then
            publish_env="UV_PUBLISH_TOKEN=$PYPI_API_TOKEN"
            echo "Using production PyPI with environment token"
        else
            echo "Using production PyPI with .pypirc configuration"
        fi
    fi
    
    # Prepare publish command
    local publish_cmd="uv publish"
    
    if [[ $use_test_pypi == true ]]; then
        publish_cmd="$publish_cmd --publish-url https://test.pypi.org/legacy/"
    fi
    
    # Execute publish
    if [[ $dry_run == true ]]; then
        echo "[DRY RUN] Would run: $publish_env $publish_cmd"
        echo "[DRY RUN] Publishing to: $(if [[ $use_test_pypi == true ]]; then echo 'Test PyPI'; else echo 'Production PyPI'; fi)"
    else
        echo "Publishing package..."
        if [[ -n "$publish_env" ]]; then
            if ! env $publish_env $publish_cmd; then
                echo "❌ Error: Failed to publish Python package"
                return 1
            fi
        else
            if ! $publish_cmd; then
                echo "❌ Error: Failed to publish Python package"
                return 1
            fi
        fi
        
        echo "✓ Python package published successfully!"
    fi
    
    return 0
}

# PyPI publication verification function
verify_pypi_publication() {
    echo ""
    echo "🔍 Verifying PyPI publication..."
    
    # Get package name and version from pyproject.toml
    local package_name=$(grep '^name = ' pyproject.toml | sed 's/name = "\(.*\)"/\1/')
    local package_version=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
    
    # Determine PyPI URL based on test mode
    local pypi_url
    local pypi_name
    if [[ $use_test_pypi == true ]]; then
        pypi_url="https://test.pypi.org/pypi"
        pypi_name="Test PyPI"
    else
        pypi_url="https://pypi.org/pypi"
        pypi_name="PyPI"
    fi
    
    echo "Checking $package_name@$package_version on $pypi_name..."
    
    # Wait a moment for PyPI to update
    sleep 3
    
    # Verify package exists
    local package_info
    if package_info=$(curl -s "$pypi_url/$package_name/json" 2>/dev/null); then
        if echo "$package_info" | grep -q "\"$package_version\""; then
            echo "✅ Package verified on $pypi_name"
            
            # Show package details
            local package_url
            if [[ $use_test_pypi == true ]]; then
                package_url="https://test.pypi.org/project/$package_name/"
            else
                package_url="https://pypi.org/project/$package_name/"
            fi
            
            echo "🌐 View at: $package_url"
            echo "📦 Install with: pip install $(if [[ $use_test_pypi == true ]]; then echo '--index-url https://test.pypi.org/simple/ '; fi)$package_name"
            
            return 0
        else
            echo "⚠️  Warning: Package exists but version $package_version not found"
            return 1
        fi
    else
        echo "⚠️  Warning: Could not verify package on $pypi_name (may take time to propagate)"
        return 1
    fi
}

# Task 7: 脚本结构优化 - 命令行参数解析
show_help() {
    echo "📦 StackOverflow MCP Server - 统一发布脚本"
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --skip-tests     Skip running tests"
    echo "  --skip-audit     Skip security audit"
    echo "  --force          Skip confirmations (use with caution)"
    echo "  --dry-run        Show what would be done without actually publishing"
    echo "  --npm-only       Only publish NPM package"
    echo "  --python-only    Only publish Python package"
    echo "  --test-pypi      Use Test PyPI for Python package"
    echo "  --help, -h       Show this help message"
    echo ""
    echo "Environment variables:"
    echo "  PYPI_API_TOKEN       - Token for production PyPI"
    echo "  TEST_PYPI_API_TOKEN  - Token for Test PyPI (optional)"
    echo ""
    exit 0
}

# 解析命令行参数
skip_tests=false
skip_audit=false
force_publish=false
dry_run=false
npm_only=false
python_only=false
use_test_pypi=false

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
        --npm-only)
            npm_only=true
            shift
            ;;
        --python-only)
            python_only=true
            shift
            ;;
        --test-pypi)
            use_test_pypi=true
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

echo "📦 StackOverflow MCP Server - 统一发布脚本"
echo "=================================================="
if [[ $dry_run == true ]]; then
    echo "🔍 DRY RUN MODE - No actual changes will be made"
    echo "=================================================="
fi

# Task 1: 环境检查功能
echo ""
echo "🔧 Checking environment requirements..."

# 检查 Python 环境 (如果需要发布 Python 包)
if [[ $npm_only != true ]]; then
    echo "Checking Python environment..."
    
    # 检查 uv
    if ! command -v uv >/dev/null 2>&1; then
        echo "❌ Error: uv is not installed. Please install it first:"
        echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
        exit 1
    fi
    echo "✓ uv version: $(uv --version)"
    
    # 检查 pyproject.toml
    if [[ ! -f "pyproject.toml" ]]; then
        echo "❌ Error: pyproject.toml not found"
        exit 1
    fi
    echo "✓ Python project structure validated"
fi

# 检查 Node.js 版本 (如果需要发布 NPM 包)
if [[ $python_only != true ]]; then
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
fi

# 验证当前工作目录是否为 Git 仓库根目录
if [[ ! -d ".git" ]]; then
    echo "❌ Error: Current directory is not a Git repository root"
    exit 1
fi
echo "✓ Git repository detected"

# 检查是否在正确的目录
if [[ $python_only != true ]] && ([[ ! -f "package.json" ]] || [[ ! -f "cli.js" ]]); then
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

# 检查认证状态
echo ""
echo "🔐 Checking authentication..."

if [[ $python_only != true ]]; then
    # 检查npm登录状态
    echo "Checking NPM authentication..."
    if ! npm whoami >/dev/null 2>&1; then
        echo "❌ Error: Not logged in to NPM. Please run 'npm login' first."
        exit 1
    fi
    current_user=$(npm whoami)
    echo "✓ NPM logged in as: $current_user"
fi

if [[ $npm_only != true ]]; then
    # 检查PyPI认证
    echo "Checking PyPI authentication..."
    if ! setup_pypi_auth; then
        exit 1
    fi
fi

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

# Python package processing (if needed)
if [[ $npm_only != true ]]; then
    # Check PyPI package status
    if ! check_pypi_package_status; then
        exit 1
    fi
    
    # Build Python package
    if ! build_python_package; then
        exit 1
    fi
    
    # Test Python package
    if [[ $skip_tests != true ]]; then
        if ! test_python_package; then
            exit 1
        fi
    fi
    
    # Publish Python package (before NPM to ensure dependency availability)
    if ! secure_publish_python; then
        exit 1
    fi
    
    # Verify Python package publication
    if [[ $dry_run != true ]]; then
        verify_pypi_publication
    fi
fi

# NPM package processing (if needed)
if [[ $python_only == true ]]; then
    echo ""
    echo "🎉 Python package publishing complete!"
    echo ""
    echo "📋 Next steps:"
    echo "1. Test the published package: pip install stackoverflow-fastmcp"
    echo "2. Update NPM package to reference the new Python version"
    echo "3. Create GitHub Release"
    echo ""
    exit 0
fi

# 询问版本类型
echo ""
initial_version=$(npm version --json | jq -r '.["@luqezman/stackoverflow-mcp"]')
echo "📊 Current NPM version: $initial_version"
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
    new_version=$(npm version --json | jq -r '.["@luqezman/stackoverflow-mcp"]')
fi
if [[ $rollback_needed == true ]]; then
    current_tag="v$new_version"
fi
echo "✓ Version: $new_version"

# Task 6: 发布前确认和日志
echo ""
echo "🚀 Ready to publish!"
echo "================================="
echo "Package: @luqezman/stackoverflow-mcp@$new_version"
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
echo "$(date): Attempting to publish @luqezman/stackoverflow-mcp@$new_version (tag: $npm_tag) by $current_user" >> "$log_file"

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
        echo "✅ Successfully published @luqezman/stackoverflow-mcp@$new_version"
        echo "$(date): Successfully published @luqezman/stackoverflow-mcp@$new_version (tag: $npm_tag)" >> "$log_file"
        rollback_needed=false  # 发布成功后禁用回滚
    fi
else
    echo "❌ Publishing failed!"
    echo "$(date): Publishing failed for @luqezman/stackoverflow-mcp@$new_version" >> "$log_file"
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

if npm view @luqezman/stackoverflow-mcp@$new_version >/dev/null 2>&1; then
    echo "✅ Package verified on NPM registry"
    echo "🌐 View at: https://www.npmjs.com/package/@luqezman/stackoverflow-mcp"
else
    echo "⚠️  Warning: Package not yet visible on registry (may take a few minutes)"
fi

# 测试npx
echo ""
echo "🧪 Testing npx installation..."
temp_dir=$(mktemp -d)
cd $temp_dir

if timeout 30 npx @luqezman/stackoverflow-mcp@$new_version --help >/dev/null 2>&1; then
    echo "✅ npx test successful"
else
    echo "⚠️  npx test failed or timed out (may take time to propagate)"
fi

cd - >/dev/null
rm -rf $temp_dir

echo ""
echo "🎉 Publishing complete!"
echo ""

# Show published packages summary
echo "📦 Published packages:"
if [[ $npm_only != true ]]; then
    local package_name=$(grep '^name = ' pyproject.toml | sed 's/name = "\(.*\)"/\1/')
    local package_version=$(grep '^version = ' pyproject.toml | sed 's/version = "\(.*\)"/\1/')
    echo "   🐍 Python: $package_name@$package_version"
    if [[ $use_test_pypi == true ]]; then
        echo "      📍 Test PyPI: https://test.pypi.org/project/$package_name/"
    else
        echo "      📍 PyPI: https://pypi.org/project/$package_name/"
    fi
fi
if [[ $python_only != true ]]; then
    echo "   📦 NPM: @luqezman/stackoverflow-mcp@$new_version"
    echo "      📍 NPM: https://www.npmjs.com/package/@luqezman/stackoverflow-mcp"
fi

echo ""
echo "📋 Next steps:"
echo "1. Update documentation to use 'npx @luqezman/stackoverflow-mcp'"
echo "2. Create GitHub Release: https://github.com/lucasmonstrox/stackoverflow-mcp/releases/new"
echo "3. Update Cursor MCP configurations to use the published package"
if [[ $npm_only != true ]]; then
    echo "4. Test Python package installation and functionality"
fi

echo ""
echo "✨ Users can now install with:"
if [[ $python_only != true ]]; then
    echo "   npx @luqezman/stackoverflow-mcp"
    echo "   npm install -g @luqezman/stackoverflow-mcp"
fi
if [[ $npm_only != true ]]; then
    local package_name=$(grep '^name = ' pyproject.toml | sed 's/name = "\(.*\)"/\1/')
    if [[ $use_test_pypi == true ]]; then
        echo "   pip install --index-url https://test.pypi.org/simple/ $package_name"
    else
        echo "   pip install $package_name"
    fi
fi 
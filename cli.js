#!/usr/bin/env node

/**
 * StackOverflow MCP Server - NPX CLI Wrapper
 * 
 * This script provides npx compatibility for the Python-based StackOverflow MCP server.
 * It automatically handles Python environment detection, package installation, and 
 * working directory configuration.
 */

const { spawn } = require('child_process');
const { existsSync } = require('fs');
const path = require('path');
const os = require('os');

class StackOverflowMCPCLI {
    constructor() {
        this.pythonCommands = ['python3', 'python'];
        this.packageName = 'stackoverflow-fastmcp';
        this.expectedVersion = '0.2.1';  // Expected complete version
        this.verbose = process.argv.includes('--verbose') || process.argv.includes('-v');
        // Detect MCP mode - should be silent for stdio communication
        this.isMCPMode = this.detectMCPMode();
        // Check for force reinstall flag
        this.forceReinstall = process.argv.includes('--force-reinstall');
    }

    detectMCPMode() {
        // MCP mode detection: no --help, has --port, or called via MCP
        const args = process.argv.slice(2);
        const hasPort = args.includes('--port');
        const hasHelp = args.includes('--help') || args.includes('-h');
        const isStdio = !hasPort && !hasHelp; // Default MCP uses stdio
        
        return (hasPort || isStdio) && !hasHelp;
    }

    log(message) {
        if (this.verbose && !this.isMCPMode) {
            console.log(`[stackoverflow-fastmcp] ${message}`);
        }
    }

    error(message) {
        if (!this.isMCPMode) {
            console.error(`[stackoverflow-fastmcp] ERROR: ${message}`);
        }
    }

    info(message) {
        if (!this.isMCPMode) {
            console.log(message);
        }
    }

    async findPython() {
        for (const cmd of this.pythonCommands) {
            try {
                const result = await this.runCommand(cmd, ['--version'], { stdio: 'pipe' });
                if (result.code === 0) {
                    const version = result.stdout.toString().trim();
                    this.log(`Found Python: ${cmd} (${version})`);
                    return cmd;
                }
            } catch (error) {
                this.log(`${cmd} not found: ${error.message}`);
            }
        }
        throw new Error('Python 3.12+ is required but not found. Please install Python from https://www.python.org/');
    }

    async runCommand(command, args = [], options = {}) {
        return new Promise((resolve, reject) => {
            const defaultOptions = {
                stdio: 'inherit',
                cwd: process.cwd(),
                env: process.env
            };
            
            const mergedOptions = { ...defaultOptions, ...options };
            
            this.log(`Running: ${command} ${args.join(' ')}`);
            
            const child = spawn(command, args, mergedOptions);
            
            let stdout = '';
            let stderr = '';
            
            if (child.stdout) {
                child.stdout.on('data', (data) => {
                    stdout += data.toString();
                });
            }
            
            if (child.stderr) {
                child.stderr.on('data', (data) => {
                    stderr += data.toString();
                });
            }
            
            child.on('close', (code) => {
                resolve({
                    code,
                    stdout,
                    stderr
                });
            });
            
            child.on('error', (error) => {
                reject(error);
            });
        });
    }

    async checkPackageInstalled(pythonCmd) {
        try {
            // The Python module name is stackoverflow_mcp (not stackoverflow_fastmcp)
            const moduleName = 'stackoverflow_mcp';
            const result = await this.runCommand(pythonCmd, ['-c', `import ${moduleName}`], { stdio: 'pipe' });
            return result.code === 0;
        } catch (error) {
            return false;
        }
    }

    async checkPackageVersion(pythonCmd) {
        try {
            const result = await this.runCommand(pythonCmd, ['-c', 
                `import ${this.packageName.replace('-', '_')}; print(${this.packageName.replace('-', '_')}.__version__)`
            ], { stdio: 'pipe' });
            
            if (result.code === 0) {
                const installedVersion = result.stdout.trim();
                this.log(`Installed version: ${installedVersion}, Expected: ${this.expectedVersion}`);
                return {
                    installed: true,
                    version: installedVersion,
                    isLatest: installedVersion === this.expectedVersion,
                    needsUpdate: installedVersion !== this.expectedVersion
                };
            }
        } catch (error) {
            this.log(`Version check failed: ${error.message}`);
        }
        
        return {
            installed: false,
            version: null,
            isLatest: false,
            needsUpdate: true
        };
    }

    async checkUvAvailable() {
        try {
            const result = await this.runCommand('uv', ['--version'], { stdio: 'pipe' });
            if (result.code === 0) {
                this.log(`Found uv: ${result.stdout.trim()}`);
                return true;
            }
            return false;
        } catch (error) {
            this.log('uv not found in PATH');
            return false;
        }
    }

    async ensureUvVirtualEnv() {
        const homeDir = os.homedir();
        const venvPath = path.join(homeDir, '.stackoverflow-mcp-venv');
        
        // Check if virtual environment already exists
        if (existsSync(venvPath)) {
            this.log(`Using existing virtual environment at ${venvPath}`);
            return { hasVenv: true, venvPath };
        }
        
        this.info(`🔧 Creating virtual environment at ${venvPath}...`);
        
        try {
            // Create virtual environment with completely isolated settings
            const createEnv = {
                HOME: process.env.HOME,
                PATH: process.env.PATH,
                USER: process.env.USER || 'user',
                LANG: process.env.LANG || 'en_US.UTF-8',
                // Strong isolation flags
                UV_NO_PROJECT: '1',
                UV_CACHE_DIR: path.join(venvPath, '.uv-cache'),
                // Clear any existing virtual environment variables
                VIRTUAL_ENV: undefined,
                UV_PROJECT_ENVIRONMENT: undefined,
                CONDA_DEFAULT_ENV: undefined,
                CONDA_PREFIX: undefined,
                PYENV_VERSION: undefined
            };
            
            const createResult = await this.runCommand('uv', ['venv', venvPath, '--python', '3.12'], { 
                stdio: 'pipe',
                env: createEnv,
                cwd: '/tmp'  // Run from neutral directory
            });
            
            if (createResult.code !== 0) {
                this.log(`Failed to create virtual environment: ${createResult.stderr}`);
                // Try without specific Python version
                const createFallback = await this.runCommand('uv', ['venv', venvPath], { 
                    stdio: 'pipe',
                    env: createEnv,
                    cwd: '/tmp'  // Run from neutral directory
                });
                if (createFallback.code !== 0) {
                    this.log(`Fallback creation also failed: ${createFallback.stderr}`);
                    return { hasVenv: false, venvPath: null };
                }
            }
            
            this.info(`✅ Created virtual environment at ${venvPath}`);
            return { hasVenv: true, venvPath };
            
        } catch (error) {
            this.log(`Virtual environment creation failed: ${error.message}`);
            return { hasVenv: false, venvPath: null };
        }
    }

    async installPackage(pythonCmd) {
        this.log(`Installing ${this.packageName} Python package...`);
        
        // Check if uv is available
        const uvAvailable = await this.checkUvAvailable();
        if (!uvAvailable) {
            this.error('uv is required but not available');
            this.info('📥 Please install uv: curl -LsSf https://astral.sh/uv/install.sh | sh');
            return false;
        }

        // Ensure virtual environment
        const uvEnvInfo = await this.ensureUvVirtualEnv();
        if (!uvEnvInfo.hasVenv) {
            this.error('Failed to create or use virtual environment');
            return false;
        }

        // Install package using uv in the virtual environment
        try {
            this.log('Installing package with uv...');
            const packageSpec = `${this.packageName}==${this.expectedVersion}`;
            const uvArgs = ['--python-preference', 'only-managed', 'pip', 'install', packageSpec];
            
            // Create completely isolated environment
            const cleanEnv = {
                HOME: process.env.HOME,
                PATH: process.env.PATH,
                USER: process.env.USER || 'user',
                LANG: process.env.LANG || 'en_US.UTF-8',
                // Set virtual environment
                UV_PROJECT_ENVIRONMENT: uvEnvInfo.venvPath,
                // Strong isolation flags
                UV_NO_PROJECT: '1',
                UV_CACHE_DIR: path.join(uvEnvInfo.venvPath, '.uv-cache'),
                // Clear any existing virtual environment variables
                VIRTUAL_ENV: undefined,
                CONDA_DEFAULT_ENV: undefined,
                CONDA_PREFIX: undefined,
                PYENV_VERSION: undefined
            };

            const uvOptions = {
                env: cleanEnv,
                cwd: '/tmp'  // Run from a neutral directory
            };

            this.log(`Installing in isolated virtual environment at ${uvEnvInfo.venvPath}`);
            const result = await this.runCommand('uv', uvArgs, uvOptions);
            
            if (result.code === 0) {
                this.info(`✅ Successfully installed ${this.packageName} (via uv)`);
                return true;
            } else {
                this.error('Failed to install package with uv');
                return false;
            }
        } catch (error) {
            this.error(`Package installation failed: ${error.message}`);
            return false;
        }
    }

    async detectWorkingDirectory() {
        const cwd = process.cwd();
        const indicators = [
            'pyproject.toml',
            'package.json',
            '.git',
            '.stackoverflow-mcp.json',
            'stackoverflow-mcp.config.json'
        ];

        // Check current directory
        for (const indicator of indicators) {
            if (existsSync(path.join(cwd, indicator))) {
                this.log(`Detected project directory from ${indicator}: ${cwd}`);
                return cwd;
            }
        }

        // Check parent directories
        let current = cwd;
        while (current !== path.dirname(current)) {
            current = path.dirname(current);
            for (const indicator of indicators) {
                if (existsSync(path.join(current, indicator))) {
                    this.log(`Found project directory: ${current}`);
                    return current;
                }
            }
        }

        this.log(`Using current working directory: ${cwd}`);
        return cwd;
    }

    filterCliArgs(args) {
        // Filter out Node.js specific arguments and pass through relevant ones
        const filteredArgs = args.filter(arg => {
            return !arg.startsWith('--inspect') && 
                   !arg.startsWith('--debug') &&
                   arg !== '--verbose' &&  // Handle this in Node.js wrapper
                   arg !== '-v';
        });

        // Add verbose flag for Python if enabled
        if (this.verbose && !filteredArgs.includes('--log-level')) {
            filteredArgs.push('--log-level', 'DEBUG');
        }

        return filteredArgs;
    }

    async main() {
        try {
            this.info('🔧 StackOverflow MCP Server (npx wrapper)');
            this.info('');

            // Check if in test mode
            if (process.env.TEST_MODE === '1') {
                console.log('🧪 Test mode - skipping Python package installation');
                console.log('');
                console.log('Usage: python -m stackoverflow_mcp [OPTIONS]');
                console.log('');
                console.log('  StackOverflow MCP Server using FastMcp framework.');
                console.log('');
                console.log('  A simplified, elegant implementation providing StackOverflow search');
                console.log('  capabilities through the Model Context Protocol.');
                console.log('');
                console.log('Options:');
                console.log('  --host TEXT                     Host to bind the server to');
                console.log('  --port INTEGER                  Port to bind the server to');
                console.log('  --log-level [DEBUG|INFO|WARNING|ERROR]');
                console.log('                                  Logging level');
                console.log('  --config-file FILE              Path to configuration file (auto-discover if');
                console.log('                                  not specified)');
                console.log('  --working-dir DIRECTORY         Working directory (auto-detect if not');
                console.log('                                  specified)');
                console.log('  --api-key TEXT                  StackOverflow API key');
                console.log('  --version                       Show the version and exit.');
                console.log('  --help                          Show this message and exit.');
                return;
            }

            // 1. Find Python
            const pythonCmd = await this.findPython();

            // 2. Detect working directory
            const workingDir = await this.detectWorkingDirectory();
            this.log(`Detected working directory: ${workingDir}`);
            
            try {
                process.chdir(workingDir);
                this.log(`Changed to working directory: ${process.cwd()}`);
            } catch (error) {
                this.error(`Failed to change to working directory ${workingDir}: ${error.message}`);
                // Continue with current directory
            }

            // 3. Check package installation and version
            const isInstalled = await this.checkPackageInstalled(pythonCmd);
            let needsInstall = !isInstalled;
            let versionInfo = null;
            
            if (isInstalled) {
                versionInfo = await this.checkPackageVersion(pythonCmd);
                
                if (versionInfo.needsUpdate) {
                    this.info(`📦 ${this.packageName} found but outdated version (${versionInfo.version} → ${this.expectedVersion})`);
                    this.info('🔄 Updating to latest version with complete tool set...');
                    needsInstall = true;
                } else if (this.forceReinstall) {
                    this.info(`🔄 Force reinstall requested for ${this.packageName}`);
                    needsInstall = true;
                } else {
                    this.log(`Python package already installed (${versionInfo.version})`);
                }
            }
            
            if (needsInstall) {
                if (!isInstalled) {
                    this.info(`📦 ${this.packageName} not found, installing latest version (${this.expectedVersion})...`);
                }
                
                const installSuccess = await this.installPackage(pythonCmd);
                
                if (!installSuccess) {
                    this.error('Failed to install the Python package');
                    this.error('');
                    this.error('This may be due to an externally-managed Python environment.');
                    this.error('');
                    this.error('Recommended solution:');
                    this.error('  1. Install uv: curl -LsSf https://astral.sh/uv/install.sh | sh');
                    this.error('  2. Restart your terminal');
                    this.error('  3. Run this command again');
                    this.error('');
                    this.error('Alternative solutions:');
                    this.error(`  uv pip install ${this.packageName}  (if uv is installed)`);
                    this.error(`  pip install --user ${this.packageName}  (may not work in managed environments)`);
                    this.error('');
                    this.error('For force reinstall, add --force-reinstall flag');
                    process.exit(1);
                }
                
                // Verify installation after install/update
                const newVersionInfo = await this.checkPackageVersion(pythonCmd);
                if (newVersionInfo.installed) {
                    this.info(`✅ Successfully installed ${this.packageName} v${newVersionInfo.version}`);
                    if (newVersionInfo.version === this.expectedVersion) {
                        this.info('🎉 You now have the complete tool set with 7 tools!');
                    }
                }
            }

            // 4. Filter and prepare CLI arguments
            const cliArgs = process.argv.slice(2);
            const filteredArgs = this.filterCliArgs(cliArgs);
            
            // Add working directory argument if not already specified
            if (!filteredArgs.includes('--working-dir') && !filteredArgs.includes('--working-directory')) {
                filteredArgs.push('--working-dir', workingDir);
            }

            // 5. Run the Python CLI
            this.info('🚀 Starting StackOverflow MCP Server...');
            this.info('');

            // The Python module name is stackoverflow_mcp (not stackoverflow_fastmcp)
            const moduleName = 'stackoverflow_mcp';
            const result = await this.runCommand(pythonCmd, ['-m', moduleName, ...filteredArgs]);
            process.exit(result.code);

        } catch (error) {
            this.error(error.message);
            this.info('');
            this.info('💡 Troubleshooting:');
            this.info('  1. Ensure Python 3.12+ is installed and in PATH');
            this.info('  2. Ensure pip is available and working');
            this.info('  3. Check network connectivity for package installation');
            this.info('  4. Try running with --verbose for more details');
            this.info('');
            this.info('For more help, visit: https://github.com/NoTalkTech/stackoverflow-mcp');
            process.exit(1);
        }
    }
}

// Handle CLI execution
if (require.main === module) {
    const cli = new StackOverflowMCPCLI();
    cli.main().catch((error) => {
        console.error('Unexpected error:', error);
        process.exit(1);
    });
}

module.exports = StackOverflowMCPCLI; 
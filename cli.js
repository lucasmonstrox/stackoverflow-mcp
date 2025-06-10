#!/usr/bin/env node

/**
 * StackOverflow MCP Server - NPX CLI Wrapper
 * 
 * This script provides npx compatibility for the Python-based StackOverflow MCP server.
 * It automatically handles virtual environment creation with uv, package installation, 
 * and server execution within the isolated environment.
 */

const { spawn } = require('child_process');
const { existsSync } = require('fs');
const path = require('path');
const os = require('os');

class StackOverflowMCPCLI {
    constructor() {
        this.packageName = 'stackoverflow-fastmcp';
        this.expectedVersion = '0.2.2';  // Expected complete version
        this.verbose = process.argv.includes('--verbose') || process.argv.includes('-v');
        // Detect MCP mode - should be silent for stdio communication
        this.isMCPMode = this.detectMCPMode();
        // Check for force reinstall flag
        this.forceReinstall = process.argv.includes('--force-reinstall');
        // Virtual environment path
        this.venvPath = path.join(os.homedir(), '.stackoverflow-mcp-venv');
    }

    detectMCPMode() {
        // MCP stdio mode detection: only suppress output for true stdio mode
        const args = process.argv.slice(2);
        const hasPort = args.includes('--port');
        const hasHelp = args.includes('--help') || args.includes('-h');
        
        // Only suppress output for stdio mode (no --port, no --help)
        const isStdioMode = !hasPort && !hasHelp;
        
        return isStdioMode;
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
        // Check if virtual environment already exists and is valid
        const pythonPath = this.getVirtualEnvPython();
        if (existsSync(this.venvPath) && existsSync(pythonPath)) {
            this.log(`Using existing virtual environment at ${this.venvPath}`);
            return true;
        }
        
        // Remove incomplete virtual environment if it exists
        if (existsSync(this.venvPath)) {
            this.log(`Removing incomplete virtual environment at ${this.venvPath}`);
            try {
                const { rmSync } = require('fs');
                rmSync(this.venvPath, { recursive: true, force: true });
            } catch (error) {
                this.log(`Warning: Could not remove incomplete venv: ${error.message}`);
            }
        }
        
        this.info(`🔧 Creating virtual environment at ${this.venvPath}...`);
        
        try {
            // Create virtual environment with uv
            const createResult = await this.runCommand('uv', ['venv', this.venvPath, '--python', '3.12'], { 
                stdio: 'pipe'
            });
            
            if (createResult.code !== 0) {
                this.log(`Failed to create virtual environment with Python 3.12: ${createResult.stderr}`);
                // Try without specific Python version
                const createFallback = await this.runCommand('uv', ['venv', this.venvPath], { 
                    stdio: 'pipe'
                });
                if (createFallback.code !== 0) {
                    this.log(`Fallback creation also failed: ${createFallback.stderr}`);
                    return false;
                }
            }
            
            // Verify the virtual environment was created successfully
            if (!existsSync(pythonPath)) {
                this.log(`Virtual environment created but Python executable not found at ${pythonPath}`);
                return false;
            }
            
            this.info(`✅ Created virtual environment at ${this.venvPath}`);
            return true;
            
        } catch (error) {
            this.log(`Virtual environment creation failed: ${error.message}`);
            return false;
        }
    }

    getVirtualEnvPython() {
        // Return path to Python executable in virtual environment
        const isWindows = process.platform === 'win32';
        const pythonExe = isWindows ? 'python.exe' : 'python';
        const binDir = isWindows ? 'Scripts' : 'bin';
        return path.join(this.venvPath, binDir, pythonExe);
    }

    async checkPackageInstalled() {
        try {
            const pythonPath = this.getVirtualEnvPython();
            // The Python module name is stackoverflow_mcp (not stackoverflow_fastmcp)
            const moduleName = 'stackoverflow_mcp';
            const result = await this.runCommand(pythonPath, ['-c', `import ${moduleName}`], { stdio: 'pipe' });
            return result.code === 0;
        } catch (error) {
            return false;
        }
    }

    async checkPackageVersion() {
        try {
            const pythonPath = this.getVirtualEnvPython();
            const result = await this.runCommand(pythonPath, ['-c', 
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

    async installPackage() {
        this.log(`Installing ${this.packageName} Python package in virtual environment...`);
        
        try {
            this.log('Installing package with uv in virtual environment...');
            const packageSpec = `${this.packageName}==${this.expectedVersion}`;
            
            // Method 1: Try using uv pip install with --python
            const result1 = await this.runCommand('uv', [
                'pip', 'install', 
                '--python', this.getVirtualEnvPython(),
                packageSpec
            ], { stdio: 'pipe' });
            
            if (result1.code === 0) {
                this.info(`✅ Successfully installed ${this.packageName} in virtual environment`);
                return true;
            }
            
            this.log(`Method 1 failed: ${result1.stderr}`);
            
            // Method 2: Try using environment variables
            this.log('Trying alternative installation method...');
            const installEnv = {
                ...process.env,
                VIRTUAL_ENV: this.venvPath,
                PATH: `${path.join(this.venvPath, process.platform === 'win32' ? 'Scripts' : 'bin')}:${process.env.PATH}`
            };
            
            const result2 = await this.runCommand('uv', [
                'pip', 'install', packageSpec
            ], { 
                stdio: 'pipe',
                env: installEnv
            });
            
            if (result2.code === 0) {
                this.info(`✅ Successfully installed ${this.packageName} in virtual environment`);
                return true;
            }
            
            this.log(`Method 2 failed: ${result2.stderr}`);
            this.error('Failed to install package with uv');
            return false;
            
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

            // 1. Check uv availability
            const uvAvailable = await this.checkUvAvailable();
            if (!uvAvailable) {
                this.error('uv is required but not available');
                this.info('📥 Please install uv: curl -LsSf https://astral.sh/uv/install.sh | sh');
                process.exit(1);
            }

            // 2. Ensure virtual environment exists
            const venvCreated = await this.ensureUvVirtualEnv();
            if (!venvCreated) {
                this.error('Failed to create or access virtual environment');
                process.exit(1);
            }

            // 3. Detect working directory
            const workingDir = await this.detectWorkingDirectory();
            this.log(`Detected working directory: ${workingDir}`);
            
            try {
                process.chdir(workingDir);
                this.log(`Changed to working directory: ${process.cwd()}`);
            } catch (error) {
                this.error(`Failed to change to working directory ${workingDir}: ${error.message}`);
                // Continue with current directory
            }

            // 4. Check package installation and version
            const isInstalled = await this.checkPackageInstalled();
            let needsInstall = !isInstalled;
            let versionInfo = null;
            
            if (isInstalled) {
                versionInfo = await this.checkPackageVersion();
                
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
                
                const installSuccess = await this.installPackage();
                
                if (!installSuccess) {
                    this.error('Failed to install the Python package');
                    this.error('');
                    this.error('Troubleshooting steps:');
                    this.error('  1. Ensure uv is properly installed and in PATH');
                    this.error('  2. Check network connectivity');
                    this.error('  3. Try running with --verbose for more details');
                    this.error('');
                    this.error('For force reinstall, add --force-reinstall flag');
                    process.exit(1);
                }
                
                // Verify installation after install/update
                const newVersionInfo = await this.checkPackageVersion();
                if (newVersionInfo.installed) {
                    this.info(`✅ Successfully installed ${this.packageName} v${newVersionInfo.version}`);
                    if (newVersionInfo.version === this.expectedVersion) {
                        this.info('🎉 You now have the complete tool set with 7 tools!');
                    }
                }
            }

            // 5. Filter and prepare CLI arguments
            const cliArgs = process.argv.slice(2);
            const filteredArgs = this.filterCliArgs(cliArgs);
            
            // Add working directory argument if not already specified
            if (!filteredArgs.includes('--working-dir') && !filteredArgs.includes('--working-directory')) {
                filteredArgs.push('--working-dir', workingDir);
            }

            // 6. Run the Python CLI using virtual environment Python
            this.info('🚀 Starting StackOverflow MCP Server in virtual environment...');
            this.info('');

            // The Python module name is stackoverflow_mcp (not stackoverflow_fastmcp)
            const moduleName = 'stackoverflow_mcp';
            const pythonPath = this.getVirtualEnvPython();
            
            // In MCP mode, use stdio: 'inherit' for direct communication
            // In non-MCP mode, allow normal output
            const runOptions = this.isMCPMode ? { stdio: 'inherit' } : {};
            const result = await this.runCommand(pythonPath, ['-m', moduleName, ...filteredArgs], runOptions);
            process.exit(result.code);

        } catch (error) {
            this.error(error.message);
            this.info('');
            this.info('💡 Troubleshooting:');
            this.info('  1. Ensure uv is installed and in PATH');
            this.info('  2. Check network connectivity for package installation');
            this.info('  3. Try running with --verbose for more details');
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
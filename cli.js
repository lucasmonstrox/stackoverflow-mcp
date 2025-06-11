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
        this.expectedVersion = '0.2.2';  // Keep current published version until 0.2.3 is released
        this.verbose = process.argv.includes('--verbose') || process.argv.includes('-v');
        // Always MCP mode - no output to avoid JSON pollution
        this.isMCPMode = true;
        this.forceReinstall = process.env.FORCE_REINSTALL === 'true';
        // Virtual environment path
        this.venvPath = path.join(os.homedir(), '.stackoverflow-mcp-venv');
    }

    log(message) {
        // Completely silent in MCP mode
    }

    error(message) {
        // Completely silent in MCP mode
    }

    info(message) {
        // Completely silent in MCP mode
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
        
        this.info(`Creating virtual environment at ${this.venvPath}...`);
        
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
            
            this.info(`Created virtual environment at ${this.venvPath}`);
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
        try {
            const packageSpec = `${this.packageName}==${this.expectedVersion}`;
            
            // Method 1: Try using uv pip install with --python
            const result1 = await this.runCommand('uv', [
                'pip', 'install', 
                '--python', this.getVirtualEnvPython(),
                packageSpec
            ], { stdio: 'pipe' });
            
            if (result1.code === 0) {
                return true;
            }
            
            // Method 2: Try using environment variables
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
                return true;
            }
            
            return false;
            
        } catch (error) {
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
        // Filter out Node.js specific arguments for MCP stdio mode
        const filteredArgs = args.filter(arg => {
            return !arg.startsWith('--inspect') && 
                   !arg.startsWith('--debug') &&
                   !arg.startsWith('--port') &&  // MCP doesn't use port
                   !arg.startsWith('--host') &&  // MCP doesn't use host
                   arg !== '--verbose' &&  // Handle this in Node.js wrapper
                   arg !== '-v';
        });

        return filteredArgs;
    }

    async main() {
        try {
            // 1. Check uv availability
            const uvAvailable = await this.checkUvAvailable();
            if (!uvAvailable) {
                process.exit(1);
            }

            // 2. Ensure virtual environment exists
            const venvCreated = await this.ensureUvVirtualEnv();
            if (!venvCreated) {
                process.exit(1);
            }

            // 3. Detect working directory
            const workingDir = await this.detectWorkingDirectory();
            
            try {
                process.chdir(workingDir);
            } catch (error) {
                // Continue with current directory
            }

            // 4. Check package installation and version
            const isInstalled = await this.checkPackageInstalled();
            let needsInstall = !isInstalled;
            let versionInfo = null;
            
            if (isInstalled) {
                versionInfo = await this.checkPackageVersion();
                
                if (versionInfo.needsUpdate) {
                    needsInstall = true;
                } else if (this.forceReinstall) {
                    needsInstall = true;
                }
            }
            
            if (needsInstall) {
                const installSuccess = await this.installPackage();
                
                if (!installSuccess) {
                    process.exit(1);
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
            const moduleName = 'stackoverflow_mcp';
            const pythonPath = this.getVirtualEnvPython();
            
            // MCP mode uses stdio: 'inherit' for direct communication
            const result = await this.runCommand(pythonPath, ['-m', moduleName, ...filteredArgs], { stdio: 'inherit' });
            process.exit(result.code);

        } catch (error) {
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
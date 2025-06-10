#!/usr/bin/env node

const { execSync, spawn } = require('child_process');
const fs = require('fs');
const path = require('path');
const os = require('os');

async function testVirtualEnvironmentCreation() {
    console.log('🧪 Testing Virtual Environment Auto-Creation');
    console.log('==========================================');

    const homeDir = os.homedir();
    const venvPath = path.join(homeDir, '.stackoverflow-mcp-venv');

    // Step 1: Clean up any existing virtual environment
    console.log('1. Cleaning up existing virtual environment...');
    try {
        if (fs.existsSync(venvPath)) {
            fs.rmSync(venvPath, { recursive: true, force: true });
            console.log('   ✅ Removed existing virtual environment');
        } else {
            console.log('   ✅ No existing virtual environment found');
        }
    } catch (error) {
        console.log(`   ⚠️  Failed to remove existing venv: ${error.message}`);
    }

    // Step 2: Test CLI outside of development environment
    console.log('\n2. Testing CLI in completely isolated environment...');
    const tempDir = '/tmp/stackoverflow-mcp-test-isolated';

    try {
        // Create test directory
        if (fs.existsSync(tempDir)) {
            fs.rmSync(tempDir, { recursive: true, force: true });
        }
        fs.mkdirSync(tempDir, { recursive: true });

        console.log(`   📁 Testing in: ${tempDir}`);
        console.log('   🚀 Running CLI with clean environment...');
        
        // Create completely clean environment without any virtual env variables
        const cleanEnv = {
            HOME: homeDir,
            PATH: process.env.PATH,
            USER: process.env.USER || 'test',
            // Explicitly unset virtual environment variables
            VIRTUAL_ENV: undefined,
            CONDA_DEFAULT_ENV: undefined,
            UV_PROJECT_ENVIRONMENT: undefined
        };
        
        // Run CLI in isolated environment
        const child = spawn('npx', ['@notalk-tech/stackoverflow-mcp@1.0.11', '--help', '--verbose'], {
            cwd: tempDir,
            env: cleanEnv,
            stdio: ['pipe', 'pipe', 'pipe']
        });
        
        let stdout = '';
        let stderr = '';
        
        child.stdout.on('data', (data) => {
            stdout += data.toString();
            process.stdout.write(data);  // Show real-time output
        });
        
        child.stderr.on('data', (data) => {
            stderr += data.toString();
            process.stderr.write(data);  // Show real-time errors
        });
        
        const exitCode = await new Promise((resolve, reject) => {
            const timeout = setTimeout(() => {
                child.kill('SIGTERM');
                resolve(-1);  // Timeout
            }, 60000);  // 60 second timeout
            
            child.on('close', (code) => {
                clearTimeout(timeout);
                resolve(code);
            });
            
            child.on('error', (error) => {
                clearTimeout(timeout);
                reject(error);
            });
        });
        
        console.log(`\n   📊 CLI exited with code: ${exitCode}`);
        
        // Check if virtual environment was created
        if (fs.existsSync(venvPath)) {
            console.log(`   ✅ Virtual environment created at: ${venvPath}`);
            
            // Check virtual environment structure
            const venvContents = fs.readdirSync(venvPath);
            console.log(`   📂 Virtual environment contents: ${venvContents.join(', ')}`);
            
            if (venvContents.includes('bin') || venvContents.includes('Scripts')) {
                console.log('   ✅ Virtual environment structure looks correct');
                
                // Test if we can use the virtual environment
                try {
                    const testPython = path.join(venvPath, 'bin', 'python');
                    if (fs.existsSync(testPython)) {
                        const pythonVersion = execSync(`${testPython} --version`, { encoding: 'utf8' });
                        console.log(`   ✅ Virtual environment Python: ${pythonVersion.trim()}`);
                    }
                } catch (error) {
                    console.log(`   ⚠️  Could not test virtual environment: ${error.message}`);
                }
            } else {
                console.log('   ⚠️  Virtual environment structure might be incomplete');
            }
        } else {
            console.log('   ❌ Virtual environment was NOT created');
            
            // Check if there were relevant log messages
            if (stdout.includes('Creating virtual environment') || stdout.includes('virtual environment')) {
                console.log('   🔍 Found virtual environment messages in output');
            }
            if (stdout.includes('uv venv')) {
                console.log('   🔍 Found uv venv command in output');
            }
        }
        
    } catch (error) {
        console.log(`   ⚠️  Test execution failed: ${error.message}`);
        
        // Still check if virtual environment was created
        if (fs.existsSync(venvPath)) {
            console.log(`   ✅ Virtual environment was created despite error: ${venvPath}`);
        }
    }

    // Step 3: Cleanup
    console.log('\n3. Cleaning up test environment...');
    try {
        if (fs.existsSync(tempDir)) {
            fs.rmSync(tempDir, { recursive: true, force: true });
            console.log('   ✅ Removed test directory');
        }
    } catch (error) {
        console.log(`   ⚠️  Failed to cleanup: ${error.message}`);
    }

    console.log('\n🎉 Virtual Environment Test Complete!');
    console.log('=======================================');

    if (fs.existsSync(venvPath)) {
        console.log(`✅ RESULT: Virtual environment exists at ${venvPath}`);
        console.log('📦 The CLI should now be able to install packages in this environment');
        
        // Show some stats about the created virtual environment
        try {
            const stats = fs.statSync(venvPath);
            console.log(`📅 Created: ${stats.birthtime.toISOString()}`);
            
            const venvContents = fs.readdirSync(venvPath);
            console.log(`📂 Contents: ${venvContents.length} items`);
        } catch (error) {
            console.log(`⚠️  Could not get virtual environment stats: ${error.message}`);
        }
    } else {
        console.log('❌ RESULT: Virtual environment was NOT created automatically');
        console.log('🔧 This indicates the auto-creation feature needs more work');
    }
}

// Run the test
testVirtualEnvironmentCreation().catch((error) => {
    console.error('Test failed:', error);
    process.exit(1);
}); 
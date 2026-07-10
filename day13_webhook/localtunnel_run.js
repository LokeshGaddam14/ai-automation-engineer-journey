const { spawn } = require('child_process');
const fs = require('fs');
const path = require('path');

const logFile = path.join(__dirname, '..', 'localtunnel_url.txt'); // keep same filename for compatibility

console.log('Starting Pinggy SSH tunnel on port 5678...');

// Clean file
fs.writeFileSync(logFile, '');

const child = spawn('ssh', [
  '-tt',
  '-o', 'StrictHostKeyChecking=no',
  '-o', 'ServerAliveInterval=30',
  '-p', '443',
  '-R', '0:localhost:5678',
  'qr@a.pinggy.io' // 'qr@a.pinggy.io' prints the URL and QR code. 'a.pinggy.io' works too.
], {
  shell: true,
  stdio: ['ignore', 'pipe', 'pipe']
});

let urlFound = false;

child.stdout.on('data', (data) => {
  const output = data.toString();
  console.log('PINGGY STDOUT:', output);
  
  // Find URL matching https://*.pinggy.link or https://*.pinggy.app
  const matches = output.match(/https:\/\/[a-zA-Z0-9-]+\.pinggy\.(?:link|app|io)/);
  if (matches && !urlFound) {
    const url = matches[0];
    console.log('Tunnel URL generated:', url);
    fs.writeFileSync(logFile, url);
    urlFound = true;
  }
});

child.stderr.on('data', (data) => {
  const error = data.toString();
  console.error('PINGGY STDERR:', error);
});

child.on('close', (code) => {
  console.log(`Pinggy process exited with code ${code}`);
  if (!urlFound) {
    fs.writeFileSync(logFile, `[EXIT] Process exited with code ${code}`);
  }
});

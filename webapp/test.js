const http = require('http');

const tests = [
  { path: '/', expected: 'Hello from my cloud webapp!' },
  { path: '/health', expected: 'healthy' },
  { path: '/info', expected: 'Rama Nandamuri' },
];

let passed = 0;
let failed = 0;

tests.forEach(test => {
  http.get(`http://localhost:3000${test.path}`, (res) => {
    let data = '';
    res.on('data', chunk => data += chunk);
    res.on('end', () => {
      if (data.includes(test.expected)) {
        console.log(`✅ PASS: ${test.path}`);
        passed++;
      } else {
        console.log(`❌ FAIL: ${test.path}`);
        failed++;
      }
      if (passed + failed === tests.length) {
        console.log(`\nResults: ${passed} passed, ${failed} failed`);
        process.exit(failed > 0 ? 1 : 0);
      }
    });
  });
});
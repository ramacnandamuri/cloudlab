const express = require('express');
const app = express();
const PORT = 3000;

app.get('/', (req, res) => {
res.send('Hello from my cloud webapp! - Week 7 High Availability 🚀');
});

app.get('/info', (req, res) => {
  res.json({
  "app": "Cloud Lab Webapp",
  "version": "1.0.0",
  "author": "Rama Nandamuri",
  "deployed_on": "AWS EC2",
  "container": true
});
});

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date(),
    hostname: require('os').hostname()
  });
});

app.get('/test', (req, res) => {
  res.json({ test: 'passed', version: '1.0.0' });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
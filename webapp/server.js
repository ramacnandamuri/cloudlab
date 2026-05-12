const express = require('express');
const app = express();
const PORT = 3000;

app.get('/', (req, res) => {
  res.send('Hello from my cloud webapp!');
});

app.get('/health', (req, res) => {
  res.json({
    status: 'healthy',
    timestamp: new Date(),
    hostname: require('os').hostname()
  });
});

app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
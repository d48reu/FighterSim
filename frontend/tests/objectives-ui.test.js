const test = require('node:test');
const assert = require('node:assert/strict');

const { renderObjectivesWidget } = require('../static/js/market-ui.js');

test('renderObjectivesWidget shows origin summary and objective progress', () => {
  const html = renderObjectivesWidget({
    origin_label: 'The Comeback',
    summary: 'Claw your way back into relevance with a solvent, credible promotion.',
    completed_count: 2,
    total_count: 3,
    objectives: [
      { label: 'Reach 35 prestige', current: 36, target: 35, progress_pct: 100, completed: true },
      { label: 'Build a roster of 10 fighters', current: 10, target: 10, progress_pct: 100, completed: true },
      { label: 'Push bank balance to $3,000,000', current: 3200000, target: 3000000, progress_pct: 100, completed: true },
    ],
  });

  assert.match(html, /The Comeback/);
  assert.match(html, /2\/3 complete/);
  assert.match(html, /Reach 35 prestige/);
  assert.match(html, /100%/);
});

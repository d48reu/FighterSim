const test = require('node:test');
const assert = require('node:assert/strict');

const { renderRivalIntel } = require('../static/js/market-ui.js');

test('renderRivalIntel shows org identity and contested targets', () => {
  const html = renderRivalIntel({
    name: 'Bellator MMA',
    prestige: 72,
    roster_count: 18,
    identity: {
      label: 'Star Chaser',
      focus: 'Pays for proven draws and visible names.',
    },
    top_targets: [
      { name: 'Bidding War Star', reason: 'Fits their brand and division focus.' },
    ],
  });

  assert.match(html, /Star Chaser/);
  assert.match(html, /Pays for proven draws/);
  assert.match(html, /Bidding War Star/);
  assert.match(html, /Contested Targets/);
});

const test = require('node:test');
const assert = require('node:assert/strict');

const { renderScoutingBoard } = require('../static/js/market-ui.js');

test('renderScoutingBoard shows the main scouting buckets and fighters', () => {
  const html = renderScoutingBoard({
    featured_prospects: [
      {
        name: 'Blue Chip Prospect',
        meta: 'Welterweight · OVR 79 · age 23',
        recommendation: { label: 'Buy Now', tone: 'buy-now', reason: 'Trajectory is strong.' },
      },
    ],
    under_the_radar: [],
    ready_now: [
      {
        name: 'Ready Now',
        meta: 'Welterweight · Strong Main Event fit',
        recommendation: { label: 'Fair Price', tone: 'neutral', reason: 'Useful now.' },
      },
    ],
    division_targets: [],
  });

  assert.match(html, /Featured Prospects/);
  assert.match(html, /Blue Chip Prospect/);
  assert.match(html, /Ready Now/);
  assert.match(html, /Immediate Options/);
});

const test = require('node:test');
const assert = require('node:assert/strict');

const { renderDecisionCenterColumn } = require('../static/js/market-ui.js');

test('renderDecisionCenterColumn renders title, recommendation badges, and empty state', () => {
  const filled = renderDecisionCenterColumn('Buy Targets', [
    {
      name: 'Buy Candidate',
      meta: 'Welterweight · OVR 78',
      recommendation: { label: 'Buy Now', tone: 'buy-now', reason: 'Hot fighter with a favorable contract window.' },
    },
  ]);
  assert.match(filled, /Buy Targets/);
  assert.match(filled, /Buy Candidate/);
  assert.match(filled, /Buy Now/);

  const empty = renderDecisionCenterColumn('Sell Candidates', []);
  assert.match(empty, /Sell Candidates/);
  assert.match(empty, /No immediate actions/);
});

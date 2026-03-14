const test = require('node:test');
const assert = require('node:assert/strict');

const {
  renderMarketContextCard,
  renderOfferEvaluation,
} = require('../static/js/market-ui.js');

test('renderMarketContextCard surfaces the key market signals', () => {
  const html = renderMarketContextCard({
    trajectory_label: 'Rising',
    recent_form: '3-0',
    market_value_hint: 'Prospect value is climbing.',
    booking_value: 'Strong Main Event',
    next_opponent_name: 'Roster Anchor',
    salary_multiplier: 1.26,
    acceptance_adjustment: 0.1,
    ai_interest_score: 101.8,
    trajectory_reasons: ['Won 3 of the last 3 fights.', 'Recent wins are coming with finishes.'],
  });

  assert.match(html, /Market Read/i);
  assert.match(html, /Rising/);
  assert.match(html, /Strong Main Event/);
  assert.match(html, /Roster Anchor/);
  assert.match(html, /1\.26x/);
  assert.match(html, /10\.0%/);
  assert.match(html, /101\.8/);
});

test('renderOfferEvaluation summarizes acceptance odds and offer leverage', () => {
  const html = renderOfferEvaluation({
    asking_salary: 100000,
    offered_salary: 120000,
    offer_ratio: 1.2,
    acceptance_probability: 0.734,
    market_context: {
      trajectory_label: 'Peaking',
      market_value_hint: 'Window is hot.',
      booking_value: 'Strong Co-Main',
      next_opponent_name: 'Veteran Foil',
      salary_multiplier: 1.12,
      acceptance_adjustment: 0.03,
      ai_interest_score: 88.4,
      trajectory_reasons: ['Won 2 of the last 3 fights.'],
    },
  });

  assert.match(html, /Offer Evaluation/i);
  assert.match(html, /73\.4%/);
  assert.match(html, /1\.20x/);
  assert.match(html, /\$100,000/);
  assert.match(html, /\$120,000/);
  assert.match(html, /Peaking/);
});

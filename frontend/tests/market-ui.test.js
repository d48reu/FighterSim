const test = require('node:test');
const assert = require('node:assert/strict');

const {
  renderMarketContextCard,
  renderOfferEvaluation,
  renderCompactMarketLine,
  getBookingSortValue,
  matchesTrajectoryFilter,
  getMarketSignalTone,
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

test('renderCompactMarketLine gives a table-friendly market summary', () => {
  const html = renderCompactMarketLine({
    trajectory_label: 'Rising',
    booking_value: 'Strong Main Event',
    market_value_hint: 'Prospect value is climbing.',
    salary_multiplier: 1.04,
    acceptance_adjustment: 0.02,
  });

  assert.match(html, /Rising/);
  assert.match(html, /Strong Main Event/);
  assert.match(html, /Prospect value is climbing\./);
  assert.match(html, /buy-now/);
});

test('getBookingSortValue ranks marquee bookings above filler', () => {
  assert.ok(getBookingSortValue('Strong Main Event') > getBookingSortValue('Strong Co-Main'));
  assert.ok(getBookingSortValue('Strong Co-Main') > getBookingSortValue('Risky Development Fight'));
  assert.ok(getBookingSortValue('Risky Development Fight') > getBookingSortValue('Low-Value Filler'));
});

test('matchesTrajectoryFilter respects all/current trajectory labels', () => {
  assert.equal(matchesTrajectoryFilter({ trajectory_label: 'Rising' }, ''), true);
  assert.equal(matchesTrajectoryFilter({ trajectory_label: 'Rising' }, 'Rising'), true);
  assert.equal(matchesTrajectoryFilter({ trajectory_label: 'Rising' }, 'Declining'), false);
});

test('getMarketSignalTone tags hot, expensive, and cold assets', () => {
  assert.equal(getMarketSignalTone({ trajectory_label: 'Rising', salary_multiplier: 1.05, acceptance_adjustment: 0.02 }), 'buy-now');
  assert.equal(getMarketSignalTone({ trajectory_label: 'Peaking', salary_multiplier: 1.22, acceptance_adjustment: 0.1 }), 'overpay');
  assert.equal(getMarketSignalTone({ trajectory_label: 'Declining', salary_multiplier: 0.92, acceptance_adjustment: -0.03 }), 'cold-asset');
});

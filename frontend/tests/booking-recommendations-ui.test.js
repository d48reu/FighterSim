const test = require('node:test');
const assert = require('node:assert/strict');

const { renderBookingRecommendations } = require('../static/js/market-ui.js');

test('renderBookingRecommendations shows recommendation buckets and matchup reasons', () => {
  const html = renderBookingRecommendations({
    best_main_event: {
      label: 'Best Main Event',
      matchup: 'Headliner A vs Headliner B',
      booking_value: 'Strong Main Event',
      reasons: ['Both fighters bring enough hype and popularity to carry a featured slot.'],
    },
    best_co_main: {
      label: 'Best Co-Main',
      matchup: 'Solid CoMain vs Veteran Foil',
      booking_value: 'Strong Co-Main',
      reasons: ['The matchup has some audience pull, but not automatic headliner juice.'],
    },
  });

  assert.match(html, /Best Main Event/);
  assert.match(html, /Headliner A vs Headliner B/);
  assert.match(html, /Strong Main Event/);
  assert.match(html, /Best Co-Main/);
});

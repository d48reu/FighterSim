const test = require('node:test');
const assert = require('node:assert/strict');

const { renderMediaStorylines } = require('../static/js/market-ui.js');

test('renderMediaStorylines shows storyline cards with angles and urgency', () => {
  const html = renderMediaStorylines([
    { type: 'rivalry', headline: 'Champion vs Blood Rival is heating up again.', angle: 'Grudge match with title stakes.', urgency: 'High' },
    { type: 'prospect', headline: 'Blue Chip Prospect is building quiet momentum.', angle: 'Fans are starting to notice the ceiling.', urgency: 'Medium' },
  ]);

  assert.match(html, /Champion vs Blood Rival/);
  assert.match(html, /Grudge match/);
  assert.match(html, /Blue Chip Prospect/);
  assert.match(html, /High/);
});

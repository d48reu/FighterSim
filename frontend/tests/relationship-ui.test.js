const test = require('node:test');
const assert = require('node:assert/strict');

const { renderRelationshipMemory } = require('../static/js/market-ui.js');

test('renderRelationshipMemory shows trust summary and persistent negotiation history', () => {
  const html = renderRelationshipMemory({
    trust_label: 'Low',
    trust_score: 28,
    summary: 'They remember the lowball and are skeptical of your intentions.',
    lowball_offer_count: 2,
    rejected_offer_count: 1,
    successful_signings: 0,
    successful_renewals: 0,
    releases: 1,
  });

  assert.match(html, /Relationship Memory/);
  assert.match(html, /Low/);
  assert.match(html, /lowball/i);
  assert.match(html, /2/);
  assert.match(html, /skeptical/i);
});

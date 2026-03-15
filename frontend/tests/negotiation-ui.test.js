const test = require('node:test');
const assert = require('node:assert/strict');

const { renderNegotiationProfile } = require('../static/js/market-ui.js');

test('renderNegotiationProfile shows morale loyalty and preference chips', () => {
  const html = renderNegotiationProfile({
    morale_label: 'Low',
    loyalty_label: 'High',
    money_priority: 'High',
    activity_priority: 'High',
    spotlight_priority: 'Medium',
    prestige_priority: 'High',
    summary: 'Wants activity, values loyalty, and expects a serious stage.',
  });

  assert.match(html, /Negotiation Read/);
  assert.match(html, /Low/);
  assert.match(html, /High/);
  assert.match(html, /Wants activity/);
  assert.match(html, /Money/);
  assert.match(html, /Prestige/);
});

const test = require('node:test');
const assert = require('node:assert/strict');

const { renderSmartAssistantWidget } = require('../static/js/market-ui.js');

test('renderSmartAssistantWidget shows all four recommended actions', () => {
  const html = renderSmartAssistantWidget({
    best_signing: { label: 'Best Signing', headline: 'Buy Candidate is the cleanest add this month.', detail: 'Buy Now · Welterweight' },
    best_renewal: { label: 'Best Renewal', headline: 'Core Prospect should be locked up before leverage rises.', detail: 'High-Leverage Renewal' },
    best_booking: { label: 'Best Booking', headline: 'Welterweight Anchor vs Opponent is your strongest main event.', detail: 'Strong Main Event' },
    biggest_risk: { label: 'Biggest Risk', headline: 'Aging Vet is turning into a cold asset.', detail: 'Sell Soon' },
  });

  assert.match(html, /Best Signing/);
  assert.match(html, /Best Renewal/);
  assert.match(html, /Best Booking/);
  assert.match(html, /Biggest Risk/);
  assert.match(html, /Buy Candidate/);
});

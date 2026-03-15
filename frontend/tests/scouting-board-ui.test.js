const test = require('node:test');
const assert = require('node:assert/strict');

const { renderScoutingBoard } = require('../static/js/market-ui.js');

test('renderScoutingBoard shows the main scouting buckets and fighters', () => {
  const html = renderScoutingBoard({
    featured_prospects: [
      {
        name: 'Blue Chip Prospect',
        meta: 'Welterweight · age 23',
        scouting_report: {
          estimated_overall_range: '74-80 OVR',
          confidence_label: 'Medium',
          upside_label: 'Blue-Chip Ceiling',
          fog_note: 'Tape looks great, but the full package is not fully verified.',
        },
        recommendation: { label: 'Buy Now', tone: 'buy-now', reason: 'Trajectory is strong.' },
      },
    ],
    under_the_radar: [],
    ready_now: [
      {
        name: 'Ready Now',
        meta: 'Welterweight · immediate option',
        scouting_report: {
          estimated_overall_range: '76-79 OVR',
          confidence_label: 'High',
          upside_label: 'Ready Now',
          fog_note: 'Enough tape exists to trust the read.',
        },
        recommendation: { label: 'Fair Price', tone: 'neutral', reason: 'Useful now.' },
      },
    ],
    division_targets: [],
  });

  assert.match(html, /Featured Prospects/);
  assert.match(html, /Blue Chip Prospect/);
  assert.match(html, /Ready Now/);
  assert.match(html, /Immediate Options/);
  assert.match(html, /74-80 OVR/);
  assert.match(html, /Scout Confidence: Medium/);
  assert.match(html, /full package is not fully verified/);
});

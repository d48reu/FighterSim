const test = require('node:test');
const assert = require('node:assert/strict');

const { renderTitlePicture } = require('../static/js/market-ui.js');

test('renderTitlePicture shows champion eliminator and politics notes', () => {
  const html = renderTitlePicture({
    champion: { name: 'Champion', record: '12-1-0', overall: 82 },
    contenders: [
      { rank: 2, name: 'Contender One', record: '11-2-0', overall: 79 },
      { rank: 3, name: 'Contender Two', record: '10-3-0', overall: 78 },
    ],
    title_eliminator: {
      fighter_a: { name: 'Contender One' },
      fighter_b: { name: 'Contender Two' },
      booking_value: 'Strong Main Event',
    },
    division_heat: { label: 'Boiling', reason: 'Top contenders are hot and tightly packed.' },
    politics: ['Champion has not fought in 365 days.', 'Two contenders are separated by less than 2 ranking points.'],
  });

  assert.match(html, /Champion/);
  assert.match(html, /Title Eliminator/);
  assert.match(html, /Contender One/);
  assert.match(html, /Boiling/);
  assert.match(html, /Champion has not fought/);
});

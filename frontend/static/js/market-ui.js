'use strict';

(function (global) {
  function esc(value) {
    return String(value ?? '')
      .replace(/&/g, '&amp;')
      .replace(/</g, '&lt;')
      .replace(/>/g, '&gt;')
      .replace(/"/g, '&quot;')
      .replace(/'/g, '&#39;');
  }

  function formatCurrency(value) {
    const amount = Number(value || 0);
    return `$${amount.toLocaleString()}`;
  }

  function formatPercentFromDelta(value) {
    const pct = Number(value || 0) * 100;
    const sign = pct > 0 ? '+' : '';
    return `${sign}${pct.toFixed(1)}%`;
  }

  function renderReasonList(reasons) {
    if (!Array.isArray(reasons) || reasons.length === 0) {
      return '<div class="market-reason muted">No strong market signals yet.</div>';
    }
    return reasons
      .map((reason) => `<div class="market-reason">${esc(reason)}</div>`)
      .join('');
  }

  function renderMarketContextCard(marketContext) {
    if (!marketContext) return '';

    return `
      <div class="market-card">
        <div class="market-card-header">
          <div class="market-card-title">Market Read</div>
          <span class="market-trajectory-badge">${esc(marketContext.trajectory_label || 'Stalled')}</span>
        </div>
        <div class="market-card-summary">${esc(marketContext.recent_form || 'No recent form')} · ${esc(marketContext.market_value_hint || 'Market is stable.')}</div>
        <div class="market-grid">
          <div class="market-stat">
            <span class="market-stat-label">Booking Fit</span>
            <span class="market-stat-value">${esc(marketContext.booking_value || 'Unclear')}</span>
          </div>
          <div class="market-stat">
            <span class="market-stat-label">Best Opponent</span>
            <span class="market-stat-value">${esc(marketContext.next_opponent_name || 'None')}</span>
          </div>
          <div class="market-stat">
            <span class="market-stat-label">Salary Mult.</span>
            <span class="market-stat-value">${Number(marketContext.salary_multiplier || 1).toFixed(2)}x</span>
          </div>
          <div class="market-stat">
            <span class="market-stat-label">Acceptance Adj.</span>
            <span class="market-stat-value">${formatPercentFromDelta(marketContext.acceptance_adjustment)}</span>
          </div>
          <div class="market-stat">
            <span class="market-stat-label">AI Heat</span>
            <span class="market-stat-value">${Number(marketContext.ai_interest_score || 0).toFixed(1)}</span>
          </div>
        </div>
        <div class="market-reasons">${renderReasonList(marketContext.trajectory_reasons)}</div>
      </div>
    `;
  }

  function renderOfferEvaluation(offerEvaluation) {
    if (!offerEvaluation) return '';

    return `
      <div class="market-card offer-eval-card">
        <div class="market-card-header">
          <div class="market-card-title">Offer Evaluation</div>
          <span class="market-trajectory-badge">${(Number(offerEvaluation.acceptance_probability || 0) * 100).toFixed(1)}%</span>
        </div>
        <div class="market-grid">
          <div class="market-stat">
            <span class="market-stat-label">Asking</span>
            <span class="market-stat-value">${formatCurrency(offerEvaluation.asking_salary)}</span>
          </div>
          <div class="market-stat">
            <span class="market-stat-label">Offered</span>
            <span class="market-stat-value">${formatCurrency(offerEvaluation.offered_salary)}</span>
          </div>
          <div class="market-stat">
            <span class="market-stat-label">Offer Ratio</span>
            <span class="market-stat-value">${Number(offerEvaluation.offer_ratio || 1).toFixed(2)}x</span>
          </div>
          <div class="market-stat">
            <span class="market-stat-label">Acceptance Odds</span>
            <span class="market-stat-value">${(Number(offerEvaluation.acceptance_probability || 0) * 100).toFixed(1)}%</span>
          </div>
        </div>
        ${renderMarketContextCard(offerEvaluation.market_context)}
      </div>
    `;
  }

  const api = {
    renderMarketContextCard,
    renderOfferEvaluation,
  };

  global.MarketUi = api;

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
})(typeof window !== 'undefined' ? window : globalThis);

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

  function getBookingSortValue(bookingValue) {
    return {
      'Strong Main Event': 4,
      'Strong Co-Main': 3,
      'Risky Development Fight': 2,
      'Low-Value Filler': 1,
    }[bookingValue] || 0;
  }

  function matchesTrajectoryFilter(marketContext, trajectoryFilter) {
    if (!trajectoryFilter) return true;
    return (marketContext?.trajectory_label || '') === trajectoryFilter;
  }

  function getMarketSignalTone(marketContext) {
    if (!marketContext) return 'neutral';
    const trajectory = marketContext.trajectory_label || 'Stalled';
    const salaryMultiplier = Number(marketContext.salary_multiplier || 1);
    const acceptanceAdjustment = Number(marketContext.acceptance_adjustment || 0);

    if ((trajectory === 'Rising' || trajectory === 'Peaking') && salaryMultiplier <= 1.08 && acceptanceAdjustment <= 0.04) {
      return 'buy-now';
    }
    if (salaryMultiplier >= 1.18 || acceptanceAdjustment >= 0.08) {
      return 'overpay';
    }
    if (trajectory === 'Declining' || (trajectory === 'Stalled' && acceptanceAdjustment < 0)) {
      return 'cold-asset';
    }
    return 'neutral';
  }

  function renderCompactMarketLine(marketContext) {
    if (!marketContext) return '';
    const tone = getMarketSignalTone(marketContext);

    return `
      <div class="market-inline-line ${tone}">
        <span class="market-inline-chip tone-${tone}">${esc(marketContext.trajectory_label || 'Stalled')}</span>
        <span class="market-inline-chip subdued">${esc(marketContext.booking_value || 'No clear fit')}</span>
      </div>
      <div class="market-inline-hint">${esc(marketContext.market_value_hint || 'Market is stable.')}</div>
    `;
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
    getBookingSortValue,
    matchesTrajectoryFilter,
    getMarketSignalTone,
    renderCompactMarketLine,
    renderMarketContextCard,
    renderOfferEvaluation,
  };

  global.MarketUi = api;

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
})(typeof window !== 'undefined' ? window : globalThis);

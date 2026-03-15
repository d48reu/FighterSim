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

  function renderRecommendationBadge(recommendation) {
    if (!recommendation) return '';
    return `<span class="market-recommendation-badge tone-${esc(recommendation.tone || 'neutral')}" title="${esc(recommendation.reason || '')}">${esc(recommendation.label || 'Fair Value')}</span>`;
  }

  function renderCompactMarketLine(marketContext, recommendation = null) {
    if (!marketContext) return '';
    const tone = recommendation?.tone || getMarketSignalTone(marketContext);

    return `
      <div class="market-inline-line ${tone}">
        ${renderRecommendationBadge(recommendation || { label: marketContext.trajectory_label || 'Stalled', tone })}
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

  function renderDecisionCenterColumn(title, items) {
    const safeItems = Array.isArray(items) ? items : [];
    const body = safeItems.length
      ? safeItems.map((item) => `
          <div class="decision-center-item">
            <div class="decision-center-item-top">
              <strong>${esc(item.name || item.weight_class || 'Unknown')}</strong>
              ${renderRecommendationBadge(item.recommendation)}
            </div>
            ${item.meta ? `<div class="decision-center-meta">${esc(item.meta)}</div>` : ''}
            ${item.reason ? `<div class="decision-center-reason">${esc(item.reason)}</div>` : ''}
          </div>
        `).join('')
      : '<div class="decision-center-empty">No immediate actions.</div>';

    return `
      <div class="decision-center-column">
        <div class="decision-center-title">${esc(title)}</div>
        ${body}
      </div>
    `;
  }

  function renderBookingRecommendations(recommendations) {
    const entries = Object.values(recommendations || {}).filter(Boolean);
    if (entries.length === 0) {
      return '<div class="decision-center-empty">No booking recommendations available.</div>';
    }
    return entries.map((entry) => `
      <div class="booking-rec-card">
        <div class="booking-rec-title">${esc(entry.label || 'Recommendation')}</div>
        <div class="booking-rec-matchup">${esc(entry.matchup || 'TBD')}</div>
        <div class="booking-rec-meta">${esc(entry.booking_value || 'Unclear')} · ${esc(entry.competitiveness || 'Unknown')} · ${esc(entry.star_power || 'Unknown')}</div>
        <div class="booking-rec-reasons">${(entry.reasons || []).slice(0, 2).map((reason) => `<div class="market-reason">${esc(reason)}</div>`).join('')}</div>
      </div>
    `).join('');
  }

  function renderScoutingBoard(board) {
    const renderBucket = (title, items) => {
      const safeItems = Array.isArray(items) ? items : [];
      const body = safeItems.length
        ? safeItems.map((item) => `
            <div class="decision-center-item">
              <div class="decision-center-item-top">
                <strong>${esc(item.name || item.weight_class || 'Unknown')}</strong>
                ${renderRecommendationBadge(item.recommendation)}
              </div>
              ${item.meta ? `<div class="decision-center-meta">${esc(item.meta)}</div>` : ''}
              ${item.scouting_report ? `<div class="decision-center-meta">Scout Confidence: ${esc(item.scouting_report.confidence_label)} · ${esc(item.scouting_report.estimated_overall_range)}</div>` : ''}
              ${item.scouting_report?.upside_label ? `<div class="market-inline-chip subdued">${esc(item.scouting_report.upside_label)}</div>` : ''}
              ${item.scouting_report?.fog_note ? `<div class="decision-center-reason">${esc(item.scouting_report.fog_note)}</div>` : ''}
            </div>
          `).join('')
        : '<div class="decision-center-empty">No immediate scouting leads.</div>';
      return `
        <div class="decision-center-column">
          <div class="decision-center-title">${esc(title)}</div>
          ${body}
        </div>
      `;
    };

    return [
      renderBucket('Featured Prospects', board?.featured_prospects || []),
      renderBucket('Under the Radar', board?.under_the_radar || []),
      renderBucket('Immediate Options', board?.ready_now || []),
      renderBucket('Division Targets', board?.division_targets || []),
    ].join('');
  }

  function renderRivalIntel(rival) {
    if (!rival) return '';
    const targets = (rival.top_targets || []).length
      ? (rival.top_targets || []).map((target) => `
          <div class="decision-center-item">
            <div class="decision-center-item-top"><strong>${esc(target.name)}</strong></div>
            <div class="decision-center-reason">${esc(target.reason)}</div>
          </div>
        `).join('')
      : '<div class="decision-center-empty">No contested targets yet.</div>';

    return `
      <div class="rival-intel-block">
        <div class="rival-section-title">Identity</div>
        <div class="market-recommendation-badge tone-overpay">${esc(rival.identity?.label || 'Unknown')}</div>
        <div class="decision-center-reason">${esc(rival.identity?.focus || '')}</div>
        <div class="rival-section-title" style="margin-top:10px">Contested Targets</div>
        ${targets}
      </div>
    `;
  }

  function renderObjectivesWidget(objectives) {
    if (!objectives) return '';
    const objectiveRows = (objectives.objectives || []).map((obj) => `
      <div class="objective-row ${obj.completed ? 'completed' : ''}">
        <div class="objective-top">
          <span class="objective-label">${esc(obj.label)}</span>
          <span class="objective-progress">${obj.progress_pct}%</span>
        </div>
        <div class="objective-bar"><div class="objective-bar-fill" style="width:${obj.progress_pct}%"></div></div>
      </div>
    `).join('') || '<div class="decision-center-empty">No active objectives.</div>';
    return `
      <div class="market-card objective-card">
        <div class="market-card-header">
          <div class="market-card-title">Owner Goals</div>
          <span class="market-trajectory-badge">${esc(objectives.origin_label || 'Campaign')}</span>
        </div>
        <div class="market-card-summary">${esc(objectives.summary || '')}</div>
        <div class="objective-completion">${objectives.completed_count || 0}/${objectives.total_count || 0} complete</div>
        <div class="objective-list">${objectiveRows}</div>
      </div>
    `;
  }

  function renderSmartAssistantWidget(actions) {
    const entries = Object.values(actions || {}).filter(Boolean);
    if (entries.length === 0) {
      return '<div class="decision-center-empty">No assistant actions right now.</div>';
    }
    return `
      <div class="market-card assistant-card">
        <div class="market-card-header">
          <div class="market-card-title">Chief of Staff</div>
          <span class="market-trajectory-badge">This Month</span>
        </div>
        <div class="assistant-list">
          ${entries.map((entry) => `
            <div class="assistant-row">
              <div class="assistant-label">${esc(entry.label || 'Action')}</div>
              <div class="assistant-headline">${esc(entry.headline || '')}</div>
              <div class="assistant-detail">${esc(entry.detail || '')}</div>
            </div>
          `).join('')}
        </div>
      </div>
    `;
  }

  function renderTitlePicture(titlePicture) {
    if (!titlePicture) return '';
    const champion = titlePicture.champion;
    const contenders = (titlePicture.contenders || []).map((c) => `
      <div class="title-contender-row">
        <span><strong>#${c.rank}</strong> ${esc(c.name)}</span>
        <span class="muted">${esc(c.record)} · ${c.overall} OVR</span>
      </div>
    `).join('') || '<div class="decision-center-empty">No contenders yet.</div>';
    const eliminator = titlePicture.title_eliminator
      ? `<div class="title-eliminator-box">
          <div class="title-eliminator-title">Title Eliminator</div>
          <div class="title-eliminator-matchup">${esc(titlePicture.title_eliminator.fighter_a.name)} vs ${esc(titlePicture.title_eliminator.fighter_b.name)}</div>
          <div class="title-eliminator-meta">${esc(titlePicture.title_eliminator.booking_value || 'Unclear')} · ${esc(titlePicture.title_eliminator.competitiveness || 'Unknown')}</div>
        </div>`
      : '<div class="decision-center-empty">No eliminator recommendation yet.</div>';
    const politics = (titlePicture.politics || []).map((note) => `<div class="market-reason">${esc(note)}</div>`).join('');

    return `
      <div class="title-picture-grid">
        <div class="market-card">
          <div class="market-card-title">Champion</div>
          ${champion ? `<div class="booking-rec-matchup">${esc(champion.name)}</div><div class="booking-rec-meta">${esc(champion.record)} · ${champion.overall} OVR</div>` : '<div class="decision-center-empty">No champion yet.</div>'}
        </div>
        <div class="market-card">
          <div class="market-card-title">Division Heat</div>
          <div class="market-recommendation-badge tone-overpay">${esc(titlePicture.division_heat?.label || 'Cold')}</div>
          <div class="market-card-summary">${esc(titlePicture.division_heat?.reason || '')}</div>
          <div class="title-politics-list">${politics}</div>
        </div>
        <div class="market-card">
          <div class="market-card-title">Contenders</div>
          ${contenders}
        </div>
        <div class="market-card">
          ${eliminator}
        </div>
      </div>
    `;
  }

  function renderNegotiationProfile(profile) {
    if (!profile) return '';
    return `
      <div class="market-card negotiation-card">
        <div class="market-card-header">
          <div class="market-card-title">Negotiation Read</div>
          <span class="market-trajectory-badge">Morale: ${esc(profile.morale_label || 'Stable')}</span>
        </div>
        <div class="market-grid">
          <div class="market-stat"><span class="market-stat-label">Loyalty</span><span class="market-stat-value">${esc(profile.loyalty_label || 'Medium')}</span></div>
          <div class="market-stat"><span class="market-stat-label">Money</span><span class="market-stat-value">${esc(profile.money_priority || 'Medium')}</span></div>
          <div class="market-stat"><span class="market-stat-label">Activity</span><span class="market-stat-value">${esc(profile.activity_priority || 'Medium')}</span></div>
          <div class="market-stat"><span class="market-stat-label">Spotlight</span><span class="market-stat-value">${esc(profile.spotlight_priority || 'Medium')}</span></div>
          <div class="market-stat"><span class="market-stat-label">Prestige</span><span class="market-stat-value">${esc(profile.prestige_priority || 'Medium')}</span></div>
        </div>
        <div class="market-card-summary">${esc(profile.summary || 'No strong negotiation preferences.')}</div>
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
        ${renderRecommendationBadge(offerEvaluation.recommendation)}
        ${renderNegotiationProfile(offerEvaluation.negotiation_profile)}
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
    renderRecommendationBadge,
    renderCompactMarketLine,
    renderDecisionCenterColumn,
    renderBookingRecommendations,
    renderScoutingBoard,
    renderRivalIntel,
    renderObjectivesWidget,
    renderSmartAssistantWidget,
    renderTitlePicture,
    renderNegotiationProfile,
    renderMarketContextCard,
    renderOfferEvaluation,
  };

  global.MarketUi = api;

  if (typeof module !== 'undefined' && module.exports) {
    module.exports = api;
  }
})(typeof window !== 'undefined' ? window : globalThis);

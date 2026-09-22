/* ===================================================
   admin.js — Research dashboard charts & table
   =================================================== */

const LEVEL_ORDER  = ['easy', 'medium', 'hard'];
const LEVEL_LABELS = { easy: 'Easy', medium: 'Medium', hard: 'Hard' };
const LEVEL_COLORS = {
  easy:   { bg: 'rgba(67,217,126,.7)',  border: '#43d97e' },
  medium: { bg: 'rgba(247,201,72,.7)', border: '#f7c948' },
  hard:   { bg: 'rgba(255,77,109,.7)', border: '#ff4d6d' },
};

const CHART_DEFAULTS = {
  responsive: true,
  plugins: { legend: { labels: { color: '#e8eaf6' } } },
  scales: {
    x: { ticks: { color: '#9ca3bf' }, grid: { color: '#2d3050' } },
    y: { ticks: { color: '#9ca3bf' }, grid: { color: '#2d3050' } },
  },
};

async function loadStats() {
  const res = await fetch('/api/stats');
  const rows = await res.json();

  // Index by level
  const byLevel = {};
  rows.forEach(r => { byLevel[r.level] = r; });

  // Summary cards
  const total = rows.reduce((s, r) => s + r.total, 0);
  const totalWins = rows.reduce((s, r) => s + r.wins, 0);
  const totalSurveys = rows.reduce((s, r) => s + (r.survey ? r.survey.count : 0), 0);
  const summaryEl = document.getElementById('summary-cards');
  summaryEl.innerHTML = `
    <div class="stat-card total"><span class="stat-number">${total}</span><span class="stat-label">Total AI Games</span></div>
    <div class="stat-card wins"><span class="stat-number">${totalWins}</span><span class="stat-label">Total Wins</span></div>
    <div class="stat-card draws"><span class="stat-number">${totalSurveys}</span><span class="stat-label">Survey Responses</span></div>
  `;

  const levels = LEVEL_ORDER.filter(l => byLevel[l]);
  const labels = levels.map(l => LEVEL_LABELS[l]);
  const bgColors  = levels.map(l => LEVEL_COLORS[l].bg);
  const bdrColors = levels.map(l => LEVEL_COLORS[l].border);

  // Win Rate Chart
  new Chart(document.getElementById('winRateChart'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Win Rate (%)',
        data: levels.map(l => byLevel[l]?.win_rate ?? 0),
        backgroundColor: bgColors,
        borderColor: bdrColors,
        borderWidth: 2,
        borderRadius: 6,
      }],
    },
    options: { ...CHART_DEFAULTS, scales: { ...CHART_DEFAULTS.scales, y: { ...CHART_DEFAULTS.scales.y, max: 100 } } },
  });

  // Duration Chart
  new Chart(document.getElementById('durationChart'), {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Avg Duration (s)',
        data: levels.map(l => byLevel[l]?.avg_duration ?? 0),
        backgroundColor: bgColors,
        borderColor: bdrColors,
        borderWidth: 2,
        borderRadius: 6,
      }],
    },
    options: CHART_DEFAULTS,
  });

  // Survey Radar / Bar Chart
  const surveyDatasets = [
    { label: 'Ease of Use',    key: 'ease_of_use',    color: '#6c63ff' },
    { label: 'Challenge',      key: 'challenge',       color: '#ff6584' },
    { label: 'Engagement',     key: 'engagement',      color: '#43d97e' },
    { label: 'Replay Intent',  key: 'replay_intent',   color: '#f7c948' },
  ].map(m => ({
    label: m.label,
    data: levels.map(l => byLevel[l]?.survey?.[m.key] ?? 0),
    backgroundColor: m.color + '33',
    borderColor: m.color,
    borderWidth: 2,
    borderRadius: 4,
  }));

  new Chart(document.getElementById('surveyChart'), {
    type: 'bar',
    data: { labels, datasets: surveyDatasets },
    options: {
      ...CHART_DEFAULTS,
      scales: { ...CHART_DEFAULTS.scales, y: { ...CHART_DEFAULTS.scales.y, min: 0, max: 5 } },
    },
  });

  // Games Count Doughnut
  new Chart(document.getElementById('gamesChart'), {
    type: 'doughnut',
    data: {
      labels,
      datasets: [{
        data: levels.map(l => byLevel[l]?.total ?? 0),
        backgroundColor: bgColors,
        borderColor: bdrColors,
        borderWidth: 2,
      }],
    },
    options: {
      responsive: true,
      plugins: { legend: { labels: { color: '#e8eaf6' } } },
    },
  });

  // Table
  const tbody = document.getElementById('stats-tbody');
  tbody.innerHTML = levels.map(l => {
    const r = byLevel[l];
    const s = r.survey;
    return `<tr>
      <td><strong>${LEVEL_LABELS[l]}</strong></td>
      <td>${r.total}</td>
      <td class="wins">${r.wins}</td>
      <td>${r.losses}</td>
      <td>${r.draws}</td>
      <td>${r.win_rate}%</td>
      <td>${r.avg_duration}s</td>
      <td>${r.avg_moves}</td>
      <td>${s ? s.ease_of_use : '—'}</td>
      <td>${s ? s.challenge : '—'}</td>
      <td>${s ? s.engagement : '—'}</td>
      <td>${s ? s.replay_intent : '—'}</td>
      <td>${s ? s.count : 0}</td>
    </tr>`;
  }).join('');
}

loadStats();

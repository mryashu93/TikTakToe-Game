/* ===================================================
   play.js — AI game page logic
   =================================================== */

// CSRF helper — reads the csrftoken cookie Django sets
function getCookie(name) {
  const value = `; ${document.cookie}`;
  const parts = value.split(`; ${name}=`);
  if (parts.length === 2) return parts.pop().split(';').shift();
  return null;
}
const CSRF_TOKEN = getCookie('csrftoken');

const SYMBOLS = { X: '✖', O: '⭕' };
let gameId = null;
let playerSymbol = null;
let aiSymbol = null;
let board = Array(9).fill(null);
let gameOver = false;

// ---- DOM refs ----
const settingsPanel = document.getElementById('settings-panel');
const gamePanel     = document.getElementById('game-panel');
const startBtn      = document.getElementById('start-btn');
const newGameBtn    = document.getElementById('new-game-btn');
const statusBar     = document.getElementById('status-bar');
const levelBadge    = document.getElementById('level-badge');
const symbolBadge   = document.getElementById('symbol-badge');
const cells         = document.querySelectorAll('.cell');

const surveyOverlay = document.getElementById('survey-overlay');
const surveyForm    = document.getElementById('survey-form');
const surveyGameId  = document.getElementById('survey-game-id');
const skipSurveyBtn = document.getElementById('skip-survey-btn');

const achievementToast = document.getElementById('achievement-toast');

// ---- Likert scale builder ----
document.querySelectorAll('.likert-scale').forEach(container => {
  for (let i = 1; i <= 5; i++) {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'likert-btn';
    btn.textContent = i;
    btn.dataset.value = i;
    btn.addEventListener('click', () => {
      container.querySelectorAll('.likert-btn').forEach(b => b.classList.remove('selected'));
      btn.classList.add('selected');
    });
    container.appendChild(btn);
  }
});

// ---- Start game ----
startBtn.addEventListener('click', async () => {
  const level  = document.querySelector('input[name="level"]:checked').value;
  const symbol = document.querySelector('input[name="symbol"]:checked').value;

  const res = await fetch('/api/game/new', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
    body: JSON.stringify({ level, player_symbol: symbol }),
  });
  const data = await res.json();
  if (!res.ok) { alert(data.error || 'Failed to start game'); return; }

  gameId       = data.game_id;
  playerSymbol = data.player_symbol;
  aiSymbol     = data.ai_symbol;
  board        = data.board;
  gameOver     = false;

  levelBadge.className = `level-badge level-${level}`;
  levelBadge.textContent = level.charAt(0).toUpperCase() + level.slice(1);
  symbolBadge.textContent = `You: ${SYMBOLS[playerSymbol]}`;

  renderBoard(board);
  setStatus('Your turn!');
  settingsPanel.classList.add('hidden');
  gamePanel.classList.remove('hidden');

  // If AI went first
  if (data.ai_first_move !== null && data.ai_first_move !== undefined) {
    renderBoard(board);
    setStatus('Your turn!');
  }
});

// ---- Cell click ----
cells.forEach(cell => {
  cell.addEventListener('click', async () => {
    if (gameOver) return;
    const idx = parseInt(cell.dataset.index);
    if (board[idx] !== null) return;

    const res = await fetch('/api/game/move', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
      body: JSON.stringify({ game_id: gameId, position: idx }),
    });
    const data = await res.json();
    if (!res.ok) { console.warn(data.error); return; }

    board = data.board;
    renderBoard(board);

    if (data.game_over) {
      gameOver = true;
      handleGameOver(data.result, data.new_achievements);
    } else {
      setStatus('Your turn!');
    }
  });
});

// ---- New game ----
newGameBtn.addEventListener('click', () => {
  settingsPanel.classList.remove('hidden');
  gamePanel.classList.add('hidden');
  surveyOverlay.classList.add('hidden');
  cells.forEach(c => { c.textContent = ''; c.className = 'cell'; });
});

// ---- Render helpers ----
function renderBoard(b) {
  cells.forEach((cell, i) => {
    const val = b[i];
    cell.textContent = val ? SYMBOLS[val] : '';
    cell.classList.remove('x', 'o', 'taken', 'win-cell');
    if (val === 'X') { cell.classList.add('x', 'taken'); }
    if (val === 'O') { cell.classList.add('o', 'taken'); }
  });
}

function highlightWinningLine(b) {
  const lines = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];
  for (const [a, c, d] of lines) {
    if (b[a] && b[a] === b[c] && b[c] === b[d]) {
      [a, c, d].forEach(i => cells[i].classList.add('win-cell'));
      return;
    }
  }
}

function setStatus(msg) {
  statusBar.textContent = msg;
}

function handleGameOver(result, newAchievements) {
  const msgs = { win: '🎉 You win!', loss: '😔 AI wins!', draw: '🤝 Draw!' };
  setStatus(msgs[result] || 'Game over');
  highlightWinningLine(board);

  // Achievements toast
  if (newAchievements && newAchievements.length) {
    showAchievements(newAchievements);
  }

  // Survey modal (after short delay)
  setTimeout(() => {
    surveyGameId.value = gameId;
    surveyOverlay.classList.remove('hidden');
  }, 1200);
}

function showAchievements(list) {
  achievementToast.innerHTML = list.map(a =>
    `<div><span style="font-size:1.5rem">${a.icon || '🏅'}</span> <strong>${a.name}</strong><br/><small>${a.description}</small></div>`
  ).join('<hr style="margin:.5rem 0;border-color:var(--border)"/>');
  achievementToast.classList.remove('hidden');
  setTimeout(() => achievementToast.classList.add('hidden'), 5000);
}

// ---- Survey submit ----
surveyForm.addEventListener('submit', async e => {
  e.preventDefault();
  const fields = ['ease_of_use', 'challenge', 'engagement', 'replay_intent'];
  const payload = { game_id: parseInt(surveyGameId.value) };
  let valid = true;

  fields.forEach(f => {
    const selected = document.querySelector(`.likert-scale[data-field="${f}"] .likert-btn.selected`);
    if (!selected) { valid = false; return; }
    payload[f] = parseInt(selected.dataset.value);
  });

  if (!valid) { alert('Please answer all 4 questions.'); return; }

  await fetch('/api/survey', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', 'X-CSRFToken': CSRF_TOKEN },
    body: JSON.stringify(payload),
  });
  surveyOverlay.classList.add('hidden');
});

skipSurveyBtn.addEventListener('click', () => {
  surveyOverlay.classList.add('hidden');
});

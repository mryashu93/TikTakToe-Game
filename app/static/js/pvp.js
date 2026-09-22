/* ===================================================
   pvp.js — Real-time PvP via Socket.IO
   =================================================== */

const SYMBOLS = { X: '✖', O: '⭕' };

const socket = io();

let mySymbol     = null;
let myRoomCode   = null;
let myTurn       = false;
let pvpBoard     = Array(9).fill(null);
let pvpGameOver  = false;

// DOM refs
const lobby        = document.getElementById('pvp-lobby');
const gamePanel    = document.getElementById('pvp-game-panel');
const createBtn    = document.getElementById('create-room-btn');
const joinBtn      = document.getElementById('join-room-btn');
const codeInput    = document.getElementById('room-code-input');
const roomInfo     = document.getElementById('room-created-info');
const roomDisplay  = document.getElementById('room-code-display');
const pvpStatus    = document.getElementById('pvp-status');
const pvpCells     = document.querySelectorAll('#pvp-board .cell');
const pvpXLabel    = document.getElementById('pvp-x-label');
const pvpOLabel    = document.getElementById('pvp-o-label');
const leaveBtn     = document.getElementById('pvp-leave-btn');

// ---- Create room ----
createBtn.addEventListener('click', () => {
  socket.emit('create_room', {});
});

socket.on('room_created', data => {
  mySymbol   = data.symbol;   // 'X'
  myRoomCode = data.room_code;
  roomDisplay.textContent = data.room_code;
  roomInfo.classList.remove('hidden');
});

// ---- Join room ----
joinBtn.addEventListener('click', () => {
  const code = codeInput.value.trim().toUpperCase();
  if (!code) return;
  socket.emit('join_room_pvp', { room_code: code });
});

socket.on('room_joined', data => {
  mySymbol   = data.symbol;   // 'O'
  myRoomCode = data.room_code;
});

// ---- Game start ----
socket.on('game_start', data => {
  pvpBoard    = data.board;
  pvpGameOver = false;
  const players = data.players;

  pvpXLabel.textContent = `✖ ${players['X'] || 'X'}`;
  pvpOLabel.textContent = `⭕ ${players['O'] || 'O'}`;

  myTurn = (data.turn === mySymbol);
  pvpStatus.textContent = myTurn ? 'Your turn!' : "Opponent's turn…";

  lobby.classList.add('hidden');
  gamePanel.classList.remove('hidden');
  renderPvPBoard(pvpBoard);
});

// ---- Cell click ----
pvpCells.forEach(cell => {
  cell.addEventListener('click', () => {
    if (!myTurn || pvpGameOver) return;
    const idx = parseInt(cell.dataset.index);
    if (pvpBoard[idx] !== null) return;
    socket.emit('pvp_move', { room_code: myRoomCode, position: idx });
  });
});

// ---- Board update ----
socket.on('board_update', data => {
  pvpBoard = data.board;
  renderPvPBoard(pvpBoard);

  if (data.game_over) {
    pvpGameOver = true;
    myTurn = false;
    if (data.result === 'draw') {
      pvpStatus.textContent = '🤝 Draw!';
    } else if (data.winner_symbol === mySymbol) {
      pvpStatus.textContent = '🎉 You win!';
    } else {
      pvpStatus.textContent = '😔 Opponent wins!';
    }
    highlightWinningLine(pvpBoard, pvpCells);
  } else {
    myTurn = (data.turn === mySymbol);
    pvpStatus.textContent = myTurn ? 'Your turn!' : "Opponent's turn…";
  }
});

socket.on('opponent_disconnected', () => {
  pvpStatus.textContent = '⚠️ Opponent disconnected. Game ended.';
  pvpGameOver = true;
  myTurn = false;
});

socket.on('error', data => {
  alert(data.message || 'An error occurred');
});

// ---- Leave ----
leaveBtn.addEventListener('click', () => {
  location.reload();
});

// ---- Render ----
function renderPvPBoard(b) {
  pvpCells.forEach((cell, i) => {
    const val = b[i];
    cell.textContent = val ? SYMBOLS[val] : '';
    cell.classList.remove('x', 'o', 'taken', 'win-cell');
    if (val === 'X') { cell.classList.add('x', 'taken'); }
    if (val === 'O') { cell.classList.add('o', 'taken'); }
  });
}

function highlightWinningLine(b, cellList) {
  const lines = [[0,1,2],[3,4,5],[6,7,8],[0,3,6],[1,4,7],[2,5,8],[0,4,8],[2,4,6]];
  for (const [a, c, d] of lines) {
    if (b[a] && b[a] === b[c] && b[c] === b[d]) {
      [a, c, d].forEach(i => cellList[i].classList.add('win-cell'));
      return;
    }
  }
}

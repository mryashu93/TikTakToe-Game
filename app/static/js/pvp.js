/* ===================================================
   pvp.js — Real-time PvP via Django Channels WebSocket
   =================================================== */

const SYMBOLS = { X: '✖', O: '⭕' };

// Connect to WebSocket
const wsScheme = window.location.protocol === 'https:' ? 'wss' : 'ws';
const socket = new WebSocket(`${wsScheme}://${window.location.host}/ws/pvp/`);

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

// ---- Send helper ----
function send(data) {
  if (socket.readyState === WebSocket.OPEN) {
    socket.send(JSON.stringify(data));
  }
}

// ---- WebSocket open ----
socket.addEventListener('open', () => {
  console.log('WebSocket connected');
});

socket.addEventListener('error', (e) => {
  console.error('WebSocket error', e);
  alert('Connection error. Please refresh the page.');
});

// ---- Receive messages ----
socket.addEventListener('message', (event) => {
  const msg = JSON.parse(event.data);

  if (msg.type === 'room_created') {
    mySymbol   = msg.symbol;
    myRoomCode = msg.room_code;
    roomDisplay.textContent = msg.room_code;
    roomInfo.classList.remove('hidden');

  } else if (msg.type === 'room_joined') {
    mySymbol   = msg.symbol;
    myRoomCode = msg.room_code;

  } else if (msg.type === 'game_start') {
    pvpBoard    = msg.board;
    pvpGameOver = false;
    const players = msg.players;

    pvpXLabel.textContent = `✖ ${players['X'] || 'X'}`;
    pvpOLabel.textContent = `⭕ ${players['O'] || 'O'}`;

    myTurn = (msg.turn === mySymbol);
    pvpStatus.textContent = myTurn ? 'Your turn!' : "Opponent's turn…";

    lobby.classList.add('hidden');
    gamePanel.classList.remove('hidden');
    renderPvPBoard(pvpBoard);

  } else if (msg.type === 'board_update') {
    pvpBoard = msg.board;
    renderPvPBoard(pvpBoard);

    if (msg.game_over) {
      pvpGameOver = true;
      myTurn = false;
      if (msg.result === 'draw') {
        pvpStatus.textContent = '🤝 Draw!';
      } else if (msg.winner_symbol === mySymbol) {
        pvpStatus.textContent = '🎉 You win!';
      } else {
        pvpStatus.textContent = '😔 Opponent wins!';
      }
      highlightWinningLine(pvpBoard, pvpCells);
    } else {
      myTurn = (msg.turn === mySymbol);
      pvpStatus.textContent = myTurn ? 'Your turn!' : "Opponent's turn…";
    }

  } else if (msg.type === 'opponent_disconnected') {
    pvpStatus.textContent = '⚠️ Opponent disconnected. Game ended.';
    pvpGameOver = true;
    myTurn = false;

  } else if (msg.type === 'error') {
    alert(msg.message || 'An error occurred');
  }
});

// ---- Create room ----
createBtn.addEventListener('click', () => {
  send({ type: 'create_room' });
});

// ---- Join room ----
joinBtn.addEventListener('click', () => {
  const code = codeInput.value.trim().toUpperCase();
  if (!code) return;
  send({ type: 'join_room', room_code: code });
});

// ---- Cell click ----
pvpCells.forEach(cell => {
  cell.addEventListener('click', () => {
    if (!myTurn || pvpGameOver) return;
    const idx = parseInt(cell.dataset.index);
    if (pvpBoard[idx] !== null) return;
    send({ type: 'pvp_move', position: idx });
  });
});

// ---- Leave ----
leaveBtn.addEventListener('click', () => {
  socket.close();
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

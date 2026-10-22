const LEVELS = {
  easy: { label: 'Easy', max: 5, gravity: 0.6, spawnEvery: 1.1 },
  medium: { label: 'Medium', max: 10, gravity: 0.8, spawnEvery: 0.9 },
  hard: { label: 'Hard', max: 20, gravity: 1.0, spawnEvery: 0.75 }
};

const numberWords = [
  'zero', 'one', 'two', 'three', 'four', 'five', 'six', 'seven', 'eight', 'nine', 'ten',
  'eleven', 'twelve', 'thirteen', 'fourteen', 'fifteen', 'sixteen', 'seventeen', 'eighteen', 'nineteen', 'twenty'
];

const countables = [
  { emoji: '🍎', name: 'apples' },
  { emoji: '⭐', name: 'stars' },
  { emoji: '🐟', name: 'fish' },
  { emoji: '🍓', name: 'strawberries' },
  { emoji: '🚗', name: 'cars' },
  { emoji: '🎈', name: 'balloons' },
  { emoji: '🐥', name: 'chicks' },
  { emoji: '🍪', name: 'cookies' },
  { emoji: '⚽', name: 'balls' },
  { emoji: '🦋', name: 'butterflies' }
];

const modes = {
  count: { title: 'Count It', emoji: '🍎', description: 'How many can you see?' },
  add: { title: 'Add It', emoji: '➕', description: 'Put the groups together' },
  subtract: { title: 'Take Away', emoji: '➖', description: 'How many are left?' },
  slice: { title: 'Ninja Slice', emoji: '🥷', description: 'Slice the right numbers!' }
};

// Belts unlock as total stars grow, like a real martial-arts grading.
const belts = [
  { name: 'White', minStars: 0, color: '#f8fafc', text: '#1f2a44' },
  { name: 'Yellow', minStars: 5, color: '#fde047', text: '#1f2a44' },
  { name: 'Orange', minStars: 15, color: '#fdba74', text: '#1f2a44' },
  { name: 'Green', minStars: 30, color: '#86efac', text: '#1f2a44' },
  { name: 'Blue', minStars: 50, color: '#60a5fa', text: '#ffffff' },
  { name: 'Purple', minStars: 75, color: '#a78bfa', text: '#ffffff' },
  { name: 'Black', minStars: 100, color: '#1f2937', text: '#ffffff' }
];

const QUESTIONS_PER_ROUND = 5;
const SLICE_SECONDS = 30;
const SLICE_LIVES = 3;
const TOKEN_SIZE = 68;
const STORAGE_KEY = 'number-ninja-progress';

const modeGrid = document.querySelector('#modeGrid');
const numberGrid = document.querySelector('#numberGrid');
const beltBadge = document.querySelector('#beltBadge');
const homeBtn = document.querySelector('#homeBtn');
const lessonOverlay = document.querySelector('#lessonOverlay');
const lessonNumber = document.querySelector('#lessonNumber');
const lessonWord = document.querySelector('#lessonWord');
const lessonParity = document.querySelector('#lessonParity');
const lessonFrames = document.querySelector('#lessonFrames');
const lessonObjects = document.querySelector('#lessonObjects');
const quizOverlay = document.querySelector('#quizOverlay');
const quizTitle = document.querySelector('#quizTitle');
const quizProgress = document.querySelector('#quizProgress');
const quizTrack = document.querySelector('#quizTrack');
const quizVisual = document.querySelector('#quizVisual');
const quizPrompt = document.querySelector('#quizPrompt');
const quizChoices = document.querySelector('#quizChoices');
const quizFeedback = document.querySelector('#quizFeedback');
const sliceOverlay = document.querySelector('#sliceOverlay');
const sliceArena = document.querySelector('#sliceArena');
const sliceIntro = document.querySelector('#sliceIntro');
const sliceIntroRule = document.querySelector('#sliceIntroRule');
const sliceRule = document.querySelector('#sliceRule');
const sliceScore = document.querySelector('#sliceScore');
const sliceLives = document.querySelector('#sliceLives');
const sliceTimer = document.querySelector('#sliceTimer');
const resultOverlay = document.querySelector('#resultOverlay');
const resultStars = document.querySelector('#resultStars');
const resultTitle = document.querySelector('#resultTitle');
const resultSummary = document.querySelector('#resultSummary');
const resultBelt = document.querySelector('#resultBelt');
const confettiLayer = document.querySelector('#confettiLayer');

const allModals = [lessonOverlay, quizOverlay, sliceOverlay, resultOverlay];

const state = {
  level: 'easy',
  stars: 0,
  lastMode: 'count',
  lessonNumber: 1,
  timers: [],
  quiz: null,
  slice: null
};

let audioCtx = null;

/* ---------- Progress (saved in this browser) ---------- */

function loadProgress() {
  try {
    const saved = JSON.parse(localStorage.getItem(STORAGE_KEY));
    if (saved && Number.isFinite(saved.stars)) state.stars = saved.stars;
    if (saved && LEVELS[saved.level]) state.level = saved.level;
  } catch (error) {
    // Storage blocked (private mode) or corrupted: start fresh.
  }
}

function saveProgress() {
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify({ stars: state.stars, level: state.level }));
  } catch (error) {
    // Progress just won't persist; the game still works.
  }
}

function currentBelt(stars = state.stars) {
  return [...belts].reverse().find((belt) => stars >= belt.minStars);
}

function renderBelt() {
  const belt = currentBelt();
  beltBadge.textContent = `🥋 ${belt.name} belt · ⭐ ${state.stars}`;
  beltBadge.style.background = belt.color;
  beltBadge.style.color = belt.text;
}

function addStars(count) {
  const before = currentBelt();
  state.stars += count;
  saveProgress();
  renderBelt();
  const after = currentBelt();
  return after !== before ? after : null;
}

/* ---------- Home screen ---------- */

function buildHome() {
  Object.entries(modes).forEach(([key, mode]) => {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'mode-card';
    card.setAttribute('aria-label', `Play ${mode.title}`);
    card.innerHTML = `
      <span class="mode-emoji">${mode.emoji}</span>
      <span class="mode-title">${mode.title}</span>
      <span class="mode-desc">${mode.description}</span>
    `;
    card.addEventListener('click', () => startMode(key));
    modeGrid.appendChild(card);
  });

  for (let n = 0; n <= 20; n++) {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = 'number-card';
    card.setAttribute('aria-label', `Learn number ${n}`);
    card.innerHTML = `
      <span class="number-char">${n}</span>
      <span class="number-word">${numberWords[n]}</span>
    `;
    card.addEventListener('click', () => openLesson(n));
    numberGrid.appendChild(card);
  }

  document.querySelectorAll('.level-btn').forEach((button) => {
    button.addEventListener('click', () => {
      state.level = button.dataset.level;
      saveProgress();
      renderLevel();
      speak(`Numbers up to ${LEVELS[state.level].max}`);
    });
  });

  renderLevel();
}

function renderLevel() {
  document.querySelectorAll('.level-btn').forEach((button) => {
    button.classList.toggle('active', button.dataset.level === state.level);
  });
}

function startMode(mode) {
  state.lastMode = mode;
  if (mode === 'slice') {
    openSlice();
  } else {
    startQuiz(mode);
  }
}

/* ---------- Modals ---------- */

function openModal(modal) {
  allModals.forEach((m) => m.classList.toggle('hidden', m !== modal));
  homeBtn.classList.remove('hidden');
}

function showHomeScreen() {
  clearTimers();
  stopSlice();
  if ('speechSynthesis' in window) speechSynthesis.cancel();
  allModals.forEach((m) => m.classList.add('hidden'));
  homeBtn.classList.add('hidden');
}

function clearTimers() {
  state.timers.forEach((id) => clearTimeout(id));
  state.timers = [];
}

function later(fn, ms) {
  state.timers.push(setTimeout(fn, ms));
}

/* ---------- Sound ---------- */

function speak(text, rate = 0.8) {
  if (!('speechSynthesis' in window)) return;
  speechSynthesis.cancel();
  const utterance = new SpeechSynthesisUtterance(text);
  utterance.lang = 'en-US';
  utterance.rate = rate;
  utterance.pitch = 1.2;
  speechSynthesis.speak(utterance);
}

function getAudio() {
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtx) return null;
  if (!audioCtx) audioCtx = new AudioCtx();
  if (audioCtx.state === 'suspended') audioCtx.resume();
  return audioCtx;
}

function playTones(frequencies, { type = 'sine', step = 0.09, length = 0.2, peak = 0.12 } = {}) {
  const ctx = getAudio();
  if (!ctx) return;

  frequencies.forEach((frequency, index) => {
    const start = ctx.currentTime + index * step;
    const oscillator = ctx.createOscillator();
    const gainNode = ctx.createGain();
    oscillator.type = type;
    oscillator.frequency.value = frequency;
    gainNode.gain.setValueAtTime(0.0001, start);
    gainNode.gain.exponentialRampToValueAtTime(peak, start + 0.05);
    gainNode.gain.exponentialRampToValueAtTime(0.0001, start + length);
    oscillator.connect(gainNode);
    gainNode.connect(ctx.destination);
    oscillator.start(start);
    oscillator.stop(start + length);
  });
}

function playSuccessTone() {
  playTones([523.25, 659.25, 783.99]);
}

function playOopsTone() {
  playTones([330, 247], { type: 'triangle', step: 0.12, peak: 0.1 });
}

function playSliceTone() {
  playTones([880, 1320], { type: 'triangle', step: 0.04, length: 0.12, peak: 0.1 });
}

function celebrate() {
  spawnConfetti();
  playSuccessTone();
}

function spawnConfetti() {
  const colors = ['#ff7eb3', '#ffd166', '#5eead4', '#60a5fa', '#a78bfa', '#f97316'];

  for (let i = 0; i < 45; i++) {
    const piece = document.createElement('span');
    piece.className = 'confetti-piece';
    piece.style.left = `${Math.random() * window.innerWidth}px`;
    piece.style.background = colors[Math.floor(Math.random() * colors.length)];
    piece.style.setProperty('--dx', `${(Math.random() - 0.5) * 260}px`);
    piece.style.animationDelay = `${(Math.random() * 0.5).toFixed(2)}s`;
    confettiLayer.appendChild(piece);

    setTimeout(() => piece.remove(), 2000);
  }
}

/* ---------- Number lesson ---------- */

function openLesson(n) {
  clearTimers();
  state.lessonNumber = n;
  lessonNumber.textContent = n;
  lessonWord.textContent = numberWords[n];
  lessonParity.textContent = n === 0 ? 'Zero means none at all' : `${n} is ${n % 2 === 0 ? 'even' : 'odd'}`;

  renderTenFrames(n);

  const item = countables[n % countables.length];
  lessonObjects.innerHTML = '';
  for (let i = 0; i < n; i++) {
    const span = document.createElement('span');
    span.textContent = item.emoji;
    lessonObjects.appendChild(span);
  }

  openModal(lessonOverlay);
  speak(numberWords[n]);
}

function renderTenFrames(n) {
  lessonFrames.innerHTML = '';
  const frameCount = n > 10 ? 2 : 1;

  for (let f = 0; f < frameCount; f++) {
    const frame = document.createElement('div');
    frame.className = 'ten-frame';
    for (let c = 0; c < 10; c++) {
      const cell = document.createElement('span');
      cell.className = 'frame-cell';
      if (f * 10 + c < n) cell.classList.add('filled');
      frame.appendChild(cell);
    }
    lessonFrames.appendChild(frame);
  }
}

function countWithMe() {
  clearTimers();
  const n = state.lessonNumber;
  const dots = [...lessonFrames.querySelectorAll('.frame-cell.filled')];
  const objects = [...lessonObjects.children];
  dots.forEach((dot) => dot.classList.remove('counted'));
  objects.forEach((obj) => obj.classList.remove('counted'));

  if (n === 0) {
    speak('Zero. There is nothing to count!');
    return;
  }

  for (let i = 0; i < n; i++) {
    later(() => {
      dots[i].classList.add('counted');
      objects[i].classList.add('counted');
      speak(numberWords[i + 1], 1);
    }, i * 800);
  }

  later(() => {
    speak(`${numberWords[n]}! Great counting!`);
    celebrate();
  }, n * 800 + 300);
}

/* ---------- Count It / Add It / Take Away ---------- */

function randInt(min, max) {
  return Math.floor(Math.random() * (max - min + 1)) + min;
}

function pick(items) {
  return items[Math.floor(Math.random() * items.length)];
}

function shuffle(items) {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

function makeQuestion(mode, max) {
  const item = pick(countables);

  if (mode === 'count') {
    const n = randInt(1, max);
    return {
      item,
      answer: n,
      groups: [{ count: n }],
      prompt: `How many ${item.emoji}?`,
      spoken: `How many ${item.name} can you count?`,
      solved: `${n} ${item.name}!`
    };
  }

  if (mode === 'add') {
    const a = randInt(1, max - 1);
    const b = randInt(1, max - a);
    return {
      item,
      answer: a + b,
      groups: [{ count: a }, { op: '+' }, { count: b }],
      prompt: `${a} + ${b} = ?`,
      spoken: `What is ${numberWords[a]} plus ${numberWords[b]}?`,
      solved: `${a} plus ${b} equals ${a + b}!`
    };
  }

  const a = randInt(2, max);
  const b = randInt(1, a - 1);
  return {
    item,
    answer: a - b,
    groups: [{ count: a, taken: b }],
    prompt: `${a} − ${b} = ?`,
    spoken: `${numberWords[a]} take away ${numberWords[b]}. How many are left?`,
    solved: `${a} take away ${b} leaves ${a - b}!`
  };
}

// Four answer buttons: the right answer plus close neighbours, in counting order.
function makeChoices(answer, max) {
  const choices = new Set([answer]);
  shuffle([-1, 1, -2, 2, -3, 3]).forEach((offset) => {
    const value = answer + offset;
    if (choices.size < 4 && value >= 0 && value <= max) choices.add(value);
  });
  while (choices.size < 4) choices.add(randInt(0, max));
  return [...choices].sort((x, y) => x - y);
}

function startQuiz(mode) {
  clearTimers();
  state.quiz = { mode, index: 0, firstTry: 0, results: [], question: null, missed: false, locked: false };
  quizTitle.textContent = `${modes[mode].emoji} ${modes[mode].title}`;
  openModal(quizOverlay);
  nextQuestion();
}

function nextQuestion() {
  const quiz = state.quiz;
  const question = makeQuestion(quiz.mode, LEVELS[state.level].max);
  quiz.question = question;
  quiz.missed = false;
  quiz.locked = false;

  quizProgress.textContent = `Question ${quiz.index + 1} of ${QUESTIONS_PER_ROUND}`;
  quizTrack.textContent = Array.from({ length: QUESTIONS_PER_ROUND }, (_, i) => quiz.results[i] || '○').join(' ');
  quizPrompt.textContent = question.prompt;
  quizFeedback.textContent = '';

  quizVisual.innerHTML = '';
  question.groups.forEach((group) => {
    if (group.op) {
      const op = document.createElement('span');
      op.className = 'quiz-op';
      op.textContent = group.op;
      quizVisual.appendChild(op);
      return;
    }
    const box = document.createElement('div');
    box.className = 'quiz-group';
    box.style.gridTemplateColumns = `repeat(${Math.min(group.count, 5)}, auto)`;
    for (let i = 0; i < group.count; i++) {
      const span = document.createElement('span');
      span.textContent = question.item.emoji;
      if (group.taken && i >= group.count - group.taken) span.classList.add('taken');
      box.appendChild(span);
    }
    quizVisual.appendChild(box);
  });

  quizChoices.innerHTML = '';
  makeChoices(question.answer, LEVELS[state.level].max).forEach((value) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'choice-btn';
    btn.textContent = value;
    btn.addEventListener('click', () => handleChoice(btn, value));
    quizChoices.appendChild(btn);
  });

  speak(question.spoken);
}

function handleChoice(btn, value) {
  const quiz = state.quiz;
  if (quiz.locked) return;

  if (value === quiz.question.answer) {
    quiz.locked = true;
    btn.classList.add('correct');
    if (!quiz.missed) quiz.firstTry += 1;
    quiz.results[quiz.index] = quiz.missed ? '🟡' : '🟢';
    quizFeedback.textContent = `✅ ${quiz.question.solved}`;
    playSuccessTone();
    speak(quiz.question.solved);

    later(() => {
      quiz.index += 1;
      if (quiz.index >= QUESTIONS_PER_ROUND) {
        finishQuiz();
      } else {
        nextQuestion();
      }
    }, 1800);
  } else {
    quiz.missed = true;
    btn.classList.add('wrong');
    btn.disabled = true;
    quizFeedback.textContent = 'Almost! Try again 💪';
    playOopsTone();
    speak('Try again!');
  }
}

function finishQuiz() {
  const { firstTry } = state.quiz;
  const stars = firstTry >= 5 ? 3 : firstTry >= 3 ? 2 : 1;
  showResult(stars, `You got ${firstTry} of ${QUESTIONS_PER_ROUND} right on the first try.`);
}

/* ---------- Ninja Slice ---------- */

function makeSliceRule(level) {
  const max = LEVELS[level].max;
  const target = randInt(1, max);
  const rules = [{
    text: `Slice every ${target}!`,
    spoken: `Slice every number ${numberWords[target]}!`,
    test: (n) => n === target,
    sample: () => target
  }];

  if (level !== 'easy') {
    const k = randInt(3, max - 3);
    rules.push(
      {
        text: 'Slice the EVEN numbers!',
        spoken: 'Slice the even numbers!',
        test: (n) => n % 2 === 0,
        sample: () => randInt(0, Math.floor(max / 2)) * 2
      },
      {
        text: 'Slice the ODD numbers!',
        spoken: 'Slice the odd numbers!',
        test: (n) => n % 2 === 1,
        sample: () => randInt(0, Math.floor((max - 1) / 2)) * 2 + 1
      },
      {
        text: `Slice numbers bigger than ${k}!`,
        spoken: `Slice numbers bigger than ${numberWords[k]}!`,
        test: (n) => n > k,
        sample: () => randInt(k + 1, max)
      },
      {
        text: `Slice numbers smaller than ${k}!`,
        spoken: `Slice numbers smaller than ${numberWords[k]}!`,
        test: (n) => n < k,
        sample: () => randInt(0, k - 1)
      }
    );
  }

  return pick(rules);
}

function openSlice() {
  clearTimers();
  stopSlice();
  const rule = makeSliceRule(state.level);
  state.slice = {
    rule,
    running: false,
    tokens: [],
    score: 0,
    mistakes: 0,
    lives: SLICE_LIVES,
    elapsed: 0,
    sinceSpawn: 0,
    lastFrame: 0,
    frameId: null,
    slicing: false
  };

  sliceRule.textContent = rule.text;
  sliceIntroRule.textContent = rule.text;
  sliceIntro.classList.remove('hidden');
  renderSliceHud();
  openModal(sliceOverlay);
  speak(rule.spoken);
}

function renderSliceHud() {
  const slice = state.slice;
  sliceScore.textContent = `⭐ ${slice.score}`;
  sliceLives.textContent = '❤️'.repeat(slice.lives) + '🤍'.repeat(SLICE_LIVES - slice.lives);
  sliceTimer.textContent = `⏱️ ${Math.max(0, Math.ceil(SLICE_SECONDS - slice.elapsed))}`;
}

function startSlice() {
  const slice = state.slice;
  getAudio();
  sliceIntro.classList.add('hidden');
  slice.running = true;
  slice.lastFrame = performance.now();
  slice.frameId = requestAnimationFrame(sliceFrame);
}

function spawnToken() {
  const slice = state.slice;
  const { max, gravity } = LEVELS[state.level];
  const width = sliceArena.clientWidth;
  const height = sliceArena.clientHeight;
  // Weight spawns toward correct answers so there is always something to slice.
  const value = Math.random() < 0.45 ? slice.rule.sample() : randInt(0, max);

  const el = document.createElement('div');
  el.className = 'slice-token';
  el.innerHTML = `<span class="token-face">${value}</span>`;
  sliceArena.appendChild(el);

  // Launch from below the arena on an arc that peaks 55–85% of the way up.
  const g = gravity * height;
  const rise = (0.55 + Math.random() * 0.3) * height;
  slice.tokens.push({
    el,
    value,
    x: TOKEN_SIZE / 2 + Math.random() * (width - TOKEN_SIZE * 1.5),
    y: height,
    vx: (Math.random() - 0.5) * 80,
    vy: -Math.sqrt(2 * g * rise),
    g
  });
}

function sliceFrame(now) {
  const slice = state.slice;
  if (!slice || !slice.running) return;

  // Clamp the step so a backgrounded tab pauses the game instead of jumping ahead.
  const dt = Math.max(0, Math.min(0.05, (now - slice.lastFrame) / 1000));
  slice.lastFrame = now;
  slice.elapsed += dt;
  slice.sinceSpawn += dt;

  if (slice.sinceSpawn >= LEVELS[state.level].spawnEvery) {
    slice.sinceSpawn = 0;
    spawnToken();
  }

  const height = sliceArena.clientHeight;
  slice.tokens = slice.tokens.filter((token) => {
    token.vy += token.g * dt;
    token.x += token.vx * dt;
    token.y += token.vy * dt;
    if (token.vy > 0 && token.y > height + 10) {
      token.el.remove();
      return false;
    }
    token.el.style.transform = `translate(${token.x}px, ${token.y}px)`;
    return true;
  });

  renderSliceHud();

  if (slice.elapsed >= SLICE_SECONDS || slice.lives <= 0) {
    finishSlice();
    return;
  }
  slice.frameId = requestAnimationFrame(sliceFrame);
}

function arenaPoint(event) {
  const rect = sliceArena.getBoundingClientRect();
  return { x: event.clientX - rect.left, y: event.clientY - rect.top };
}

function trySlice(point) {
  const slice = state.slice;
  if (!slice || !slice.running) return;

  const dot = document.createElement('span');
  dot.className = 'slash-dot';
  dot.style.left = `${point.x}px`;
  dot.style.top = `${point.y}px`;
  sliceArena.appendChild(dot);
  setTimeout(() => dot.remove(), 300);

  const pad = 8;
  slice.tokens = slice.tokens.filter((token) => {
    const hit = point.x >= token.x - pad && point.x <= token.x + TOKEN_SIZE + pad
      && point.y >= token.y - pad && point.y <= token.y + TOKEN_SIZE + pad;
    if (!hit) return true;

    if (slice.rule.test(token.value)) {
      slice.score += 1;
      token.el.classList.add('good');
      playSliceTone();
    } else {
      slice.lives -= 1;
      slice.mistakes += 1;
      token.el.classList.add('bad');
      playOopsTone();
    }
    setTimeout(() => token.el.remove(), 450);
    return false;
  });
}

function stopSlice() {
  const slice = state.slice;
  if (!slice) return;
  slice.running = false;
  if (slice.frameId) cancelAnimationFrame(slice.frameId);
  sliceArena.querySelectorAll('.slice-token, .slash-dot').forEach((el) => el.remove());
  slice.tokens = [];
}

function finishSlice() {
  const { score, lives } = state.slice;
  stopSlice();
  const stars = score >= 12 ? 3 : score >= 7 ? 2 : score >= 1 ? 1 : 0;
  const ending = lives <= 0 ? 'Out of hearts!' : "Time's up!";
  showResult(stars, `${ending} You sliced ${score} right number${score === 1 ? '' : 's'}.`);
}

/* ---------- Results ---------- */

function showResult(stars, summary) {
  const titles = ["Let's try again!", 'Nice try!', 'Great job!', 'Super ninja!'];
  resultStars.textContent = '⭐'.repeat(stars) + '☆'.repeat(3 - stars);
  resultTitle.textContent = titles[stars];
  resultSummary.textContent = summary;

  const newBelt = addStars(stars);
  if (newBelt) {
    resultBelt.textContent = `🥋 You earned the ${newBelt.name} belt!`;
    resultBelt.classList.remove('hidden');
  } else {
    resultBelt.classList.add('hidden');
  }

  openModal(resultOverlay);
  if (stars > 0) celebrate();
  speak(newBelt ? `${titles[stars]} You earned the ${newBelt.name} belt!` : titles[stars], 0.9);
}

/* ---------- Wiring ---------- */

document.querySelector('#hearNumberBtn').addEventListener('click', () => speak(numberWords[state.lessonNumber]));
document.querySelector('#countWithMeBtn').addEventListener('click', countWithMe);
document.querySelector('#sliceStartBtn').addEventListener('click', startSlice);
document.querySelector('#playAgainBtn').addEventListener('click', () => startMode(state.lastMode));
document.querySelector('#resultHomeBtn').addEventListener('click', showHomeScreen);
document.querySelectorAll('[data-close]').forEach((btn) => btn.addEventListener('click', showHomeScreen));
homeBtn.addEventListener('click', showHomeScreen);

document.addEventListener('keydown', (event) => {
  if (event.key === 'Escape') showHomeScreen();
});

sliceArena.addEventListener('pointerdown', (event) => {
  if (!state.slice || !state.slice.running) return;
  state.slice.slicing = true;
  sliceArena.setPointerCapture(event.pointerId);
  trySlice(arenaPoint(event));
});

sliceArena.addEventListener('pointermove', (event) => {
  if (!state.slice || !state.slice.slicing) return;
  trySlice(arenaPoint(event));
});

['pointerup', 'pointercancel'].forEach((type) => {
  sliceArena.addEventListener(type, () => {
    if (state.slice) state.slice.slicing = false;
  });
});

loadProgress();
buildHome();
renderBelt();
showHomeScreen();

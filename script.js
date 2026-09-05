const alphabetData = {
  A: { word: 'Apple', sound: 'ah', phonics: 'A says ah', emoji: '🍎' },
  B: { word: 'Bear', sound: 'b', phonics: 'B says b', emoji: '🧸' },
  C: { word: 'Cat', sound: 'k', phonics: 'C says k', emoji: '🐱' },
  D: { word: 'Dog', sound: 'd', phonics: 'D says d', emoji: '🐶' },
  E: { word: 'Elephant', sound: 'eh', phonics: 'E says eh', emoji: '🐘' },
  F: { word: 'Fish', sound: 'f', phonics: 'F says f', emoji: '🐟' },
  G: { word: 'Giraffe', sound: 'g', phonics: 'G says g', emoji: '🦒' },
  H: { word: 'Hippo', sound: 'h', phonics: 'H says h', emoji: '🦛' },
  I: { word: 'Ice Cream', sound: 'ih', phonics: 'I says ih', emoji: '🍦' },
  J: { word: 'Jam', sound: 'j', phonics: 'J says j', emoji: '🧺' },
  K: { word: 'Kite', sound: 'k', phonics: 'K says k', emoji: '🪁' },
  L: { word: 'Lion', sound: 'l', phonics: 'L says l', emoji: '🦁' },
  M: { word: 'Moon', sound: 'm', phonics: 'M says m', emoji: '🌙' },
  N: { word: 'Nose', sound: 'n', phonics: 'N says n', emoji: '👃' },
  O: { word: 'Orange', sound: 'oh', phonics: 'O says oh', emoji: '🍊' },
  P: { word: 'Penguin', sound: 'p', phonics: 'P says p', emoji: '🐧' },
  Q: { word: 'Queen', sound: 'kw', phonics: 'Q says kw', emoji: '👑' },
  R: { word: 'Rainbow', sound: 'r', phonics: 'R says r', emoji: '🌈' },
  S: { word: 'Sun', sound: 's', phonics: 'S says s', emoji: '☀️' },
  T: { word: 'Tree', sound: 't', phonics: 'T says t', emoji: '🌳' },
  U: { word: 'Umbrella', sound: 'uh', phonics: 'U says uh', emoji: '☂️' },
  V: { word: 'Violin', sound: 'v', phonics: 'V says v', emoji: '🎻' },
  W: { word: 'Watermelon', sound: 'w', phonics: 'W says w', emoji: '🍉' },
  X: { word: 'Xylophone', sound: 'z', phonics: 'X says z', emoji: '🎼' },
  Y: { word: 'Yarn', sound: 'y', phonics: 'Y says y', emoji: '🧶' },
  Z: { word: 'Zebra', sound: 'z', phonics: 'Z says z', emoji: '🦓' }
};

const objectBank = {
  A: ['Apple', 'Airplane', 'Ant', 'Apron', 'Anchor', 'Arrow'],
  B: ['Ball', 'Banana', 'Bear', 'Book', 'Boat', 'Bird'],
  C: ['Cat', 'Car', 'Cookie', 'Cup', 'Cloud', 'Camel'],
  D: ['Dog', 'Donut', 'Drum', 'Dinosaur', 'Duck', 'Door'],
  E: ['Elephant', 'Egg', 'Eagle', 'Envelope', 'Earth', 'Easel'],
  F: ['Fish', 'Flower', 'Frog', 'Fork', 'Firetruck', 'Fan'],
  G: ['Giraffe', 'Gift', 'Guitar', 'Globe', 'Goat', 'Game'],
  H: ['Horse', 'Hat', 'House', 'Hammer', 'Hotdog', 'Heart'],
  I: ['Ice Cream', 'Igloo', 'Insect', 'Island', 'Image', 'Iron'],
  J: ['Jam', 'Jar', 'Jet', 'Jacket', 'Jellyfish', 'Juice'],
  K: ['Kite', 'Kangaroo', 'Key', 'Kiwi', 'Koala', 'Kettle'],
  L: ['Lion', 'Leaf', 'Lemon', 'Lamp', 'Ladder', 'Lollipop'],
  M: ['Moon', 'Milk', 'Mouse', 'Mushroom', 'Monkey', 'Map'],
  N: ['Nose', 'Nest', 'Nugget', 'Nail', 'Net', 'Notebook'],
  O: ['Orange', 'Owl', 'Octopus', 'Onion', 'Olive', 'Oven'],
  P: ['Penguin', 'Piano', 'Panda', 'Pencil', 'Pizza', 'Pail'],
  Q: ['Queen', 'Quail', 'Quarter', 'Question', 'Quilt', 'Quokka'],
  R: ['Rainbow', 'Robot', 'Rocket', 'Rabbit', 'Rose', 'Ring'],
  S: ['Sun', 'Star', 'Strawberry', 'Shark', 'Socks', 'Ship'],
  T: ['Tree', 'Turtle', 'Train', 'Teddy', 'Taco', 'Tiger'],
  U: ['Umbrella', 'Unicorn', 'Upstairs', 'Urchin', 'Utensil', 'Underwear'],
  V: ['Violin', 'Volcano', 'Van', 'Vase', 'Video', 'Velvet'],
  W: ['Watermelon', 'Whale', 'Wheel', 'Wagon', 'Window', 'Watch'],
  X: ['Xylophone', 'X-ray', 'Xmas Tree', 'Xylophone', 'Xylophone', 'Xylophone'],
  Y: ['Yarn', 'Yogurt', 'Yarn Ball', 'Yo-yo', 'Yawn', 'Yak'],
  Z: ['Zebra', 'Zoo', 'Zucchini', 'Zipper', 'Zigzag', 'Zero']
};

const letterGrid = document.querySelector('#letterGrid');
const lessonOverlay = document.querySelector('#lessonOverlay');
const traceOverlay = document.querySelector('#traceOverlay');
const objectOverlay = document.querySelector('#objectOverlay');
const homeBtn = document.querySelector('#homeBtn');
const selectedLetterBig = document.querySelector('#selectedLetterBig');
const letterPhonic = document.querySelector('#letterPhonic');
const letterWord = document.querySelector('#letterWord');
const uppercasePreview = document.querySelector('#uppercasePreview');
const lowercasePreview = document.querySelector('#lowercasePreview');
const traceStatus = document.querySelector('#traceStatus');
const traceCanvas = document.querySelector('#traceCanvas');
const traceCtx = traceCanvas.getContext('2d');
const objectScene = document.querySelector('#objectScene');
const objectPrompt = document.querySelector('#objectPrompt');
const objectProgress = document.querySelector('#objectProgress');
const confettiLayer = document.querySelector('#confettiLayer');

const state = {
  currentLetter: 'A',
  activeTraceCase: 'uppercase',
  traceProgress: 0,
  foundCount: 0,
  targetCount: 3,
  currentSceneItems: []
};

function buildAlphabetGrid() {
  const letters = Object.keys(alphabetData);

  letters.forEach((letter) => {
    const card = document.createElement('button');
    card.className = 'letter-card';
    card.type = 'button';
    card.setAttribute('aria-label', `Learn letter ${letter}`);
    card.innerHTML = `
      <span class="letter-char">${letter}</span>
      <span class="letter-word">${alphabetData[letter].word}</span>
    `;

    card.addEventListener('click', () => openLesson(letter));
    letterGrid.appendChild(card);
  });
}

function openLesson(letter) {
  state.currentLetter = letter;
  const info = alphabetData[letter];

  selectedLetterBig.textContent = letter;
  letterPhonic.textContent = info.sound;
  letterWord.textContent = `${letter} is for ${info.word}`;
  uppercasePreview.textContent = letter;
  lowercasePreview.textContent = letter.toLowerCase();

  lessonOverlay.classList.remove('hidden');
  homeBtn.classList.remove('hidden');

  playLetterAudio(letter, true);
}

function showHomeScreen() {
  lessonOverlay.classList.add('hidden');
  traceOverlay.classList.add('hidden');
  objectOverlay.classList.add('hidden');
  homeBtn.classList.add('hidden');
}

function escapeModal() {
  lessonOverlay.classList.add('hidden');
  traceOverlay.classList.add('hidden');
  objectOverlay.classList.add('hidden');
}

function cleanSpeechText(text) {
  const phonemeMap = {
    'æ': 'ah',
    'b': 'b',
    'k': 'k',
    'd': 'd',
    'ɛ': 'eh',
    'f': 'f',
    'g': 'g',
    'h': 'h',
    'ɪ': 'ih',
    'dʒ': 'j',
    'l': 'l',
    'm': 'm',
    'n': 'n',
    'oʊ': 'oh',
    'p': 'p',
    'kw': 'kw',
    'r': 'r',
    's': 's',
    't': 't',
    'ʌ': 'uh',
    'v': 'v',
    'w': 'w',
    'z': 'z',
    'j': 'y'
  };

  return String(text)
    .replace(/\/([^/]+)\//g, (_, inner) => phonemeMap[inner] || inner)
    .replace(/\//g, ' ')
    .replace(/\s+/g, ' ')
    .trim();
}

function playLetterAudio(letter, isIntro = false) {
  const info = alphabetData[letter];
  const message = `${letter} is for ${info.word}.`;

  if ('speechSynthesis' in window) {
    speechSynthesis.cancel();

    const utterance = new SpeechSynthesisUtterance(message);
    utterance.lang = 'en-US';
    utterance.rate = 0.6;
    utterance.pitch = 1.2;
    speechSynthesis.speak(utterance);
  }

  playToneSequence();
}

function playToneSequence() {
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtx) return;

  const audioCtx = new AudioCtx();
  const notes = [440, 554, 659];

  notes.forEach((frequency, index) => {
    const oscillator = audioCtx.createOscillator();
    const gainNode = audioCtx.createGain();
    oscillator.type = 'triangle';
    oscillator.frequency.value = frequency;
    gainNode.gain.setValueAtTime(0.0001, audioCtx.currentTime + index * 0.10);
    gainNode.gain.exponentialRampToValueAtTime(0.18, audioCtx.currentTime + index * 0.10 + 0.05);
    gainNode.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + index * 0.10 + 0.18);
    oscillator.connect(gainNode);
    gainNode.connect(audioCtx.destination);
    oscillator.start(audioCtx.currentTime + index * 0.10);
    oscillator.stop(audioCtx.currentTime + index * 0.10 + 0.18);
  });

  setTimeout(() => audioCtx.close(), 700);
}

function playSuccessTone() {
  const AudioCtx = window.AudioContext || window.webkitAudioContext;
  if (!AudioCtx) return;

  const audioCtx = new AudioCtx();
  const pattern = [523.25, 659.25, 783.99];

  pattern.forEach((frequency, index) => {
    const oscillator = audioCtx.createOscillator();
    const gainNode = audioCtx.createGain();
    oscillator.type = 'sine';
    oscillator.frequency.value = frequency;
    gainNode.gain.setValueAtTime(0.0001, audioCtx.currentTime + index * 0.09);
    gainNode.gain.exponentialRampToValueAtTime(0.12, audioCtx.currentTime + index * 0.09 + 0.06);
    gainNode.gain.exponentialRampToValueAtTime(0.0001, audioCtx.currentTime + index * 0.09 + 0.2);
    oscillator.connect(gainNode);
    gainNode.connect(audioCtx.destination);
    oscillator.start(audioCtx.currentTime + index * 0.09);
    oscillator.stop(audioCtx.currentTime + index * 0.09 + 0.2);
  });

  setTimeout(() => audioCtx.close(), 700);
}

function celebrate() {
  spawnConfetti();
  playSuccessTone();
  if ('speechSynthesis' in window) {
    speechSynthesis.cancel();
    const utterance = new SpeechSynthesisUtterance('Great job! Awesome!');
    utterance.lang = 'en-US';
    utterance.rate = 0.9;
    speechSynthesis.speak(utterance);
  }
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

function setupTraceCanvas() {
  const width = traceCanvas.width;
  const height = traceCanvas.height;

  traceCtx.clearRect(0, 0, width, height);
  traceCtx.fillStyle = '#fff';
  traceCtx.fillRect(0, 0, width, height);

  const letter = state.activeTraceCase === 'uppercase' ? state.currentLetter : state.currentLetter.toLowerCase();
  const fontSize = state.activeTraceCase === 'uppercase' ? 180 : 170;

  traceCtx.font = `900 ${fontSize}px "Comic Sans MS", cursive`;
  traceCtx.textAlign = 'center';
  traceCtx.textBaseline = 'middle';
  traceCtx.fillStyle = '#dbeafe';
  traceCtx.fillText(letter, width / 2, height / 2 + 10);

  traceCtx.font = `900 ${fontSize}px "Comic Sans MS", cursive`;
  traceCtx.fillStyle = 'rgba(96, 165, 250, 0.28)';
  traceCtx.fillText(letter, width / 2, height / 2 + 10);

  const startX = width / 2 - 60;
  const startY = height / 2 + 80;
  traceCtx.beginPath();
  traceCtx.fillStyle = '#f97316';
  traceCtx.arc(startX, startY, 10, 0, Math.PI * 2);
  traceCtx.fill();

  traceCtx.strokeStyle = '#fbbf24';
  traceCtx.lineWidth = 4;
  traceCtx.beginPath();
  traceCtx.moveTo(startX + 16, startY - 18);
  traceCtx.lineTo(startX + 28, startY - 45);
  traceCtx.lineTo(startX + 38, startY - 10);
  traceCtx.stroke();

  traceCtx.fillStyle = '#f59e0b';
  traceCtx.fillText('Start', startX + 45, startY - 56);

  state.traceProgress = 0;
  traceStatus.textContent = 'Follow the stars and trace the letter.';

  clearTraceCanvas();
}

function clearTraceCanvas() {
  const width = traceCanvas.width;
  const height = traceCanvas.height;
  traceCtx.clearRect(0, 0, width, height);
  traceCtx.fillStyle = '#fff';
  traceCtx.fillRect(0, 0, width, height);

  const letter = state.activeTraceCase === 'uppercase' ? state.currentLetter : state.currentLetter.toLowerCase();
  const fontSize = state.activeTraceCase === 'uppercase' ? 180 : 170;
  traceCtx.font = `900 ${fontSize}px "Comic Sans MS", cursive`;
  traceCtx.textAlign = 'center';
  traceCtx.textBaseline = 'middle';
  traceCtx.fillStyle = 'rgba(96, 165, 250, 0.20)';
  traceCtx.fillText(letter, width / 2, height / 2 + 10);

  const startX = width / 2 - 60;
  const startY = height / 2 + 80;
  traceCtx.beginPath();
  traceCtx.fillStyle = '#f97316';
  traceCtx.arc(startX, startY, 10, 0, Math.PI * 2);
  traceCtx.fill();

  traceCtx.strokeStyle = '#fbbf24';
  traceCtx.lineWidth = 4;
  traceCtx.beginPath();
  traceCtx.moveTo(startX + 16, startY - 18);
  traceCtx.lineTo(startX + 28, startY - 45);
  traceCtx.lineTo(startX + 38, startY - 10);
  traceCtx.stroke();

  traceCtx.fillStyle = '#f59e0b';
  traceCtx.fillText('Start', startX + 45, startY - 56);

  traceCanvas.dataset.drawing = 'false';
  traceCanvas.dataset.lastX = '0';
  traceCanvas.dataset.lastY = '0';
}

function beginTraceGame() {
  lessonOverlay.classList.add('hidden');
  traceOverlay.classList.remove('hidden');
  state.activeTraceCase = 'uppercase';
  setupTraceCanvas();

  document.querySelectorAll('.trace-switch').forEach((button) => {
    button.classList.toggle('active', button.dataset.traceCase === state.activeTraceCase);
  });
}

function traceStep(x, y) {
  const letter = state.activeTraceCase === 'uppercase' ? state.currentLetter : state.currentLetter.toLowerCase();
  const fontSize = state.activeTraceCase === 'uppercase' ? 180 : 170;

  const offscreen = document.createElement('canvas');
  offscreen.width = traceCanvas.width;
  offscreen.height = traceCanvas.height;
  const offCtx = offscreen.getContext('2d');
  offCtx.font = `900 ${fontSize}px "Comic Sans MS", cursive`;
  offCtx.textAlign = 'center';
  offCtx.textBaseline = 'middle';
  offCtx.fillText(letter, traceCanvas.width / 2, traceCanvas.height / 2 + 10);

  const pixel = offCtx.getImageData(Math.max(0, Math.min(traceCanvas.width - 1, x)), Math.max(0, Math.min(traceCanvas.height - 1, y)), 1, 1).data;
  const active = pixel[3] > 120;

  if (active && traceCanvas.dataset.drawing !== 'true') {
    traceCanvas.dataset.drawing = 'true';
    traceCtx.beginPath();
    traceCtx.moveTo(x, y);
  } else if (active && traceCanvas.dataset.drawing === 'true') {
    traceCtx.lineTo(x, y);
    traceCtx.strokeStyle = '#4f46e5';
    traceCtx.lineWidth = 12;
    traceCtx.lineCap = 'round';
    traceCtx.lineJoin = 'round';
    traceCtx.stroke();
    state.traceProgress += 1;

    if (state.traceProgress > 50) {
      completeTrace();
    }
  }
}

function completeTrace() {
  const caseLabel = state.activeTraceCase === 'uppercase' ? 'Uppercase' : 'Lowercase';
  traceStatus.textContent = `${caseLabel} letter complete! Great tracing!`;
  celebrate();

  if (state.activeTraceCase === 'uppercase') {
    state.activeTraceCase = 'lowercase';
    document.querySelectorAll('.trace-switch').forEach((button) => {
      button.classList.toggle('active', button.dataset.traceCase === state.activeTraceCase);
    });
    setTimeout(() => {
      traceStatus.textContent = 'Now trace the lowercase letter.';
      clearTraceCanvas();
      setupTraceCanvas();
    }, 900);
  } else {
    setTimeout(() => {
      traceOverlay.classList.add('hidden');
      lessonOverlay.classList.remove('hidden');
      buildObjectScene();
      objectOverlay.classList.remove('hidden');
    }, 1100);
  }
}

function buildObjectScene() {
  const letter = state.currentLetter;
  const bank = objectBank[letter] || [alphabetData[letter].word, alphabetData[letter].word, alphabetData[letter].word];
  const targetItems = shuffle([...bank]).slice(0, 3);
  const distractors = shuffle(Object.keys(alphabetData).filter((item) => item !== letter).map((item) => alphabetData[item].word)).slice(0, 4);
  const allItems = shuffle([...targetItems, ...distractors]).map((item, index) => ({
    id: `${item}-${index}`,
    label: item,
    isTarget: targetItems.includes(item),
    emoji: pickObjectEmoji(item)
  }));

  state.currentSceneItems = allItems;
  state.foundCount = 0;
  state.targetCount = 3;

  objectPrompt.textContent = `Can you find 3 items starting with the letter ${letter}?`;
  objectProgress.textContent = `0 / 3 found`;
  objectScene.innerHTML = '';

  allItems.forEach((item) => {
    const btn = document.createElement('button');
    btn.type = 'button';
    btn.className = 'object-item';
    btn.dataset.found = 'false';
    btn.innerHTML = `
      <span class="object-icon">${item.emoji}</span>
      <span class="object-label">${item.label}</span>
    `;

    btn.addEventListener('click', () => {
      if (btn.dataset.found === 'true') return;
      if (item.isTarget) {
        btn.dataset.found = 'true';
        btn.style.opacity = '0.9';
        state.foundCount += 1;
        objectProgress.textContent = `${state.foundCount} / ${state.targetCount} found`;
        playSuccessTone();

        if (state.foundCount === state.targetCount) {
          celebrate();
          setTimeout(() => {
            objectOverlay.classList.add('hidden');
            lessonOverlay.classList.remove('hidden');
          }, 1200);
        }
      } else {
        btn.style.transform = 'scale(0.96)';
        btn.style.background = 'linear-gradient(180deg, #fee2e2, #fecaca)';
        setTimeout(() => {
          btn.style.transform = '';
          btn.style.background = 'linear-gradient(180deg, #fff, #ecfeff)';
        }, 300);
      }
    });

    objectScene.appendChild(btn);
  });
}

function pickObjectEmoji(item) {
  const emojiMap = {
    Apple: '🍎', Airplane: '✈️', Ant: '🐜', Apron: '🧺', Anchor: '⚓', Arrow: '🏹',
    Ball: '⚽', Banana: '🍌', Bear: '🧸', Book: '📖', Boat: '⛵', Bird: '🐦',
    Cat: '🐱', Car: '🚗', Cookie: '🍪', Cup: '☕', Cloud: '☁️', Camel: '🐪',
    Dog: '🐶', Donut: '🍩', Drum: '🥁', Dinosaur: '🦖', Duck: '🦆', Door: '🚪',
    Elephant: '🐘', Egg: '🥚', Eagle: '🦅', Envelope: '✉️', Earth: '🌍', Easel: '🖍️',
    Fish: '🐟', Flower: '🌼', Frog: '🐸', Fork: '🍴', Firetruck: '🚒', Fan: '🌀',
    Giraffe: '🦒', Gift: '🎁', Guitar: '🎸', Globe: '🌍', Goat: '🐐', Game: '🎲',
    Horse: '🐴', Hat: '🎩', House: '🏠', Hammer: '🔨', Hotdog: '🌭', Heart: '💖',
    'Ice Cream': '🍦', Igloo: '🧊', Insect: '🐛', Island: '🏝️', Image: '🖼️', Iron: '🔩',
    Jam: '🍓', Jar: '🫙', Jet: '✈️', Jacket: '🧥', Jellyfish: '🪼', Juice: '🧃',
    Kite: '🪁', Kangaroo: '🦘', Key: '🔑', Kiwi: '🥝', Koala: '🐨', Kettle: '🫖',
    Lion: '🦁', Leaf: '🍃', Lemon: '🍋', Lamp: '💡', Ladder: '🪜', Lollipop: '🍭',
    Moon: '🌙', Milk: '🥛', Mouse: '🐭', Mushroom: '🍄', Monkey: '🐵', Map: '🗺️',
    Nose: '👃', Nest: '🪺', Nugget: '🍗', Nail: '🔩', Net: '🕸️', Notebook: '📓',
    Orange: '🍊', Owl: '🦉', Octopus: '🐙', Onion: '🧅', Olive: '🫒', Oven: '🔥',
    Penguin: '🐧', Piano: '🎹', Panda: '🐼', Pencil: '✏️', Pizza: '🍕', Pail: '🪣',
    Queen: '👑', Quail: '🐦', Quarter: '🪙', Question: '❓', Quilt: '🧵', Quokka: '🦘',
    Rainbow: '🌈', Robot: '🤖', Rocket: '🚀', Rabbit: '🐰', Rose: '🌹', Ring: '💍',
    Sun: '☀️', Star: '⭐', Strawberry: '🍓', Shark: '🦈', Socks: '🧦', Ship: '🚢',
    Tree: '🌳', Turtle: '🐢', Train: '🚆', Teddy: '🧸', Taco: '🌮', Tiger: '🐯',
    Umbrella: '☂️', Unicorn: '🦄', Upstairs: '🏠', Urchin: '🌊', Utensil: '🍴', Underwear: '👚',
    Violin: '🎻', Volcano: '🌋', Van: '🚐', Vase: '🏺', Video: '📹', Velvet: '🧵',
    Watermelon: '🍉', Whale: '🐳', Wheel: '🛞', Wagon: '🚂', Window: '🪟', Watch: '⌚',
    Xylophone: '🎼', 'X-ray': '🩺', 'Xmas Tree': '🎄',
    Yarn: '🧶', Yogurt: '🥣', 'Yarn Ball': '🧶', 'Yo-yo': '🪀', Yawn: '😴', Yak: '🐂',
    Zebra: '🦓', Zoo: '🦍', Zucchini: '🥬', Zipper: '⚡', Zigzag: '🌈', Zero: '0️⃣'
  };

  return emojiMap[item] || '✨';
}

function shuffle(items) {
  const copy = [...items];
  for (let i = copy.length - 1; i > 0; i--) {
    const j = Math.floor(Math.random() * (i + 1));
    [copy[i], copy[j]] = [copy[j], copy[i]];
  }
  return copy;
}

document.querySelector('#playLetterBtn').addEventListener('click', () => playLetterAudio(state.currentLetter, true));
document.querySelector('#traceBtn').addEventListener('click', beginTraceGame);
document.querySelector('#findObjectBtn').addEventListener('click', () => {
  lessonOverlay.classList.add('hidden');
  buildObjectScene();
  objectOverlay.classList.remove('hidden');
});
document.querySelector('#closeLessonBtn').addEventListener('click', () => {
  escapeModal();
  showHomeScreen();
});
document.querySelector('#closeTraceBtn').addEventListener('click', () => {
  traceOverlay.classList.add('hidden');
  lessonOverlay.classList.remove('hidden');
});
document.querySelector('#closeObjectBtn').addEventListener('click', () => {
  objectOverlay.classList.add('hidden');
  lessonOverlay.classList.remove('hidden');
});
document.querySelector('#clearTraceBtn').addEventListener('click', () => {
  clearTraceCanvas();
  state.traceProgress = 0;
  traceStatus.textContent = 'Try again!';
});
document.querySelector('#objectResetBtn').addEventListener('click', buildObjectScene);
homeBtn.addEventListener('click', showHomeScreen);

document.querySelectorAll('.trace-switch').forEach((button) => {
  button.addEventListener('click', () => {
    state.activeTraceCase = button.dataset.traceCase;
    document.querySelectorAll('.trace-switch').forEach((b) => {
      b.classList.toggle('active', b === button);
    });
    clearTraceCanvas();
    traceStatus.textContent = 'Trace the selected letter.';
  });
});

traceCanvas.addEventListener('pointerdown', (event) => {
  const rect = traceCanvas.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * traceCanvas.width;
  const y = ((event.clientY - rect.top) / rect.height) * traceCanvas.height;
  traceCanvas.dataset.drawing = 'true';
  traceCtx.beginPath();
  traceCtx.moveTo(x, y);
  traceStep(x, y);
});

traceCanvas.addEventListener('pointermove', (event) => {
  if (traceCanvas.dataset.drawing !== 'true') return;
  const rect = traceCanvas.getBoundingClientRect();
  const x = ((event.clientX - rect.left) / rect.width) * traceCanvas.width;
  const y = ((event.clientY - rect.top) / rect.height) * traceCanvas.height;
  traceStep(x, y);
});

traceCanvas.addEventListener('pointerup', () => {
  traceCanvas.dataset.drawing = 'false';
});

traceCanvas.addEventListener('pointerleave', () => {
  traceCanvas.dataset.drawing = 'false';
});

buildAlphabetGrid();
showHomeScreen();

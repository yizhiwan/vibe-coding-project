# Number Ninja

A maths game for young kids (about ages 3–7) to learn counting, adding and taking away. Kids earn stars that level up a ninja belt, from White all the way to Black. It's the sibling of [alphabet-adventure](../alphabet-adventure) and uses the same look and feel.

Runs entirely in the browser: no install, no account, no internet needed once loaded.

## Games

| Game | How it works |
| --- | --- |
| 🍎 **Count It** | Count the objects and tap the right number |
| ➕ **Add It** | Two groups of objects, e.g. 3 + 2 = ? |
| ➖ **Take Away** | Some objects are crossed out, e.g. 6 − 2 = ? |
| 🥷 **Ninja Slice** | Numbers fly up the screen; tap or swipe across the ones that match the rule. Wrong slices cost a heart (3 hearts, 30 seconds) |

Ninja Slice rules depend on the level: "Slice every 3!" on Easy; on Medium and Hard also even numbers, odd numbers, and numbers bigger or smaller than a target.

### Learn your numbers

Tap any number from 0 to 20 to see it with its word, a ten-frame and a row of objects. **Hear it!** says the number, and **Count with me** counts each dot out loud.

## Levels

Pick how high the numbers go on the home screen:

| Level | Numbers up to |
| --- | --- |
| Easy | 5 |
| Medium | 10 |
| Hard | 20 |

## Stars and belts

Each Count, Add or Take Away round is 5 questions. Stars are based on answers right on the first try (a wrong tap can be retried, but doesn't count as first try):

| First-try answers | Stars |
| --- | --- |
| 5 of 5 | ⭐⭐⭐ |
| 3–4 | ⭐⭐ |
| 0–2 | ⭐ |

In Ninja Slice: 12+ correct slices = ⭐⭐⭐, 7+ = ⭐⭐, 1+ = ⭐.

Total stars unlock belts:

| Belt | Stars needed |
| --- | --- |
| White | 0 |
| Yellow | 5 |
| Orange | 15 |
| Green | 30 |
| Blue | 50 |
| Purple | 75 |
| Black | 100 |

Stars and the chosen level are saved in the browser, so progress stays after closing the page. Clearing browser data resets it.

## Running it

Open `index.html` in a browser, or run a live-reloading dev server on port 3000:

```bash
npm install
npm run dev
```

Spoken words use the browser's built-in speech, so turn the sound on. Works on phones and tablets too.

## Files

| File | Purpose |
| --- | --- |
| `index.html` | Page layout: home screen, lesson, quiz, Ninja Slice and result panels |
| `styles.css` | Look and feel, shared palette with alphabet-adventure |
| `script.js` | Game logic, question generation, Ninja Slice physics, stars and belts |
| `live-reload.js` | Reloads the page when files change during development |

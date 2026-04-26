# Controller Documentation

## Pixel Ecosystem Empire RPG (HTML - Recommended)

## Super quick start (lazy mode)
Just run:

```bash
python run_game.py
```

It will start a local server and open the game in your browser automatically.

This repository includes a **browser-playable** top-down pixel ecosystem/empire simulation:

- `ecosystem_rpg.html`
- `ecosystem_rpg.js`

### How to run
1. From the repo root, start a local web server:
   ```bash
   python -m http.server 8000
   ```
2. Open your browser to:
   ```
   http://localhost:8000/ecosystem_rpg.html
   ```

### Interaction model (no WASD movement)
This version is simulation-first and click-driven (closer to the style in your reference):

- **Inspect**: Click map tiles to inspect biome/building/resource ownership.
- **Sprinkle Food**: Click/drag to drop food particles for ecosystem behavior.
- **Spawn Creature**: Click to spawn villagers/wildlife/raiders.
- **Claim Territory**: Click to expand borders.
- **Build tools**: Place houses/farms/mines/markets/towers with resource costs.
- **Bottom controls**: Pause/resume, speed slider, research, save/load/reset.
- **Esc**: Return to Inspect mode.

### Included systems
- Procedural world generation with distinct biome coloring and coastline/water.
- Autonomous ecosystem simulation (villagers, rabbits, wolves, raiders).
- Empire-building systems (construction, influence borders, claiming).
- Economy simulation (resources, prices, taxes, daily production/consumption).
- Diplomacy + raids + dynamic random events.
- Day/night + weather effects.
- Save/load using browser localStorage.

---

## Legacy desktop prototype (optional)
A previous Tkinter prototype is still present:

- `ecosystem_rpg.py`

Run with:
```bash
python ecosystem_rpg.py
```

(() => {
  'use strict';

  const TILE = 8;
  const WORLD_W = 180;
  const WORLD_H = 120;
  const STORAGE_KEY = 'ecosystem_empire_html_v3';

  const BIOME_COLORS = {
    forest: '#6d955f',
    plains: '#86ab70',
    desert: '#ccb88a',
    tundra: '#8ca3ab',
    swamp: '#57775d',
    ruins: '#7a6f78',
    water: '#44698f',
    shore: '#ccb28a',
  };

  const BUILDINGS = {
    house: { color: '#d6ab7d', cost: { wood: 12, stone: 8 }, influence: 2 },
    farm: { color: '#98c83f', cost: { wood: 10 }, influence: 1 },
    mine: { color: '#8d8d8d', cost: { wood: 8, stone: 12 }, influence: 1 },
    market: { color: '#f2d36e', cost: { wood: 18, stone: 10, gold: 8 }, influence: 3 },
    wall: { color: '#666666', cost: { stone: 6 }, influence: 0 },
    road: { color: '#9d7e5d', cost: { stone: 2 }, influence: 0 },
    tower: { color: '#ba5d63', cost: { wood: 12, stone: 20 }, influence: 2 },
  };

  const FACTIONS = ['Northreach', 'Dunemar', 'Verdant'];
  const MODES = ['inspect', 'sprinkle_food', 'spawn_creature', 'claim', ...Object.keys(BUILDINGS).map((k) => `build_${k}`)];

  const rand = (a, b) => Math.random() * (b - a) + a;
  const clamp = (v, a, b) => Math.max(a, Math.min(b, v));
  const dist = (ax, ay, bx, by) => Math.hypot(ax - bx, ay - by);

  class Game {
    constructor(canvas) {
      this.canvas = canvas;
      this.ctx = canvas.getContext('2d');
      this.ctx.imageSmoothingEnabled = false;

      this.mode = 'inspect';
      this.speed = 1;
      this.paused = false;
      this.weather = 'clear';
      this.time = 9.5;
      this.day = 1;
      this.seed = Math.floor(rand(1000, 999999));

      this.world = [];
      this.influence = new Set();
      this.territory = new Map();

      this.creatures = [];
      this.villagers = [];
      this.animals = [];
      this.enemies = [];
      this.foodParticles = [];
      this.sparkles = [];
      this.generation = 1;

      this.resources = { wood: 80, stone: 65, food: 80, gold: 35, rare: 5 };
      this.prices = { wood: 3, stone: 4, food: 2, gold: 10, rare: 20 };
      this.taxRate = 0.12;
      this.tech = { agriculture: 0, masonry: 0, trade: 0, military: 0, ecology: 0 };
      this.laws = { rationing: false, openBorders: false, conscription: false };
      this.factions = FACTIONS.map((name, i) => ({
        name,
        relation: [12, -15, 6][i],
        military: [18, 32, 20][i],
        wealth: [65, 58, 62][i],
      }));

      this.eventTimer = 300;
      this.marketTimer = 0;
      this.raidCooldown = 0;
      this.messages = [];
      this.selectedInfo = null;

      this.dragging = false;
      this.mouse = { x: 0, y: 0, wx: 0, wy: 0 };

      this.generateWorld();
      this.spawnInitialLife();
      this.bindUI();
      this.message(`World seed ${this.seed}`);

      this.last = performance.now();
      requestAnimationFrame(this.loop.bind(this));
    }

    noise(x, y) {
      const n = Math.sin((x * 12.9898 + y * 78.233 + this.seed) * 0.0041) * 43758.5453;
      return n - Math.floor(n);
    }

    generateWorld() {
      this.world = Array.from({ length: WORLD_H }, (_, y) =>
        Array.from({ length: WORLD_W }, (_, x) => {
          const n = this.noise(x, y);
          const edgeDist = Math.min(x, y, WORLD_W - x - 1, WORLD_H - y - 1);
          let biome = 'plains';
          let fertility = 0.6;
          let water = false;

          if (n < 0.12 || edgeDist < 3) {
            biome = 'water';
            fertility = 0;
            water = true;
          } else if (n < 0.2) {
            biome = 'shore';
            fertility = 0.45;
          } else if (n < 0.35) {
            biome = 'forest';
            fertility = 0.8;
          } else if (n < 0.5) {
            biome = 'plains';
            fertility = 0.65;
          } else if (n < 0.65) {
            biome = 'swamp';
            fertility = 0.74;
          } else if (n < 0.77) {
            biome = 'desert';
            fertility = 0.25;
          } else if (n < 0.9) {
            biome = 'ruins';
            fertility = 0.35;
          } else {
            biome = 'tundra';
            fertility = 0.42;
          }

          const tile = {
            biome,
            fertility,
            water,
            building: null,
            owner: null,
            resource: null,
            amount: 0,
            discovered: true,
          };

          if (!water) {
            const r = Math.random();
            if (r < 0.18 && (biome === 'forest' || biome === 'swamp')) {
              tile.resource = 'tree';
              tile.amount = Math.floor(rand(20, 70));
            } else if (r < 0.27) {
              tile.resource = 'stone';
              tile.amount = Math.floor(rand(20, 60));
            } else if (r < 0.33) {
              tile.resource = 'berry';
              tile.amount = Math.floor(rand(12, 35));
            } else if (r < 0.36 && biome === 'ruins') {
              tile.resource = 'ruin';
              tile.amount = Math.floor(rand(10, 30));
            }
          }
          return tile;
        })
      );
    }

    spawnInitialLife() {
      for (let i = 0; i < 45; i++) this.spawnCreature('villager');
      for (let i = 0; i < 90; i++) this.spawnCreature(Math.random() < 0.2 ? 'wolf' : 'rabbit');
      this.rebuildGroups();
    }

    rebuildGroups() {
      this.villagers = this.creatures.filter((c) => c.kind === 'villager');
      this.animals = this.creatures.filter((c) => c.kind === 'rabbit' || c.kind === 'wolf');
      this.enemies = this.creatures.filter((c) => c.kind === 'raider');
    }

    spawnCreature(type, x = null, y = null) {
      const px = x ?? rand(4, WORLD_W - 4);
      const py = y ?? rand(4, WORLD_H - 4);
      const tile = this.tile(Math.floor(px), Math.floor(py));
      if (!tile || tile.water) return;

      const colors = {
        villager: '#6fe7f6',
        rabbit: '#cfffc4',
        wolf: '#ff9a66',
        raider: '#ff5464',
      };
      const jobs = ['farmer', 'miner', 'trader', 'guard'];
      const c = {
        id: crypto.randomUUID(),
        kind: type,
        x: px,
        y: py,
        vx: rand(-0.4, 0.4),
        vy: rand(-0.4, 0.4),
        hp: type === 'wolf' ? 46 : type === 'raider' ? 52 : 30,
        maxHp: type === 'wolf' ? 46 : type === 'raider' ? 52 : 30,
        hunger: rand(10, 30),
        fatigue: rand(0, 15),
        age: 0,
        fitness: rand(0.2, 1.0),
        generation: this.generation,
        color: colors[type],
        glow: colors[type],
        job: type === 'villager' ? jobs[Math.floor(rand(0, jobs.length))] : null,
        task: 'idle',
        targetId: null,
      };
      this.creatures.push(c);
      return c;
    }

    bindUI() {
      const toolbar = document.getElementById('toolbar');
      toolbar.innerHTML = `
        <button data-mode="inspect">Inspect</button>
        <button data-mode="sprinkle_food">Sprinkle Food</button>
        <button data-mode="spawn_creature">Spawn Creature</button>
        <button data-mode="claim">Claim Territory</button>
        <button data-mode="build_house">Build House</button>
        <button data-mode="build_farm">Build Farm</button>
        <button data-mode="build_mine">Build Mine</button>
        <button data-mode="build_market">Build Market</button>
        <button data-mode="build_tower">Build Tower</button>
      `;
      toolbar.querySelectorAll('button').forEach((b) => {
        b.addEventListener('click', () => {
          this.mode = b.dataset.mode;
          this.message(`Mode: ${this.mode.replace('_', ' ')}`);
        });
      });

      document.getElementById('btnPause').addEventListener('click', () => (this.paused = !this.paused));
      document.getElementById('speed').addEventListener('input', (e) => (this.speed = Number(e.target.value)));
      document.getElementById('btnSave').addEventListener('click', () => this.save());
      document.getElementById('btnLoad').addEventListener('click', () => this.load());
      document.getElementById('btnReset').addEventListener('click', () => this.reset());
      document.getElementById('btnResearch').addEventListener('click', () => this.research());

      this.canvas.addEventListener('mousemove', (e) => {
        const rect = this.canvas.getBoundingClientRect();
        this.mouse.x = e.clientX - rect.left;
        this.mouse.y = e.clientY - rect.top;
        this.mouse.wx = Math.floor((this.mouse.x / this.canvas.width) * WORLD_W);
        this.mouse.wy = Math.floor((this.mouse.y / this.canvas.height) * WORLD_H);
      });

      this.canvas.addEventListener('mousedown', () => {
        this.dragging = true;
        this.handleClick();
      });
      this.canvas.addEventListener('mouseup', () => (this.dragging = false));
      this.canvas.addEventListener('mouseleave', () => (this.dragging = false));

      window.addEventListener('keydown', (e) => {
        if (e.key === 'Escape') this.mode = 'inspect';
      });
    }

    tile(x, y) {
      if (x < 0 || y < 0 || x >= WORLD_W || y >= WORLD_H) return null;
      return this.world[y][x];
    }

    message(m) {
      const stamp = `D${this.day} ${String(Math.floor(this.time)).padStart(2, '0')}:${String(Math.floor((this.time % 1) * 60)).padStart(2, '0')}`;
      this.messages.unshift(`[${stamp}] ${m}`);
      this.messages = this.messages.slice(0, 12);
      document.getElementById('events').innerHTML = this.messages.map((x) => `<div>${x}</div>`).join('');
    }

    handleClick() {
      const x = this.mouse.wx;
      const y = this.mouse.wy;
      const tile = this.tile(x, y);
      if (!tile) return;

      if (this.mode === 'sprinkle_food') {
        this.foodParticles.push({ x: x + 0.5, y: y + 0.5, amount: 8 + rand(0, 8) });
        for (let i = 0; i < 14; i++) this.sparkles.push({ x: x + rand(-0.4, 0.4), y: y + rand(-0.4, 0.4), life: rand(0.3, 1.2), color: '#ffe8a6' });
        return;
      }

      if (this.mode === 'spawn_creature') {
        const pick = Math.random();
        const type = pick < 0.45 ? 'villager' : pick < 0.75 ? 'rabbit' : pick < 0.93 ? 'wolf' : 'raider';
        this.spawnCreature(type, x + rand(0.1, 0.8), y + rand(0.1, 0.8));
        this.rebuildGroups();
        return;
      }

      if (this.mode === 'claim') {
        this.claimArea(x, y, 4);
        this.message(`Territory claimed around ${x},${y}`);
        return;
      }

      if (this.mode.startsWith('build_')) {
        const type = this.mode.replace('build_', '');
        this.build(type, x, y);
        return;
      }

      if (this.mode === 'inspect') {
        this.selectedInfo = { x, y, tile };
      }
    }

    build(type, x, y) {
      const tile = this.tile(x, y);
      if (!tile || tile.water || tile.building) return;
      const b = BUILDINGS[type];
      if (!b) return;
      if (!Object.entries(b.cost).every(([k, v]) => this.resources[k] >= v)) {
        this.message('Not enough resources');
        return;
      }
      Object.entries(b.cost).forEach(([k, v]) => (this.resources[k] -= v));
      tile.building = type;
      if (b.influence > 0) this.claimArea(x, y, b.influence);
      if (type === 'house') {
        for (let i = 0; i < 3; i++) this.spawnCreature('villager', x + rand(0.2, 0.8), y + rand(0.2, 0.8));
        this.rebuildGroups();
      }
      this.message(`Built ${type}`);
    }

    claimArea(cx, cy, r) {
      for (let y = cy - r; y <= cy + r; y++) {
        for (let x = cx - r; x <= cx + r; x++) {
          const t = this.tile(x, y);
          if (!t || dist(x, y, cx, cy) > r + 0.3) continue;
          this.influence.add(`${x},${y}`);
          t.owner = 'Player';
          this.territory.set(`${x},${y}`, 1);
        }
      }
    }

    research() {
      const keys = Object.keys(this.tech).filter((k) => this.tech[k] < 5);
      if (!keys.length) return this.message('All tech maxed');
      if (this.resources.gold < 12 || this.resources.rare < 1) return this.message('Need 12 gold + 1 rare');
      const pick = keys[Math.floor(rand(0, keys.length))];
      this.resources.gold -= 12;
      this.resources.rare -= 1;
      this.tech[pick] += 1;
      this.message(`Researched ${pick} -> Lv ${this.tech[pick]}`);
    }

    simulateCreature(c, dt) {
      c.age += dt;
      c.hunger += dt * (c.kind === 'wolf' ? 2.2 : c.kind === 'raider' ? 1.8 : 1.25);
      c.fatigue += dt * (this.time > 20 || this.time < 6 ? 1.3 : 0.7);

      const seek = (tx, ty, speed = 1.2) => {
        const d = dist(c.x, c.y, tx, ty);
        if (d > 0.01) {
          c.vx = ((tx - c.x) / d) * speed;
          c.vy = ((ty - c.y) / d) * speed;
        }
      };

      if (c.kind === 'rabbit') {
        c.task = 'foraging';
        const nearestFood = this.foodParticles.reduce((best, f) => {
          const d = dist(c.x, c.y, f.x, f.y);
          return d < best.d ? { d, f } : best;
        }, { d: Infinity, f: null });
        if (nearestFood.f && nearestFood.d < 12) {
          seek(nearestFood.f.x, nearestFood.f.y, 1.1);
          if (nearestFood.d < 0.8) {
            nearestFood.f.amount -= 6 * dt;
            c.hunger = Math.max(0, c.hunger - 22 * dt);
          }
        } else if (Math.random() < 0.03) {
          c.vx += rand(-0.8, 0.8);
          c.vy += rand(-0.8, 0.8);
        }

        if (c.age > 26 && Math.random() < 0.0025 && this.animals.length < 220) {
          const child = this.spawnCreature('rabbit', c.x + rand(-0.9, 0.9), c.y + rand(-0.9, 0.9));
          if (child) child.generation = c.generation + 1;
          this.generation = Math.max(this.generation, c.generation + 1);
        }
      } else if (c.kind === 'wolf') {
        c.task = 'hunting';
        const prey = this.creatures.filter((x) => x.kind === 'rabbit').reduce((best, x) => {
          const d = dist(c.x, c.y, x.x, x.y);
          return d < best.d ? { d, x } : best;
        }, { d: Infinity, x: null });
        if (prey.x) {
          seek(prey.x.x, prey.x.y, 1.45);
          if (prey.d < 0.9) {
            prey.x.hp -= 45 * dt;
            c.hunger = Math.max(0, c.hunger - 30 * dt);
          }
        }
      } else if (c.kind === 'villager') {
        if (c.hunger > 50 && this.resources.food > 0) {
          const eat = Math.min(2 * dt, this.resources.food);
          this.resources.food -= eat;
          c.hunger -= eat * 8;
        }

        const nearest = (type) => {
          let best = { d: Infinity, x: Math.floor(c.x), y: Math.floor(c.y) };
          for (let y = 0; y < WORLD_H; y++) {
            for (let x = 0; x < WORLD_W; x++) {
              const t = this.world[y][x];
              if (t.building === type) {
                const d = (x - c.x) ** 2 + (y - c.y) ** 2;
                if (d < best.d) best = { d, x, y };
              }
            }
          }
          return best;
        };

        if (c.job === 'farmer') {
          c.task = 'farming';
          const f = nearest('farm');
          seek(f.x + 0.5, f.y + 0.5, 1.15 + this.tech.agriculture * 0.06);
          if (dist(c.x, c.y, f.x + 0.5, f.y + 0.5) < 1.0 && Math.random() < 0.15) {
            this.resources.food += 0.8 + this.tech.agriculture * 0.3;
          }
        } else if (c.job === 'miner') {
          c.task = 'mining';
          let target = null;
          let best = Infinity;
          for (let y = Math.max(0, Math.floor(c.y) - 15); y < Math.min(WORLD_H, Math.floor(c.y) + 15); y++) {
            for (let x = Math.max(0, Math.floor(c.x) - 15); x < Math.min(WORLD_W, Math.floor(c.x) + 15); x++) {
              const t = this.world[y][x];
              if (t.resource === 'stone') {
                const d = (x - c.x) ** 2 + (y - c.y) ** 2;
                if (d < best) {
                  best = d;
                  target = { x, y };
                }
              }
            }
          }
          if (target) {
            seek(target.x + 0.5, target.y + 0.5, 1.1 + this.tech.masonry * 0.05);
            const t = this.tile(target.x, target.y);
            if (dist(c.x, c.y, target.x + 0.5, target.y + 0.5) < 1 && t?.amount > 0) {
              t.amount -= 0.8;
              this.resources.stone += 0.7 + this.tech.masonry * 0.2;
              if (t.amount <= 0) t.resource = null;
            }
          }
        } else if (c.job === 'trader') {
          c.task = 'trading';
          const m = nearest('market');
          seek(m.x + 0.5, m.y + 0.5, 1.35 + this.tech.trade * 0.05);
          if (dist(c.x, c.y, m.x + 0.5, m.y + 0.5) < 1.2 && Math.random() < 0.12) this.resources.gold += 0.8 + this.tech.trade * 0.3;
        } else {
          c.task = 'guarding';
          const foe = this.enemies.reduce((best, e) => {
            const d = dist(c.x, c.y, e.x, e.y);
            return d < best.d ? { d, e } : best;
          }, { d: Infinity, e: null });
          if (foe.e) {
            seek(foe.e.x, foe.e.y, 1.45 + this.tech.military * 0.06);
            if (foe.d < 1) foe.e.hp -= 20 * dt + this.tech.military * 2;
          } else if (Math.random() < 0.02) {
            c.vx += rand(-0.5, 0.5);
            c.vy += rand(-0.5, 0.5);
          }
        }
      } else if (c.kind === 'raider') {
        c.task = 'raiding';
        let hx = WORLD_W / 2;
        let hy = WORLD_H / 2;
        const homes = [];
        for (let y = 0; y < WORLD_H; y++) {
          for (let x = 0; x < WORLD_W; x++) {
            if (this.world[y][x].building === 'house') homes.push({ x, y });
          }
        }
        if (homes.length) {
          const h = homes[Math.floor(rand(0, homes.length))];
          hx = h.x + 0.5;
          hy = h.y + 0.5;
        }
        seek(hx, hy, 1.25);
        for (const v of this.villagers) {
          if (dist(c.x, c.y, v.x, v.y) < 0.9) v.hp -= 26 * dt;
        }
      }

      c.vx = clamp(c.vx + rand(-0.1, 0.1), -2.2, 2.2);
      c.vy = clamp(c.vy + rand(-0.1, 0.1), -2.2, 2.2);
      c.x = clamp(c.x + c.vx * dt, 0.4, WORLD_W - 0.4);
      c.y = clamp(c.y + c.vy * dt, 0.4, WORLD_H - 0.4);

      const tile = this.tile(Math.floor(c.x), Math.floor(c.y));
      if (tile?.water) {
        c.vx *= -0.5;
        c.vy *= -0.5;
        c.x += c.vx * dt;
        c.y += c.vy * dt;
      }

      if (c.hunger > 120) c.hp -= 18 * dt;
      if (c.hp <= 0 || c.age > 1200) {
        this.creatures = this.creatures.filter((x) => x.id !== c.id);
        this.rebuildGroups();
      }
    }

    updateWorld(dt) {
      if (this.paused) return;
      const scaled = dt * this.speed;

      this.time += scaled * 0.38;
      if (this.time >= 24) {
        this.time -= 24;
        this.day += 1;
        this.dailyEconomy();
      }

      this.marketTimer += scaled;
      if (this.marketTimer > 4) {
        this.marketTimer = 0;
        for (const k of Object.keys(this.prices)) {
          this.prices[k] = clamp(Math.floor(4 + (55 - this.resources[k]) * 0.05 + rand(-1, 2)), 1, 40);
        }
      }

      this.eventTimer -= 1 * this.speed;
      if (this.eventTimer <= 0) {
        this.eventTimer = rand(210, 390);
        this.triggerEvent();
      }

      this.raidCooldown -= 1 * this.speed;
      const hostility = this.factions.reduce((n, f) => n + Math.max(0, -f.relation), 0);
      if (this.raidCooldown <= 0 && hostility > 60 && Math.random() < 0.08) {
        this.spawnRaid(Math.floor(rand(4, 10)));
        this.raidCooldown = rand(180, 320);
      }

      if (Math.random() < 0.003) {
        this.weather = ['clear', 'rain', 'snow', 'storm'][Math.floor(rand(0, 4))];
      }

      for (const f of [...this.foodParticles]) {
        f.amount -= 0.7 * scaled;
        if (f.amount <= 0) this.foodParticles = this.foodParticles.filter((x) => x !== f);
      }

      for (const s of [...this.sparkles]) {
        s.life -= scaled * 0.5;
        if (s.life <= 0) this.sparkles = this.sparkles.filter((x) => x !== s);
      }

      for (const c of [...this.creatures]) this.simulateCreature(c, scaled);
      this.rebuildGroups();

      if (this.dragging) this.handleClick();
    }

    dailyEconomy() {
      let food = 0;
      let stone = 0;
      let taxBase = 0;
      for (let y = 0; y < WORLD_H; y++) {
        for (let x = 0; x < WORLD_W; x++) {
          const b = this.world[y][x].building;
          if (b === 'farm') food += 4 + this.world[y][x].fertility * 6 + this.tech.agriculture;
          if (b === 'mine') stone += 3 + this.tech.masonry;
          if (b === 'market') taxBase += 8;
          if (b === 'house') taxBase += 3;
        }
      }
      this.resources.food += food;
      this.resources.stone += stone;
      const tax = taxBase * this.taxRate * (1 + this.tech.trade * 0.1);
      this.resources.gold += tax;
      this.resources.food -= this.villagers.length * (this.laws.rationing ? 0.3 : 0.6);
      for (const f of this.factions) f.relation = clamp(f.relation + Math.floor(rand(-2, 3)), -100, 100);
      this.message(`Daily update +${food.toFixed(0)} food +${stone.toFixed(0)} stone +${tax.toFixed(0)}g`);
    }

    spawnRaid(count) {
      for (let i = 0; i < count; i++) {
        const side = Math.floor(rand(0, 4));
        const x = side === 0 ? rand(1, WORLD_W - 2) : side === 1 ? rand(1, WORLD_W - 2) : side === 2 ? 1 : WORLD_W - 2;
        const y = side === 0 ? 1 : side === 1 ? WORLD_H - 2 : rand(1, WORLD_H - 2);
        this.spawnCreature('raider', x, y);
      }
      this.rebuildGroups();
      this.message('Raiders spotted at borders');
    }

    triggerEvent() {
      const events = ['disease', 'invasion', 'boom', 'scarcity', 'festival'];
      const e = events[Math.floor(rand(0, events.length))];
      if (e === 'disease' && this.villagers.length) {
        const v = this.villagers[Math.floor(rand(0, this.villagers.length))];
        v.hp -= 18;
        this.message('Disease outbreak among villagers');
      } else if (e === 'invasion') {
        this.spawnRaid(Math.floor(rand(3, 9)));
      } else if (e === 'boom') {
        this.resources.gold += 20;
        this.message('Trade boom: +20 gold');
      } else if (e === 'scarcity') {
        const pick = ['wood', 'stone', 'food'][Math.floor(rand(0, 3))];
        this.resources[pick] = Math.max(0, this.resources[pick] - 20);
        this.message(`Scarcity: -20 ${pick}`);
      } else {
        this.resources.food += 25;
        this.resources.gold += 8;
        this.message('Festival boosted morale and trade');
      }
    }

    drawWorld() {
      const { ctx, canvas } = this;
      const tw = canvas.width / WORLD_W;
      const th = canvas.height / WORLD_H;

      for (let y = 0; y < WORLD_H; y++) {
        for (let x = 0; x < WORLD_W; x++) {
          const t = this.world[y][x];
          ctx.fillStyle = BIOME_COLORS[t.biome] || '#777';
          ctx.fillRect(x * tw, y * th, tw + 0.6, th + 0.6);

          if (this.influence.has(`${x},${y}`)) {
            ctx.fillStyle = 'rgba(95, 178, 255, 0.16)';
            ctx.fillRect(x * tw, y * th, tw + 0.5, th + 0.5);
          }

          if (t.resource) {
            const col = t.resource === 'tree' ? '#2f6a37' : t.resource === 'stone' ? '#8d8d8d' : t.resource === 'berry' ? '#ca4a68' : '#d8c16d';
            ctx.fillStyle = col;
            ctx.fillRect(x * tw + tw * 0.25, y * th + th * 0.25, tw * 0.5, th * 0.5);
          }

          if (t.building) {
            ctx.fillStyle = BUILDINGS[t.building].color;
            ctx.fillRect(x * tw + tw * 0.12, y * th + th * 0.12, tw * 0.76, th * 0.76);
          }
        }
      }

      for (const fp of this.foodParticles) {
        ctx.fillStyle = '#ffe8ac';
        ctx.beginPath();
        ctx.arc(fp.x * tw, fp.y * th, Math.max(1, tw * 0.34), 0, Math.PI * 2);
        ctx.fill();
      }

      for (const s of this.sparkles) {
        ctx.fillStyle = s.color;
        ctx.globalAlpha = clamp(s.life, 0, 1);
        ctx.fillRect(s.x * tw, s.y * th, 2, 2);
        ctx.globalAlpha = 1;
      }
    }

    drawCreatures() {
      const { ctx, canvas } = this;
      const tw = canvas.width / WORLD_W;
      const th = canvas.height / WORLD_H;

      for (const c of this.creatures) {
        const px = c.x * tw;
        const py = c.y * th;
        ctx.fillStyle = c.color;
        ctx.shadowColor = c.glow;
        ctx.shadowBlur = 8;
        ctx.beginPath();
        ctx.arc(px, py, Math.max(1.5, tw * 0.45), 0, Math.PI * 2);
        ctx.fill();
        ctx.shadowBlur = 0;
      }
    }

    drawWeatherAndLighting() {
      const { ctx, canvas } = this;
      let darkness = 0;
      if (this.time < 6 || this.time > 20) darkness = 0.32;

      if (this.weather === 'rain' || this.weather === 'storm') {
        const drops = this.weather === 'storm' ? 180 : 110;
        ctx.strokeStyle = this.weather === 'storm' ? 'rgba(133,177,219,0.6)' : 'rgba(154,193,227,0.45)';
        for (let i = 0; i < drops; i++) {
          const x = rand(0, canvas.width);
          const y = rand(0, canvas.height);
          ctx.beginPath();
          ctx.moveTo(x, y);
          ctx.lineTo(x + 2, y + 7);
          ctx.stroke();
        }
        darkness += this.weather === 'storm' ? 0.17 : 0.08;
      }

      if (darkness > 0) {
        ctx.fillStyle = `rgba(7, 15, 23, ${darkness})`;
        ctx.fillRect(0, 0, canvas.width, canvas.height);
      }
    }

    drawOverlay() {
      const { ctx, canvas } = this;
      const tw = canvas.width / WORLD_W;
      const th = canvas.height / WORLD_H;
      ctx.strokeStyle = '#ffffff99';
      ctx.strokeRect(this.mouse.wx * tw, this.mouse.wy * th, tw, th);

      if (this.mode === 'sprinkle_food') {
        ctx.fillStyle = 'rgba(255,235,172,0.25)';
        ctx.beginPath();
        ctx.arc(this.mouse.wx * tw, this.mouse.wy * th, 16, 0, Math.PI * 2);
        ctx.fill();
      }
    }

    updatePanels() {
      const pop = this.creatures.length;
      const fitness = pop ? this.creatures.reduce((n, c) => n + c.fitness, 0) / pop : 0;
      const panel = document.getElementById('hudStats');
      panel.innerHTML = `
        <div><label>Population</label><strong>${pop}</strong></div>
        <div><label>Generation</label><strong>${this.generation}</strong></div>
        <div><label>Avg Fitness</label><strong>${fitness.toFixed(2)}</strong></div>
        <div><label>Time</label><strong>${String(Math.floor(this.time)).padStart(2, '0')}:${String(Math.floor((this.time % 1) * 60)).padStart(2, '0')}</strong></div>
      `;

      document.getElementById('economy').innerHTML = Object.entries(this.resources)
        .map(([k, v]) => `<div>${k.padEnd(5, ' ')} : ${Math.floor(v)} <span class="muted">(p ${this.prices[k]})</span></div>`)
        .join('');

      document.getElementById('simInfo').innerHTML = `
        <div>Villagers: ${this.villagers.length}</div>
        <div>Wildlife: ${this.animals.length}</div>
        <div>Raiders: ${this.enemies.length}</div>
        <div>Mode: ${this.mode.replaceAll('_', ' ')}</div>
        <div>Weather: ${this.weather}</div>
        <div>Territory Tiles: ${this.influence.size}</div>
      `;

      document.getElementById('diplomacy').innerHTML = this.factions
        .map((f) => `<div>${f.name} — rel ${f.relation} / mil ${f.military}</div>`)
        .join('');

      if (this.selectedInfo) {
        const t = this.selectedInfo.tile;
        document.getElementById('inspect').innerHTML = `
          <div>Tile: ${this.selectedInfo.x}, ${this.selectedInfo.y}</div>
          <div>Biome: ${t.biome}</div>
          <div>Building: ${t.building || 'none'}</div>
          <div>Resource: ${t.resource || 'none'} ${t.amount ? `(${Math.floor(t.amount)})` : ''}</div>
          <div>Owner: ${t.owner || 'neutral'}</div>
        `;
      }
    }

    save() {
      const data = {
        mode: this.mode,
        speed: this.speed,
        paused: this.paused,
        weather: this.weather,
        time: this.time,
        day: this.day,
        seed: this.seed,
        world: this.world,
        influence: [...this.influence],
        creatures: this.creatures,
        generation: this.generation,
        foodParticles: this.foodParticles,
        resources: this.resources,
        prices: this.prices,
        taxRate: this.taxRate,
        tech: this.tech,
        laws: this.laws,
        factions: this.factions,
        messages: this.messages,
      };
      localStorage.setItem(STORAGE_KEY, JSON.stringify(data));
      this.message('Saved');
    }

    load() {
      const raw = localStorage.getItem(STORAGE_KEY);
      if (!raw) return this.message('No save found');
      const d = JSON.parse(raw);
      Object.assign(this, {
        mode: d.mode,
        speed: d.speed,
        paused: d.paused,
        weather: d.weather,
        time: d.time,
        day: d.day,
        seed: d.seed,
        world: d.world,
        generation: d.generation,
        foodParticles: d.foodParticles,
        resources: d.resources,
        prices: d.prices,
        taxRate: d.taxRate,
        tech: d.tech,
        laws: d.laws,
        factions: d.factions,
        messages: d.messages,
        creatures: d.creatures,
      });
      this.influence = new Set(d.influence);
      this.rebuildGroups();
      this.message('Loaded');
    }

    reset() {
      localStorage.removeItem(STORAGE_KEY);
      window.location.reload();
    }

    loop(ts) {
      const dt = Math.min(0.08, (ts - this.last) / 1000);
      this.last = ts;

      this.updateWorld(dt);

      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      this.drawWorld();
      this.drawCreatures();
      this.drawWeatherAndLighting();
      this.drawOverlay();
      this.updatePanels();

      requestAnimationFrame(this.loop.bind(this));
    }
  }

  window.addEventListener('load', () => {
    const canvas = document.getElementById('game');
    const resize = () => {
      const w = Math.min(window.innerWidth - 40, 1300);
      const h = Math.min(window.innerHeight - 30, 860);
      canvas.width = Math.floor(w * 0.75);
      canvas.height = Math.floor(h);
    };
    resize();
    window.addEventListener('resize', resize);

    new Game(canvas);
  });
})();

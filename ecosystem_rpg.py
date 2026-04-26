import json
import math
import random
import time
from dataclasses import dataclass, field, asdict
from enum import Enum
from pathlib import Path
import tkinter as tk
from typing import Dict, List, Optional, Set, Tuple


TILE_SIZE = 16
WORLD_W = 96
WORLD_H = 96
VIEW_W = 56
VIEW_H = 40
UI_W = 320
CANVAS_W = VIEW_W * TILE_SIZE + UI_W
CANVAS_H = VIEW_H * TILE_SIZE
SAVE_FILE = Path("ecosystem_save.json")


class Biome(str, Enum):
    FOREST = "forest"
    DESERT = "desert"
    TUNDRA = "tundra"
    SWAMP = "swamp"
    RUINS = "ruins"


BIOME_COLORS = {
    Biome.FOREST: "#2c7a3f",
    Biome.DESERT: "#bfa35f",
    Biome.TUNDRA: "#8fb0b8",
    Biome.SWAMP: "#3d5f45",
    Biome.RUINS: "#6b5f66",
}

BUILDING_TYPES = {
    "house": {"cost": {"wood": 15, "stone": 8}, "color": "#d2b48c", "influence": 2},
    "farm": {"cost": {"wood": 10}, "color": "#9acd32", "influence": 1},
    "mine": {"cost": {"wood": 8, "stone": 12}, "color": "#8f8f8f", "influence": 1},
    "wall": {"cost": {"stone": 6}, "color": "#707070", "influence": 0},
    "road": {"cost": {"stone": 2}, "color": "#b28d64", "influence": 0},
    "market": {"cost": {"wood": 20, "stone": 12, "gold": 8}, "color": "#ffd166", "influence": 3},
    "tower": {"cost": {"wood": 12, "stone": 20}, "color": "#aa4444", "influence": 2},
}

RESOURCE_COLORS = {
    "tree": "#1f5b2a",
    "stone_node": "#888888",
    "berry": "#b83b5e",
    "ruin": "#d4af37",
}

WEATHER_TYPES = ["clear", "rain", "snow", "storm"]


@dataclass
class Tile:
    biome: str
    fertility: float
    water: bool = False
    discovered: bool = False
    resource: Optional[str] = None
    resource_amount: int = 0
    building: Optional[str] = None
    owner: Optional[str] = None


@dataclass
class Unit:
    x: float
    y: float
    hp: int
    max_hp: int
    kind: str


@dataclass
class Villager(Unit):
    job: str = "farmer"
    hunger: float = 100.0
    fatigue: float = 0.0
    carrying: Dict[str, int] = field(default_factory=dict)
    task: str = "idle"


@dataclass
class Animal(Unit):
    species: str = "rabbit"
    hunger: float = 0.0
    age: int = 0


@dataclass
class Faction:
    name: str
    relation: int = 0
    military: int = 10
    wealth: int = 50


class Game:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title("Pixel Ecosystem Empire RPG")
        self.canvas = tk.Canvas(root, width=CANVAS_W, height=CANVAS_H, bg="#111")
        self.canvas.pack()

        self.world: List[List[Tile]] = []
        self.player = Unit(12.0, 12.0, hp=100, max_hp=100, kind="player")
        self.villagers: List[Villager] = []
        self.animals: List[Animal] = []
        self.enemies: List[Unit] = []
        self.factions = {
            "Northreach": Faction("Northreach", relation=10, military=20, wealth=70),
            "Dunemar": Faction("Dunemar", relation=-10, military=30, wealth=60),
            "Verdant": Faction("Verdant", relation=5, military=18, wealth=55),
        }
        self.resources = {"wood": 45, "stone": 35, "food": 35, "gold": 20, "rare": 2}
        self.stockpile = {"wood": 0, "stone": 0, "food": 0, "gold": 0, "rare": 0}
        self.prices = {"wood": 3, "stone": 4, "food": 2, "gold": 10, "rare": 24}
        self.tax_rate = 0.12
        self.tech = {
            "agriculture": 0,
            "masonry": 0,
            "trade": 0,
            "military": 0,
            "ecology": 0,
        }
        self.laws = {"rationing": False, "open_borders": False, "conscription": False}

        self.influence: Set[Tuple[int, int]] = set()
        self.border_color = "#67b0ff"
        self.discovery_radius = 8
        self.selected_building = "house"

        self.time_of_day = 7.0
        self.day_count = 1
        self.weather = "clear"
        self.camera_x = 0
        self.camera_y = 0
        self.message_log: List[str] = []

        self.keys_down: Set[str] = set()
        self.spawn_cooldown = 0
        self.event_timer = 300
        self.market_timer = 0
        self.world_seed = random.randint(1000, 999999)
        random.seed(self.world_seed)

        self.init_world()
        self.init_population()
        self.bind_input()
        self.add_msg(f"World seed: {self.world_seed}")
        self.add_msg("Build with mouse. Hotkeys 1-7 select structures.")

        self.last_time = time.time()
        self.loop()

    def add_msg(self, msg: str) -> None:
        stamp = f"D{self.day_count} {int(self.time_of_day):02d}:{int((self.time_of_day%1)*60):02d}"
        self.message_log.insert(0, f"[{stamp}] {msg}")
        self.message_log = self.message_log[:11]

    def init_world(self) -> None:
        self.world = []
        for y in range(WORLD_H):
            row = []
            for x in range(WORLD_W):
                noise = self.sample_noise(x, y)
                biome = Biome.FOREST
                fertility = 0.6
                water = False
                if noise < 0.16:
                    biome, fertility, water = Biome.SWAMP, 0.8, True
                elif noise < 0.35:
                    biome, fertility = Biome.FOREST, 0.75
                elif noise < 0.56:
                    biome, fertility = Biome.DESERT, 0.25
                elif noise < 0.74:
                    biome, fertility = Biome.RUINS, 0.35
                else:
                    biome, fertility = Biome.TUNDRA, 0.45
                t = Tile(biome=biome.value, fertility=fertility, water=water)
                if not water:
                    roll = random.random()
                    if roll < 0.18 and biome in (Biome.FOREST, Biome.SWAMP):
                        t.resource, t.resource_amount = "tree", random.randint(40, 90)
                    elif roll < 0.24:
                        t.resource, t.resource_amount = "stone_node", random.randint(30, 80)
                    elif roll < 0.28:
                        t.resource, t.resource_amount = "berry", random.randint(15, 40)
                    elif roll < 0.30 and biome == Biome.RUINS:
                        t.resource, t.resource_amount = "ruin", random.randint(10, 25)
                row.append(t)
            self.world.append(row)

    def sample_noise(self, x: int, y: int) -> float:
        v = math.sin((x * 12.9898 + y * 78.233 + self.world_seed) * 0.005) * 43758.5453
        return v - math.floor(v)

    def init_population(self) -> None:
        for i in range(5):
            self.villagers.append(Villager(13 + i * 0.6, 14 + (i % 2), hp=60, max_hp=60, kind="villager", job=random.choice(["farmer", "miner", "guard", "trader"])))
        for _ in range(38):
            species = "wolf" if random.random() < 0.22 else "rabbit"
            hp = 45 if species == "wolf" else 20
            x, y = random.uniform(0, WORLD_W - 1), random.uniform(0, WORLD_H - 1)
            self.animals.append(Animal(x, y, hp=hp, max_hp=hp, kind="animal", species=species))

    def bind_input(self) -> None:
        self.root.bind("<KeyPress>", self.on_key_down)
        self.root.bind("<KeyRelease>", self.on_key_up)
        self.canvas.bind("<Button-1>", self.on_click)
        self.canvas.bind("<Button-3>", self.on_right_click)

    def on_key_down(self, e):
        k = e.keysym.lower()
        self.keys_down.add(k)
        if k in "1234567":
            idx = int(k) - 1
            self.selected_building = list(BUILDING_TYPES.keys())[idx]
            self.add_msg(f"Selected {self.selected_building}")
        elif k == "e":
            self.gather_nearby()
        elif k == "f":
            self.attack_nearby()
        elif k == "t":
            self.research_random_tech()
        elif k == "l":
            self.toggle_law()
        elif k == "f5":
            self.save_game()
        elif k == "f9":
            self.load_game()

    def on_key_up(self, e):
        k = e.keysym.lower()
        if k in self.keys_down:
            self.keys_down.remove(k)

    def world_tile(self, x: int, y: int) -> Optional[Tile]:
        if 0 <= x < WORLD_W and 0 <= y < WORLD_H:
            return self.world[y][x]
        return None

    def on_click(self, e):
        if e.x >= VIEW_W * TILE_SIZE:
            self.ui_click(e)
            return
        tx = e.x // TILE_SIZE + self.camera_x
        ty = e.y // TILE_SIZE + self.camera_y
        self.place_building(tx, ty)

    def on_right_click(self, e):
        if e.x >= VIEW_W * TILE_SIZE:
            return
        tx = e.x // TILE_SIZE + self.camera_x
        ty = e.y // TILE_SIZE + self.camera_y
        self.player.x, self.player.y = tx + 0.5, ty + 0.5

    def ui_click(self, e):
        rel_y = e.y
        if 20 <= rel_y <= 40:
            self.save_game()
        elif 45 <= rel_y <= 65:
            self.load_game()

    def can_afford(self, cost: Dict[str, int]) -> bool:
        return all(self.resources.get(r, 0) >= amt for r, amt in cost.items())

    def spend(self, cost: Dict[str, int]) -> None:
        for r, amt in cost.items():
            self.resources[r] -= amt

    def place_building(self, x: int, y: int) -> None:
        tile = self.world_tile(x, y)
        if not tile or tile.water:
            return
        if tile.building:
            self.add_msg("Tile occupied")
            return
        blueprint = BUILDING_TYPES[self.selected_building]
        if not self.can_afford(blueprint["cost"]):
            self.add_msg("Not enough resources")
            return
        self.spend(blueprint["cost"])
        tile.building = self.selected_building
        if blueprint["influence"]:
            self.expand_influence(x, y, blueprint["influence"])
        if self.selected_building == "house":
            self.villagers.append(Villager(x + 0.5, y + 0.5, hp=60, max_hp=60, kind="villager", job=random.choice(["farmer", "miner", "guard", "trader"])))
        self.add_msg(f"Built {self.selected_building} @ {x},{y}")

    def expand_influence(self, x: int, y: int, radius: int) -> None:
        for yy in range(y - radius, y + radius + 1):
            for xx in range(x - radius, x + radius + 1):
                if 0 <= xx < WORLD_W and 0 <= yy < WORLD_H and math.dist((x, y), (xx, yy)) <= radius + 0.5:
                    self.influence.add((xx, yy))
                    self.world[yy][xx].owner = "Player"

    def gather_nearby(self):
        px, py = int(self.player.x), int(self.player.y)
        for yy in range(py - 1, py + 2):
            for xx in range(px - 1, px + 2):
                tile = self.world_tile(xx, yy)
                if not tile or not tile.resource:
                    continue
                amount = min(10, tile.resource_amount)
                if tile.resource == "tree":
                    self.resources["wood"] += amount
                elif tile.resource == "stone_node":
                    self.resources["stone"] += amount
                elif tile.resource == "berry":
                    self.resources["food"] += amount
                elif tile.resource == "ruin":
                    self.resources["rare"] += max(1, amount // 4)
                    self.resources["gold"] += max(1, amount // 3)
                tile.resource_amount -= amount
                if tile.resource_amount <= 0:
                    tile.resource = None
                self.add_msg("Gathered resources")
                return
        self.add_msg("No harvestable resource nearby")

    def attack_nearby(self):
        for enemy in list(self.enemies):
            if math.dist((self.player.x, self.player.y), (enemy.x, enemy.y)) < 1.8:
                enemy.hp -= 22
                if enemy.hp <= 0:
                    self.enemies.remove(enemy)
                    self.resources["gold"] += 4
                    self.add_msg("Enemy slain")
                else:
                    self.add_msg("Hit enemy")
                return
        self.add_msg("No enemy in range")

    def research_random_tech(self):
        choices = [k for k, v in self.tech.items() if v < 5]
        if not choices:
            self.add_msg("All tech maxed")
            return
        if self.resources["gold"] < 10 or self.resources["rare"] < 1:
            self.add_msg("Need 10 gold + 1 rare to research")
            return
        t = random.choice(choices)
        self.resources["gold"] -= 10
        self.resources["rare"] -= 1
        self.tech[t] += 1
        self.add_msg(f"Researched {t} -> Lv {self.tech[t]}")

    def toggle_law(self):
        key = random.choice(list(self.laws.keys()))
        self.laws[key] = not self.laws[key]
        self.add_msg(f"Law changed: {key}={self.laws[key]}")

    def process_player_movement(self, dt: float):
        speed = 4.5
        dx = (1 if "d" in self.keys_down or "right" in self.keys_down else 0) - (1 if "a" in self.keys_down or "left" in self.keys_down else 0)
        dy = (1 if "s" in self.keys_down or "down" in self.keys_down else 0) - (1 if "w" in self.keys_down or "up" in self.keys_down else 0)
        if dx != 0 and dy != 0:
            dx *= 0.707
            dy *= 0.707
        self.player.x = min(WORLD_W - 0.01, max(0, self.player.x + dx * speed * dt))
        self.player.y = min(WORLD_H - 0.01, max(0, self.player.y + dy * speed * dt))
        self.camera_x = int(min(max(0, self.player.x - VIEW_W / 2), WORLD_W - VIEW_W))
        self.camera_y = int(min(max(0, self.player.y - VIEW_H / 2), WORLD_H - VIEW_H))

    def update_discovery(self):
        px, py = int(self.player.x), int(self.player.y)
        for yy in range(py - self.discovery_radius, py + self.discovery_radius + 1):
            for xx in range(px - self.discovery_radius, px + self.discovery_radius + 1):
                tile = self.world_tile(xx, yy)
                if tile and math.dist((px, py), (xx, yy)) <= self.discovery_radius:
                    tile.discovered = True

    def update_world_clock(self, dt: float):
        self.time_of_day += dt * 0.42
        if self.time_of_day >= 24:
            self.time_of_day -= 24
            self.day_count += 1
            self.daily_update()

    def daily_update(self):
        produced_food = 0
        produced_stone = 0
        tax_base = 0
        for y in range(WORLD_H):
            for x in range(WORLD_W):
                b = self.world[y][x].building
                if b == "farm":
                    produced_food += int(4 + self.world[y][x].fertility * 6 + self.tech["agriculture"])
                elif b == "mine":
                    produced_stone += int(3 + self.tech["masonry"])
                elif b == "market":
                    tax_base += 8
                elif b == "house":
                    tax_base += 3
        self.resources["food"] += produced_food
        self.resources["stone"] += produced_stone
        tax = int(tax_base * self.tax_rate * (1 + 0.1 * self.tech["trade"]))
        self.resources["gold"] += tax
        for f in self.factions.values():
            f.relation += random.randint(-2, 2)
            f.relation = max(-100, min(100, f.relation))
        self.add_msg(f"Daily economy: +{produced_food} food +{produced_stone} stone +{tax}g tax")

    def update_weather(self):
        if random.random() < 0.006:
            self.weather = random.choice(WEATHER_TYPES)
            self.add_msg(f"Weather changed to {self.weather}")

    def update_villagers(self, dt: float):
        for v in self.villagers:
            v.hunger -= dt * 1.7
            v.fatigue += dt * (0.8 if 6 <= self.time_of_day <= 20 else 1.6)
            if v.hunger < 35 and self.resources["food"] > 0:
                eat = min(3, self.resources["food"])
                self.resources["food"] -= eat
                v.hunger += eat * 14
                v.task = "eating"
            if v.fatigue > 70:
                hx, hy = self.find_nearest_building(v.x, v.y, "house")
                self.move_toward(v, hx + 0.5, hy + 0.5, dt, speed=2.2)
                v.task = "sleeping"
                if math.dist((v.x, v.y), (hx + 0.5, hy + 0.5)) < 1.2:
                    v.fatigue = max(0, v.fatigue - dt * 12)
            else:
                self.run_job(v, dt)
            if v.hunger <= 0:
                v.hp -= int(8 * dt)
            if v.hp <= 0:
                self.villagers.remove(v)
                self.add_msg("A villager died")

    def run_job(self, v: Villager, dt: float):
        if v.job == "farmer":
            tx, ty = self.find_nearest_building(v.x, v.y, "farm")
            self.move_toward(v, tx + 0.5, ty + 0.5, dt, speed=2.8)
            v.task = "farming"
            if math.dist((v.x, v.y), (tx + 0.5, ty + 0.5)) < 1.2 and random.random() < 0.08:
                self.resources["food"] += 1 + self.tech["agriculture"] // 2
        elif v.job == "miner":
            tx, ty = self.find_nearest_resource(v.x, v.y, "stone_node")
            self.move_toward(v, tx + 0.5, ty + 0.5, dt, speed=2.4)
            v.task = "mining"
            tile = self.world_tile(tx, ty)
            if tile and tile.resource == "stone_node" and math.dist((v.x, v.y), (tx + 0.5, ty + 0.5)) < 1.2:
                gain = 1 + self.tech["masonry"] // 2
                self.resources["stone"] += gain
                tile.resource_amount -= gain
                if tile.resource_amount <= 0:
                    tile.resource = None
        elif v.job == "trader":
            tx, ty = self.find_nearest_building(v.x, v.y, "market")
            self.move_toward(v, tx + 0.5, ty + 0.5, dt, speed=3.0)
            v.task = "trading"
            if math.dist((v.x, v.y), (tx + 0.5, ty + 0.5)) < 1.4 and random.random() < 0.08:
                self.resources["gold"] += 1 + self.tech["trade"] // 2
        else:
            target = self.find_nearest_enemy(v.x, v.y)
            v.task = "guarding"
            if target:
                self.move_toward(v, target.x, target.y, dt, speed=3.1)
                if math.dist((v.x, v.y), (target.x, target.y)) < 1.3:
                    target.hp -= int(8 + self.tech["military"] * 2)

    def find_nearest_building(self, x: float, y: float, bname: str) -> Tuple[int, int]:
        best = (int(x), int(y))
        best_d = 10**9
        for yy in range(WORLD_H):
            for xx in range(WORLD_W):
                if self.world[yy][xx].building == bname:
                    d = (xx - x) ** 2 + (yy - y) ** 2
                    if d < best_d:
                        best_d, best = d, (xx, yy)
        return best

    def find_nearest_resource(self, x: float, y: float, rname: str) -> Tuple[int, int]:
        best = (int(x), int(y))
        best_d = 10**9
        for yy in range(max(0, int(y) - 18), min(WORLD_H, int(y) + 18)):
            for xx in range(max(0, int(x) - 18), min(WORLD_W, int(x) + 18)):
                t = self.world[yy][xx]
                if t.resource == rname:
                    d = (xx - x) ** 2 + (yy - y) ** 2
                    if d < best_d:
                        best_d, best = d, (xx, yy)
        return best

    def find_nearest_enemy(self, x: float, y: float) -> Optional[Unit]:
        best = None
        best_d = 999
        for e in self.enemies:
            d = math.dist((x, y), (e.x, e.y))
            if d < best_d:
                best_d = d
                best = e
        return best

    def move_toward(self, u: Unit, tx: float, ty: float, dt: float, speed: float):
        dx, dy = tx - u.x, ty - u.y
        dist = math.hypot(dx, dy)
        if dist > 0.001:
            step = min(dist, speed * dt)
            u.x += dx / dist * step
            u.y += dy / dist * step

    def update_animals(self, dt: float):
        for a in list(self.animals):
            a.age += 1
            a.hunger += dt * (2.2 if a.species == "wolf" else 1.4)
            if a.species == "rabbit":
                if random.random() < 0.05:
                    angle = random.random() * math.tau
                    a.x = min(WORLD_W - 0.1, max(0.1, a.x + math.cos(angle) * 1.4))
                    a.y = min(WORLD_H - 0.1, max(0.1, a.y + math.sin(angle) * 1.4))
                tile = self.world_tile(int(a.x), int(a.y))
                if tile and tile.fertility > 0.55:
                    a.hunger = max(0, a.hunger - dt * 1.8)
                if a.age % 350 == 0 and random.random() < 0.12 and len(self.animals) < 80:
                    self.animals.append(Animal(a.x + random.uniform(-1, 1), a.y + random.uniform(-1, 1), hp=20, max_hp=20, kind="animal", species="rabbit"))
            else:
                target = self.find_nearest_species(a.x, a.y, "rabbit")
                if target:
                    self.move_toward(a, target.x, target.y, dt, speed=2.6)
                    if math.dist((a.x, a.y), (target.x, target.y)) < 0.8:
                        if target in self.animals:
                            self.animals.remove(target)
                        a.hunger = max(0, a.hunger - 25)
                if a.age % 500 == 0 and random.random() < 0.08 and len(self.animals) < 80:
                    self.animals.append(Animal(a.x, a.y, hp=45, max_hp=45, kind="animal", species="wolf"))
            if a.hunger > 110:
                self.animals.remove(a)

    def find_nearest_species(self, x: float, y: float, species: str) -> Optional[Animal]:
        best = None
        best_d = 999
        for a in self.animals:
            if a.species != species:
                continue
            d = math.dist((x, y), (a.x, a.y))
            if d < best_d:
                best_d, best = d, a
        return best

    def update_enemies(self, dt: float):
        for e in list(self.enemies):
            tx, ty = self.find_nearest_building(e.x, e.y, "house")
            self.move_toward(e, tx + 0.5, ty + 0.5, dt, speed=2.2)
            if math.dist((e.x, e.y), (self.player.x, self.player.y)) < 1.3:
                self.player.hp -= int(14 * dt)
            for v in self.villagers:
                if math.dist((e.x, e.y), (v.x, v.y)) < 1.2:
                    v.hp -= int(12 * dt)
            for v in self.villagers:
                if v.job == "guard" and math.dist((e.x, e.y), (v.x, v.y)) < 1.4:
                    e.hp -= int(9 * dt + self.tech["military"])
            if e.hp <= 0:
                self.enemies.remove(e)

    def update_economy(self, dt: float):
        self.market_timer += dt
        if self.market_timer < 4:
            return
        self.market_timer = 0
        for k in self.prices:
            stock = self.resources[k]
            base = 4 + random.randint(-1, 1)
            self.prices[k] = max(1, int(base + (40 - stock) * 0.07))
        traders = sum(1 for v in self.villagers if v.job == "trader")
        if traders > 0:
            self.resources["gold"] += traders
            if self.resources["food"] < 20 and self.resources["gold"] > 5:
                amount = min(8, self.resources["gold"] // self.prices["food"])
                self.resources["food"] += amount
                self.resources["gold"] -= amount * self.prices["food"]

    def dynamic_events(self):
        self.event_timer -= 1
        if self.event_timer > 0:
            return
        self.event_timer = random.randint(240, 420)
        evt = random.choice(["disease", "invasion", "storm", "boom", "scarcity"])
        if evt == "disease" and self.villagers:
            victim = random.choice(self.villagers)
            victim.hp -= 20
            self.add_msg("Disease outbreak! A villager got sick.")
        elif evt == "invasion":
            self.spawn_raid(size=random.randint(3, 8))
            self.add_msg("Raid incoming from hostile faction!")
        elif evt == "storm":
            self.weather = "storm"
            self.resources["food"] = max(0, self.resources["food"] - 8)
            self.add_msg("Storm damaged crops.")
        elif evt == "boom":
            self.resources["gold"] += 20
            self.add_msg("Trade boom: +20 gold")
        elif evt == "scarcity":
            loss = random.choice(["wood", "stone", "food"])
            self.resources[loss] = max(0, self.resources[loss] - 15)
            self.add_msg(f"Resource shortage: -15 {loss}")

    def spawn_raid(self, size: int):
        for _ in range(size):
            side = random.choice(["top", "bottom", "left", "right"])
            if side == "top":
                x, y = random.uniform(0, WORLD_W - 1), 0.3
            elif side == "bottom":
                x, y = random.uniform(0, WORLD_W - 1), WORLD_H - 0.3
            elif side == "left":
                x, y = 0.3, random.uniform(0, WORLD_H - 1)
            else:
                x, y = WORLD_W - 0.3, random.uniform(0, WORLD_H - 1)
            self.enemies.append(Unit(x, y, hp=45, max_hp=45, kind="enemy"))

    def render(self):
        self.canvas.delete("all")
        self.draw_world()
        self.draw_units()
        self.draw_weather_and_lighting()
        self.draw_ui()

    def draw_world(self):
        for vy in range(VIEW_H):
            wy = self.camera_y + vy
            if not (0 <= wy < WORLD_H):
                continue
            for vx in range(VIEW_W):
                wx = self.camera_x + vx
                if not (0 <= wx < WORLD_W):
                    continue
                tile = self.world[wy][wx]
                x0, y0 = vx * TILE_SIZE, vy * TILE_SIZE
                x1, y1 = x0 + TILE_SIZE, y0 + TILE_SIZE

                if not tile.discovered:
                    self.canvas.create_rectangle(x0, y0, x1, y1, fill="#000", outline="#050505")
                    continue

                color = BIOME_COLORS[Biome(tile.biome)]
                if tile.water:
                    color = "#2a5db0"
                self.canvas.create_rectangle(x0, y0, x1, y1, fill=color, outline="#000000")

                if (wx, wy) in self.influence:
                    self.canvas.create_rectangle(x0 + 1, y0 + 1, x1 - 1, y1 - 1, outline=self.border_color)

                if tile.resource:
                    rc = RESOURCE_COLORS[tile.resource]
                    self.canvas.create_rectangle(x0 + 4, y0 + 4, x1 - 4, y1 - 4, fill=rc, outline="#101010")

                if tile.building:
                    bc = BUILDING_TYPES[tile.building]["color"]
                    self.canvas.create_rectangle(x0 + 2, y0 + 2, x1 - 2, y1 - 2, fill=bc, outline="#141414")

    def draw_unit(self, u: Unit, color: str):
        sx = int((u.x - self.camera_x) * TILE_SIZE)
        sy = int((u.y - self.camera_y) * TILE_SIZE)
        if 0 <= sx < VIEW_W * TILE_SIZE and 0 <= sy < VIEW_H * TILE_SIZE:
            r = 5 if u.kind == "player" else 4
            self.canvas.create_rectangle(sx - r, sy - r, sx + r, sy + r, fill=color, outline="#222")

    def draw_units(self):
        self.draw_unit(self.player, "#fff2a8")
        for v in self.villagers:
            c = "#7fd2ff" if v.job != "guard" else "#ff8888"
            self.draw_unit(v, c)
        for a in self.animals:
            self.draw_unit(a, "#f4f4f4" if a.species == "rabbit" else "#8a5a44")
        for e in self.enemies:
            self.draw_unit(e, "#ff2e2e")

    def draw_weather_and_lighting(self):
        darkness = 0
        if self.time_of_day < 6 or self.time_of_day > 20:
            darkness = int(95 + abs(12 - self.time_of_day) * 7)
        if self.weather == "rain":
            for _ in range(65):
                x = random.randint(0, VIEW_W * TILE_SIZE)
                y = random.randint(0, VIEW_H * TILE_SIZE)
                self.canvas.create_line(x, y, x + 2, y + 7, fill="#6ea4d8")
            darkness += 20
        elif self.weather == "snow":
            for _ in range(50):
                x = random.randint(0, VIEW_W * TILE_SIZE)
                y = random.randint(0, VIEW_H * TILE_SIZE)
                self.canvas.create_oval(x, y, x + 2, y + 2, fill="#e8f2ff", outline="")
            darkness += 10
        elif self.weather == "storm":
            for _ in range(75):
                x = random.randint(0, VIEW_W * TILE_SIZE)
                y = random.randint(0, VIEW_H * TILE_SIZE)
                self.canvas.create_line(x, y, x + 3, y + 8, fill="#618fb8")
            darkness += 35
        if darkness > 0:
            shade = f"#{max(0, 255-darkness):02x}{max(0, 255-darkness):02x}{max(0, 255-darkness):02x}"
            self.canvas.create_rectangle(0, 0, VIEW_W * TILE_SIZE, VIEW_H * TILE_SIZE, fill=shade, stipple="gray50", outline="")

    def draw_ui(self):
        x0 = VIEW_W * TILE_SIZE
        self.canvas.create_rectangle(x0, 0, CANVAS_W, CANVAS_H, fill="#191919", outline="#333")
        y = 10
        self.canvas.create_text(x0 + 10, y, anchor="nw", fill="#fff", font=("Courier", 11, "bold"), text="Empire Panel")
        y += 18
        self.canvas.create_text(x0 + 10, y, anchor="nw", fill="#aaa", font=("Courier", 9), text="Click: build   Right-click: move")
        y += 16
        self.canvas.create_text(x0 + 10, y, anchor="nw", fill="#fff", font=("Courier", 9), text="[Save F5]")
        self.canvas.create_rectangle(x0 + 8, 20, x0 + 90, 40, outline="#888")
        self.canvas.create_text(x0 + 10, 46, anchor="nw", fill="#fff", font=("Courier", 9), text="[Load F9]")
        self.canvas.create_rectangle(x0 + 8, 45, x0 + 90, 65, outline="#888")

        y = 78
        self.canvas.create_text(x0 + 10, y, anchor="nw", fill="#f6f6f6", font=("Courier", 10, "bold"), text=f"Day {self.day_count} {self.time_of_day:04.1f}h {self.weather}")
        y += 24
        self.canvas.create_text(x0 + 10, y, anchor="nw", fill="#fff", font=("Courier", 9), text=f"HP {self.player.hp}/{self.player.max_hp} | Pop {len(self.villagers)}")

        y += 18
        for k, v in self.resources.items():
            self.canvas.create_text(x0 + 10, y, anchor="nw", fill="#d9f3cf", font=("Courier", 9), text=f"{k:<5}: {v:>4} (p {self.prices[k]})")
            y += 14

        y += 8
        self.canvas.create_text(x0 + 10, y, anchor="nw", fill="#fff", font=("Courier", 9, "bold"), text=f"Selected: {self.selected_building}")
        y += 14
        self.canvas.create_text(
            x0 + 10,
            y,
            anchor="nw",
            fill="#aaa",
            font=("Courier", 8),
            text="1 house 2 farm 3 mine 4 wall\n5 road 6 market 7 tower\nE gather  F attack  T tech  L law",
        )

        y += 50
        self.canvas.create_text(x0 + 10, y, anchor="nw", fill="#fff", font=("Courier", 9, "bold"), text="Tech Levels")
        y += 14
        for name, lvl in self.tech.items():
            self.canvas.create_text(x0 + 10, y, anchor="nw", fill="#ffd891", font=("Courier", 8), text=f"{name:<11}: {lvl}")
            y += 12

        y += 6
        self.canvas.create_text(x0 + 10, y, anchor="nw", fill="#fff", font=("Courier", 9, "bold"), text="Diplomacy")
        y += 14
        for f in self.factions.values():
            tone = "#8ef58e" if f.relation >= 0 else "#ff9b9b"
            self.canvas.create_text(x0 + 10, y, anchor="nw", fill=tone, font=("Courier", 8), text=f"{f.name[:9]:<9} rel {f.relation:>3} mil {f.military:>2}")
            y += 12

        y += 6
        self.canvas.create_text(x0 + 10, y, anchor="nw", fill="#fff", font=("Courier", 9, "bold"), text="Events")
        y += 14
        for m in self.message_log[:10]:
            self.canvas.create_text(x0 + 10, y, anchor="nw", fill="#c6d3ff", font=("Courier", 7), text=m)
            y += 11

    def save_game(self):
        data = {
            "seed": self.world_seed,
            "player": asdict(self.player),
            "villagers": [asdict(v) for v in self.villagers],
            "animals": [asdict(a) for a in self.animals],
            "enemies": [asdict(e) for e in self.enemies],
            "resources": self.resources,
            "prices": self.prices,
            "tech": self.tech,
            "laws": self.laws,
            "day_count": self.day_count,
            "time_of_day": self.time_of_day,
            "weather": self.weather,
            "influence": list(self.influence),
            "world": [[asdict(t) for t in row] for row in self.world],
            "factions": {k: asdict(v) for k, v in self.factions.items()},
        }
        SAVE_FILE.write_text(json.dumps(data))
        self.add_msg("Game saved")

    def load_game(self):
        if not SAVE_FILE.exists():
            self.add_msg("No save file")
            return
        data = json.loads(SAVE_FILE.read_text())
        self.world_seed = data["seed"]
        self.player = Unit(**data["player"])
        self.villagers = [Villager(**v) for v in data["villagers"]]
        self.animals = [Animal(**a) for a in data["animals"]]
        self.enemies = [Unit(**e) for e in data["enemies"]]
        self.resources = data["resources"]
        self.prices = data["prices"]
        self.tech = data["tech"]
        self.laws = data["laws"]
        self.day_count = data["day_count"]
        self.time_of_day = data["time_of_day"]
        self.weather = data["weather"]
        self.influence = {tuple(x) for x in data["influence"]}
        self.factions = {k: Faction(**v) for k, v in data["factions"].items()}
        self.world = [[Tile(**t) for t in row] for row in data["world"]]
        self.add_msg("Game loaded")

    def loop(self):
        now = time.time()
        dt = min(0.12, now - self.last_time)
        self.last_time = now

        self.process_player_movement(dt)
        self.update_world_clock(dt)
        self.update_discovery()
        self.update_weather()
        self.update_villagers(dt)
        self.update_animals(dt)
        self.update_enemies(dt)
        self.update_economy(dt)
        self.dynamic_events()

        hostile_power = sum(max(0, -f.relation) for f in self.factions.values())
        self.spawn_cooldown -= 1
        if self.spawn_cooldown <= 0 and hostile_power > 70 and random.random() < 0.08:
            self.spawn_cooldown = random.randint(90, 200)
            self.spawn_raid(size=2 + hostile_power // 40)
            self.add_msg("Hostile border skirmish!")

        if self.player.hp <= 0:
            self.add_msg("You fell in battle. Respawning.")
            self.player.hp = self.player.max_hp
            self.player.x, self.player.y = 12, 12

        self.render()
        self.root.after(70, self.loop)


def main():
    root = tk.Tk()
    Game(root)
    root.mainloop()


if __name__ == "__main__":
    main()

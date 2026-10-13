# Idle Pond — Design Spec (MVP)

Date: 2026-10-13
Status: Approved in brainstorming, pending written-spec review

## 1. Overview

Idle Pond is an idle game where the player runs a virtual pond. Fish passively
produce coins (including while the player is offline). Coins buy more fish and
pond upgrades; spending coins earns XP, and levelling up unlocks new species.

Targets: web (HTML5) and mobile (Android, iOS) from a single codebase.

### Decisions

| Topic | Decision |
|---|---|
| Core loop | Fish produce coins → buy fish/upgrades → XP → level → unlock species |
| Engine | Godot 4 (latest stable), GDScript |
| Platforms | Godot exports: Web, Android, iOS |
| Save | Cloud save + accounts via Supabase (REST, no plugin), plus local save |
| View / art | Side-view aquarium, placeholder art (simple shapes / CC0 sprites) |
| MVP scope | 1 pond, 8 species, 3 upgrades, offline earnings, guest + email login |

### Out of scope (MVP)

Prestige, monetization (ads / IAP), leaderboards, multiple ponds, breeding,
server-authoritative economy, final art and audio.

## 2. Architecture

Game logic is separated from presentation so it can be unit-tested without
running the scene tree.

| Unit | Responsibility | Depends on |
|---|---|---|
| `SpeciesData` (Resource, one `.tres` per species) | id, name, unlock_level, base_cost, coins_per_sec, zone (`surface`/`mid`/`bottom`), sprite | — |
| `Balance` (`balance.gd`, constants) | All tuning numbers not tied to a species (multipliers, curves, upgrade costs) | — |
| `Economy` (static functions) | income/sec, fish cost, sell refund, offline earnings, XP→level, upgrade cost/effect | inputs only, `Balance` |
| `GameState` (autoload) | coins, xp, level, fish owned per species, upgrade levels, lifetime_coins; emits change signals | `Economy` |
| `SaveService` (autoload) | Serialize/deserialize GameState (JSON + `save_version`), local save, cloud sync, merge, migrations | `GameState`, `SupabaseClient` |
| `SupabaseClient` | Thin `HTTPRequest` wrapper: anonymous sign-in, email link/sign-in, token refresh, `save_game` / `load_game` RPC | — |

### Scenes

- `Main` — root; contains `PondView` and HUD (coins, coins/sec, level + XP bar).
- `PondView` — side-view aquarium with three depth bands (surface / mid / bottom),
  water shader (surface wave + light rays), bubble particles.
- `Fish` — wanders randomly within its species' depth band.
  Rendered fish are capped (default 40) for performance; the economy always uses
  the true owned counts.
- Panels: `Shop` (species list; locked species greyed out showing unlock level;
  buy and sell buttons), `Upgrades`, `Account` (guest status, link email, sign in/out).

### Tick

Every frame: `coins += income_per_sec * delta` (also added to `lifetime_coins`).
HUD text refreshes at most 10 times per second.

## 3. Economy

### Income

```
income_per_sec = Σ(owned[s] × coins_per_sec[s]) × food_multiplier
food_multiplier = 1 + 0.25 × food_level
```

### Fish

- Buy cost: `base_cost × 1.15^owned[s]`
- Sell refund: 50% of the price paid for the most recent fish of that species,
  i.e. `0.5 × base_cost × 1.15^(owned[s] - 1)`.
- Pond capacity limits total fish owned (all species combined). Buying is
  disabled when the pond is full.

### XP and levels

- 1 XP per coin spent (fish and upgrades). Selling does not remove XP.
- XP required to go from level L to L+1: `50 × 2.2^(L-1)`.
- Level is unbounded; species unlocks end at level 15.

### Species

| Unlock Lv | Species | Zone | Base cost | Coins/sec |
|---|---|---|---|---|
| 1 | Guppy | surface | 10 | 0.5 |
| 2 | Snail | bottom | 60 | 2 |
| 3 | Goldfish | mid | 400 | 10 |
| 5 | Tetra | mid | 2,500 | 45 |
| 7 | Catfish | bottom | 15,000 | 200 |
| 9 | Angelfish | mid | 100,000 | 1,000 |
| 12 | Koi | surface | 750,000 | 5,500 |
| 15 | Arowana | surface | 6,000,000 | 30,000 |

Names and numbers are placeholders, tunable in data files.

### Upgrades (n = current upgrade level, starting at 0)

| Upgrade | Effect | Cost |
|---|---|---|
| Pond Size | capacity = 10 + 5n | `100 × 3^n` |
| Better Food | food_multiplier = 1 + 0.25n | `500 × 4^n` |
| Deep Sleep | offline cap = 2h + 2h·n, max 24h (n ≤ 11) | `1000 × 5^n` |

### Offline earnings

`offline_coins = income_per_sec × min(elapsed_seconds, offline_cap)`, paid at
100%, shown in a "While you were away" popup. Negative elapsed time is treated
as 0.

### Number display

Values are floats. Display with suffixes: K, M, B, T (e.g. `1.2K`, `3.4M`).

### Pacing targets (verified by simulation test)

- First new species (level 2) within 2 minutes of a new game.
- All 8 species (level 15) within 3–5 days of simulated idle play
  (model: player checks in periodically and spends greedily).

## 4. Backend and saving

### Auth (Supabase)

- First launch: automatic anonymous sign-in (guest). No signup before play.
- `Account` panel: link email + password to the guest account; sign in on another
  device with that email to continue the same save.
- Session (access + refresh token) stored locally and refreshed automatically.

### Database

```sql
create table saves (
  user_id        uuid primary key references auth.users on delete cascade,
  data           jsonb not null,
  save_version   int not null,
  lifetime_coins double precision not null default 0,
  updated_at     timestamptz not null default now()
);
alter table saves enable row level security;
-- policies: select / insert / update only where user_id = auth.uid()
```

RPC functions (Postgres, `security invoker`):

- `save_game(data jsonb, save_version int, lifetime_coins double precision)` —
  upserts the caller's row, sets `updated_at = now()` (server clock).
- `load_game()` — returns the caller's row plus
  `elapsed_seconds = extract(epoch from now() - updated_at)`.

Only the public anon key ships in the client; the service-role key is never
included.

### Save cadence

- Local (`user://save.json`; IndexedDB-backed on web): every 10 s and on
  pause / close.
- Cloud: every 60 s, on pause / close, and immediately after the first purchase
  of a newly unlocked species.

### Startup flow

1. Load local save; game is playable immediately.
2. Fetch cloud save. If both exist, keep the one with the higher
   `lifetime_coins` (robust against clock differences between devices).
3. Offline earnings use server `elapsed_seconds` when the cloud call succeeds,
   otherwise device-clock elapsed time since local `saved_at`.

### Error handling

- Network failure: continue on local save; retry cloud on the next 60 s cycle.
  Gameplay is never blocked by the network.
- Old save format: `save_version` + one migration function per version step.
- Corrupt local save: fall back to cloud save; if none, start a new game.

### Known limitation

The economy is client-authoritative; a player can edit their own save. Accepted
for a single-player MVP with no leaderboards or paid currency.

## 5. Testing

- **Unit (GUT):** Economy formulas, level curve, offline earnings + cap, sell
  refund, capacity limit, save serialize/deserialize round-trip, migrations,
  merge rule.
- **Balance simulation (GUT):** scripted greedy player verifies pacing targets
  in section 3.
- **Database:** SQL tests that RLS prevents user A from reading or writing
  user B's save.
- **Manual smoke:** Web and Android exports — new game, buy, level up, close,
  reopen, offline popup, link email, sign in on second device.

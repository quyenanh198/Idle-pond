# Idle Pond MVP Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the Idle Pond MVP described in `docs/superpowers/specs/2026-10-13-idle-pond-design.md`: a side-view idle pond game in Godot with coin production, 8 species unlocked by level, 3 upgrades, offline earnings, and Supabase guest/email accounts with cloud save.

**Architecture:** Pure game logic (`Balance`, `Economy`, `SaveCodec`, `NumberFormat`) is static GDScript with no scene dependencies, so it is unit-tested headless with GUT. `GameState` (autoload) owns progress and actions; `SaveService` (autoload) owns local + cloud persistence via a thin REST `SupabaseClient`. All visuals and UI are built in code from a tiny `main.tscn` root (placeholder art drawn with `_draw()` plus a water shader).

**Tech Stack:** Godot 4.7.2 (GDScript, GL Compatibility renderer), GUT 9.7.1, Supabase (Auth + Postgres RPC over REST), PostgreSQL 16 locally for SQL/RLS tests, Python 3 for a mock Supabase server in integration tests.

## Global Constraints

- Engine: Godot 4.7.2, renderer `gl_compatibility` (required for the Web export).
- Exports: Web (no thread support, so no COOP/COEP headers needed), Android, iOS.
- Viewport 720×1280, portrait, stretch mode `canvas_items`, aspect `expand`.
- Economy values exactly as spec section 3: start coins 15, fish cost growth 1.15, sell refund 50%, 1 XP per coin spent, XP to next level `50 × 3.5^(L-1)`, food +25%/level additive, capacity `10 + 5n`, offline cap `2h + 2h·n` max 24h (n ≤ 11), upgrade costs `100×3^n`, `500×4^n`, `1000×5^n`.
- Species table exactly as the spec (ids `guppy, snail, goldfish, tetra, catfish, angelfish, koi, arowana`).
- Rendered fish cap 40; economy uses real counts.
- Local save `user://save.json` every 10 s and on pause/close; cloud every 60 s, on pause/close, and on first purchase of a species.
- Merge rule: higher `lifetime_coins` wins; tie keeps local.
- Only the Supabase anon key ships in the client, never the service-role key.
- Gameplay never blocks on the network; HTTP timeout 10 s.
- Tests: `./run_tests.sh` (GUT unit + integration against a mock server) and `./scripts/test_db.sh` (SQL/RLS on a throwaway local Postgres).

## File Structure

```
project.godot                      engine config, autoloads
icon.svg                           app icon (placeholder)
.gitignore / .gutconfig.json
run_tests.sh                       import + GUT (starts mock Supabase)
export_presets.cfg                 Web / Android / iOS presets
README.md                          setup, Supabase config, testing, exporting
addons/gut/                        vendored GUT 9.7.1 (MIT)
config/supabase.cfg                Supabase URL + anon key (empty = cloud off)
data/species/*.tres                8 SpeciesData resources
scripts/data/species_data.gd       SpeciesData resource class
scripts/data/species_catalog.gd    loads + sorts all species
scripts/core/balance.gd            tuning constants
scripts/core/economy.gd            pure formulas
scripts/core/number_format.gd      1.2K / 3.4M formatting
scripts/core/save_codec.gd         save envelope, migration, merge, offline time
scripts/autoload/game_state.gd     progress + actions (autoload GameState)
scripts/autoload/save_service.gd   local/cloud persistence (autoload SaveService)
scripts/net/supabase_client.gd     REST auth + RPC
scripts/pond/pond_view.gd          side-view pond: water, decor, bubbles, fish
scripts/pond/fish.gd               one wandering fish
shaders/water.gdshader             gradient + light rays + surface wave
scripts/ui/main.gd                 root layout, theme, offline popup, start
scripts/ui/hud.gd                  coins, income, level bar, toast, cloud status
scripts/ui/shop_panel.gd           buy/sell species
scripts/ui/upgrades_panel.gd       3 upgrades
scripts/ui/account_panel.gd        guest / link email / sign in / sign out
scenes/main.tscn                   root Control with main.gd
supabase/migrations/20261015000000_saves.sql
supabase/tests/auth_stub.sql       minimal Supabase auth schema for local tests
supabase/tests/saves_rls_test.sql
scripts/test_db.sh
tests/mock_supabase.py
tests/unit/test_*.gd
tests/integration/test_cloud_sync.gd
```

## Code location note

The full source for every step below is written once, in the repository, in
the commit for that task (commit messages listed per task). This plan defines
the interfaces, tests and acceptance checks; the code blocks show the parts a
reviewer must check against (tests, formulas, SQL, protocol).

---

### Task 1: Project scaffold + GUT + test runner

**Files:** Create `project.godot`, `icon.svg`, `.gitignore`, `.gutconfig.json`, `run_tests.sh`, `addons/gut/` (vendored from tag `v9.7.1`), `tests/unit/test_smoke.gd`, stub `tests/mock_supabase.py`.

**Interfaces:** Produces `./run_tests.sh`: runs `godot --headless --import`, then `godot --headless -s addons/gut/gut_cmdln.gd -gconfig=res://.gutconfig.json`; starts `tests/mock_supabase.py $PORT` in the background and exports `MOCK_SUPABASE_URL`. Exit code non-zero on any failure.

`project.godot` key settings:
```ini
config/features=PackedStringArray("4.7", "GL Compatibility")
run/main_scene="res://scenes/main.tscn"
window/size/viewport_width=720
window/size/viewport_height=1280
window/stretch/mode="canvas_items"
window/stretch/aspect="expand"
window/handheld/orientation=1
renderer/rendering_method="gl_compatibility"
renderer/rendering_method.mobile="gl_compatibility"
```

- [ ] Step 1: Vendor GUT: `git clone --depth 1 --branch v9.7.1 https://github.com/bitwes/Gut /tmp/gut && cp -r /tmp/gut/addons/gut addons/gut`
- [ ] Step 2: Write project files above and `tests/unit/test_smoke.gd` (`assert_true(true)`).
- [ ] Step 3: Run `./run_tests.sh` → Expected: `1 passed`, exit 0.
- [ ] Step 4: Commit `chore: scaffold Godot project with GUT test runner`.

---

### Task 2: Species data + Balance + NumberFormat

**Files:** Create `scripts/data/species_data.gd`, `scripts/data/species_catalog.gd`, `data/species/*.tres` (8), `scripts/core/balance.gd`, `scripts/core/number_format.gd`. Test `tests/unit/test_species_catalog.gd`, `tests/unit/test_number_format.gd`. Delete `test_smoke.gd`.

**Interfaces (produces):**
- `class_name SpeciesData extends Resource`, `enum Zone { SURFACE, MID, BOTTOM }`, exported `id: String, display_name: String, unlock_level: int, base_cost: float, coins_per_sec: float, zone: Zone, color: Color, body_size: Vector2, sprite: Texture2D`
- `SpeciesCatalog.all() -> Array[SpeciesData]` (sorted by `unlock_level`, explicit path list so exports never miss a file), `SpeciesCatalog.by_id(id: String) -> SpeciesData` (null if unknown)
- `Balance`: `START_COINS=15.0, FISH_COST_GROWTH=1.15, SELL_REFUND_RATIO=0.5, XP_BASE=50.0, XP_GROWTH=3.5, FOOD_BONUS_PER_LEVEL=0.25, POND_BASE_CAPACITY=10, POND_CAPACITY_PER_LEVEL=5, OFFLINE_BASE_CAP_SEC=7200.0, OFFLINE_CAP_PER_LEVEL_SEC=7200.0, MAX_RENDERED_FISH=40`, ids `POND_SIZE="pond_size", BETTER_FOOD="better_food", DEEP_SLEEP="deep_sleep"`, `UPGRADES = {id: {"name", "base_cost", "growth", "max_level"}}` with max_level -1 = unlimited (deep_sleep 11)
- `NumberFormat.short(value: float) -> String`: `< 10` non-integer → one decimal rounded down; `< 1000` → integer floor; else K/M/B/T with one decimal rounded down (beyond T stays T)

Species data (zone 0 surface, 1 mid, 2 bottom):

| id | name | Lv | base_cost | coins/sec | zone | color | body_size |
|---|---|---|---|---|---|---|---|
| guppy | Guppy | 1 | 10 | 0.5 | 0 | (1, 0.55, 0.2) | (26, 12) |
| snail | Snail | 2 | 140 | 1.25 | 2 | (0.6, 0.45, 0.3) | (22, 16) |
| goldfish | Goldfish | 3 | 1900 | 3 | 1 | (1, 0.75, 0.1) | (34, 18) |
| tetra | Tetra | 5 | 26000 | 8 | 1 | (0.2, 0.7, 1) | (24, 10) |
| catfish | Catfish | 7 | 360000 | 20 | 2 | (0.45, 0.42, 0.35) | (56, 18) |
| angelfish | Angelfish | 9 | 4900000 | 50 | 1 | (0.95, 0.95, 0.8) | (34, 34) |
| koi | Koi | 12 | 68000000 | 120 | 0 | (1, 0.35, 0.25) | (64, 24) |
| arowana | Arowana | 15 | 930000000 | 300 | 0 | (0.85, 0.75, 0.3) | (84, 22) |

Tests:
```gdscript
# test_species_catalog.gd
func test_has_eight_species_sorted_by_unlock_level():
	assert_eq(SpeciesCatalog.all().map(func(s): return s.unlock_level), [1, 2, 3, 5, 7, 9, 12, 15])
func test_ids_unique_and_lookup_works():  # 8 unique ids, by_id("koi").display_name == "Koi", by_id("shark") == null
func test_each_tier_earns_more_per_fish_and_costs_more():  # strictly increasing coins_per_sec and base_cost
func test_spec_values():  # guppy 10 / 0.5 / SURFACE, arowana 930000000 / 300

# test_number_format.gd
short(0.0)=="0"; short(0.5)=="0.5"; short(12.7)=="12"; short(999.0)=="999"
short(1000.0)=="1.0K"; short(1299.0)=="1.2K"; short(3.45e6)=="3.4M"
short(5.67e9)=="5.6B"; short(7.85e12)=="7.8T"; short(1.55e15)=="1550.0T"
```

- [ ] Step 1: Write tests → Step 2: run, expect FAIL (identifiers not declared) → Step 3: implement → Step 4: run, expect PASS → Step 5: commit `feat: add species data, balance constants and number formatting`.

---

### Task 3: Economy formulas

**Files:** Create `scripts/core/economy.gd`; test `tests/unit/test_economy.gd`.

**Interfaces (all static on `class_name Economy`):**
```
fish_cost(base_cost: float, owned: int) -> float            = base_cost * 1.15^owned
sell_refund(base_cost: float, owned: int) -> float          = 0 if owned<=0 else 0.5 * fish_cost(base_cost, owned-1)
food_multiplier(food_level: int) -> float                   = 1 + 0.25*level
income_per_sec(owned: Dictionary, species: Array[SpeciesData], food_level: int) -> float
capacity(pond_level: int) -> int                            = 10 + 5n
offline_cap_sec(deep_sleep_level: int) -> float             = 7200 + 7200n
offline_earnings(income: float, elapsed_sec: float, cap_sec: float) -> float = income * clamp(elapsed, 0, cap)
xp_to_next(level: int) -> float                             = 50 * 3.5^(level-1)
level_progress(total_xp: float) -> Dictionary               = {"level": int, "into": float, "needed": float}
upgrade_cost(id: String, level: int) -> float               = base_cost * growth^level
upgrade_maxed(id: String, level: int) -> bool
```

Tests (abridged; each is an assert in the test file):
```
fish_cost(10,0)=10; fish_cost(10,2)=13.225
sell_refund(10,0)=0; sell_refund(10,1)=5; sell_refund(10,3)=0.5*13.225
income({"guppy":4,"snail":2,"unknown":9}, all, 0)=4.5; with food 2 = 6.75
capacity(0)=10; capacity(3)=25; offline_cap_sec(0)=7200; offline_cap_sec(11)=86400
offline_earnings(2,100,7200)=200; (2,99999,7200)=14400; (2,-50,7200)=0
xp_to_next(1)=50; level_progress(0)={1,0,50}; level_progress(49.9).level=1; (50).level=2; (235) = level 3, into 10
upgrade_cost(pond,0)=100; (pond,2)=900; (food,1)=2000; (deep,1)=5000
upgrade_maxed(deep,10)=false; (deep,11)=true; (pond,500)=false
```

- [ ] Steps: failing test → FAIL → implement → PASS → commit `feat: add economy formulas`.

---

### Task 4: GameState autoload

**Files:** Create `scripts/autoload/game_state.gd`; modify `project.godot` `[autoload] GameState="*res://scripts/autoload/game_state.gd"`; test `tests/unit/test_game_state.gd` (instantiates the script directly with `autofree`).

**Interfaces (produces):**
- signals `changed`, `leveled_up(level: int)`, `species_first_bought(species_id: String)` (on 0→1)
- vars `coins, xp, lifetime_coins: float`, `owned: Dictionary` (id → int), `upgrades: Dictionary` (id → int), `running: bool` (income ticks in `_process` only when true)
- `reset()`, `level()`, `level_progress()`, `total_fish()`, `capacity()`, `income_per_sec()`, `offline_cap_sec()`
- `owned_count(s)`, `is_unlocked(s)`, `fish_cost(s)`, `sell_refund(s)`, `can_buy(s)`, `buy(s) -> bool`, `sell(s) -> bool`
- `upgrade_level(id)`, `upgrade_cost(id)`, `can_upgrade(id)`, `upgrade(id) -> bool`
- `earn(amount)` (adds to coins and lifetime), `apply_offline(elapsed_sec) -> float`
- `to_dict() -> Dictionary` (`coins, xp, lifetime_coins, owned, upgrades`), `load_dict(d)` (accepts JSON round-tripped floats; drops unknown species ids)
- Rules: spending coins adds the same XP; sell refunds are not lifetime earnings and keep XP.

Tests: new game (15 coins, Lv 1, 0 fish, cap 10); buy spends 10 and gives 10 XP, next cost 11.5; locked/unaffordable rejected; 11th fish rejected at cap 10; sell refunds 5 and keeps XP; 100-coin upgrade emits `leveled_up(2)` and unlocks snail; `species_first_bought` once for two buys; upgrades raise capacity/income, deep sleep maxes at 11 with 86400 s cap; offline capped at 7200 s and counted in lifetime, negative → 0; `to_dict` → JSON → `load_dict` round trip with ints restored and `shark` dropped.

- [ ] Steps: failing test → FAIL → implement → PASS → commit `feat: add GameState with buy, sell, upgrades and offline earnings`.

---

### Task 5: Balance simulation test

**Files:** Test `tests/unit/test_balance_simulation.gd`.

Drives the real `GameState`: 4 sessions/day of 60 × 10 s steps (shop greedily, then `earn(income*10)`), `apply_offline(3h50m)` between sessions and an extra 8 h at night. Greedy rule: buy Deep Sleep when it costs ≤ 25% of coins; otherwise take the action with the best income gain per coin among buying a fish (if not full), replacing the lowest-tier fish with a higher tier (if full; price = cost − refund), Better Food, and Pond Size (if full; value = top species income ÷ (pond cost + top fish cost)). Wait if the best action is unaffordable.

Assertions: `level2_at ∈ [1, 120] s`, `level15_at ∈ [3, 5] days`. Python prototype result: 60 s and 4.0 days. If out of band, retune data and spec together, never the bounds.

- [ ] Steps: write test → run, expect PASS with log `level 2 at ~60s, level 15 at ~4.0 days` → commit `test: add balance simulation for pacing targets`.

---

### Task 6: SaveCodec

**Files:** Create `scripts/core/save_codec.gd`; test `tests/unit/test_save_codec.gd`.

**Interfaces (static on `class_name SaveCodec`):**
```
CURRENT_VERSION := 1
encode(state: Dictionary, saved_at: float) -> String  # {"save_version", "saved_at", "state"}
decode(text: String) -> Dictionary                    # migrated envelope or {}
migrate(envelope: Dictionary) -> Dictionary           # {} if version > CURRENT_VERSION
from_cloud_rows(rows: Variant) -> Dictionary          # {"save_version", "state", "elapsed_seconds"} or {}
pick(local: Dictionary, cloud: Dictionary) -> String  # "local" | "cloud" | ""
offline_elapsed(source: String, local: Dictionary, cloud: Dictionary, now: float) -> float
```
Offline rule: cloud → `max(elapsed_seconds, 0)`; local → `max(now - saved_at, 0)`, capped by cloud `elapsed_seconds` when present; none → 0.

Tests: round trip; `""`, `"{not json"`, `"[1,2]"`, missing state, version 99 → `{}`; cloud rows `[]`/`null` → `{}`, row → state + elapsed; pick table (both empty "", only local, only cloud, higher wins, tie local); offline rules incl. clock-backwards → 0.

- [ ] Steps: failing test → FAIL → implement → PASS → commit `feat: add save codec with migration, merge and offline-time rules`.

---

### Task 7: SupabaseClient

**Files:** Create `scripts/net/supabase_client.gd`, `config/supabase.cfg` (`[supabase] url="" anon_key=""` with a comment: anon key only, never service_role); test `tests/unit/test_supabase_client.gd`.

**Interfaces (`class_name SupabaseClient extends Node`):**
- vars `url`, `anon_key`, `session: Dictionary` (`access_token, refresh_token, expires_at, user_id`), `session_path` (default `user://session.cfg`)
- `load_config(path)`, `is_configured()`, `is_signed_in()`
- coroutines returning `{"ok": bool, "code": int, "data": Variant, "error": String}`:
  - `ensure_session() -> bool`: not signed in → anonymous sign-in; expiring within 60 s → refresh; refresh rejected with 4xx → clear session and sign in as new guest; network failure → false
  - `sign_in_anonymously() -> bool` → `POST /auth/v1/signup {}`
  - `refresh_session()` → `POST /auth/v1/token?grant_type=refresh_token {"refresh_token"}`
  - `sign_in_with_password(email, password)` → `POST /auth/v1/token?grant_type=password`
  - `link_email(email)` → `PUT /auth/v1/user {"email"}` (Supabase sends a confirmation mail)
  - `set_password(password)` → `PUT /auth/v1/user {"password"}`
  - `get_user()` → `GET /auth/v1/user`
  - `sign_out()` → `POST /auth/v1/logout`, clears session
  - `save_game(state, save_version, lifetime_coins)` → `POST /rest/v1/rpc/save_game {"p_data","p_save_version","p_lifetime_coins"}`
  - `load_game()` → `POST /rest/v1/rpc/load_game {}`
- Headers: `apikey: <anon>`, `Authorization: Bearer <access_token or anon>`, `Content-Type: application/json`; `HTTPRequest.timeout = 10`.
- static `parse_response(result, code, body) -> Dictionary` (error text from `msg|message|error_description|error`, else `HTTP <code>`; non-success result → `network error <n>`), static `session_from_auth(data, now) -> Dictionary` (`{}` unless `access_token` present).

Tests: parse success / HTTP error message / empty 500 / network error; `session_from_auth` valid, error body, null; unconfigured vs configured client.

- [ ] Steps: failing test → FAIL → implement → PASS → commit `feat: add Supabase REST client for auth and save RPCs`.

---

### Task 8: SaveService + mock Supabase integration test

**Files:** Create `scripts/autoload/save_service.gd`, real `tests/mock_supabase.py`; modify `project.godot` autoload `SaveService`; tests `tests/unit/test_save_service.gd`, `tests/integration/test_cloud_sync.gd`.

**Interfaces (autoload `SaveService`):**
- signals `offline_earned(amount: float)`, `cloud_status_changed(status: String)` (`off|syncing|ok|error`)
- vars `client: SupabaseClient` (child created in `_ready`), `local_path`, `cloud_status`
- `start()` (coroutine, called once by Main): load local → `GameState.running = true` → start 10 s local / 60 s cloud timers, connect `species_first_bought` → if configured, `ensure_session` + `load_game` → `SaveCodec.pick` → load cloud state if chosen → `apply_offline(SaveCodec.offline_elapsed(...))` → `save_local()` → emit `offline_earned` if ≥ 1 → `sync_cloud()`
- `save_local()`, `read_local() -> Dictionary` (`{}` if missing or corrupt), `sync_cloud()` (skips if busy or unconfigured), `sign_in(email, password) -> Dictionary` (then merge by pick), `sign_out()` (reset to a new guest pond)
- `_notification`: on `APPLICATION_PAUSED`, `APPLICATION_FOCUS_OUT`, `WM_CLOSE_REQUEST` (after start) → save local + cloud.

Mock server (`tests/mock_supabase.py <port>`): in-memory; checks `apikey == "test-anon-key"`; implements signup, refresh-token grant (rotates tokens), password grant (always 400 `Invalid login credentials`), `rpc/save_game`, `rpc/load_game` (array of rows with `elapsed_seconds`).

Tests: local round trip + `saved_at ≈ now`; missing and corrupt files read `{}`; integration (pending if `MOCK_SUPABASE_URL` unset): guest sign-in → save → load round trip with elapsed ≥ 0; expired session refreshes to a new token; bad password error text.

- [ ] Steps: failing tests → FAIL → implement → PASS (integration not pending) → commit `feat: add SaveService with local save, cloud sync and merge`.

---

### Task 9: Supabase schema, RPCs and RLS tests

**Files:** Create `supabase/migrations/20261015000000_saves.sql`, `supabase/tests/auth_stub.sql`, `supabase/tests/saves_rls_test.sql`, `scripts/test_db.sh`.

Migration: `public.saves` exactly as spec section 4; RLS enabled; select/insert/update policies `to authenticated` on `auth.uid() = user_id`; `revoke all` from anon/authenticated then grant select/insert/update to authenticated; `save_game(p_data jsonb, p_save_version int, p_lifetime_coins double precision) returns timestamptz` (upsert, `updated_at = now()`), `load_game() returns table(data, save_version, lifetime_coins, updated_at, elapsed_seconds)`; both `security invoker`, `set search_path = ''`; execute revoked from `public, anon`, granted to `authenticated`.

Auth stub (local only): roles `anon`, `authenticated`; schema `auth` with `auth.users(id uuid pk)` and `auth.uid()` reading `request.jwt.claim.sub`.

RLS test (as role `authenticated`, sub switched per user): A saves twice and loads latest with elapsed ≥ 0; B loads 0 rows, selects 0 rows, updates 0 rows, cannot insert A's row; role `anon` cannot call `load_game`. Ends with `saves RLS tests passed`.

`scripts/test_db.sh`: `initdb` a temp cluster (via `runuser -u postgres` when root), start on a socket dir, create db, apply stub + migration + test with `ON_ERROR_STOP`, stop and delete on exit.

- [ ] Steps: write test + script → run, FAIL (migration missing) → write migration → run, PASS → commit `feat: add Supabase saves table, RPCs and RLS tests`.

---

### Task 10: Pond view

**Files:** Create `shaders/water.gdshader`, `scripts/pond/fish.gd`, `scripts/pond/pond_view.gd`; test `tests/unit/test_pond_view.gd`.

**Interfaces:**
- `pond_view.gd extends Control`: children water `ColorRect` (shader), decor `Control` (sand, 6 swaying seaweed strands, 2 rocks, drawn via its `draw` signal), fish `Node2D` layer, `CPUParticles2D` bubbles. Bands (fraction of height): surface 0.08–0.30, mid 0.36–0.62, bottom 0.74–0.86. Syncs fish on `GameState.changed` and on resize by diffing per species (no full rebuild).
- static `render_counts(owned: Dictionary, cap: int) -> Dictionary`: under cap → same counts (zeros dropped); over cap → each owned species gets `1 + floor(n * (cap - kinds) / total)`, leftover slots go to the largest species; sum == cap.
- `band_rect(zone: int) -> Rect2`
- `fish.gd extends Node2D`: `setup(s: SpeciesData, area: Rect2)`, var `band`; wanders to random targets in band, faces travel direction, bottom species 0.4× speed; draws sprite if set, else ellipse body + wiggling tail + eye.
- Shader: depth gradient (surface → deep), drifting light rays, wavy surface line.

Tests: under cap identical; `{"guppy":1000, 7 others:1}` with cap 40 → sum 40, every species ≥ 1, guppy > snail; zero counts skipped.

- [ ] Steps: failing test → FAIL → implement → PASS → commit `feat: add side-view pond with water shader, decor, bubbles and fish`.

---

### Task 11: UI + run checks

**Files:** Create `scenes/main.tscn` (root `Control` full rect + `main.gd`), `scripts/ui/{main,hud,shop_panel,upgrades_panel,account_panel}.gd`.

- `main.gd`: theme font size 26; `VBoxContainer`: HUD, pond (expand), `TabContainer` (min height 520) with Shop / Upgrades / Account; connects `offline_earned` to an `AcceptDialog` "Welcome back!"; calls `SaveService.start()`.
- `hud.gd`: coins (large), `+X/s`, `Lv N` + XP `ProgressBar`, cloud status text (`""`, `Syncing…`, `Saved`, `Offline`), level-up toast naming newly unlocked species; refresh every 0.1 s.
- `shop_panel.gd`: capacity line `Pond: n / cap fish`; per species: color swatch, name ×count and `+X/s each` (or `Unlocks at Lv N`), `Buy <cost>` (disabled unless `can_buy`), `Sell +<refund>`; refresh on `changed` and every 0.25 s.
- `upgrades_panel.gd`: per upgrade name (Lv n), effect text (`Capacity 10 → 15`, `Income x1.00 → x1.25`, `Offline earnings up to 2h → 4h`), `Upgrade <cost>` or `Max`.
- `account_panel.gd`: status (not configured / offline / guest / pending confirmation / signed in as), email + password fields, buttons Link email, Set password, Sign in, Sign out (disabled while busy), result message, note that sign-in keeps the pond with more coins.

Checks:
- [ ] Headless run: `godot --headless --quit-after 300` → no `SCRIPT ERROR` / `Parse Error` / `ERROR:` lines.
- [ ] Visual: `xvfb-run -s "-screen 0 720x1280x24" godot --rendering-driver opengl3 --write-movie <dir>/frame.png --fixed-fps 30 --quit-after 90` → last frame shows water, sand, seaweed, bubbles, HUD `15 coins`, Guppy `Buy 10` enabled, other species locked.
- [ ] `./run_tests.sh` still passes.
- [ ] Commit `feat: add HUD, shop, upgrades and account UI`.

---

### Task 12: Export presets, README, Web export verification

**Files:** Create `export_presets.cfg` (Web: no threads, PWA on, excludes `tests/*, addons/gut/*, supabase/*, docs/*`, path `build/web/index.html`; Android: `com.idlepond.game`, internet permission; iOS: bundle id `com.idlepond.game`, team id empty), `README.md` (requirements, run, tests, Supabase setup incl. enabling Anonymous sign-ins and running the migration, filling `config/supabase.cfg`, exporting per platform, tuning).

- [ ] Download 4.7.2 export templates (web templates only are needed for verification), `godot --headless --export-release Web build/web/index.html`.
- [ ] Serve `build/web` locally, open in Playwright Chromium, click Guppy's Buy button, screenshot. Expected: renders, no console errors, coins 15 → 5, `Pond: 1 / 10 fish`.
- [ ] Commit `chore: add export presets and README`, push.

---

## Spec coverage check

| Spec item | Task |
|---|---|
| Species data, 8 species, zones | 2 |
| Balance constants, upgrades table | 2, 3 |
| Economy formulas, offline, levels | 3 |
| New game 15 coins, buy/sell/capacity/upgrades, signals | 4 |
| Pacing targets | 5 |
| Save envelope, versioning, migration, merge, offline-time rule, corrupt save | 6, 8 |
| Supabase auth (guest, link email, password sign-in, refresh), RPCs, anon key only | 7 |
| Save cadence, startup flow, network failure never blocks | 8 |
| Table, RLS, RPCs, RLS tests | 9 |
| Side-view pond, 3 bands, water shader, bubbles, fish wander, render cap 40 | 10 |
| HUD 10×/s, Shop, Upgrades, Account, offline popup | 11 |
| Web/Android/iOS presets, Web smoke test | 12 |

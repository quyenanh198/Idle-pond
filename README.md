# Idle Pond

An idle game where you run your own pond. Fish earn coins (also while you are
away), coins buy more fish and pond upgrades, and spending coins levels you up
to unlock new species. Runs on the web, Android and iOS from one Godot project.

- Design: `docs/superpowers/specs/2026-10-13-idle-pond-design.md`
- Implementation plan: `docs/superpowers/plans/2026-10-15-idle-pond-mvp.md`

## Requirements

- [Godot 4.7.2](https://godotengine.org/download) (standard build, not .NET)
- For tests: Python 3, and PostgreSQL 16 binaries for the database tests

## Run

Open the folder in the Godot editor and press Play, or from a terminal:

```bash
godot --path .
```

Without Supabase configured the game saves locally only.

## Tests

```bash
./run_tests.sh        # GUT unit + integration tests (starts a mock Supabase server)
./scripts/test_db.sh  # applies the migration to a throwaway Postgres and checks RLS
```

`run_tests.sh` includes a balance simulation that fails if the economy drifts
from the pacing targets (first new species within 2 minutes, all 8 within
3–5 days of normal play).

## Cloud save (Supabase)

1. Create a project at [supabase.com](https://supabase.com).
2. Authentication > Sign In / Providers: enable **Anonymous sign-ins** and keep
   **Email** enabled.
3. Apply `supabase/migrations/20261015000000_saves.sql`, either in the SQL
   editor or with the Supabase CLI (`supabase link` then `supabase db push`).
4. Project Settings > API: copy the project URL and the **anon** public key into
   `config/supabase.cfg`:

   ```ini
   [supabase]
   url="https://YOUR-PROJECT.supabase.co"
   anon_key="YOUR-ANON-KEY"
   ```

   The anon key is safe to ship; row level security keeps each player's save
   private. **Never** put the `service_role` key in the game.

Players start as guests. In the Account tab they can link an email (Supabase
sends a confirmation link), then set a password and sign in on another device.
When two saves meet, the one with more lifetime coins is kept.

The economy is calculated on the device, so a player could edit their own
save. That is fine for a single-player game without leaderboards.

## Export

Install the 4.7.2 export templates (Editor > Manage Export Templates), then:

- **Web:** `godot --headless --export-release Web build/web/index.html`.
  Serve `build/web` over HTTPS from any static host. No special headers are
  needed (thread support is off).
- **Android:** install the Android SDK and set its path and a debug keystore in
  Editor Settings > Export > Android, then
  `godot --headless --export-release Android build/android/idle-pond.apk`.
  Use a release keystore for store builds.
- **iOS:** on macOS with Xcode, set your Apple team id in the iOS preset, then
  export and open the generated Xcode project.

## Project layout

| Path | What it is |
|---|---|
| `data/species/*.tres` | The 8 species (cost, coins/sec, unlock level, look) |
| `scripts/core/balance.gd` | Economy tuning numbers |
| `scripts/core/economy.gd` | Pure economy formulas |
| `scripts/core/save_codec.gd` | Save format, migrations, merge rule |
| `scripts/autoload/game_state.gd` | Player progress and actions (`GameState`) |
| `scripts/autoload/save_service.gd` | Local + cloud saving (`SaveService`) |
| `scripts/net/supabase_client.gd` | Supabase REST auth and RPC calls |
| `scripts/pond/` | Pond view and fish (placeholder art drawn in code) |
| `shaders/water.gdshader` | Water gradient, light rays, surface wave |
| `scripts/ui/` | HUD and Shop / Upgrades / Account panels |
| `supabase/` | Database migration and RLS tests |
| `tests/` | GUT tests and the mock Supabase server |

## Tuning and art

Change species in `data/species/*.tres` and global numbers in
`scripts/core/balance.gd`, then run `./run_tests.sh` to re-check pacing.
To use real art, set a species' `sprite` texture; fish draw it instead of the
placeholder shape.

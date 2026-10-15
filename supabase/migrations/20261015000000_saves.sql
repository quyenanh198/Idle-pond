-- One cloud save per user. The economy is client-authoritative (see spec section 4).
create table public.saves (
  user_id        uuid primary key references auth.users (id) on delete cascade,
  data           jsonb not null,
  save_version   int not null,
  lifetime_coins double precision not null default 0,
  updated_at     timestamptz not null default now()
);

alter table public.saves enable row level security;

create policy "saves_select_own" on public.saves
  for select to authenticated using (auth.uid() = user_id);
create policy "saves_insert_own" on public.saves
  for insert to authenticated with check (auth.uid() = user_id);
create policy "saves_update_own" on public.saves
  for update to authenticated using (auth.uid() = user_id) with check (auth.uid() = user_id);

revoke all on public.saves from anon, authenticated;
grant select, insert, update on public.saves to authenticated;

-- Upserts the caller's save; updated_at uses the server clock.
create function public.save_game(p_data jsonb, p_save_version int, p_lifetime_coins double precision)
returns timestamptz
language sql
security invoker
set search_path = ''
as $$
  insert into public.saves (user_id, data, save_version, lifetime_coins, updated_at)
  values (auth.uid(), p_data, p_save_version, p_lifetime_coins, now())
  on conflict (user_id) do update
    set data = excluded.data,
        save_version = excluded.save_version,
        lifetime_coins = excluded.lifetime_coins,
        updated_at = now()
  returning updated_at;
$$;

-- Returns the caller's save plus seconds since it was written (server clock).
create function public.load_game()
returns table (
  data jsonb,
  save_version int,
  lifetime_coins double precision,
  updated_at timestamptz,
  elapsed_seconds double precision
)
language sql
stable
security invoker
set search_path = ''
as $$
  select s.data, s.save_version, s.lifetime_coins, s.updated_at,
         extract(epoch from now() - s.updated_at)::double precision
  from public.saves s
  where s.user_id = auth.uid();
$$;

revoke execute on function public.save_game(jsonb, int, double precision) from public, anon;
revoke execute on function public.load_game() from public, anon;
grant execute on function public.save_game(jsonb, int, double precision) to authenticated;
grant execute on function public.load_game() to authenticated;

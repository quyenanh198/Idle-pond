-- Runs as the `authenticated` role with request.jwt.claim.sub set per user,
-- the same way PostgREST does. Any failed check raises and stops psql.
insert into auth.users (id) values
  ('11111111-1111-1111-1111-111111111111'),
  ('22222222-2222-2222-2222-222222222222');

set role authenticated;

-- User A saves twice (insert, then update).
select set_config('request.jwt.claim.sub', '11111111-1111-1111-1111-111111111111', false);
select public.save_game('{"coins": 1}'::jsonb, 1, 1);
select public.save_game('{"coins": 2}'::jsonb, 1, 2);
do $$
declare r record;
begin
  select * into r from public.load_game();
  if r.data->>'coins' <> '2' then raise exception 'A should load own latest save, got %', r.data; end if;
  if r.elapsed_seconds < 0 then raise exception 'elapsed must be >= 0'; end if;
end $$;

-- User B sees nothing of A and cannot change A's row.
select set_config('request.jwt.claim.sub', '22222222-2222-2222-2222-222222222222', false);
do $$
declare n int;
begin
  select count(*) into n from public.load_game();
  if n <> 0 then raise exception 'B must not load A''s save'; end if;
  select count(*) into n from public.saves;
  if n <> 0 then raise exception 'B must not select A''s row'; end if;
  update public.saves set lifetime_coins = 999 where user_id = '11111111-1111-1111-1111-111111111111';
  get diagnostics n = row_count;
  if n <> 0 then raise exception 'B must not update A''s row'; end if;
  begin
    insert into public.saves (user_id, data, save_version) values ('11111111-1111-1111-1111-111111111111', '{}', 1);
    raise exception 'B must not insert a row for A';
  exception when insufficient_privilege or unique_violation then null;
  end;
end $$;

-- Not signed in (anon role) cannot call the RPCs.
reset role;
set role anon;
do $$
begin
  begin
    perform public.load_game();
    raise exception 'anon must not call load_game';
  exception when insufficient_privilege then null;
  end;
end $$;
reset role;
select 'saves RLS tests passed' as result;

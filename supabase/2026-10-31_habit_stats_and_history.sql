-- TaskQuest: habit stats + check-in history
-- Run once in Supabase → SQL Editor. Safe to run again.

-- 1. Which stats each habit trains, e.g. {"str":0.5,"end":0.5}
alter table public.habits add column if not exists stats jsonb;

-- 2. One row per habit per day checked in (feeds the calendar and the stat totals).
--    habit_id matches the type of habits.id, whatever it is.
do $$
declare id_type text;
begin
  select data_type into id_type
  from information_schema.columns
  where table_schema = 'public' and table_name = 'habits' and column_name = 'id';

  execute format($f$
    create table if not exists public.habit_checkins (
      id         bigint generated always as identity primary key,
      user_id    uuid not null default auth.uid() references auth.users(id) on delete cascade,
      habit_id   %s references public.habits(id) on delete set null,  -- deleting a habit keeps its history and stats
      habit_name text,
      day        date not null,                                         -- the player's local day
      xp         integer not null default 0,
      gold       integer not null default 0,
      stats      jsonb,                                                 -- stat points earned, e.g. {"str":1.6,"end":1.6}
      created_at timestamptz not null default now()
    )$f$, case when id_type = 'uuid' then 'uuid' else 'bigint' end);
end $$;

create unique index if not exists habit_checkins_once_a_day on public.habit_checkins (habit_id, day);
create index        if not exists habit_checkins_user_day   on public.habit_checkins (user_id, day);

-- 3. Players can only see and change their own history
alter table public.habit_checkins enable row level security;

drop policy if exists "checkins: read own"   on public.habit_checkins;
drop policy if exists "checkins: add own"    on public.habit_checkins;
drop policy if exists "checkins: change own" on public.habit_checkins;
drop policy if exists "checkins: remove own" on public.habit_checkins;

create policy "checkins: read own"   on public.habit_checkins for select using (auth.uid() = user_id);
create policy "checkins: add own"    on public.habit_checkins for insert with check (auth.uid() = user_id);
create policy "checkins: change own" on public.habit_checkins for update using (auth.uid() = user_id) with check (auth.uid() = user_id);
create policy "checkins: remove own" on public.habit_checkins for delete using (auth.uid() = user_id);

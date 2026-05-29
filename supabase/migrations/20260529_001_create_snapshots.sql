-- snapshots: one row per (ticker, date), populated daily after KRX close
create table if not exists snapshots (
    ticker              text        not null,
    name                text,
    date                date        not null,
    close               numeric,
    volume              bigint,
    market_cap          bigint,
    foreign_net_buy     bigint,
    institution_net_buy bigint,
    sector              text,
    signal_score        numeric,
    grade               text,       -- S / A / B / C / D

    primary key (ticker, date)
);

-- read-only public access; writes go through service_role (pipeline)
alter table snapshots enable row level security;

create policy "public read-only"
    on snapshots
    for select
    to anon, authenticated
    using (true);

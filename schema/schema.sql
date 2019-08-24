\i drop_all.sql

drop domain if exists amount_type cascade;
create domain amount_type decimal(28, 8) not null check (value >= 0);

drop domain if exists order_value_type cascade;
create domain order_value_type decimal(24, 4) not null check (value >= 0);

drop domain if exists currency_type cascade;
create domain currency_type char(3) not null;

create table currencies (
    currency_code       currency_type primary key,
    name                varchar not null,
    is_crypto           bool not null
);

create table users (
    user_id             serial primary key,
    username            varchar not null unique,
    email               varchar not null unique
);

create table password_authentication (
    auth_id             serial primary key,
    user_id             int not null references users(user_id),
    password_hash       varchar not null
);

create table accounts (
    account_id          serial primary key,
    user_id             int not null references users(user_id),
    currency_code       currency_type references currencies(currency_code),
    balance             amount_type default 0,
    unique(user_id, currency_code)
);

create table sessions (
    session_id          serial primary key,
    user_id             int not null references users(user_id),
    session_key         bytea not null unique,
    created_at          timestamp not null default now(),
    last_updated_at     timestamp not null default now(),
    is_active           bool not null default true
);

create table password_login_attempts (
    was_successful      bool not null,
    auth_id             int references password_authentication(auth_id),
    session_id          int references sessions(session_id),
    attempt_time        timestamp not null default now()
);

drop type if exists event_type;
create type event_type as enum ('Deposit', 'Withdraw');

drop type if exists status_type;
create type status_type as enum (
    'Open', 'Processing', 'Closed', 'Cancelled'
);

drop type if exists order_enum_type;
create type order_enum_type as enum (
    'Buy', 'Sell'
);

create table account_events (
    account_event_id    serial primary key,
    account_id          int not null references accounts(account_id),
    event               event_type not null,
    amount              amount_type,
    status              status_type not null default 'Open',
    fee                 amount_type,
    timest              timestamp not null default now()
);

create table bitcoin_withdraws (
    account_event_id    int not null
                        references account_events(account_event_id),
    destination         varchar not null,
    transaction_id      varchar default null,
    when_processed      timestamp default null
);

create table bitcoin_deposits (
    account_event_id    int not null
                        references account_events(account_event_id),
    transaction_id      varchar not null,
    chain_index         int not null
);

create table orders (
    order_id            serial primary key,
    user_id             int not null references users(user_id),
    base_currency       currency_type references currencies(currency_code),
    quote_currency      currency_type references currencies(currency_code),
    -- price has 4 decimals after it
    price               order_value_type,
    -- and amount too, therefore result will have 8 decimals
    amount              order_value_type,
    status              status_type not null default 'Open',
    order_type          order_enum_type not null,
    created_at          timestamp not null default now()
);

-- used for cancelling an open order
create table order_events (
    event_id            serial primary key,
    order_id            int not null references orders(order_id),
    event_status        status_type not null,
    -- status of the order after applying the change
    order_status        status_type not null,
    created_at          timestamp not null default now()
);

-- if sell.timest < buy.timest:
--   price = max(sell.price, buy.price)
-- else
--   price = min(sell.price, buy.price)

-- amount = min(buy.amount, sell.amount)

create table trades (
    trade_id            serial primary key,
    trade_price         order_value_type,
    trade_amount        order_value_type,

    buy_id              int not null references orders(order_id),
    buy_fee             amount_type,

    sell_id             int not null references orders(order_id),
    sell_fee            amount_type,

    created_at          timestamp not null default now()
);

\i functions.sql

insert into currencies (currency_code, name, is_crypto) values
('BTC', 'Bitcoin', true),
('ETH', 'Ethereum', true),
('SYL', 'Syrian Lira', false),
('USD', 'US Dollar', false),
('EUR', 'Euro', false)
;

select create_user(
    'dino', 'dino@dino.com',
    '$5$rounds=535000$0IaXtxO0tCbOnADV$8fyofa5k3Ap1xLsWeGfNDXzH7U4QnxVR9xAM5.uWqe1'
);

select create_user(
    'zzz', 'zzz@zzz.com',
    '$5$rounds=535000$0IaXtxO0tCbOnADV$8fyofa5k3Ap1xLsWeGfNDXzH7U4QnxVR9xAM5.uWqe1'
);

update accounts set balance = 1000000;

select place_order(1, 'BTC', 'USD', 5785, 1, 'Sell');
select place_order(1, 'BTC', 'USD', 5783, 1, 'Sell');
select place_order(1, 'BTC', 'USD', 5782, 1, 'Sell');
select place_order(1, 'BTC', 'USD', 5781, 2, 'Sell');

select place_order(2, 'BTC', 'USD', 5784, 1, 'Buy');
select place_order(2, 'BTC', 'USD', 5783, 1, 'Buy');
select place_order(2, 'BTC', 'USD', 5782, 1, 'Buy');
select place_order(2, 'BTC', 'USD', 5781, 1, 'Buy');
select place_order(2, 'BTC', 'USD', 5780, 1, 'Buy');

insert into account_events (account_id, event, amount, fee)
values (2, 'Deposit', 100, 0);


drop function if exists create_user;
create function create_user (
    _username varchar, _email varchar, _password_hash varchar)
returns int as $$
    -- insert into users table
    -- use user_id to insert into password_authentication table too
    with insert_1 as (
        insert into users (username, email)
        values ($1, $2)
        on conflict (username) do nothing
        returning user_id
    ), insert_2 as (
        insert into password_authentication (user_id, password_hash)
        select user_id, $3 from insert_1
    )
    insert into accounts (user_id, currency_code)
    select user_id, currency_code from insert_1, currencies
    returning user_id;
$$ language sql;

drop function if exists login;
create function login (_auth_id int, _session_key bytea) returns void as $$
    with insert_1 as (
        insert into sessions (user_id, session_key)
        select user_id, $2
        from password_authentication
        where auth_id = $1
        returning session_id
    )
    insert into password_login_attempts (was_successful, auth_id, session_id)
    select true, $1, session_id from insert_1;
$$ language sql;

drop type if exists place_order_result cascade;
create type place_order_result as (
    deduct_currency currency_type,
    deduct_amount amount_type
);

drop function if exists place_order;
create function place_order(_user_id int,
    _base_currency currency_type, _quote_currency currency_type,
    _price order_value_type, _amount order_value_type,
    _order_type order_enum_type)
returns place_order_result as $$
declare
    deduct_currency currency_type = 'BTC';
    deduct_amount amount_type = '0';
begin
    if _order_type = 'Buy' then
        deduct_currency = _quote_currency;
        deduct_amount = _price * _amount;
    else
        deduct_currency = _base_currency;
        deduct_amount = _amount;
    end if;

    raise notice 'Deducting % % from user(%)',
        deduct_amount, deduct_currency, _user_id;

    update accounts
    set balance = balance - deduct_amount
    where user_id = _user_id and currency_code = deduct_currency;

    insert into orders (
        user_id, quote_currency, base_currency, price, amount, order_type
    ) values (
        _user_id, _quote_currency, _base_currency, _price, _amount, _order_type
    );

    return (deduct_currency, deduct_amount);
end
$$ language plpgsql;

drop function if exists make_withdraw_bitcoin_request;
create function make_withdraw_bitcoin_request(
    user_id int, bitcoin_address varchar, amount amount_type, fee amount_type)
returns void as $$
    with update_1 as (
        update accounts
        set balance = balance - amount - fee
        where user_id = $1 and currency_code = 'BTC'
        returning account_id
    ), insert_1 as (
        insert into account_events (account_id, event, amount, fee)
        select account_id, 'Withdraw', $3, $4 from update_1
        returning account_event_id
    )
    insert into bitcoin_withdraws (account_event_id, destination)
    select account_event_id, $2 from insert_1;
$$ language sql;

drop function if exists current_bitcoin_chain_index;
create function current_bitcoin_chain_index(user_id int) returns int as $$
    with account as (
        select account_id
        from accounts
        where user_id = $1 and currency_code = 'BTC'
    ), event as (
        select account_event_id
        from account_events
        join account
        on account_events.account_id = account.account_id
        where event = 'Deposit'
    )
    select coalesce(max(chain_index), 0)
    from bitcoin_deposits
    join event
    on bitcoin_deposits.account_event_id = event.account_event_id;
$$ language sql;


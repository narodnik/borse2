drop function if exists remaining_amount;
create function remaining_amount(order_id int) returns order_value_type as $$
    with order_select as (
        select amount as order_amount, order_type
        from orders where order_id = $1
    ),
    trades_sum as (
        select coalesce(sum(trade_amount), 0) as total_traded
        from trades
        where 
            case (select order_type from order_select)
                when 'Buy' then buy_id = $1
                when 'Sell' then sell_id = $1
            end
    )
    select cast(order_amount - total_traded as order_value_type)
    from order_select, trades_sum
$$ language sql;

drop function if exists update_balance_if_closed_order;
create function update_balance_if_closed_order(
    _order_id int, _user_id int, _currency_code currency_type)
returns void as $$
declare
    order_status status_type;
    _order_type order_enum_type;
    total_traded amount_type = '0';
begin
    select status, order_type into order_status, _order_type
    from orders
    where order_id = _order_id;

    if order_status != 'Closed' then
        return;
    end if;

    if _order_type = 'Buy' then
        select sum(trade_amount) into total_traded
        from trades
        where buy_id = _order_id;
    else
        select sum(trade_amount * trade_price) into total_traded
        from trades
        where sell_id = _order_id;
    end if;

    raise notice 'Updating balance % % % %',
        _order_id, _user_id, _currency_code, total_traded;

    update accounts
    set balance = balance + total_traded
    where user_id = _user_id and currency_code = _currency_code;
end
$$ language plpgsql;

drop function if exists match_one_order;
create function match_one_order() returns varchar as $$
declare
    match record;
    order_ids int[];
    trade_price order_value_type = 0;
    trade_amount order_value_type = 0;
begin
    with buy_order as (
        select * from orders
        where order_type = 'Buy' and
            status = 'Open'
        order by price desc limit 1
    )
    select
        buy_order.base_currency as base_currency,
        buy_order.quote_currency as quote_currency,

        buy_order.order_id as buy_order_id,
        buy_order.user_id as buy_user_id,
        buy_order.price as buy_price,
        buy_order.created_at as buy_created_at,

        sell_orders.order_id as sell_order_id,
        sell_orders.user_id as sell_user_id,
        sell_orders.price as sell_price,
        sell_orders.created_at as sell_created_at
    from buy_order, orders as sell_orders
    into match
    where
        sell_orders.order_type = 'Sell' and
        sell_orders.price <= buy_order.price and
        sell_orders.base_currency = buy_order.base_currency and
        sell_orders.quote_currency = buy_order.quote_currency and
        sell_orders.status = 'Open'
    order by sell_orders.price asc limit 1;

    if match is null then
        return null;
    end if;

    order_ids = array[match.buy_order_id, match.sell_order_id];

    update orders
    set status = 'Processing'
    where order_id = any(order_ids);

    if match.sell_created_at < match.buy_created_at then
        trade_price = greatest(match.buy_price, match.sell_price);
    else
        trade_price = least(match.buy_price, match.sell_price);
    end if;

    trade_amount = least(
        remaining_amount(match.buy_order_id),
        remaining_amount(match.sell_order_id));

    insert into trades (
        trade_price, trade_amount, buy_id, buy_fee, sell_id, sell_fee
    ) values (
        trade_price, trade_amount, match.buy_order_id, 0,
        match.sell_order_id, 0);

    update orders
    set status = 'Closed'
    where
        order_id = any(order_ids) and remaining_amount(order_id) = 0;

    perform update_balance_if_closed_order(
        match.buy_order_id, match.buy_user_id, match.base_currency);

    perform update_balance_if_closed_order(
        match.sell_order_id, match.sell_user_id, match.quote_currency);

    update orders
    set status = 'Open'
    where order_id = any(order_ids) and status = 'Processing';

    raise notice 'price % @ % (%)', trade_amount, trade_price, match;

    return json_build_object(
        'price', trade_price, 'amount', trade_amount,
        'base', match.base_currency, 'quote', match.quote_currency
    );
end
$$ language plpgsql;


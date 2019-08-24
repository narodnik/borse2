-- this should be cached in a special table
-- fetch day of last trade, generate ticker info up to day before

drop function if exists query_ticker_info;
create function query_ticker_info(base currency_type, quote currency_type)
returns json as $$
    with filtered_trades as (
        select trade_price, trades.created_at as created_at from trades
        join orders on buy_id = order_id
        where base_currency = base and quote_currency = quote
    ), limits as (
        select
            min(trade_price) as low_price,
            max(trade_price) as high_price,
            date_trunc('day', created_at) as limits_daily
        from filtered_trades
        group by limits_daily
        order by limits_daily
    ), open as (
        select distinct on (open_daily)
            low_price,
            high_price,
            trade_price as open_price,
            date_trunc('day', created_at) as open_daily
        from filtered_trades
        join limits on limits_daily = date_trunc('day', created_at)
        order by open_daily, created_at asc
    ), close as (
        select distinct on (daily)
            low_price::varchar,
            high_price::varchar,
            open_price::varchar,
            trade_price::varchar as close_price,
            date_trunc('day', created_at) as daily
        from filtered_trades
        join open on open_daily = date_trunc('day', created_at)
        order by daily, created_at desc
    )
    select array_to_json(array_agg(row_to_json(close)))
    from close;
$$ language sql;


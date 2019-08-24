import bitcoin_api

assert not bitcoin_api.is_valid_address('hello')
assert bitcoin_api.is_valid_address('1M4wHdskSyJAXNJpE92fS6dT3K8w1kKpCw')

print(bitcoin_api.get_address(0, 110))


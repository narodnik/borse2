import decimal
import borse.bitcoin_api
import borse.utility

def is_valid_numeric_type(numeric, precision):
    if not isinstance(numeric, str):
        return False
    try:
        value = decimal.Decimal(numeric)
    except decimal.InvalidOperation:
        return False
    return borse.utility.decimal_has_correct_precision(value, precision)

def is_valid_email(email_address):
    return (isinstance(email_address, str) and
            borse.utility.is_email(email_address))

def is_valid_public_key(public_key):
    return (isinstance(public_key, str) and
            borse.utility.is_hex(public_key, 32))

def is_valid_currency_code(currency_code):
    return (isinstance(currency_code, str) and len(currency_code) == 3 and
            currency_code.isupper() and currency_code.isalpha())

def is_valid_order_value(order_value):
    return is_valid_numeric_type(order_value, 4)

def is_valid_order_type(order_type):
    return (isinstance(order_type, str) and order_type in ('Buy', 'Sell'))

def is_valid_bitcoin_address(bitcoin_address):
    return (isinstance(bitcoin_address, str) and
            borse.bitcoin_api.is_valid_address(bitcoin_address))

def is_valid_amount(amount):
    return is_valid_numeric_type(amount, 8)

class RequestBase:

    def __init__(self, command, ident):
        self.command = command
        self.id = ident

    def _check_spec(self, params, spec):
        if len(params) != len(spec):
            return False

        for param, type_spec in zip(params, spec):
            if isinstance(type_spec, type):
                if not isinstance(param, type_spec):
                    return False
            elif type_spec == 'email':
                if not is_valid_email(param):
                    return False
            elif type_spec == 'public_key':
                if not is_valid_public_key(param):
                    return False
            elif type_spec == 'currency_code':
                if not is_valid_currency_code(param):
                    return False
            elif type_spec == 'order_value':
                if not is_valid_order_value(param):
                    return False
            elif type_spec == 'order_type':
                if not is_valid_order_type(param):
                    return False
            elif type_spec == 'bitcoin_address':
                if not is_valid_bitcoin_address(param):
                    return False
            elif type_spec == 'amount':
                if not is_valid_amount(param):
                    return False

        return True


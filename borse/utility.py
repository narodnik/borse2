import decimal
import re
import string
import sys

def eprint(*args, **kwargs):
    print('error:', *args, file=sys.stderr, **kwargs)

def is_hex(hex_string, length):
    return (len(hex_string) == length * 2 and
            all(character in string.hexdigits for character in hex_string))

email_regex = re.compile(r"[^@]+@[^@]+\.[^@]+")
def is_email(email_address):
    return email_regex.fullmatch(email_address) is not None

def decimal_has_correct_precision(value, precision):
    pennies = decimal.Decimal('10') ** -precision
    return value.quantize(pennies) == value


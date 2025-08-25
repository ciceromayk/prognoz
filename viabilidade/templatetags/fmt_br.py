from django import template

register = template.Library()

def fmt_br(value):
    try:
        value = float(value)
        return f"{value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except (ValueError, TypeError):
        return value


def div(value, arg):
    try:
        return float(value) / float(arg) if float(arg) != 0 else 0
    except (ValueError, TypeError, ZeroDivisionError):
        return 0

def mul(value, arg):
    try:
        return float(value) * float(arg)
    except (ValueError, TypeError):
        return 0


def get_item(dictionary, key):
    try:
        return dictionary.get(key)
    except AttributeError:
        return ''

register.filter('fmt_br', fmt_br)
register.filter('div', div)
register.filter('mul', mul)
register.filter('get_item', get_item)

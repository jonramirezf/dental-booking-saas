# ============================================================
# ARCHIVO 7/7 — agenda/templatetags/agenda_extras.py
# UBICACIÓN:   agenda/templatetags/agenda_extras.py  (archivo NUEVO)
# Crea también:  agenda/templatetags/__init__.py  (vacío)
# ============================================================
from django import template

register = template.Library()

@register.filter
def get_item(dictionary, key):
    return dictionary.get(key)

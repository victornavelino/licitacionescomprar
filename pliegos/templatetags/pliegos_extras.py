from django import template

register = template.Library()


@register.filter
def get_item(item: dict, key: str):
    return item.get(key)

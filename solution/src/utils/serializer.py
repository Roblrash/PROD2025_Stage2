from sqlalchemy.orm import class_mapper
from uuid import UUID

def to_dict(obj):
    """
    Переводит в формат dict
    """
    return {column.name: getattr(obj, column.name) for column in class_mapper(obj.__class__).columns}

def uuid_to_str(value):
    """
    Переводит UUID в формат str
    """
    if isinstance(value, UUID):
        return str(value)
    return value

def remove_none_values(data):
    """
    Удаляет все параметры None из JSON
    """
    if isinstance(data, dict):
        return {k: remove_none_values(v) for k, v in data.items() if v is not None}
    elif isinstance(data, list):
        return [remove_none_values(item) for item in data if item is not None]
    else:
        return data

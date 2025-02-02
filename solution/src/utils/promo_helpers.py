from datetime import datetime, date
from src.models.promocode import PromoCode

def calculate_active(promo: PromoCode) -> bool:
    current_date = datetime.utcnow().date()
    active_from = promo.active_from or date.min
    active_until = promo.active_until or date.max
    if current_date < active_from or current_date > active_until:
        return False
    if promo.mode == "COMMON" and promo.used_count >= promo.max_count:
        return False
    if promo.mode == "UNIQUE" and not promo.promo_unique:
        return False
    return True

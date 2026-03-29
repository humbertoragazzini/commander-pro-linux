def validate_fan_number(fan_id: int) -> bool:
    return 1 <= fan_id <= 6

def validate_fan_speed(speed: int) -> bool:
    return 0 <= speed <= 100

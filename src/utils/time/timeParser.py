import re

TIME_UNITS = {
    "초": 1,
    "s": 1,
    "sec": 1,
    "분": 60,
    "m": 60,
    "min": 60,
    "시간": 3600,
    "h": 3600,
    "hr": 3600,
    "일": 86400,
    "d": 86400,
    "day": 86400,
}


def parse_time_string(time_str):
    match = re.match(r"(\d+)\s*([a-zA-Z가-힣]+)", time_str)
    if not match:
        return None
    value, unit = match.groups()
    value = int(value)
    unit = unit.lower()
    for k, v in TIME_UNITS.items():
        if unit.startswith(k):
            return value * v
    return None

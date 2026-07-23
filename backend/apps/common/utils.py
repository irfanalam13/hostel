import datetime as dt

def month_key(date_obj: dt.date) -> str:
    return f"{date_obj.year:04d}-{date_obj.month:02d}"

def parse_month_key(key: str) -> dt.date:
    y, m = key.split("-")
    return dt.date(int(y), int(m), 1)
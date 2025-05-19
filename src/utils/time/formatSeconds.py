
def format_seconds(seconds):
    if seconds % 86400 == 0:
        return f"{seconds // 86400}일"
    elif seconds % 3600 == 0:
        return f"{seconds // 3600}시간"
    elif seconds % 60 == 0:
        return f"{seconds // 60}분"
    else:
        return f"{seconds}초"

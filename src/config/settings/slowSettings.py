SLOW_TIMES = [
    ((lambda h, m: (h == 8 and m > 40) or (h == 9 and m < 30)), "1"),
    ((lambda h, m: (h == 9 and m > 40) or (h == 10 and m < 30)), "2"),
    ((lambda h, m: (h == 10 and m > 40) or (h == 11 and m < 30)), "3"),
    ((lambda h, m: (h == 11 and m > 40) or (h == 12 and m < 30)), "4"),

    ((lambda h, m: (h == 13 and m > 30) or (h == 14 and m < 20)), "5"),
    ((lambda h, m: (h == 14 and m > 30) or (h == 15 and m < 20)), "6"),
    ((lambda h, m: (h == 15 and m > 30) or (h == 16 and m < 20)), "7"),

    ((lambda h, m: (h == 16 and m > 40) or (h == 17 and m < 30)), "8"),
    ((lambda h, m: (h == 17 and m > 40) or (h == 18 and m < 30)), "9"),

    ((lambda h, m: (h == 19 and m > 30) or (h == 20 and m < 20)), "10"),
    ((lambda h, m: (h == 20 and m > 30) or (h == 21 and m < 20)), "11"),
]

from datetime import datetime, timedelta


def calculate_easter(year):
    """Calcola la data di Pasqua usando l'algoritmo di Meeus/Jones/Butcher"""
    a = year % 19
    b = year // 100
    c = year % 100
    d = b // 4
    e = b % 4
    f = (b + 8) // 25
    g = (b - f + 1) // 3
    h = (19 * a + b - d - g + 15) % 30
    i = c // 4
    k = c % 4
    l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    month = (h + l - 7 * m + 114) // 31
    day = ((h + l - 7 * m + 114) % 31) + 1
    return datetime(year, month, day)


def generate_easter_dates(start_year=2000, end_year=2051):
    """Genera le date di Pasqua e Pasquetta per un range di anni"""
    easter_dates = {}
    for year in range(start_year, end_year):
        easter = calculate_easter(year)
        easter_monday = easter + timedelta(days=1)
        easter_dates[year] = (easter, easter_monday)
    return easter_dates
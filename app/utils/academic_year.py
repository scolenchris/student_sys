from datetime import datetime


ACADEMIC_YEAR_START_MONTH = 9


def get_default_academic_year(now=None):
    current = now or datetime.now()
    return (
        current.year
        if current.month >= ACADEMIC_YEAR_START_MONTH
        else current.year - 1
    )

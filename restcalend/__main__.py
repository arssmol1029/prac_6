"""
Prints a calendar in reStructuredText format.
"""

import calendar
import sys


MONTH_NAMES = {
    1: "January",
    2: "February",
    3: "March",
    4: "April",
    5: "May",
    6: "June",
    7: "July",
    8: "August",
    9: "September",
    10: "October",
    11: "November",
    12: "December",
}


def rst_calendar(year: int, month: int) -> str:
    """
    Returns a calendar in reStructuredText format.
    """
    calendar_rst = f".. table:: {MONTH_NAMES[month]} {year}\n\n"
    calendar_rst += "    == == == == == == ==\n"
    calendar_rst += "    Mo Tu We Th Fr Sa Su\n"
    calendar_rst += "    == == == == == == ==\n"

    for week in calendar.monthcalendar(year, month):
        calendar_rst += "    "
        for day in week:
            if day == 0:
                calendar_rst += r"\  "
            else:
                calendar_rst += f"{day:2d} "
        calendar_rst += "\n"

    calendar_rst += "    == == == == == == =="
    return calendar_rst


def main():
    year = int(sys.argv[1])
    month = int(sys.argv[2])

    print("CALENDAR\n", "========\n\n", rst_calendar(year, month), sep="")

if __name__ == "__main__":
    main()
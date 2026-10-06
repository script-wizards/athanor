/* planetary.c: which planet rules the hour, as athanor reckons it. */
#include <stdio.h>
#include <time.h>

/* Chaldean order, slowest planet to swiftest */
static const char *CHALDEAN[] = {
    "Saturn", "Jupiter", "Mars", "Sun", "Venus", "Mercury", "Moon",
};

/* CHALDEAN index ruling each weekday's first hour, Sunday first */
static const int DAY_RULER[] = { 3, 6, 2, 5, 1, 4, 0 };

/* Twelve unequal hours of daylight, then twelve of darkness. */
static const char *planetary_hour(time_t now, time_t rise, time_t set,
                                  time_t next_rise, int weekday)
{
    int day = now >= rise && now < set;
    time_t start = day ? rise : set;
    double span = (double)((day ? set : next_rise) - start) / 12;
    int hour = (int)((now - start) / span) + (day ? 0 : 12);
    return CHALDEAN[(DAY_RULER[weekday] + hour) % 7];
}

static time_t at(int hour, int min, int mday)
{
    struct tm t = { .tm_year = 126, .tm_mon = 9, .tm_mday = mday,
                    .tm_hour = hour, .tm_min = min, .tm_isdst = -1 };
    return mktime(&t);
}

int main(void)
{
    /* Jersey City, Monday the 5th of October 2026 */
    time_t rise = at(7, 4, 5), set = at(18, 34, 5), next = at(7, 5, 6);
    printf("hour of %s\n", planetary_hour(at(22, 12, 5), rise, set, next, 1));
    return 0;
}

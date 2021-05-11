# -*- coding: utf-8 -*-


def A():
    return lambda publication: True


def YEAR_RANGE(start, end=None):
    if end is None:
        return lambda publication: start <= publication.year
    else:
        return lambda publication: start <= publication.year and publication.year < end


class GPConfig:
    DB_PATH = "./gp.db"
    DBLP_PIDS = (
        (
            "92/7397",  # Martin Albrecht
            lambda publication: (
                publication.year in (2008, 2009, 2010) or publication.year >= 2015
            ),
        ),
    )
    OUTPUTS = (("output/list-of-publications.md", "templates/list-of-publications.md"),)

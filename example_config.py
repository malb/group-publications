# -*- coding: utf-8 -*-
from db import Publication


def A():
    return lambda publication: True


def YEAR_RANGE(start, end=None):
    if end is None:
        return lambda publication: start <= publication.year
    else:
        return lambda publication: start <= publication.year and publication.year < end


class GPConfig:
    DB_PATH = "gp.db"
    DBLP_PIDS = (
        (
            "92/7397",  # Martin Albrecht
            lambda publication: (
                publication.year in (2008, 2009, 2010) or publication.year >= 2015
            ),
        ),
        (
            "19/2372",  # Carlos Cid
            YEAR_RANGE(2003, None),
        ),
        (
            "158/7281",  # Rachel Player
            A(),
        ),
    )
    OUTPUTS = (
        (
            "output/list-of-publications.md",
            "templates/list-of-publications.md",
            lambda query: query,
        ),
        (
            "output/list-of-publications-no-preprints.md",
            "templates/list-of-publications.md",
            lambda query: query.filter(Publication.type != "informal"),
        ),
    )

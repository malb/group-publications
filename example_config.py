# -*- coding: utf-8 -*-
from db import Publication


class GPConfig:
    # database file
    DB_PATH = "gp.db"

    # the main source of DBLP PIDs
    DBLP_PID_CSV = "example.csv"

    # manually add DBLP_PIDs with arbitrary predicates
    #  DBLP_PIDS = (
    #   (
    #        "92/7397",  # Martin Albrecht
    #        lambda publication: (
    #            publication.year in (2008, 2009, 2010) or publication.year >= 2015
    #        ),
    #    ),
    MANUAL_DBLP_PIDS = ()

    # output filename, template filename, filter callable
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

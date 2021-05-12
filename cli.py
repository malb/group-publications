#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
"""
import click
from db import Publication
from gp import update_from_dblp, render_templates, session
import logging
from sqlalchemy import or_


@click.group()
def gp():
    "Maintaining a list of publications for a group of people."
    pass


@gp.command()
@click.option("--test", help="Do not commit results to dataase", type=bool, default=False)
@click.option(
    "--loglvl",
    help="Level of verbosity",
    type=click.Choice(["DEBUG", "INFO", "WARNING"], case_sensitive=False),
    default="INFO",
)
def pull(test, loglvl):
    """
    Pull data from DBLP.

    :param test: Do not actually write the data to disk
    :param loglvl: Verbosity level

    """

    logging.basicConfig(level=loglvl, format="%(message)s")
    update_from_dblp(commit=not test)


@gp.command()
@click.option(
    "--loglvl",
    help="Level of verbosity",
    type=click.Choice(["DEBUG", "INFO", "WARNING"], case_sensitive=False),
    default="INFO",
)
def push(loglvl):
    """
    Write database to outputs given in `GPConfig.OUTPUTS`.

    :param loglvl: Verbosity level

    """

    logging.basicConfig(level=loglvl, format="%(message)s")
    render_templates()


@gp.command()
@click.option(
    "--loglvl",
    help="Level of verbosity",
    type=click.Choice(["DEBUG", "INFO", "WARNING"], case_sensitive=False),
    default="INFO",
)
def sync(loglvl):
    """
    Pull & push.

    :param loglvl: Verbosity level

    """
    logging.basicConfig(level=loglvl, format="%(message)s")
    pull()
    push()


@gp.command()
@click.argument("dblp_key", type=str)
def toggle(dblp_key):
    """
    Toggle visibility of entry given by `dblp_key`.
    """

    Publication.toggle_visibility(session, dblp_key, commit=True)


@gp.command()
@click.argument("years", nargs=-1, type=int)
@click.option("--preprints/--no-preprints", default=True)
def show(years, preprints):
    """
    Show publications.

    :param years: restrict to these years
    :param preprints: include preprints

    """
    query = session.query(Publication).filter(Publication.visible).order_by(Publication.year.desc())
    if not preprints:
        query = query.filter(Publication.type != "informal")
    if years:
        query = query.filter(or_(Publication.year == year for year in years))
    publications = query.all()

    for publication in publications:
        print("- %s" % str(publication), end="\n\n")


if __name__ == "__main__":
    gp()

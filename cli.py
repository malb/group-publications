#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
"""
import click
from gp import Publication, update_from_dblp, render_templates
import logging


@click.group()
def gp():
    "Maintaining a list of publications for a group of people"
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
    logging.basicConfig(level=loglvl, format="%(message)s")
    update_from_dblp(commit=not test)


@gp.command()
@click.option(
    "--preprints",
    help="Include pre-prints",
    type=bool,
    default=True,
)
@click.option(
    "--loglvl",
    help="Level of verbosity",
    type=click.Choice(["DEBUG", "INFO", "WARNING"], case_sensitive=False),
    default="INFO",
)
def push(preprints, loglvl):
    logging.basicConfig(level=loglvl, format="%(message)s")
    render_templates(skip_informal=not preprints)


@gp.command()
@click.argument("dblp_key", type=str)
def toggle(dblp_key):
    Publication.toggle_visibility(dblp_key, commit=True)


if __name__ == "__main__":
    gp()

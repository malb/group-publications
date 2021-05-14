# -*- coding: utf-8 -*-
from config import GPConfig
from db import Base, Author, Publication
from functools import partial
from jinja2 import Template
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
import csv
import logging
import re
import requests
import xml.etree.ElementTree as ET


def year_ranges(publication, pairs):
    """
    predicate that accepts if publication is in one of the (start, end) year pairs.

    Pairs format:

    - The empty list means: accept all
    - `(2003, None)` means: all from 2003 (inclusive)
    - `(2003, 2005)` means: all between 2003 and 2005 (endpoints inclusive)

    :param publication:
    :param pairs: pairs of start, end (inclusive)
    :returns:

    """
    if publication.visibility is not None:
        return publication.visibility

    # we treat an empty list as "accept all" instead of "reject all"
    if not pairs:
        return True

    for start, end in pairs:
        if end and start <= publication.year and publication.year <= end:
            return True
        elif start <= publication.year:
            return True
    return False


def dblp_pids():
    """
    Return all DBLP PIDs according to `GPConfig`

    :returns: list of pairs: (dblp pid, predicate)

    """
    _dblp_pids = []
    with open("gp.csv", "r") as fh:
        reader = csv.reader(fh)
        next(reader, None)  # skip the headers
        for row in reader:
            dblp_pid, name = row[:2]
            pairs = []
            years = iter(row[2:])
            for start in years:
                if not start:
                    break
                start = int(start)
                end = next(years)
                if end:
                    end = int(end)
                else:
                    end = None
                pairs.append((start, end))
            _dblp_pids.append((dblp_pid, partial(year_ranges, pairs=pairs)))
    _dblp_pids.extend(GPConfig.MANUAL_DBLP_PIDS)
    return _dblp_pids


def dblp_fetch(pid):
    """
    Fetch https://dblp.uni-trier.de/pid/{pid}.xml

    :param pid: DBLP pid
    :returns:  `xml.etree.ElementTree`

    """

    url = "https://dblp.uni-trier.de/pid/{pid}.xml".format(pid=pid)
    r = requests.get(url)
    if r.status_code != 200:
        raise RuntimeError(
            "Request returned status code {status_code}".format(status_code=r.status_code)
        )
    root = ET.fromstring(r.text)
    return root


def dblp_parse(root):
    """
    Parse DBLP XML

    :param root: `xml.etree.ElementTree` output of `dblp_fetch`
    :returns: a list of `Publication`s

    """

    publications = []

    for child in root:
        if not child.tag == "r":
            continue

        publication = list(child)[0]

        dblp_key = publication.attrib["key"]

        publication_type = None
        if publication.tag == "article":
            if "publtype" in publication.attrib and publication.attrib["publtype"] == "informal":
                publication_type = "informal"
            else:
                publication_type = "article"
        elif publication.tag in (
            "informal",
            "inproceedings",
            "incollection",
            "article",
            "phdthesis",
            "proceedings",
            "book",
        ):
            publication_type = publication.tag
        else:
            raise ValueError(
                "Type of publication for '%s' not understood" % ET.tostring(publication)
            )

        author_tag = "editor" if publication_type in ("proceedings",) else "author"

        authors = []
        for author in publication.findall(author_tag):
            author_name = author.text
            # Foo Bar 0001 is a thing on DBLP
            author_name = re.match("([^0-9]*)([0-9]+)?", author_name).group(1).strip()
            authors.append(Author.from_dblp_pid(session, author.attrib["pid"], author_name))

        # many-to-many relations don't preserve order but author order can matter so we store it manually
        author_order = Publication.author_orderf(authors)

        title = publication.findtext("title")
        if title.endswith("."):
            title = title[:-1]

        year = int(publication.findtext("year"))
        url = publication.findtext("ee")
        dblp_url = publication.findtext("url")
        pages = publication.findtext("pages", "")

        if publication_type in ("article", "informal"):
            venue = publication.findtext("journal")
        elif publication_type == "inproceedings":
            venue = publication.findtext("booktitle")
        elif publication_type == "incollection":
            venue = publication.findtext("booktitle")
        elif publication.tag == "phdthesis":
            venue = publication.findtext("school")
        elif publication.tag == "book":
            venue = publication.findtext("publisher")
        elif publication.tag == "proceedings":
            venue = publication.findtext("publisher")
        else:
            raise ValueError(
                "Type of publication for '%s' not understood when parsing for venue"
                % ET.tostring(publication)
            )

        volume = publication.findtext("volume", "")
        number = publication.findtext("number", "")
        # IACR ePrint is so important to us we treat is specially
        if venue == "IACR Cryptol. ePrint Arch.":
            number = re.match("http(s)?://eprint.iacr.org/([0-9]{4})/([0-9]+)", url).group(3)

        publications.append(
            # get it from DB if it exists, otherwise create new entry
            Publication.from_dblp_key(
                session,
                key=dblp_key,
                type=publication_type,
                authors=authors,
                author_order=author_order,
                title=title,
                pages=pages,
                venue=venue,
                volume=volume,
                number=number,
                year=year,
                url=url,
                dblp_url=dblp_url,
                visibility=None,
            )
        )
        logging.debug("Found '{publication}'".format(publication=publications[-1]))

    return publications


def update_from_dblp(commit=False):
    """
    Pull data from DBLP and update database.

    .. note :: Existing entries are not updated. This is deliberate.

    :param commit: if `True` commit result to disk.

    """
    new = []
    for group_member, predicate in dblp_pids():
        logging.info("Fetching user '{group_member}'".format(group_member=group_member))
        root = dblp_fetch(group_member)
        publications = dblp_parse(root)

        for publication in publications:
            # we may have added the authors to the DB in the meantime, avoid duplicates by rechecking
            publication.authors = [
                Author.from_dblp_pid(session, pid=author.dblp_pid, name=author.name)
                for author in publication.authors
            ]
            if publication.visibility is None and predicate(publication):
                logging.info("Added '{publication}'".format(publication=publication))
                publication.visibility = True
                new.append(publication)

            if publication.id is None:
                session.add(publication)

    if commit:
        session.commit()

    return tuple(new)


def render_templates():

    query = session.query(Publication).filter(Publication.visibility)
    query = query.order_by(Publication.year.desc())

    for output_path, template_path, filterf in GPConfig.OUTPUTS:
        publications = filterf(query).all()

        with open(template_path, "r") as th:
            template = Template(th.read())
            output = template.render(publications=publications)
            with open(output_path, "w") as oh:
                oh.write(output)


engine = create_engine("sqlite:///%s" % GPConfig.DB_PATH, echo=False)
session = sessionmaker(bind=engine)()
Base.metadata.create_all(engine)

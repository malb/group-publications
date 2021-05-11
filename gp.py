# -*- coding: utf-8 -*-
import requests
import re
import xml.etree.ElementTree as ET
from config import GPConfig
import logging

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from sqlalchemy import Table, Column, Boolean, Integer, String, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.orm.exc import NoResultFound

from jinja2 import Template


engine = create_engine("sqlite:///%s" % GPConfig.DB_PATH, echo=False)
session = sessionmaker(bind=engine)()
Base = declarative_base()


association_table = Table(
    "authors_and_papers",
    Base.metadata,
    Column("author_id", Integer, ForeignKey("authors.id")),
    Column("publication_id", Integer, ForeignKey("publications.id")),
)


class Author(Base):

    __tablename__ = "authors"

    id = Column(Integer, primary_key=True)
    dblp_pid = Column(String, unique=True)
    name = Column(String)
    publications = relationship(
        "Publication", secondary=association_table, back_populates="authors"
    )

    @staticmethod
    def from_dblp_pid(pid, name):
        try:
            return session.query(Author).filter(Author.dblp_pid == pid).one()
        except NoResultFound:
            return Author(dblp_pid=pid, name=name)

    def __repr__(self):
        return "{pid}: {name}".format(pid=self.dblp_pid, name=self.name)


class Publication(Base):

    __tablename__ = "publications"

    id = Column(Integer, primary_key=True)
    dblp_key = Column(String, unique=True)
    type = Column(
        Enum(
            "informal",
            "inproceedings",
            "incollection",
            "article",
            "phdthesis",
            "proceedings",
            "book",
        )
    )
    authors = relationship("Author", secondary=association_table, back_populates="publications")
    author_order = Column(String)
    title = Column(String)
    pages = Column(String, default="")
    year = Column(Integer)
    venue = Column(String)
    volume = Column(String, default="")
    number = Column(String, default="")
    url = Column(String, default="")
    dblp_url = Column(String, default="")
    visible = Column(Boolean, default=True)
    comment = Column(String, default="")
    public_comment = Column(String, default="")

    def from_dblp_key(key, **kwds):
        try:
            return session.query(Publication).filter(Publication.dblp_key == key).one()
        except NoResultFound:
            return Publication(dblp_key=key, **kwds)

    def __repr__(self):
        return '{{year: {year}, key: "{key}", title: "{title}"}}'.format(
            year=self.year,
            key=self.dblp_key,
            title=self.title,
        )

    @staticmethod
    def author_orderf(authors):
        "We need to maintain the order of authors manually"
        return ", ".join([author.dblp_pid for author in authors])

    @property
    def authors_str(self):
        authors = self.author_order
        for author in self.authors:
            authors = authors.replace(author.dblp_pid, author.name)
        return authors

    @staticmethod
    def toggle_visibility(dblp_key, commit=False):
        publication = session.query(Publication).filter(Publication.dblp_key == dblp_key).one()
        publication.visible = not publication.visible
        if commit:
            session.commit()


Base.metadata.create_all(engine)

#
# DBLP interface
#


def dblp_fetch(pid):
    url = "https://dblp.uni-trier.de/pid/{pid}.xml".format(pid=pid)
    r = requests.get(url)
    if r.status_code != 200:
        raise RuntimeError(
            "Request returned status code {status_code}".format(status_code=r.status_code)
        )
    root = ET.fromstring(r.text)
    return root


def dblp_parse(root):
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

        authors = []
        for author in publication.findall("author"):
            author_name = author.text
            # Foo Bar 0001 is a thing on DBLP
            author_name = re.match("([^0-9]*)([0-9]+)?", author_name).group(1).strip()
            authors.append(Author.from_dblp_pid(author.attrib["pid"], author_name))

        author_order = Publication.author_orderf(authors)

        title = publication.findtext("title")
        if title.endswith("."):
            title = title[:-1]
        year = int(publication.findtext("year"))
        url = publication.findtext("ee")
        dblp_url = publication.findtext("url")

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

        pages = publication.findtext("pages", "")
        volume = publication.findtext("volume", "")
        number = publication.findtext("number", "")

        # IACR ePrint is so important to us we treat is specially
        if venue == "IACR Cryptol. ePrint Arch.":
            number = re.match("http(s)?://eprint.iacr.org/([0-9]{4})/([0-9]+)", url).group(3)

        publications.append(
            Publication.from_dblp_key(
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
            )
        )
        logging.info("Found {publication}".format(publication=publications[-1]))

    return publications


def update_from_dblp(commit=False):
    for group_member, predicate in GPConfig.DBLP_PIDS:
        logging.info("Fetching user '{group_member}'".format(group_member=group_member))
        root = dblp_fetch(group_member)
        publications = dblp_parse(root)

        for publication in publications:
            publication.authors = [
                Author.from_dblp_pid(pid=author.dblp_pid, name=author.name)
                for author in publication.authors
            ]
            if predicate(publication) and publication.id is None:
                session.add(publication)
    if commit:
        session.commit()


def render_templates(skip_informal=False):

    query = session.query(Publication).filter(Publication.visible)
    if skip_informal:
        query = query.filter(Publication.type != "informal")

    query = query.order_by(Publication.year.desc())
    publications = query.all()

    for output_path, template_path in GPConfig.OUTPUTS:
        with open(template_path, "r") as th:
            template = Template(th.read())
            output = template.render(publications=publications)
            with open(output_path, "w") as oh:
                oh.write(output)

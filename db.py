# -*- coding: utf-8 -*-
from sqlalchemy import Table, Column, Boolean, Date, Integer, String, Enum, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy.exc import NoResultFound
import datetime

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
    def from_dblp_pid(session, pid, name):
        try:
            return session.query(Author).filter(Author.dblp_pid == pid).one()
        except NoResultFound:
            return Author(dblp_pid=pid, name=name)

    def __repr__(self):
        return "{pid}: {name}".format(pid=self.dblp_pid, name=self.name)


PUBLICATION_TYPES = (
    "informal",
    "inproceedings",
    "incollection",
    "article",
    "phdthesis",
    "proceedings",
    "book",
)


class Publication(Base):

    __tablename__ = "publications"

    id = Column(Integer, primary_key=True)
    dblp_key = Column(String, unique=True)
    type = Column(Enum(*PUBLICATION_TYPES))
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
    visibility = Column(Boolean, default=None)
    comment = Column(String, default="")
    public_comment = Column(String, default="")
    dblp_mdate = Column(Date)
    cdate = Column(Date, default=datetime.date.today())

    @staticmethod
    def from_dblp_key(session, key, **kwds):
        try:
            return session.query(Publication).filter(Publication.dblp_key == key).one()
        except NoResultFound:
            return Publication(dblp_key=key, **kwds)

    def __str__(self):
        return (
            "{publication.authors_str}: "
            "{publication.title}, "
            "{publication.venue} "
            "{publication.year} "
            "# {publication.dblp_key}"
        ).format(publication=self)

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
    def toggle_visibility(session, dblp_key, commit=False):
        publication = session.query(Publication).filter(Publication.dblp_key == dblp_key).one()
        publication.visibility = not publication.visibility
        if commit:
            session.commit()

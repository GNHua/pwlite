# -*- coding: utf-8 -*-
"""User models."""
from flask import abort, g
from peewee import Model, CharField, BooleanField, IntegerField, \
    DateTimeField, TextField, ForeignKeyField
from playhouse.sqlite_ext import FTSModel, SearchField
from datetime import datetime

from pwlite.extensions import db


class BaseModel(Model):
    class Meta:
        database = db

    @classmethod
    def get_or_404(cls, *query, **filters):
        try:
            return cls.get(*query, **filters)
        except cls.DoesNotExist:
            abort(404)


class BaseFTSModel(FTSModel):
    class Meta:
        database = db


class WikiGroup(BaseModel):
    name = CharField(unique=True)
    db_name = CharField(unique=True)
    active = BooleanField(default=True)

    def db_filename(self):
        return '{0}.db'.format(self.db_name)


class WikiPage(BaseModel):
    """Model of wiki pages.
    """
    title = CharField(unique=True)
    markdown = TextField(null=True, default='')
    html = TextField(null=True, default='')
    toc = TextField(null=True, default='')
    current_version = IntegerField(default=1)
    modified_on = DateTimeField(index=True, default=datetime.utcnow)

    def update_content(self, diff, markdown, html, toc):
        WikiPageVersion.create(
            wiki_page=self,
            diff=diff,
            version=self.current_version,
            modified_on=self.modified_on
        )

        (WikiPageIndex
         .update(markdown=markdown)
         .where(WikiPageIndex.docid==self.id)
         .execute())

        (WikiPage
         .update(
             markdown=markdown,
             html=html,
             toc=toc,
             current_version=WikiPage.current_version+1,
             modified_on=datetime.utcnow())
         .where(WikiPage.id==self.id)
         .execute())

        # remove unused WikiReference
        (WikiReference
         .delete()
         .where(WikiReference.referenced.in_(g.wiki_refs))
         .execute())

    def update_content_after_upload(self, diff, file_markdown, file_html):
        WikiPageVersion.create(
            wiki_page=self,
            diff=diff,
            version=self.current_version,
            modified_on=self.modified_on
        )

        (WikiPageIndex
         .update(markdown=self.markdown+file_markdown)
         .where(WikiPageIndex.docid==self.id)
         .execute())

        (WikiPage
         .update(
             markdown=WikiPage.markdown+file_markdown,
             html=WikiPage.html+file_html,
             current_version=WikiPage.current_version+1,
             modified_on=datetime.utcnow())
         .where(WikiPage.id==self.id)
         .execute())


class WikiPageIndex(BaseFTSModel):
    title = SearchField()
    markdown = SearchField()

    class Meta:
        # Use the porter stemming algorithm to tokenize content.
        # Does not store extra copy of indexed content.
        options = {'tokenize': 'porter',
                   'content': WikiPage}


class WikiPageVersion(BaseModel):
    """Model of page versions.
    """
    wiki_page = ForeignKeyField(WikiPage, backref='versions')
    diff = TextField()
    version = IntegerField()
    modified_on = DateTimeField()


class WikiReference(BaseModel):
    referencing = ForeignKeyField(WikiPage, backref='references')
    referenced = ForeignKeyField(WikiPage, backref='referenced_by')

    class Meta:
        indexes = (
            (('referencing', 'referenced'), True),
        )


class WikiFile(BaseModel):
    """Model of uploaded files.

    .. py:attribute:: name

        file name

    .. py:attribute:: mime_type

        file type. Example: image/png.

    .. py:attribute:: size

        file size in bytes

    .. py:attribute:: upload_on

        the time when file is uploaded
    """
    name = CharField(max_length=256)
    mime_type = CharField(null=True)
    size = IntegerField(null=True) # in bytes
    uploaded_on = DateTimeField(default=datetime.utcnow)


class WikiKeypage(BaseModel):
    """Model of key pages."""
    wiki_page = ForeignKeyField(WikiPage, backref='keypage')

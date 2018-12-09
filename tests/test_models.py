# -*- coding: utf-8 -*-
"""Model unit tests."""

import pytest
from datetime import datetime
from peewee import IntegrityError, fn
from datetime import timezone, timedelta
import time

from .factories import WikiGroupFactory
from pwlite.models import WikiGroup
from pwlite.models import WikiPage, WikiPageIndex, WikiPageVersion, WikiReference
from pwlite.utils import get_object_or_404


@pytest.mark.usefixtures('db')
class TestWikiGroup:
    """Wiki group tests."""

    def test_factory(self, db):
        wiki_group = WikiGroupFactory.create()
        retrieved = WikiGroup.get_by_id(wiki_group.id)
        assert retrieved.id == 1
        assert retrieved.name == 'wiki group 1'
        assert retrieved.db_name == 'wikigroup1'
        assert retrieved.active == True

    def test_db_atomic(self, db):
        with db.atomic():
            for i in range(10):
                WikiGroupFactory.create()
        assert WikiGroup.select().count() == 10

    def test_unique_constraint(self, db):
        WikiGroup.create(name='wiki group 1', db_name='wikigroup1')
        with pytest.raises(IntegrityError):
            WikiGroup.create(name='wiki group 1', db_name='wikigroup1')

    def test_insert_many_with_replace(self, db):
        data_source = [
            dict(name='wiki group 1', db_name='wikigroup1', active=True),
            dict(name='wiki group 1', db_name='wikigroup1', active=False),
            dict(name='wiki group 2', db_name='wikigroup2', active=True)
        ]
        WikiGroup.insert_many(data_source).on_conflict_replace().execute()
        assert WikiGroup.select().count() == 2
        wiki_groups = (WikiGroup
                       .select()
                       .execute())
        assert wiki_groups[0].name == 'wiki group 1'
        assert wiki_groups[0].active == False
        assert wiki_groups[1].name == 'wiki group 2'
        assert wiki_groups[1].active == True

    def test_insert_many_with_replace(self, db):
        data_source = [
            dict(name='wiki group 1', db_name='wikigroup1', active=True),
            dict(name='wiki group 1', db_name='wikigroup1', active=False),
            dict(name='wiki group 2', db_name='wikigroup2', active=True)
        ]

        (WikiGroup
         .insert_many(data_source)
         .on_conflict_ignore()
         .execute())

        assert WikiGroup.select().count() == 2
        wiki_groups = (WikiGroup
                       .select()
                       .execute())
        assert wiki_groups[0].name == 'wiki group 1'
        assert wiki_groups[0].active == True
        assert wiki_groups[1].name == 'wiki group 2'
        assert wiki_groups[1].active == True

    def test_upsert(self, db):
        wiki_group_id = (WikiGroup
                         .replace(name='wiki group 1', db_name='wikigroup1')
                         .execute())
        wiki_group = (WikiGroup
                      .select()
                      .execute())[0]
        assert wiki_group.active is True
        wiki_group_id = (WikiGroup
                         .replace(name='wiki group 1', db_name='wikigroup1', active=False)
                         .execute())
        wiki_group = (WikiGroup
                      .select()
                      .execute())[0]
        assert wiki_group.active is False
        assert WikiGroup.select().count() == 1

    def test_model_equal(self, db):
        wiki_group = WikiGroupFactory.create()
        retrieved_full = WikiGroup.select().execute()[0]
        retrieved_only_id = WikiGroup.select(WikiGroup.id).execute()[0]
        assert retrieved_full == retrieved_only_id

    def test_remove_model_from_list(self, db):
        wiki_group = WikiGroupFactory.create()
        retrieved_full = WikiGroup.select().execute()[0]
        retrieved_only_id = WikiGroup.select(WikiGroup.id).execute()
        retrieved_only_id = list(retrieved_only_id)
        retrieved_only_id.remove(retrieved_full)
        assert len(retrieved_only_id) == 0

    def test_delete_and_in(self, db):
        with db.atomic():
            for i in range(3):
                WikiGroupFactory.create()

        WikiGroup.delete().where(WikiGroup.id.in_([1,2])).execute()
        assert WikiGroup.select().count() == 1
        assert WikiGroup.get_by_id(3)

    def test_DoesNotExist(self, db):
        with pytest.raises(WikiGroup.DoesNotExist):
            WikiGroup.get_by_id(10)

    def test_get_object_or_404(self, db):
        WikiGroup.create(name='wiki group 1', db_name='wikigroup1')
        WikiGroup.create(name='wiki group 2', db_name='wikigroup2')
        wiki_group = get_object_or_404(
            WikiGroup.select(WikiGroup.id, WikiGroup.db_name),
            WikiGroup.name=='wiki group 2'
        )
        assert wiki_group.id == 2


@pytest.mark.usefixtures('db')
class TestWikiPage:
    """Wiki page tests."""

    def test_search_title(self, db):
        with db.atomic():
            for i in range(3):
                WikiPage.create(title='foo {0}'.format(i+1))
                WikiPage.create(title='bar {0}'.format(i+1))

        WikiPageIndex.rebuild()
        WikiPageIndex.optimize()

        wiki_pages_foo = WikiPageIndex.search('foo')
        assert [wp.title for wp in wiki_pages_foo] == ['foo 1', 'foo 2', 'foo 3']
        wiki_pages_bar = WikiPageIndex.search('bar')
        assert [wp.title for wp in wiki_pages_bar] == ['bar 1', 'bar 2', 'bar 3']

    def test_search_markdown(self, db):
        with db.atomic():
            for i in range(3):
                WikiPage.create(title='title {0}'.format(i), markdown='foo {0}'.format(i+1))
                WikiPage.create(title='title {0}'.format(i+3), markdown='bar {0}'.format(i+1))

        WikiPageIndex.rebuild()
        WikiPageIndex.optimize()

        wiki_pages_foo = WikiPageIndex.search('foo')
        assert [wp.markdown for wp in wiki_pages_foo] == ['foo 1', 'foo 2', 'foo 3']
        wiki_pages_bar = WikiPageIndex.search('bar')
        assert [wp.markdown for wp in wiki_pages_bar] == ['bar 1', 'bar 2', 'bar 3']

    def test_no_index_rebuild_optimize(self, db):
        with db.atomic():
            for i in range(3):
                wiki_page = WikiPage.create(
                    title='foo {0}'.format(i+1),
                    markdown='bar {0}'.format(i+1)
                )
                WikiPageIndex.create(
                    docid=wiki_page.id,
                    title=wiki_page.title,
                    markdown=wiki_page.markdown
                )

        wiki_pages_foo = WikiPageIndex.search('foo')
        assert [wp.title for wp in wiki_pages_foo] == ['foo 1', 'foo 2', 'foo 3']
        wiki_pages_bar = WikiPageIndex.search('bar')
        assert [wp.markdown for wp in wiki_pages_bar] == ['bar 1', 'bar 2', 'bar 3']

    def test_search_after_update(self, db):
        with db.atomic():
            wiki_page = WikiPage.create(
                title='foo'
            )
            WikiPageIndex.create(
                docid=wiki_page.id,
                title=wiki_page.title
            )

        wiki_pages_bar = WikiPageIndex.search('bar')
        assert len(wiki_pages_bar) == 0

        WikiPageIndex.update(title='bar').where(WikiPageIndex.docid==1).execute()
        WikiPage.update(title='bar').where(WikiPage.id==1).execute()

        wiki_pages_bar = WikiPageIndex.search('bar')
        assert wiki_pages_bar[0].title == 'bar'

    def test_search_when_fts_model_is_out_of_sync(self, db):
        with db.atomic():
            wiki_page = WikiPage.create(
                title='foo'
            )
            WikiPageIndex.create(
                docid=wiki_page.id,
                title='bar'
            )

        wiki_pages_bar = WikiPageIndex.search('bar')
        assert isinstance(wiki_pages_bar[0], WikiPageIndex)
        assert wiki_pages_bar[0].title == 'foo'

    def test_non_searchable_field(self, db):
        with db.atomic():
            wiki_page = WikiPage.create(
                title='foo',
                markdown='bar',
                html='spam'
            )
            WikiPageIndex.create(
                docid=wiki_page.id,
                title=wiki_page.title,
                markdown=wiki_page.markdown
            )

        query = (WikiPage
                 .select(WikiPage, WikiPageIndex.bm25(3.0, 2.0))
                 .join(
                     WikiPageIndex,
                     on=(WikiPage.id == WikiPageIndex.docid))
                 .where(WikiPageIndex.match('foo bar'))
                 .order_by(WikiPageIndex.bm25(3.0, 2.0)))
        wiki_page = query.execute()[0]
        count = query.count()

        assert wiki_page.title == 'foo'
        assert wiki_page.markdown == 'bar'
        assert wiki_page.html == 'spam'
        assert count == 1

    def test_search_score(self, db):
        with db.atomic():
            wiki_page = WikiPage.create(
                title='foo1',
                markdown='bar'
            )
            WikiPageIndex.create(
                docid=wiki_page.id,
                title=wiki_page.title,
            )

            wiki_page = WikiPage.create(
                title='bar',
                markdown='foo1 '
            )
            WikiPageIndex.create(
                docid=wiki_page.id,
                title=wiki_page.title,
                markdown=wiki_page.markdown
            )

        query = WikiPageIndex.search_bm25(
            'foo1',
            weights={'title': 3.0, 'markdown': 2.0},
            with_score=True,
            score_alias='search_score',
            explicit_ordering=True
        )
        # assert False
        assert isinstance(query.execute()[0], WikiPageIndex)

        # assert [wp.docid for wp in query] == [1, 2]

    def test_atomic_update_for_string_addition(self, db):
        wiki_page = WikiPage.create(
            title='foo',
            markdown='bar'
        )

        (WikiPage
         .update(markdown=WikiPage.markdown+' spam')
         .where(WikiPage.id==wiki_page.id)
         .execute())

        wiki_page = WikiPage.get_by_id(wiki_page.id)
        assert wiki_page.markdown == 'bar spam'

    def test_atomic_update_for_string_addition_when_initially_empth(self, db):
        wiki_page = WikiPage.create(
            title='foo'
        )

        wiki_page = WikiPage.get_by_id(1)

        (WikiPage
         .update(markdown=WikiPage.markdown+'spam')
         .where(WikiPage.id==wiki_page.id)
         .execute())

        wiki_page = WikiPage.get_by_id(wiki_page.id)
        assert wiki_page.markdown == 'spam'

    def test_timezone(self, db):
        wiki_page = WikiPage.create(
            title='foo'
        )

        mdt = timezone(timedelta(hours=-7), 'MDT')
        time_utc = wiki_page.modified_on.replace(tzinfo=timezone.utc)
        time_mdt = time_utc.astimezone(mdt).replace(tzinfo=timezone.utc)
        assert time_mdt - time_utc == timedelta(hours=-7)


@pytest.mark.usefixtures('db')
class TestWikiPageVersion:
    """Wiki page version tests."""

    def test_versions(self, db):
        with db.atomic():
            wiki_page = WikiPage.create(
                title='foo',
            )
            for i in range(10):
                WikiPageVersion.create(
                    wiki_page=wiki_page,
                    diff=str(i+1),
                    version=i+1,
                    modified_on=time.time()
                )

        wiki_page = WikiPage.select().where(WikiPage.id==1)[0]
        assert [v.diff for v in wiki_page.versions] == [str(i+1) for i in range(10)]

    def test_column_contains(self, db):
        with db.atomic():
            wiki_page = WikiPage.create(
                title='foo',
            )
            for i in range(10):
                WikiPageVersion.create(
                    wiki_page=wiki_page,
                    diff='bar'+str(i+1),
                    version=i+1,
                    modified_on=time.time()
                )

        query = (WikiPageVersion
                 .select()
                 .where(WikiPageVersion.diff.contains('bar')))
        wiki_page_versions = query.execute()
        assert [wiki_page_version.diff for wiki_page_version in wiki_page_versions] == ['bar'+str(i+1) for i in range(10)]


class TestWikiReference:
    """Wiki reference tests."""

    def test_many_to_many_relationship_of_same_model(self, db):
        with db.atomic():
            wiki_pages_ref_ing = []
            wiki_pages_ref_ed = []
            for i in range(3):
                wiki_pages_ref_ing.append(WikiPage.create(title='ref-ing {0}'.format(i+1)))
                wiki_pages_ref_ed.append(WikiPage.create(title='ref-ed {0}'.format(i+1)))

            for i in range(3):
                for j in range(3):
                    WikiReference.create(
                        referencing = wiki_pages_ref_ing[i],
                        referenced = wiki_pages_ref_ed[j]
                    )

        wiki_pages = (WikiPage
                      .select()
                      .join(WikiReference, on=WikiReference.referencing)
                      .where(WikiReference.referenced == wiki_pages_ref_ed[0])
                      .execute())
        assert isinstance(wiki_pages[0], WikiPage)

        assert [wp.title for wp in wiki_pages] == ['ref-ing 1', 'ref-ing 2', 'ref-ing 3']

    def test_unique_constraint_on_multiple_columns(self, db):
        with db.atomic():
            wiki_page_ref_ing = WikiPage.create(title='ref-ing')
            wiki_page_ref_ed = WikiPage.create(title='ref-ed')

            WikiReference.create(
                referencing = wiki_page_ref_ing,
                referenced = wiki_page_ref_ed
            )

        with pytest.raises(IntegrityError):
            WikiReference.create(
                referencing = wiki_page_ref_ing,
                referenced = wiki_page_ref_ed
            )

    def test_remove_with_in(self, db):
        with db.atomic():
            wiki_pages_ref_ing = []
            wiki_pages_ref_ed = []
            for i in range(3):
                wiki_pages_ref_ing.append(WikiPage.create(title='ref-ing {0}'.format(i+1)))
                wiki_pages_ref_ed.append(WikiPage.create(title='ref-ed {0}'.format(i+1)))

            for i in range(3):
                for j in range(3):
                    WikiReference.create(
                        referencing = wiki_pages_ref_ing[i],
                        referenced = wiki_pages_ref_ed[j]
                    )

        wiki_page = (WikiPage
                     .select()
                     .where(WikiPage.title=='ref-ing 1')
                     .execute())[0]
        refs_to_del = list(WikiPage
                           .select(WikiPage.id)
                           .join(WikiReference, on=WikiReference.referenced)
                           .where(WikiReference.referencing==wiki_page)
                           .execute())
                    
        (WikiReference
         .delete()
         .where(WikiReference.referenced.in_(refs_to_del))
         .execute())

        assert WikiReference.select().where(WikiReference.referencing==wiki_page).count() == 0
from flask import g
import markdown
from markdown.inlinepatterns import Pattern
from markdown.util import etree
from markdown.extensions import Extension
from peewee import IntegrityError

from pwlite.models import WikiPage, WikiPageIndex, WikiReference, WikiFile

wiki_page_regex = r'\[\[(.+?)\]\]'
wiki_file_regex = r'\[(file|image):(\d+)(@(\d+)x(\d+))?\]'

# TODO: look into another markdown parse, mistune

# Parse wiki page
class WikiPagePattern(Pattern):

    def handleMatch(self, m):
        wiki_page_title = m.group(2)
        try:
            wiki_page = (WikiPage
                         .select(WikiPage.id)
                         .where(WikiPage.title==wiki_page_title)
                         .get())
        except WikiPage.DoesNotExist:
            wiki_page = WikiPage.create(title=wiki_page_title)
            wiki_page_index = WikiPageIndex.create(docid=wiki_page.id, title=wiki_page_title)

        (WikiReference
         .insert(referencing=g.wiki_page, referenced=wiki_page)
         .on_conflict_ignore()
         .execute())

        try:
            g.wiki_refs.remove(wiki_page)
        except ValueError:
            pass

        return render_wiki_page(wiki_page.id, wiki_page_title)


class WikiPageExtension(Extension):

    def extendMarkdown(self, md, md_globals):
        md.inlinePatterns['wiki_page'] = WikiPagePattern(wiki_page_regex)


# Parse wiki file & image
class WikiFilePattern(Pattern):

    def handleMatch(self, m):
        _, _, wiki_file_type, wiki_file_id, wh, w, h = [m.group(i) for i in range(7)]

        try:
            wiki_file = WikiFile.get_by_id(int(wiki_file_id))
        except WikiFile.DoesNotExist:
            return

        return render_wiki_file(
            wiki_file.id,
            wiki_file.name,
            wiki_file_type,
            w=w,
            h=h
        )


class WikiFileExtension(Extension):

    def extendMarkdown(self, md, md_globals):
        md.inlinePatterns['wiki_file'] = WikiFilePattern(wiki_file_regex)


class WikiMarkdown(markdown.Markdown):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, extensions=[
            WikiPageExtension(),
            WikiFileExtension(),
            'markdown.extensions.toc',
            'pymdownx.github'
        ], **kwargs)

    def __call__(self, markdown):
        try:
            self.toc = ''
            html = super().convert(markdown)
        except RecursionError:
            html = markdown
        return self.toc, html


def render_wiki_page(wiki_page_id, wiki_page_title, tostring=False):
    el = etree.Element('a', attrib={
            'href': '/{0}/page/{1}'.format(g.wiki_group, wiki_page_id)
        })
    el.text = wiki_page_title
    if tostring:
        return etree.tostring(el, encoding='unicode') 
    else:
        return el


def render_wiki_file(
    wiki_file_id,
    wiki_file_name,
    wiki_file_type,
    w=0,
    h=0,
    tostring=False
):
    link = '/{0}/file/{1}?filename={2}'.format(
        g.wiki_group,
        wiki_file_id,
        wiki_file_name
    )
    if wiki_file_type == 'image':
        el = etree.Element('img', attrib={'src': link})
        if w != 0:
            el.attrib['width'] = w
        if h != 0:
            el.attrib['height'] = h
    elif wiki_file_type == 'file':
        sub_el = etree.Element('img', attrib={
            'alt': 'file icon',
            'src': '/static/images/file-icon.png',
            'width': '20',
            'height': '20'
        })
        sub_el.tail = wiki_file_name
        el = etree.Element('a', attrib={'href': link})
        el.append(sub_el)
    if tostring:
        return etree.tostring(el, encoding='unicode') 
    else:
        return el

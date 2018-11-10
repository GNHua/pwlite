# -*- coding: utf-8 -*-
"""Wiki section, including wiki pages for each group."""
from flask import Blueprint, g, render_template, redirect, url_for, \
    request, flash, send_from_directory, abort, current_app
from datetime import datetime, date
import os
import math

from pwlite.extensions import db, markdown
from pwlite.utils import flash_errors, xstr, get_object_or_404, \
    calc_page_num, format_datetime
from pwlite.models import WikiPage, WikiPageIndex, WikiKeypage, \
    WikiPageVersion, WikiReference, WikiFile
from pwlite.wiki.forms import WikiEditForm, UploadForm, RenameForm, \
    SearchForm, KeyPageEditForm
from pwlite.diff import make_patch
from pwlite.settings import DB_PATH
from pwlite.markdown import render_wiki_page, render_wiki_file

blueprint = Blueprint('wiki', __name__, static_folder='../static', url_prefix='/<wiki_group>')


@blueprint.url_defaults
def add_wiki_group_code(endpoint, values):
    if 'wiki_group' in values:
        return

    try:
        values.setdefault('wiki_group', g.wiki_group)
    except AttributeError:
        pass


@blueprint.url_value_preprocessor
def pull_wiki_group_code(endpoint, values):
    g.wiki_group = values.pop('wiki_group')
    if g.wiki_group not in current_app.active_wiki_groups:
        abort(404)


@blueprint.before_request
def open_database_connection():
    db.pick('{0}.db'.format(g.wiki_group))


@blueprint.after_request
def close_database_connection(response):
    db.close()
    return response


# Docs: http://flask.pocoo.org/docs/1.0/templating/#context-processors
@blueprint.context_processor
def inject_wiki_group_data():
    if g.wiki_group not in current_app.active_wiki_groups:
        return dict()

    if '/edit/' in request.path or '/upload/' in request.path:
        return dict(wiki_group=g.wiki_group)

    search_form = SearchForm()

    query = (WikiPage
             .select(WikiPage.id, WikiPage.title)
             .join(
                 WikiKeypage,
                 on=(WikiKeypage.wiki_page))
             .order_by(WikiKeypage.id))
    wiki_keypages = query.execute()

    # TODO: enhancement - this might be a performance bottleneck in the future.
    query = (WikiPage
             .select(WikiPage.id, WikiPage.title, WikiPage.modified_on)
             .order_by(WikiPage.modified_on.desc())
             .limit(5))
    wiki_changes = query.execute()

    if wiki_changes[0].modified_on.date() == date.today():
        latest_change_time = wiki_changes[0].modified_on.strftime('[%H:%M]')
    else:
        latest_change_time = wiki_changes[0].modified_on.strftime('[%b %d]')

    return dict(
        wiki_group=g.wiki_group,
        search_form=search_form,
        wiki_keypages=wiki_keypages,
        wiki_changes=wiki_changes,
        latest_change_time=latest_change_time,
        format_datetime=format_datetime
    )


@blueprint.route('/home')
def home():
    """Home page."""
    return redirect(url_for('.page', wiki_page_id=1))


@blueprint.route('/page/<int:wiki_page_id>')
def page(wiki_page_id):
    wiki_page = get_object_or_404(
        WikiPage.select(
            WikiPage.id,
            WikiPage.title,
            WikiPage.html,
            WikiPage.toc,
            WikiPage.modified_on),
        WikiPage.id==wiki_page_id
    )
    return render_template(
        'wiki/page.html',
        wiki_page=wiki_page
    )


@blueprint.route('/edit/<int:wiki_page_id>', methods=['GET', 'POST'])
def edit(wiki_page_id):
    wiki_page = get_object_or_404(
        WikiPage.select(
            WikiPage.id,
            WikiPage.title,
            WikiPage.markdown,
            WikiPage.current_version,
            WikiPage.modified_on),
        WikiPage.id==wiki_page_id
    )
    form = WikiEditForm()
    # TODO: add upload form

    if form.validate_on_submit():
        if form.current_version.data == wiki_page.current_version:
            g.wiki_page = wiki_page
            g.wiki_refs = list(WikiPage
                               .select(WikiPage.id)
                               .join(WikiReference, on=WikiReference.referenced)
                               .where(WikiReference.referencing == wiki_page)
                               .execute())

            diff = make_patch(wiki_page.markdown, form.textArea.data)
            if diff:
                with db.atomic():
                    toc, html = markdown(form.textArea.data)
                    WikiPageVersion.create(
                        wiki_page=wiki_page,
                        diff=diff,
                        version=wiki_page.current_version,
                        modified_on=wiki_page.modified_on
                    )

                    (WikiPageIndex
                     .update(markdown=form.textArea.data)
                     .where(WikiPageIndex.docid==wiki_page.id)
                     .execute())

                    (WikiPage
                     .update(
                         markdown=form.textArea.data,
                         html=html,
                         toc=toc,
                         current_version=WikiPage.current_version,
                         modified_on=datetime.utcnow())
                     .where(WikiPage.id==wiki_page.id)
                     .execute())

                    # remove unused WikiReference
                    (WikiReference
                     .delete()
                     .where(WikiReference.referenced.in_(g.wiki_refs))
                     .execute())

            return redirect(url_for('.page', wiki_page_id=wiki_page.id))
        else:
            flash('Other changes have been made to this '
                  'wiki page since you started editing it.')

    return render_template(
        'wiki/edit.html',
        wiki_page=wiki_page,
        form=form
    )


@blueprint.route('/upload/<int:wiki_page_id>')
def upload(wiki_page_id):
    form = UploadForm()
    return render_template(
        'wiki/upload.html', 
        wiki_page_id=wiki_page_id,
        form=form
    )


# TODO: add upload from edit page
@blueprint.route('/handle-upload', methods=['POST'])
def handle_upload():
    form = request.form
    wiki_page_id = int(form.get('wiki_page_id', None))

    file_markdown, file_html = '', ''
    with db.atomic():
        for i, file in enumerate(request.files.getlist('wiki_file')):
            # create a WikiFile in database and retrieve id
            wiki_file = WikiFile.create(
                name=file.filename,
                mime_type=file.mimetype
            )
            # save uploaded file with WikiFile.id as filename
            file.save(os.path.join(DB_PATH, g.wiki_group, str(wiki_file.id)))
            wiki_file.size = file.tell()
            wiki_file.save()

            if 'image' in wiki_file.mime_type:
                file_type = 'image'
            else:
                file_type = 'file'
            file_markdown += '\n\n[{}:{}]'.format(file_type, wiki_file.id)
            file_html += '<p>{}</p>'.format(render_wiki_file(
                wiki_file.id,
                wiki_file.name,
                file_type,
                tostring=True
            ))

        wiki_page = get_object_or_404(
            WikiPage.select(
                WikiPage.id,
                WikiPage.markdown,
                WikiPage.current_version,
                WikiPage.modified_on),
            WikiPage.id==wiki_page_id
        )

        diff = make_patch(xstr(wiki_page.markdown), xstr(wiki_page.markdown)+file_markdown)
        WikiPageVersion.create(
            wiki_page=wiki_page,
            diff=diff,
            version=wiki_page.current_version,
            modified_on=wiki_page.modified_on
        )

        (WikiPageIndex
        .update(markdown=wiki_page.markdown+file_markdown)
        .where(WikiPageIndex.docid==wiki_page.id)
        .execute())

        (WikiPage
        .update(
            markdown=WikiPage.markdown+file_markdown,
            html=WikiPage.html+file_html,
            current_version=WikiPage.current_version+1,
            modified_on=datetime.utcnow())
        .where(WikiPage.id==wiki_page.id)
        .execute())

    return ''


@blueprint.route('/reference/<int:wiki_page_id>')
def reference(wiki_page_id):
    wiki_page = get_object_or_404(
        WikiPage.select(
            WikiPage.id,
            WikiPage.title),
        WikiPage.id==wiki_page_id
    )
    wiki_referencing_pages = (WikiPage
                              .select(WikiPage.id, WikiPage.title)
                              .join(WikiReference, on=WikiReference.referencing)
                              .where(WikiReference.referenced == wiki_page)
                              .execute())
    return render_template(
        'wiki/reference.html',
        wiki_page=wiki_page,
        wiki_referencing_pages=wiki_referencing_pages
    )


@blueprint.route('/rename/<int:wiki_page_id>', methods=['GET', 'POST'])
def rename(wiki_page_id):
    wiki_page = get_object_or_404(
        WikiPage.select(
            WikiPage.id,
            WikiPage.title),
        WikiPage.id==wiki_page_id
    )
    if wiki_page.title == 'Home':
        return redirect(url_for('.home'))

    form = RenameForm(new_title=wiki_page.title)

    if form.validate_on_submit():
        new_title = form.new_title.data
        if wiki_page.title == new_title:
            flash('The page name is not changed.', 'warning')
        elif WikiPage.select().where(WikiPage.title==new_title).count() > 0:
            flash('The new page title has already been taken.', 'warning')
        else:
            with db.atomic():
                old_markdown = '[[{}]]'.format(wiki_page.title)
                new_markdown = '[[{}]]'.format(new_title)

                old_html = render_wiki_page(wiki_page.id, wiki_page.title, tostring=True)
                new_html = render_wiki_page(wiki_page.id, new_title, tostring=True)

                # update the markdown of referencing wiki page 
                query = (WikiPage
                        .select(WikiPage.id, WikiPage.markdown, WikiPage.html)
                        .join(WikiReference, on=WikiReference.referencing)
                        .where(WikiReference.referenced == wiki_page))
                wiki_referencing_pages = query.execute()
                for ref in wiki_referencing_pages:
                    ref.markdown = ref.markdown.replace(old_markdown, new_markdown)
                    ref.html = ref.html.replace(old_html, new_html)
                    ref.save()

                # update the diff of related wiki page versions
                query = (WikiPageVersion
                        .select(WikiPageVersion.diff)
                        .where(WikiPageVersion.diff.contains(old_markdown)))
                wiki_page_versions = query.execute()
                for pv in wiki_page_versions:
                    pv.diff = pv.diff.replace(old_markdown, new_markdown)
                    pv.save()

                wiki_page.title = new_title
                wiki_page.save()

            return redirect(url_for('.page', wiki_page_id=wiki_page.id))

    return render_template(
        'wiki/rename.html',
        wiki_page=wiki_page,
        form=form
    )


@blueprint.route('/file/<int:wiki_file_id>')
def file(wiki_file_id):
    fn = request.args.get('filename')
    if not fn:
        wiki_file = get_object_or_404(
            WikiFile.select(WikiFile.id, WikiFile.name),
            WikiFile.id==wiki_file_id
        )
        fn = wiki_file.name
    return send_from_directory(
        os.path.join(DB_PATH, g.wiki_group),
        str(wiki_file.id),
        as_attachment=True,
        attachment_filename=fn
    )


# TODO: add abitrary number per page, sort by other column, such as timestamp
@blueprint.route('/search', methods=['GET', 'POST'])
def search():
    search_keyword = request.args.get('search')
    kwargs = dict(current_page_number = request.args.get('page', default=1, type=int))
    form = SearchForm(search=search_keyword)

    if search_keyword and not search_keyword.isspace():
        query = (WikiPage
                 .select(
                     WikiPage.id, WikiPage.title, WikiPage.modified_on,
                     WikiPageIndex.bm25(1.0, 3.0, 2.0))
                 .join(
                     WikiPageIndex,
                     on=(WikiPage.id==WikiPageIndex.docid))
                 .where(WikiPageIndex.match(search_keyword))
                 .order_by(WikiPageIndex.bm25(1.0, 3.0, 2.0))
                 .paginate(kwargs['current_page_number'], paginate_by=100))
        kwargs['wiki_pages'] = query.execute()
        count = query.count()
        kwargs['total_page_number'] = math.ceil(count / 100)
        kwargs['start_page_number'], kwargs['end_page_number'] = \
            calc_page_num(kwargs['current_page_number'], kwargs['total_page_number'])

    if form.validate_on_submit():
        return redirect(url_for('.search', search=form.search.data))

    return render_template(
        'wiki/search.html',
        form=form,
        **kwargs
    )


# TODO: implement history diff check
@blueprint.route('/history/<int:wiki_page_id>')
def history(wiki_page_id):
    return ''


@blueprint.route('/keypage-edit', methods=['GET', 'POST'])
def keypage_edit():
    query = (WikiPage
             .select(WikiPage.id, WikiPage.title)
             .join(
                 WikiKeypage,
                 on=(WikiKeypage.wiki_page))
             .order_by(WikiKeypage.id))
    wiki_keypages = query.execute()
    keypage_titles = [wiki_keypage.title for wiki_keypage in wiki_keypages]
    form = KeyPageEditForm(textArea='\n'.join(keypage_titles))

    if form.validate_on_submit():
        new_titles = form.textArea.data.splitlines()
        query = (WikiPage
                 .select(WikiPage.id, WikiPage.title)
                 .where(WikiPage.title.in_(new_titles)))
        wiki_pages = [(wiki_page,) for wiki_page in query.execute()]

        WikiKeypage.drop_table(safe=True)
        WikiKeypage.create_table(safe=True)
        (WikiKeypage
         .insert_many(wiki_pages, fields=[WikiKeypage.wiki_page])
         .execute())

        return redirect(url_for('.home'))

    return render_template(
        'wiki/keypage_edit.html',
        form=form
    )


# TODO: enhancement - choose number of changes, sort by arbitrary column
@blueprint.route('/changes')
def changes():
    query = (WikiPage
             .select(WikiPage.id, WikiPage.title, WikiPage.modified_on)
             .order_by(WikiPage.modified_on.desc())
             .limit(50))
    wiki_changes = query.execute()

    return render_template(
        'wiki/changes.html',
        wiki_changes=wiki_changes
    )

# TODO: implement group admin
@blueprint.route('/admin')
def admin():
    return ''

# TODO: view all wiki pages
# TODO: delete wiki pages
# TODO: view all wiki files
# TODO: delete wiki files


@blueprint.route('/markdown')
def markdown_instructions():
    return render_template('wiki/markdown.html')

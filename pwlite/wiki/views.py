# -*- coding: utf-8 -*-
"""Wiki section, including wiki pages for each group."""
from flask import Blueprint, g, render_template, redirect, url_for, \
    request, flash, send_from_directory, abort
from datetime import datetime, timedelta
import os
import math
import difflib

from pwlite.decorators import decorate_blueprint
from pwlite.extensions import db, markdown
from pwlite.utils import flash_errors, xstr, get_object_or_404, \
    calc_page_num, get_pagination_kwargs, paginate
from pwlite.models import WikiPage, WikiPageIndex, WikiKeypage, \
    WikiPageVersion, WikiReference, WikiFile
from pwlite.wiki.forms import WikiEditForm, UploadForm, RenameForm, \
    SearchForm, KeyPageEditForm, HistoryRecoverForm
from pwlite.diff import make_patch, apply_patches
from pwlite.settings import DB_PATH, TIMEZONE
from pwlite.markdown import render_wiki_page, render_wiki_file

blueprint = Blueprint('wiki', __name__, static_folder='../static', url_prefix='/<wiki_group>')
decorate_blueprint(blueprint)


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
    upload_form = UploadForm()

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
                    wiki_page.update_content(diff, form.textArea.data, html, toc)

            return redirect(url_for('.page', wiki_page_id=wiki_page.id))
        else:
            flash('Other changes have been made to this '
                  'wiki page since you started editing it.')

    return render_template(
        'wiki/edit.html',
        wiki_page=wiki_page,
        form=form,
        upload_form=upload_form
    )


@blueprint.route('/upload/<int:wiki_page_id>')
def upload(wiki_page_id):
    form = UploadForm()
    return render_template(
        'wiki/upload.html', 
        wiki_page_id=wiki_page_id,
        form=form
    )


@blueprint.route('/handle-upload', methods=['POST'])
def handle_upload():
    form = request.form
    wiki_page_id = int(form.get('wiki_page_id', None))
    upload_from_upload_page = form.get('upload_page', None)

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

        if upload_from_upload_page:
            wiki_page = get_object_or_404(
                WikiPage.select(
                    WikiPage.id,
                    WikiPage.markdown,
                    WikiPage.current_version,
                    WikiPage.modified_on),
                WikiPage.id==wiki_page_id
            )

            diff = make_patch(xstr(wiki_page.markdown), xstr(wiki_page.markdown)+file_markdown)
            wiki_page.update_content_after_upload(diff, file_markdown, file_html)

            return ''

    return file_markdown


@blueprint.route('/reference/<int:wiki_page_id>')
def reference(wiki_page_id):
    wiki_page = get_object_or_404(
        WikiPage.select(
            WikiPage.id,
            WikiPage.title),
        WikiPage.id==wiki_page_id
    )
    query = (WikiPage
             .select(WikiPage.id, WikiPage.title)
             .join(WikiReference, on=WikiReference.referencing)
             .where(WikiReference.referenced == wiki_page))
    wiki_referencing_pages = query.execute()

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
                         .where(WikiReference.referenced==wiki_page))
                wiki_referencing_pages = query.execute()
                for ref in wiki_referencing_pages:
                    new_markdown_content = ref.markdown.replace(old_markdown, new_markdown)
                    (WikiPageIndex
                     .update(markdown=new_markdown_content)
                     .where(WikiPageIndex.docid==ref.id)
                     .execute())

                    (WikiPage
                     .update(
                         markdown=new_markdown_content,
                         html=ref.html.replace(old_html, new_html))
                     .where(WikiPage.id==ref.id)
                     .execute())

                # update the diff of related wiki page versions
                query = (WikiPageVersion
                         .select(WikiPageVersion.id, WikiPageVersion.diff)
                         .where(WikiPageVersion.diff.contains(old_markdown)))
                wiki_page_versions = query.execute()
                for pv in wiki_page_versions:
                    (WikiPageVersion
                     .update(diff=pv.diff.replace(old_markdown, new_markdown))
                     .where(WikiPageVersion.id==pv.id)
                     .execute())

                (WikiPage
                 .update(title=new_title)
                 .where(WikiPage.id==wiki_page.id)
                 .execute())

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
        str(wiki_file_id),
        as_attachment=True,
        attachment_filename=fn
    )


@blueprint.route('/search', methods=['GET', 'POST'])
def search():
    keyword = request.args.get('keyword')
    start_date = request.args.get('start')
    end_date = request.args.get('end')
    current_page_number=request.args.get('page', default=1, type=int)
    number_per_page = 100
    kwargs = dict()
    form = SearchForm(keyword=keyword, start_date=start_date, end_date=end_date)

    if keyword and not keyword.isspace():
        filter = [WikiPageIndex.match(keyword)]
        if start_date:
            temp = datetime.strptime(start_date, '%m/%d/%Y').replace(tzinfo=TIMEZONE)
            filter.append(WikiPage.modified_on > temp.timestamp())
        if end_date:
            temp = datetime.strptime(end_date, '%m/%d/%Y')+timedelta(days=1)
            temp = temp.replace(tzinfo=TIMEZONE)
            filter.append(WikiPage.modified_on < temp.timestamp())

        query = (WikiPage
                 .select(WikiPage.id, WikiPage.title, WikiPage.modified_on)
                 .join(
                     WikiPageIndex,
                     on=(WikiPage.id==WikiPageIndex.docid))
                 .where(*filter)
                 .order_by(WikiPageIndex.rank(2.0, 1.0), WikiPage.modified_on.desc()))
        # TODO: add title-only search
        # query = query.where(WikiPage.title.contains(search_keyword))
        kwargs = paginate(query)

    if form.validate_on_submit():
        return redirect(url_for(
            '.search',
            keyword=form.keyword.data,
            start=form.start_date.data,
            end=form.end_date.data
        ))

    return render_template(
        'wiki/search.html',
        form=form,
        **kwargs
    )


@blueprint.route('/history/<int:wiki_page_id>', methods=['GET', 'POST'])
def history(wiki_page_id):
    wiki_page = get_object_or_404(
        WikiPage.select(),
        WikiPage.id==wiki_page_id
    )

    if wiki_page.current_version == 1:
        return redirect(url_for('.page', wiki_page_id=wiki_page_id))

    form = HistoryRecoverForm()
    if form.validate_on_submit():
        if form.version.data >= wiki_page.current_version:
            flash('Please enter an old version number.')
        else:
            query = (WikiPageVersion
                     .select()
                     .where(
                         WikiPageVersion.wiki_page==wiki_page,
                         WikiPageVersion.version>=form.version.data)
                     .order_by(WikiPageVersion.id.desc()))
            wiki_page_versions = query.execute()
            old_to_current_patches = [pv.diff for pv in wiki_page_versions]
            recovered_content = apply_patches(wiki_page.markdown, old_to_current_patches, revert=True)

            g.wiki_page = wiki_page
            g.wiki_refs = list(WikiPage
                               .select(WikiPage.id)
                               .join(WikiReference, on=WikiReference.referenced)
                               .where(WikiReference.referencing == wiki_page)
                               .execute())

            diff = make_patch(wiki_page.markdown, recovered_content)
            if diff:
                with db.atomic():
                    toc, html = markdown(recovered_content)
                    wiki_page.update_content(diff, recovered_content, html, toc)
            return redirect(url_for('.page', wiki_page_id=wiki_page.id))

    old_ver_num = request.args.get('version', default=wiki_page.current_version-1, type=int)
    new_ver_num = old_ver_num + 1
    if new_ver_num > wiki_page.current_version:
        return redirect(url_for(
            '.history',
            wiki_page_id=wiki_page_id,
            version=wiki_page.current_version-1
        ))

    query = (WikiPageVersion
             .select()
             .where(
                 WikiPageVersion.wiki_page==wiki_page,
                 WikiPageVersion.version>=old_ver_num)
             .order_by(WikiPageVersion.id.desc()))
    wiki_page_versions = query.execute()
    old_to_current_patches = [pv.diff for pv in wiki_page_versions]
    new_markdown = apply_patches(wiki_page.markdown, old_to_current_patches[:-1], revert=True)
    old_markdown = apply_patches(new_markdown, [old_to_current_patches[-1]], revert=True)

    diff = difflib.HtmlDiff()
    diff_table = diff.make_table(old_markdown.splitlines(), new_markdown.splitlines())
    diff_table = diff_table.replace('&nbsp;', ' ').replace(' nowrap="nowrap"', '')

    kwargs = dict()
    get_pagination_kwargs(kwargs, old_ver_num, wiki_page.current_version-1)

    return render_template(
        'wiki/history.html',
        wiki_page=wiki_page,
        form=form,
        wiki_page_versions=wiki_page_versions,
        old_ver_num=old_ver_num,
        new_ver_num=new_ver_num,
        diff_table=diff_table,
        **kwargs
    )


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
        wiki_pages = list()
        new_titles = form.textArea.data.splitlines()
        for new_title in new_titles:
            wiki_page = (WikiPage
                         .select(WikiPage.id, WikiPage.title)
                         .where(WikiPage.title==new_title)
                         .execute())
            if wiki_page:
                wiki_pages.append((wiki_page[0],))

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
             .order_by(WikiPage.modified_on.desc()))
    kwargs = paginate(query)

    return render_template(
        'wiki/changes.html',
        **kwargs
    )


@blueprint.route('/admin')
def group_admin():
    wiki_page_num = WikiPage.select().count()
    wiki_file_num = WikiFile.select().count()
    return render_template(
        'wiki/group_admin.html',
        wiki_page_num=wiki_page_num,
        wiki_file_num=wiki_file_num
    )


@blueprint.route('/all-pages')
def all_pages():
    query = (WikiPage
             .select(WikiPage.id, WikiPage.title, WikiPage.modified_on)
             .order_by(WikiPage.id))
    kwargs = paginate(query)

    return render_template(
        'wiki/all_pages.html',
        **kwargs
    )

# TODO: delete wiki pages


@blueprint.route('/all-files')
def all_files():
    query = (WikiFile
             .select()
             .order_by(WikiFile.id))
    kwargs = paginate(query)

    return render_template(
        'wiki/all_files.html',
        **kwargs
    )

# TODO: delete wiki files


@blueprint.route('/pdf/<int:wiki_page_id>')
def pdf(wiki_page_id):
    wiki_page = get_object_or_404(
        WikiPage.select(
            WikiPage.id,
            WikiPage.title,
            WikiPage.html,
            WikiPage.modified_on),
        WikiPage.id==wiki_page_id
    )

    return render_template(
        'wiki/pdf.html',
        wiki_page=wiki_page,
    )


@blueprint.route('/markdown')
def markdown_instructions():
    return render_template('wiki/markdown.html')

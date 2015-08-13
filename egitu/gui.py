#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2014-2015 Davide Andreoli <dave@gurumeditation.it>
#
# This file is part of Egitu.
#
# Egitu is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public
# License as published by the Free Software Foundation; either
# version 3 of the License, or (at your option) any later version.
#
# Egitu is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with Egitu.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import absolute_import, print_function

import os

from efl import elementary as elm
from efl.evas import Rectangle
from efl.elementary.window import StandardWindow
from efl.elementary.box import Box
from efl.elementary.button import Button
from efl.elementary.check import Check
from efl.elementary.entry import Entry, ELM_WRAP_NONE, utf8_to_markup
from efl.elementary.hoversel import Hoversel
from efl.elementary.icon import Icon, ELM_ICON_STANDARD
from efl.elementary.label import Label
from efl.elementary.genlist import Genlist, GenlistItemClass
from efl.elementary.menu import Menu
from efl.elementary.panes import Panes
from efl.elementary.popup import Popup
from efl.elementary.scroller import Scroller
from efl.elementary.table import Table
from efl.elementary.frame import Frame
from efl.elementary.separator import Separator

from egitu.utils import options, GravatarPict, ErrorPopup, FolderSelector, \
    CommandOutputEntry, recent_history_get, recent_history_push, \
    EXPAND_BOTH, EXPAND_HORIZ, EXPAND_VERT, FILL_BOTH, FILL_HORIZ, FILL_VERT
from egitu.dagview import DagGraph
from egitu.diffview import DiffViewer
from egitu.remotes import RemotesDialog
from egitu.branches import BranchesDialog
from egitu.pushpull import PullPopup, PushPopup
from egitu.vcs import git_clone


class RepoSelector(Popup):
    def __init__(self, app):
        self.app = app

        Popup.__init__(self, app.win)

        # title
        self.part_text_set('title,text', 'Recent Repositories')
        self.part_content_set('title,icon', Icon(self, standard='egitu'))

        # main table
        tb = Table(self, padding=(0,4), 
                   size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        self.content = tb
        tb.show()

        # sep
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_BOTH)
        tb.pack(sep, 0, 0, 1, 1)
        sep.show()

        # recent list
        itc = GenlistItemClass(item_style='no_icon',
                               text_get_func=self._gl_text_get)

        li = Genlist(self, homogeneous=True,
                     size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        li.callback_selected_add(self._recent_selected_cb)

        recents = recent_history_get()
        if recents:
            for path in recents:
                li.item_append(itc, path)
        else:
            item = li.item_append(itc, None)
            item.disabled = True
        li.show()

        r = Rectangle(self.evas, color=(0,0,0,0), size_hint_min=(300,200),
                      size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        tb.pack(r, 0, 1, 1, 1)
        tb.pack(li, 0, 1, 1, 1)

        # sep
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_BOTH)
        tb.pack(sep, 0, 2, 1, 1)
        sep.show()

        # buttons
        bt = Button(self, text='Close')
        bt.callback_clicked_add(lambda b: self.delete())
        self.part_content_set('button1', bt)

        bt = Button(self, text='Clone')
        bt.callback_clicked_add(self._clone_btn_cb)
        self.part_content_set('button2', bt)

        bt = Button(self, text='Open')
        bt.callback_clicked_add(self._load_btn_cb)
        self.part_content_set('button3', bt)

        #
        self.show()

    def _gl_text_get(self, obj, part, path):
        if path is None:
            return 'no recent repository'
        else:
            path, name = os.path.split(path)
            return '{} → {}'.format(name, path)

    def _load_btn_cb(self, bt):
        fs = FolderSelector(self)
        fs.callback_done_add(self._fs_done_cb)

    def _fs_done_cb(self, fs, path):
        fs.delete()
        if path and os.path.isdir(path):
            self.app.try_to_load(path)
            self.delete()
    
    def _clone_btn_cb(self, bt):
        self.delete()
        self.app.action_clone()

    def _recent_selected_cb(self, li, item):
        self.app.try_to_load(item.data)
        self.delete()


class ClonePopup(Popup):
    def __init__(self, parent, app):
        self.app = app

        Popup.__init__(self, parent)

        # title
        self.part_text_set('title,text', 'Clone')
        self.part_content_set('title,icon', Icon(self, standard='egitu'))

        # main table
        tb = Table(self, padding=(0,4),
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        self.content = tb
        tb.show()

        # sep
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_HORIZ)
        tb.pack(sep, 0, 0, 2, 1)
        sep.show()

        # url
        en = Entry(self, single_line=True, scrollable=True,
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        en.part_text_set('guide', 'Path or URL to clone')
        tb.pack(en, 0, 1, 2, 1)
        en.show()
        self.url_entry = en

        # parent folder
        en = Entry(self, single_line=True, scrollable=True,
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        en.part_text_set('guide', 'Parent folder to clone into')
        tb.pack(en, 0, 2, 1, 1)
        en.show()

        bt = Button(self, text='', content=Icon(self, standard='folder'))
        bt.callback_clicked_add(self._folder_clicked_cb)
        tb.pack(bt, 1, 2, 1, 1)
        bt.show()
        self.folder_entry = en

        # shallow check
        ck = Check(self, text='Shallow (no history and no branches, faster)',
                   size_hint_expand=EXPAND_BOTH, size_hint_align=(0.0,0.5))
        tb.pack(ck, 0, 3, 2, 1)
        ck.show()
        self.shallow_check = ck

        # output entry
        en = CommandOutputEntry(self, min_size=(400, 150))
        tb.pack(en, 0, 4, 2, 1)
        en.show()
        self.output_entry = en

        # sep
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_HORIZ)
        tb.pack(sep, 0, 5, 2, 1)
        sep.show()

        # bottons
        bt = Button(self, text='Close')
        bt.callback_clicked_add(lambda b: self.delete())
        self.part_content_set('button1', bt)
        bt.show()
        self.close_btn = bt

        bt = Button(self, text='Clone')
        bt.callback_clicked_add(self._clone_clicked_cb)
        self.part_content_set('button2', bt)
        bt.show()
        self.clone_btn = bt

        #
        self.show()

    def op_start(self):
        self.clone_btn.disabled = True
        self.close_btn.disabled = True
        self.output_entry.text = None
        self.output_entry.pulse_start()

    def op_end(self):
        self.output_entry.pulse_stop()
        self.clone_btn.disabled = False
        self.close_btn.disabled = False

    def _folder_clicked_cb(self, btn):
        fs = FolderSelector(self)
        fs.callback_done_add(self._fs_done_cb)

    def _fs_done_cb(self, fs, path):
        fs.delete()
        if path and os.path.isdir(path):
            self.folder_entry.text = path

    def _clone_clicked_cb(self, btn):
        url = self.url_entry.text
        folder = self.folder_entry.text
        shallow = self.shallow_check.state

        if not url:
            self.output_entry.error_set('Invalid URL')
            return

        if not folder or not os.path.isdir(folder):
            self.output_entry.error_set('Invalid folder')
            return

        repo_name = url.split('/')[-1].replace('.git', '')
        folder = os.path.join(folder, repo_name)
        if os.path.isdir(folder):
            self.output_entry.error_set('Repository folder:<br>%s<br>already exists' % folder)
            return

        self.op_start()
        git_clone(self._clone_done_cb, self._clone_progress_cb,
                  url, folder, shallow)

    def _clone_progress_cb(self, line, sep):
        self.output_entry.append_raw(line, sep)

    def _clone_done_cb(self, success, folder):
        self.op_end()
        if success:
            self.output_entry.successfull()
            self.app.try_to_load(folder)
        else:
            self.output_entry.failure()


class MainMenuButton(Button):
    def __init__(self, app):
        self.app = app
        self._menu = None
        Button.__init__(self, app.win, text='Menu',
                        content=Icon(app.win, standard='home'))
        self.callback_pressed_add(self._button_pressed_cb)

    def _button_pressed_cb(self, btn):
        # close the menu if it is visible yet
        if self._menu and self._menu.visible:
            self._menu.delete()
            self._menu = None
            return

        # build a new menu
        m = Menu(self.top_widget)
        self._menu = m

        # main actions
        disabled = self.app.repo is None
        m.item_add(None, 'Refresh', 'refresh', 
                   self.app.action_reload_repo).disabled = disabled
        m.item_add(None, 'Open...', 'folder',
                   self.app.action_open)
        m.item_add(None, 'Edit branches...', 'git-branch', 
                   self.app.action_branches).disabled = disabled
        m.item_add(None, 'Edit remotes...', 'git-remote', 
                   self.app.action_remotes).disabled = disabled
        m.item_separator_add()

        # general options
        it_gen = m.item_add(None, 'General', 'preference')

        it = m.item_add(it_gen, 'Use relative dates', None,
                           self._item_check_opts_cb, 'date_relative')
        it.content = Check(self, state=options.date_relative)

        it_gravatar = m.item_add(it_gen, 'Gravatar')
        for name in ('mm', 'identicon', 'monsterid', 'wavatar', 'retro'):
            icon = 'arrow_right' if name == options.gravatar_default else None
            m.item_add(it_gravatar, name, icon,  self._item_gravatar_cb)
        m.item_separator_add(it_gravatar)
        m.item_add(it_gravatar, 'Clear icons cache', 'delete',
                   lambda m,i: GravatarPict.clear_icon_cache())

        # dag options
        it_dag = m.item_add(None, 'Dag', 'preference')

        it = m.item_add(it_dag, 'Show remote refs', None,
                        self._item_check_opts_cb, 'show_remotes_in_dag')
        it.content = Check(self, state=options.show_remotes_in_dag)

        it = m.item_add(it_dag, 'Show commit messagges', None,
                        self._item_check_opts_cb, 'show_message_in_dag')
        it.content = Check(self, state=options.show_message_in_dag)

        # diff options
        it_diff = m.item_add(None, 'Diff', 'preference')

        it = m.item_add(it_diff, 'Wrap long lines', None,
                        self._item_wrap_line_cb)
        it.content = Check(self, state=options.diff_text_wrap)

        it_font = m.item_add(it_diff, 'Font face')
        for face in ('Sans', 'Mono'):
            icon = 'arrow_right' if face == options.diff_font_face else None
            m.item_add(it_font, face, icon, self._item_font_face_cb)

        it_font = m.item_add(it_diff, 'Font size')
        for size in (8, 9, 10, 11, 12, 13, 14):
            icon = 'arrow_right' if size == options.diff_font_size else None
            m.item_add(it_font, str(size), icon, self._item_font_size_cb)

        # quit item
        m.item_separator_add()
        m.item_add(None, 'About', 'info', self.app.action_about)
        m.item_add(None, 'Quit', 'close', self.app.action_quit)


        # show the menu
        x, y, w, h = self.geometry
        m.move(x, y + h)
        m.show()

    def _item_check_opts_cb(self, menu, item, opt):
        setattr(options, opt, not item.content.state)
        self.app.action_update_dag()

    def _item_gravatar_cb(self, menu, item):
        if options.gravatar_default != item.text:
            options.gravatar_default = item.text
            GravatarPict.clear_icon_cache()

    def _item_wrap_line_cb(self, menu, item):
        options.diff_text_wrap = not item.content.state
        self.app.win.diff_view.refresh_diff()

    def _item_font_face_cb(self, menu, item):
        options.diff_font_face = item.text
        self.app.action_update_diffview()

    def _item_font_size_cb(self, menu, item):
        options.diff_font_size = int(item.text)
        self.app.action_update_diffview()


class EditableDescription(Entry):
    def __init__(self, app):
        self.app = app
        Entry.__init__(self, app.win, single_line=True,
                       text='No repository loaded',
                       size_hint_weight=EXPAND_HORIZ,
                       size_hint_align=FILL_HORIZ)
        self.callback_clicked_add(self._click_cb)
        self.callback_activated_add(self._done_cb, save=True)
        self.callback_unfocused_add(self._done_cb, save=False)
        self.callback_aborted_add(self._done_cb, save=False)
        self.go_passive()

    def _click_cb(self, entry):
        if self.app.repo is not None and not self.editable:
            self.go_active()

    def go_passive(self):
        if hasattr(self, 'orig_text'):
            del self.orig_text
        self.editable = False
        self.scrollable = False
        self.text_style_user_push("DEFAULT='font_size=18'")
        self.tooltip_text_set('Click to edit description')

    def go_active(self):
        self.orig_text = self.text
        self.focus = False
        self.editable = True
        self.scrollable = True
        self.text_style_user_push("DEFAULT='font_size=18'")
        self.tooltip_unset()
        ic = Icon(self, standard='close', size_hint_min=(20,20))
        ic.callback_clicked_add(self._done_cb, False)
        self.part_content_set('end', ic)
        self.focus = True

    def _done_cb(self, entry, save):
        if save is True:
            self.app.repo.description_set(self.text, self._description_set_cb)
        else:
            self.text = self.orig_text
        self.go_passive()

    def _description_set_cb(self, success):
        # TODO alert if fail
        self.text = self.app.repo.description


class EgituWin(StandardWindow):
    def __init__(self, app):
        self.app = app
        self.branch_selector = None
        self.caption_label = None
        self.status_label = None
        self.graph = None
        self.diff_view = None

        StandardWindow.__init__(self, 'egitu', 'Efl GIT gUi - Egitu',
                                size=(800,600), autodel=True)
        self.callback_delete_request_add(lambda o: elm.exit())

    def populate(self):
        # main vertical box
        box = Box(self, size_hint_weight = EXPAND_BOTH)
        self.resize_object_add(box)
        box.show()

        ### header
        fr = Frame(self, style='outdent_bottom', size_hint_weight=EXPAND_HORIZ,
                   size_hint_align=FILL_BOTH)
        box.pack_end(fr)
        fr.show()

        tb = Table(self, padding=(3,3),
                   size_hint_weight=EXPAND_HORIZ, size_hint_align=FILL_BOTH)
        fr.content = tb
        tb.show()

        # main menu button
        bt = MainMenuButton(self.app)
        tb.pack(bt, 0, 0, 1, 1)
        bt.show()

        # editable description entry
        self.caption_label = EditableDescription(self.app)
        tb.pack(self.caption_label, 1, 0, 1, 1)
        self.caption_label.show()

        # status label + button
        self.status_label = lb = Entry(self, single_line=True, editable=False)
        tb.pack(lb, 2, 0, 1, 1)
        lb.show()

        # branch selector
        self.branch_selector = Hoversel(self, text='Branch', disabled=True,
                                      content=Icon(self, standard='git-branch'))
        self.branch_selector.callback_selected_add(self.branch_selected_cb)
        tb.pack(self.branch_selector, 3, 0, 1, 1)
        self.branch_selector.show()

        # pull button
        bt = Button(self, text='Pull', disabled=True,
                    content=Icon(self, standard='git-pull'))
        bt.callback_clicked_add(self.app.action_pull)
        tb.pack(bt, 4, 0, 1, 1)
        bt.show()
        self.pull_btn = bt

        # push button
        bt = Button(self, text='Push', disabled=True,
                    content=Icon(self, standard='git-push'))
        bt.callback_clicked_add(self.app.action_push)
        tb.pack(bt, 5, 0, 1, 1)
        bt.show()
        self.push_btn = bt

        ### Main content (left + right panes)
        panes = Panes(self, content_left_size = 0.5,
                       size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        box.pack_end(panes)
        panes.show()

        # the dag graph inside a scroller on the left
        self.graph = DagGraph(self, self.app)
        fr = Frame(self, style='pad_medium', content=self.graph)
        scr = Scroller(self, content=fr,
                       size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        scr.bounce_set(0, 1)
        panes.part_content_set('left', scr)

        # the diff viewer on the right
        self.diff_view = DiffViewer(self, self.app)
        self.diff_view.size_hint_weight = EXPAND_BOTH
        self.diff_view.size_hint_align = 0.0, 0.0
        panes.part_content_set('right', self.diff_view)

        #
        self.show()

    def update_all(self):
        self.update_header()
        self.graph.populate(self.app.repo)

    def update_header(self):
        repo = self.app.repo

        # update window title
        self.title = '%s [%s]' % (repo.name, repo.current_branch)

        # update repo description
        if self.app.repo is None:
            self.caption_label.text = 'No repository loaded'
        elif repo.description:
            self.caption_label.text = repo.description
        else:
            self.caption_label.text = 'Unnamed repository; click to edit.'

        # update the branch selector
        if self.app.repo is None:
            self.branch_selector.clear()
            self.branch_selector.text = 'No repository'
            self.branch_selector.disabled = True
        else:
            self.branch_selector.clear()
            self.branch_selector.disabled = False
            for branch in repo.branches_names:
                if branch == repo.current_branch:
                    self.branch_selector.item_add(branch, 'arrow_right',
                                                  ELM_ICON_STANDARD)
                else:
                    self.branch_selector.item_add(branch)
            self.branch_selector.text = repo.current_branch or 'Unknown'

        # update the status label
        if repo.status.is_merging:
            text = "<warning>!! MERGING !!</warning>"
        elif repo.status.is_cherry:
            text = "<warning>CHERRY-PICKING</warning>"
        elif repo.status.is_reverting:
            text = "<warning>REVERTING</warning>"
        elif repo.status.is_bisecting:
            text = "<warning>BISECTING</warning>"
        elif repo.status.ahead == 1 and repo.status.is_clean:
            text = '<warning>Ahead by 1 commit</warning>'
        elif repo.status.ahead > 1 and repo.status.is_clean:
            text = '<warning>Ahead by {} commits</warning>'.format(repo.status.ahead)
        elif repo.status.is_clean:
            text = '<success>Status is clean!</success>'
        else:
            text = '<warning>Status is dirty !!!</warning>'

        self.status_label.text = text
        self.status_label.tooltip_text_set(repo.status.textual)
        
        # push/pull buttons
        self.pull_btn.disabled = self.push_btn.disabled = self.app.repo is None

    def branch_selected_cb(self, hoversel, item):
        def _switch_done_cb(success, err_msg=None):
            if success:
                self.update_header()
                self.graph.populate(self.app.repo)
            else:
                ErrorPopup(self, 'Operation Failed', utf8_to_markup(err_msg))

        self.app.repo.current_branch_set(item.text, _switch_done_cb)

    def show_commit(self, commit):
        self.diff_view.commit_set(commit)

    def _binds_cb_refresh(self, src, key, event):
        self.refresh()
        return True

    def _binds_cb_open(self, src, key, event):
        RepoSelector(self.app)
        return True

    def _binds_cb_quit(self, src, key, event):
        elm.exit()
        return True

    def _binds_cb_branches(self, src, key, event):
        BranchesDialog(self.app, self)
        return True

    def _binds_cb_push(self, src, key, event):
        PushPopup(self, self.app)
        return True

    def _binds_cb_pull(self, src, key, event):
        PullPopup(self, self.app)
        return True

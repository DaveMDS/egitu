#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2014 Davide Andreoli <dave@gurumeditation.it>
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

from __future__ import absolute_import

import os

from efl import elementary as elm
from efl.evas import Rectangle
from efl.elementary.window import StandardWindow
from efl.elementary.box import Box
from efl.elementary.button import Button
from efl.elementary.check import Check
from efl.elementary.entry import Entry
from efl.elementary.fileselector import Fileselector
from efl.elementary.hoversel import Hoversel
from efl.elementary.icon import Icon, ELM_ICON_STANDARD
from efl.elementary.label import Label
from efl.elementary.list import List
from efl.elementary.menu import Menu
from efl.elementary.panes import Panes
from efl.elementary.popup import Popup
from efl.elementary.scroller import Scroller
from efl.elementary.table import Table
from efl.elementary.frame import Frame

from egitu.utils import options, theme_resource_get, GravatarPict, \
    recent_history_get, recent_history_push, \
    EXPAND_BOTH, EXPAND_HORIZ, FILL_BOTH, FILL_HORIZ
from egitu.dagview import DagGraph
from egitu.diffview import DiffViewer
from egitu.vcs import repo_factory


def LOG(text):
    print(text)
    # pass


class RepoSelector(Popup):
    def __init__(self, win, url=None):
        Popup.__init__(self, win)
        self.win = win

        # title
        self.part_text_set('title,text', 'Recent Repositories')
        ic = Icon(self, file=theme_resource_get('egitu.png'))
        self.part_content_set('title,icon', ic)

        # content: recent list
        li = List(self, size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        li.callback_activated_add(self.recent_selected_cb)

        recents = recent_history_get()
        if recents:
            for recent_url in recents:
                path, name = os.path.split(recent_url)
                item = li.item_append(name)
                item.data['url'] = recent_url
        else:
            item = li.item_append('no recent repository')
            item.disabled = True
        li.show()

        # table+rect to respect min size :/
        tb = Table(self, size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        r = Rectangle(self.evas, color=(0,0,0,0), size_hint_min=(200,200),
                      size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        tb.pack(r, 0, 0, 1, 1)
        tb.pack(li, 0, 0, 1, 1)
        self.content = tb

        # popup auto-list - not expand well :(
        # self.size_hint_weight = EXPAND_BOTH
        # self.size_hint_align = FILL_BOTH
        # self.size_hint_min = 400, 400
        # self.item_append('no recent repos', None)
        # self.item_append('asd2', None)
        # self.item_append('asd2', None)

        # buttons
        bt = Button(self, text='Open')
        bt.callback_clicked_add(self.load_btn_cb)
        self.part_content_set('button1', bt)

        bt = Button(self, text='Clone (TODO)')
        bt.disabled = True
        self.part_content_set('button2', bt)

        bt = Button(self, text='Create (TODO)')
        bt.disabled = True
        self.part_content_set('button3', bt)

        if url is not None:
            self.try_to_load(url)
        else:
            self.callback_block_clicked_add(lambda p: p.delete())
            self.show()

    def load_btn_cb(self, bt):
        fs = FolderSelector(self)
        fs.callback_done_add(self.fs_done_cb)

    def fs_done_cb(self, fs, path):
        fs.delete()
        if path and os.path.isdir(path):
            self.try_to_load(path)

    def recent_selected_cb(self, li, item):
        self.try_to_load(item.data['url'])

    def try_to_load(self, path):
        repo = repo_factory(path)
        if repo:
            repo.load_from_url(path, self.load_done_cb, repo)
        else:
            self.show()

    def load_done_cb(self, success, repo):
        if success is True:
            # save to recent history
            recent_history_push(repo.url)

            # show the new loaded repo
            self.win.repo_set(repo)
            self.delete()
        else:
            self.show()


class FolderSelector(Fileselector):
    def __init__(self, parent):
        Fileselector.__init__(self, parent, is_save=False, folder_only=True,
                        size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        self.path = os.getcwd()

        # table+rect to respect min size :/
        tb = Table(self, size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        r = Rectangle(self.evas, color=(0,0,0,0), size_hint_min=(300,300),
                      size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        tb.pack(r, 0, 0, 1, 1)
        tb.pack(self, 0, 0, 1, 1)

        self.popup = Popup(parent)
        self.popup.part_text_set('title,text', 'Choose repository')
        self.popup.content = tb
        self.popup.show()

        self.show()

    def delete(self):
        self.popup.delete()


class EgituMenu(Menu):
    def __init__(self, win, parent):
        Menu.__init__(self, win)
        self.win = win

        # main actions
        self.item_add(None, "Refresh", "refresh", self._item_refresh_cb)
        self.item_add(None, "Open", "folder", self._item_open_cb)
        self.item_separator_add()

        # general options
        it_gen = self.item_add(None, "General", "preference")
        
        it = self.item_add(it_gen, "Use relative dates", None,
                           self._item_check_opts_cb, 'date_relative')
        it.content = Check(self, state=options.date_relative)

        it_gravatar = self.item_add(it_gen, "Gravatar")
        for name in ('mm', 'identicon', 'monsterid', 'wavatar', 'retro'):
            icon = "arrow_right" if name == options.gravatar_default else None
            self.item_add(it_gravatar, name, icon,  self._item_gravatar_cb)
        self.item_separator_add(it_gravatar)
        self.item_add(it_gravatar, 'Clear icons cache', 'delete',
                      lambda m,i: GravatarPict.clear_icon_cache())

        # dag options
        it_dag = self.item_add(None, "Dag", "preference")

        it = self.item_add(it_dag, "Show remote refs", None,
                           self._item_check_opts_cb, 'show_remotes_in_dag')
        it.content = Check(self, state=options.show_remotes_in_dag)

        it = self.item_add(it_dag, "Show commit messagges", None,
                           self._item_check_opts_cb, 'show_message_in_dag')
        it.content = Check(self, state=options.show_message_in_dag)

        # diff options
        it_diff = self.item_add(None, "Diff", "preference")

        it = self.item_add(it_diff, "Wrap long lines", None,
                           self._item_wrap_line_cb)
        it.content = Check(self, state=options.diff_text_wrap)

        it_font = self.item_add(it_diff, "Font face")
        for face in ('Sans', 'Mono'):
            icon = "arrow_right" if face == options.diff_font_face else None
            self.item_add(it_font, face, icon, self._item_font_face_cb)

        it_font = self.item_add(it_diff, "Font size")
        for size in (8, 9, 10, 11, 12, 13, 14):
            icon = "arrow_right" if size == options.diff_font_size else None
            self.item_add(it_font, str(size), icon, self._item_font_size_cb)

        x, y, w, h = parent.geometry
        self.move(x + w, y + 10)
        self.show()

    def _item_refresh_cb(self, menu, item):
        def _refresh_done_cb(success):
            self.win.update_header()
            self.win.graph.populate(self.win.repo)
        self.win.repo.refresh(_refresh_done_cb)

    def _item_open_cb(self, menu, item):
        RepoSelector(self.win)

    def _item_check_opts_cb(self, menu, item, opt):
        setattr(options, opt, not item.content.state)
        self.win.graph.populate(self.win.repo)

    def _item_gravatar_cb(self, menu, item):
        if options.gravatar_default != item.text:
            options.gravatar_default = item.text
            GravatarPict.clear_icon_cache()

    def _item_wrap_line_cb(self, menu, item):
        options.diff_text_wrap = not item.content.state
        self.win.diff_view.refresh_diff()

    def _item_font_face_cb(self, menu, item):
        options.diff_font_face = item.text
        self.win.diff_view.refresh_diff()

    def _item_font_size_cb(self, menu, item):
        options.diff_font_size = int(item.text)
        self.win.diff_view.refresh_diff()


class EditableDescription(Entry):
    def __init__(self, win):
        self.win = win
        Entry.__init__(self, win, editable=True, single_line=True,
                       size_hint_weight=EXPAND_HORIZ, size_hint_align=FILL_HORIZ)
        self.text_style_user_push("DEFAULT='font_size=18'")
        self.tooltip_text_set("Click to edit description")
        self.callback_clicked_add(self._click_cb)
        self.callback_activated_add(self._done_cb, save=True)
        self.callback_aborted_add(self._done_cb, save=False)

    def _click_cb(self, entry):
        self.scrollable = True
        self.tooltip_unset()
        self.orig_text = self.text
        ic = Icon(self, standard="close", size_hint_min=(20,20))
        ic.callback_clicked_add(self._done_cb, False)
        self.part_content_set("end", ic)

    def _done_cb(self, entry, save):
        self.scrollable = False
        self.tooltip_text_set("Click to edit description")
        self.focus = False
        if save is True:
            self.win.repo.description_set(self.text, self._description_set_cb)
        else:
            self.text = self.orig_text
            del self.orig_text

    def _description_set_cb(self, success):
        # TODO alert if fail
        self.text = self.win.repo.description


class EgituWin(StandardWindow):
    def __init__(self):
        self.repo = None
        self.branch_selector = None
        self.caption_label = None
        self.status_label = None
        self.graph = None
        self.diff_view = None

        StandardWindow.__init__(self, "egitu", "Efl GIT gUi - Egitu")
        self.autodel_set(True)
        self.callback_delete_request_add(lambda o: elm.exit())

        # main vertical box
        box = Box(self, size_hint_weight = EXPAND_BOTH)
        self.resize_object_add(box)
        box.show()

        # header
        fr = Frame(self, style="pad_medium")
        fr.size_hint_weight = EXPAND_HORIZ
        fr.size_hint_align = FILL_BOTH
        box.pack_end(fr)
        fr.show()

        tb = Table(self)
        tb.size_hint_weight = EXPAND_HORIZ
        tb.size_hint_align = FILL_BOTH
        fr.content = tb
        tb.show()

        # main menu button
        bt = Button(self, text='Menu')
        bt.content = Icon(self, standard='home')
        bt.callback_clicked_add(lambda b: EgituMenu(self, b))
        tb.pack(bt, 0, 0, 1, 1)
        bt.show()
       
        # editable description entry
        self.caption_label = ed = EditableDescription(self)
        tb.pack(ed, 1, 0, 1, 1)
        ed.show()

        # branch selector
        lb = Label(self, text='On branch')
        tb.pack(lb, 2, 0, 1, 1)
        lb.show()

        self.branch_selector = brsel = Hoversel(self, text='none')
        brsel.callback_selected_add(self.branch_selected_cb)
        tb.pack(brsel, 3, 0, 1, 1)
        brsel.show()

        # status label + button
        self.status_label = lb = Entry(self, single_line=True, editable=False)
        tb.pack(lb, 4, 0, 1, 1)
        lb.show()

        # self.commit_button = bt = Button(self, text="commit! (TODO)")
        # bt.disabled = True
        # tb.pack(bt, 5, 0, 1, 1)

        ### Main content (left + right panes)
        panes = Panes(self, content_left_size = 0.5,
                       size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        box.pack_end(panes)
        panes.show()

        # the dag graph inside a scroller on the left
        self.graph = DagGraph(self, self.repo)
        fr = Frame(self, style="pad_medium", content=self.graph)
        scr = Scroller(self, content=fr,
                       size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        panes.part_content_set("left", scr)

        # the diff viewer on the right
        self.diff_view = DiffViewer(self, self.repo)
        self.diff_view.size_hint_weight = EXPAND_BOTH
        self.diff_view.size_hint_align = 0.0, 0.0
        panes.part_content_set("right", self.diff_view)


        self.resize(800, 600)
        
        self.show()

    def repo_set(self, repo):
        self.repo = repo
        self.update_header()
        self.graph.populate(repo)
        
    def update_header(self):
        # update the branch selector
        try:
            self.branch_selector.clear()
            for branch in self.repo.branches:
                if branch == self.repo.current_branch:
                    self.branch_selector.item_add(branch, 'arrow_right', ELM_ICON_STANDARD)
                else:
                    self.branch_selector.item_add(branch)
            self.branch_selector.text = self.repo.current_branch
            self.branch_selector.content = Icon(self, standard='arrow_right')
        except:
            self.branch_selector.text = "Unknown"

        # update window title
        self.title = "%s [%s]" % (self.repo.name, self.repo.current_branch)

        # update repo description
        self.caption_label.text = self.repo.description or \
                                  'Unnamed repository; click to edit.'

        # update the status
        if self.repo.status.ahead == 1 and self.repo.status.is_clean:
            text = "<warning>Ahead by 1 commit</warning>"
        elif self.repo.status.ahead > 1 and self.repo.status.is_clean:
            text = "<warning>Ahead by {} commits</warning>".format(self.repo.status.ahead)
        elif self.repo.status.is_clean:
            text = "<success>Status is clean!</success>"
            # self.commit_button.hide()
        else:
            text = "<warning>Status is dirty !!!</warning>"
            # self.commit_button.show()

        self.status_label.text = text
        self.status_label.tooltip_text_set(self.repo.status.textual)

    def branch_selected_cb(self, flipselector, item):
        # TODO alert if unstaged changes are present
        def _switch_done_cb(success):
            self.update_header()
            self.graph.populate(self.repo)

        self.repo.current_branch_set(item.text, _switch_done_cb)

    def show_commit(self, commit):
        self.diff_view.commit_set(self.repo, commit)



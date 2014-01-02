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

import os

from efl import elementary as elm
from efl.evas import Rectangle
from efl.elementary.window import StandardWindow
from efl.elementary.box import Box
from efl.elementary.button import Button
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

from egitu_utils import options, theme_resource_get, \
    EXPAND_BOTH, EXPAND_HORIZ, FILL_BOTH, FILL_HORIZ
from egitu_gui_dag import DagGraph
from egitu_gui_commitbox import CommitInfoBox
from egitu_vcs import repo_factory


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
        if len(options.recent_repos) < 1:
            item = li.item_append('no recent repository')
            item.disabled = True
        else:
            for recent_url in options.recent_repos:
                path, name = os.path.split(recent_url)
                item = li.item_append(name)
                item.data['url'] = recent_url
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
            # save to recent history (popping to the top if necessary)
            if repo.url in options.recent_repos:
                options.recent_repos.remove(repo.url)
            options.recent_repos.insert(0, repo.url)

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
        self.item_add(None, "Refresh", "refresh", self._item_refresh_cb)
        self.item_add(None, "Open", "open", self._item_open_cb)
        x, y, w, h = parent.geometry
        self.move(x + w, y + 10)
        self.show()

    def _item_refresh_cb(self, menu, item):
        def _refresh_done_cb(success):
            self.win.update_header()
            self.win.graph.update()
        self.win.repo.refresh(_refresh_done_cb)

    def _item_open_cb(self, menu, item):
        RepoSelector(self.win)

class EditableDescription(Entry):
    def __init__(self, win):
        self.win = win
        Entry.__init__(self, win, editable=True, single_line=True, scale=1.5,
                       size_hint_weight=EXPAND_HORIZ, size_hint_align=FILL_HORIZ)
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
        self.commit_list = None
        # self.commit_button = None

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
        self.status_label = lb = Label(self)
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

        # the commit box on the right
        self.commit_info = CommitInfoBox(self, self.repo, show_diff=True)
        self.commit_info.size_hint_weight = EXPAND_BOTH
        self.commit_info.size_hint_align = 0.0, 0.0
        panes.part_content_set("right", self.commit_info)


        self.resize(700, 500)
        
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
                    self.branch_selector.item_add(branch, 'home', ELM_ICON_STANDARD)
                else:
                    self.branch_selector.item_add(branch)
            self.branch_selector.text = self.repo.current_branch
            self.branch_selector.content = Icon(self, standard='home')
        except:
            self.branch_selector.text = "Unknown"

        # update window title
        self.title = "%s [%s]" % (self.repo.name, self.repo.current_branch)

        # update repo description
        self.caption_label.text = self.repo.description or \
                                  'Unnamed repository; click to edit.'

        # update the status
        if self.repo.status.is_clean:
            self.status_label.text = "<hilight>Status is clean!</>"
            self.status_label.tooltip_text_set("# On branch %s <br>nothing to commit (working directory clean)" % self.repo.current_branch)
            # self.commit_button.hide()
        else:
            self.status_label.text = "<hilight>Status is dirty !!!</>"
            # TODO tooltip
            # self.commit_button.show()

    def branch_selected_cb(self, flipselector, item):
        # TODO alert if unstaged changes are present
        def _switch_done_cb(success):
            self.update_header()
            self.graph.update()

        self.repo.current_branch_set(item.text, _switch_done_cb)

    def show_commit(self, commit):
        self.commit_info.commit_set(self.repo, commit)



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

from __future__ import absolute_import, print_function, unicode_literals

from efl.elementary.window import DialogWindow
from efl.elementary.box import Box
from efl.elementary.button import Button
from efl.elementary.separator import Separator
from efl.elementary.frame import Frame
from efl.elementary.icon import Icon
from efl.elementary.label import Label
from efl.elementary.entry import Entry, utf8_to_markup
from efl.elementary.panes import Panes
from efl.elementary.genlist import Genlist, GenlistItemClass, \
    ELM_LIST_COMPRESS, ELM_OBJECT_SELECT_MODE_ALWAYS

from egitu.gui import DiffedEntry
from egitu.branches import MergeBranchPopup
from egitu.utils import ComboBox, ErrorPopup, CommitTooltip, \
    EXPAND_BOTH, FILL_BOTH, EXPAND_HORIZ, FILL_HORIZ


class CommitsList(Genlist):
    def __init__(self, parent, **kargs):
        Genlist.__init__(self, parent, homogeneous=True, mode=ELM_LIST_COMPRESS,
                         size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH,
                         **kargs)

        self._itc = GenlistItemClass(item_style='default_style',
                                     text_get_func=self._gl_text_get,
                                     content_get_func=self._gl_content_get)

    def append(self, commit):
        self.item_append(self._itc, commit)

    def _gl_text_get(self, gl, part, commit):
        return '<b>{}:</b> {}'.format(commit.author, commit.title)

    def _gl_content_get(self, gl, part, commit):
        if part == 'elm.swallow.icon':
            return Icon(gl, standard='git-commit')
        else:
            en = Entry(gl, editable=False, single_line=True,
                       text='<name>{}</>'.format(commit.sha_short))
            # en.tooltip_window_mode = True  # TODO why this fail??
            en.tooltip_content_cb_set(self._tooltip_content_cb, commit)
            return en

    def _tooltip_content_cb(self, entry, tooltip, commit):
        # print(tooltip)  # TODO tooltip param is wrong, report on phab !!
        return CommitTooltip(tooltip, commit, show_full_msg=True)


class CompareDialog(DialogWindow):
    def __init__(self, parent, app, target=None):
        self.app = app
        self._selected_item = None

        DialogWindow.__init__(self, parent, 'Egitu-compare', 'Compare tool',
                              size=(500,500), autodel=True)

        # main vertical box (inside a padding frame)
        vbox = Box(self, padding=(0, 6), size_hint_expand=EXPAND_BOTH,
                   size_hint_fill=FILL_BOTH)
        fr = Frame(self, style='pad_medium', size_hint_expand=EXPAND_BOTH)
        self.resize_object_add(fr)
        fr.content = vbox
        fr.show()
        vbox.show()

        # two combos
        hbox = Box(self, horizontal=True, padding=(6,0),
                   size_hint_expand=EXPAND_HORIZ, size_hint_fill=FILL_HORIZ)
        vbox.pack_end(hbox)
        hbox.show()

        cb1 = ComboBox(self, text=app.repo.status.current_branch.name)
        cb1.icon = Icon(cb1, standard='git-branch')
        cb1.callback_selected_add(lambda c: self.compare())
        hbox.pack_end(cb1)
        cb1.show()
        self.base_combo = cb1

        lb = Label(self, text='<b>...</b>', size_hint_align=(0.5,1.0))
        hbox.pack_end(lb)
        lb.show()

        cb2 = ComboBox(self, text=target or app.repo.status.current_branch.name)
        cb2.icon = Icon(cb1, standard='git-branch')
        cb2.callback_selected_add(lambda c: self.compare())
        hbox.pack_end(cb2)
        cb2.show()
        self.compare_combo = cb2

        for branch in app.repo.branches:
            cb1.item_append(branch.name, 'git-branch')
            cb2.item_append(branch.name, 'git-branch')
        for branch in app.repo.remote_branches:
            cb1.item_append(branch, 'git-branch')
            cb2.item_append(branch, 'git-branch')
        for tag in app.repo.tags:
            cb1.item_append(tag.name, 'git-tag')
            cb2.item_append(tag.name, 'git-tag')

        # vertical panes
        panes = Panes(self, horizontal=True, content_left_size=0.25,
                      size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        vbox.pack_end(panes)
        panes.show()

        # commit list (inside a frame)
        li = CommitsList(panes, select_mode=ELM_OBJECT_SELECT_MODE_ALWAYS)
        li.callback_selected_add(self._list_selected_cb)
        li.show()
        self.commits_list = li

        fr = Frame(panes, content=li)
        panes.part_content_set('left', fr)
        fr.show()
        self.commits_frame = fr

        # diff
        de = DiffedEntry(panes)
        panes.part_content_set('right', de)
        de.show()
        self.diff_entry = de

        # buttons
        hbox = Box(self, horizontal=True,
                   size_hint_expand=EXPAND_HORIZ, size_hint_fill=FILL_BOTH)
        vbox.pack_end(hbox)
        hbox.show()

        bt = Button(self, text='Merge', content=Icon(self, standard='git-merge'))
        bt.callback_clicked_add(lambda b: MergeBranchPopup(self, self.app,
                                                    self.compare_combo.text))
        hbox.pack_end(bt)
        bt.show()
        self.merge_btn = bt

        lb = Entry(self, single_line=True, editable=False)
        hbox.pack_end(lb)
        lb.show()
        self.merge_label = lb

        sep = Separator(self, size_hint_expand=EXPAND_HORIZ)
        hbox.pack_end(sep)

        bt = Button(self, text='Close')
        bt.callback_clicked_add(lambda b: self.delete())
        hbox.pack_end(bt)
        bt.show()

        #
        self.compare()
        self.show()

    def compare(self):
        self.commits_list.clear()
        self.diff_entry.text = None
        self.app.repo.request_commits(self._commits_done_cb,
                                      self._commits_progress_cb,
                                      ref1=self.base_combo.text,
                                      ref2=self.compare_combo.text)

    def _commits_progress_cb(self, commit):
        self.commits_list.append(commit)

    def _commits_done_cb(self, success, err_msg=None):
        count = self.commits_list.items_count
        if not success:
            ErrorPopup(self, msg=utf8_to_markup(err_msg))
            return

        # update commits list
        if count == 0:
            self.commits_frame.text = 'No commits to show'
        else:
            self.commits_frame.text = '{} {} in {} but not in {}'.format(
                                    count, 'commit' if count == 1 else 'commits',
                                    self.compare_combo.text,
                                    self.base_combo.text)

        # update diff entry
        if count == 0:
            self.diff_entry.text = \
                '<info>There isn’t anything to compare.</info><br>' \
                'The two revisions are identical.<br>' \
                'You’ll need to use two different branch names ' \
                'to get a valid comparison.'
        else:
            self.update_diff()

        # update merge button + label
        if self.base_combo.text != self.app.repo.status.current_branch.name:
            self.merge_btn.disabled = True
            self.merge_label.text = '<warning>You can only merge in the current branch.</>'
        elif count == 0:
            self.merge_btn.disabled = True
            self.merge_label.text = '<info>Nothing to merge.</>'
        else:
            self.merge_btn.disabled = False
            self.merge_label.text = '' # TODO check conflicts !!!

    def update_diff(self):
        self.diff_entry.loading_set()
        sel_item = self.commits_list.selected_item
        if sel_item is not None:
            commit = sel_item.data
            self.app.repo.request_diff(self._diff_done_cb, ref1=commit.sha)
        elif self.commits_list.items_count < 50:
            self.app.repo.request_diff(self._diff_done_cb, compare=True,
                                       ref1=self.base_combo.text,
                                       ref2=self.compare_combo.text)
        else:
            self.diff_entry.text = \
                '<warning>Warning: </warning>The diff is huge (%d commits).<br>' \
                'I cannot show all the commits at the same time, ' \
                'you can still show single commits.' % \
                self.commits_list.items_count

    def _diff_done_cb(self, lines, success):
        self.diff_entry.lines_set(lines)

    def _list_selected_cb(self, li, item):
        if item == self._selected_item:
            item.selected = False
            self._selected_item = None
        else:
            self._selected_item = item
        self.update_diff()


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

from efl.elementary.entry import Entry, markup_to_utf8, utf8_to_markup, \
    ELM_WRAP_NONE, ELM_WRAP_MIXED
from efl.elementary.window import StandardWindow
from efl.elementary.box import Box
from efl.elementary.panes import Panes
from efl.elementary.button import Button
from efl.elementary.check import Check

from egitu.utils import DiffedEntry, ErrorPopup, EXPAND_BOTH, FILL_BOTH, \
    EXPAND_HORIZ, FILL_HORIZ


class CommitDialog(StandardWindow):
    def __init__(self, repo, win, revert_commit=None):
        self.repo = repo
        self.win = win
        self.confirmed = False
        self.revert_commit = revert_commit

        StandardWindow.__init__(self, 'Egitu', 'Egitu', autodel=True)

        vbox = Box(self, size_hint_weight=EXPAND_BOTH,
                   size_hint_align=FILL_BOTH)
        self.resize_object_add(vbox)
        vbox.show()

        # title
        title = 'Revert commit' if revert_commit else 'Commit changes'
        en = Entry(self, editable=False,
                   text='<title><align=center>%s</align></title>' % title,
                   size_hint_weight=EXPAND_HORIZ, size_hint_align=FILL_HORIZ)
        vbox.pack_end(en)
        en.show()

        # revert auto-commit checkbox
        if revert_commit:
            ck = Check(vbox, state=True, text='Automatically commit the revert')
            ck.callback_changed_add(lambda c: self.msg_entry.disabled_set(not c.state))
            vbox.pack_end(ck)
            ck.show()
            self.revert_chk = ck

        # Panes
        panes = Panes(self, content_left_size = 0.2, horizontal=True,
                      size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        vbox.pack_end(panes)
        panes.show()

        # message entry
        en = Entry(self, editable=True, scrollable=True,
                   size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        en.part_text_set('guide', 'Enter commit message here')
        panes.part_content_set("left", en)
        if revert_commit:
            en.text = 'Revert [%s]<br><br>This reverts commit %s.<br><br>' % \
                      (revert_commit.title, revert_commit.sha)
            en.cursor_end_set()
        en.show()
        self.msg_entry = en

        # diff entry
        self.diff_entry = DiffedEntry(self)
        panes.part_content_set('right', self.diff_entry)
        self.diff_entry.show()

        # buttons
        hbox = Box(self, horizontal=True, size_hint_weight=EXPAND_HORIZ,
                   size_hint_align=FILL_HORIZ)
        vbox.pack_end(hbox)
        hbox.show()

        bt = Button(self, text='Cancel')
        bt.callback_clicked_add(lambda b: self.delete())
        hbox.pack_end(bt)
        bt.show()

        bt = Button(self, text='Revert' if revert_commit else 'Commit')
        bt.callback_clicked_add(self.commit_button_cb)
        hbox.pack_end(bt)
        bt.show()

        # show the window and give focus to the editable entry
        self.size = 500, 500
        self.show()
        en.focus = True

        # load the diff
        if revert_commit:
            repo.request_diff(self.diff_done_cb, revert=True,
                              commit1=self.revert_commit)
        else:
            repo.request_diff(self.diff_done_cb, only_staged=True)

    def diff_done_cb(self, lines, success):
        self.diff_entry.lines_set(lines)

    def commit_button_cb(self, bt):
        if not self.confirmed:
            self.confirmed = True
            bt.text = 'Are you sure?'
        elif self.revert_commit:
            bt.text = 'Revert'
            self.confirmed = False
            self.repo.revert(self.commit_done_cb, self.revert_commit,
                             auto_commit=self.revert_chk.state, 
                             commit_msg=markup_to_utf8(self.msg_entry.text))
        else:
            bt.text = 'Commit'
            self.confirmed = False
            self.repo.commit(self.commit_done_cb,
                             markup_to_utf8(self.msg_entry.text))

    def commit_done_cb(self, success, err_msg=None):
        if success:
            self.delete()
            self.win.update_header()
            self.win.graph.populate(self.repo)
        else:
            ErrorPopup(self, 'Operation Failed', utf8_to_markup(err_msg))

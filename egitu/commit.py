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

from __future__ import absolute_import

from efl.elementary.entry import Entry, markup_to_utf8, utf8_to_markup, \
    ELM_WRAP_NONE, ELM_WRAP_MIXED
from efl.elementary.window import DialogWindow
from efl.elementary.box import Box
from efl.elementary.panes import Panes
from efl.elementary.button import Button
from efl.elementary.check import Check

from egitu.utils import DiffedEntry, ErrorPopup, ConfirmPupup, \
    EXPAND_BOTH, FILL_BOTH, EXPAND_HORIZ, FILL_HORIZ


class DiscardDialog(ConfirmPupup):
    def __init__(self, repo, win, files=[]):
        self.win = win
        self.repo = repo
        self.files = files

        if files:
            msg = 'The following files will be <b>reverted</b> to the last commit:' \
                  '<br><br><b>%s</b>' % '<br>'.join(files)
        else:
            msg = 'This will <b>destroy ALL</b> the changes not committed !!!'

        ConfirmPupup.__init__(self, win, msg=msg, ok_cb=self._confirm_cb)

    def _confirm_cb(self):
        self.repo.discard(self._discard_done_cb, self.files)

    def _discard_done_cb(self, success, err_msg=None):
        self.delete()
        if success:
            self.win.refresh()
        else:
            ErrorPopup(self, 'Operation Failed', utf8_to_markup(err_msg))


class CommitDialog(DialogWindow):
    def __init__(self, repo, win, revert_commit=None, cherrypick_commit=None):
        self.repo = repo
        self.win = win
        self.confirmed = False
        self.revert_commit = revert_commit
        self.cherrypick_commit = cherrypick_commit

        DialogWindow.__init__(self, win, 'Egitu', 'Egitu', 
                              size=(500,500), autodel=True)

        vbox = Box(self, size_hint_weight=EXPAND_BOTH,
                   size_hint_align=FILL_BOTH)
        self.resize_object_add(vbox)
        vbox.show()

        # title
        if revert_commit:
            title = 'Revert commit'
        elif cherrypick_commit:
            title = 'Cherry-pick commit'
        else:
            title = 'Commit changes'
        en = Entry(self, editable=False,
                   text='<title><align=center>%s</align></title>' % title,
                   size_hint_weight=EXPAND_HORIZ, size_hint_align=FILL_HORIZ)
        vbox.pack_end(en)
        en.show()

        # auto-commit checkbox (for revert and cherry-pick)
        if revert_commit or cherrypick_commit:
            ck = Check(vbox, state=True)
            ck.text = 'Automatically commit, in branch: %s' % \
                      self.repo.current_branch
            ck.callback_changed_add(lambda c: self.msg_entry.disabled_set(not c.state))
            vbox.pack_end(ck)
            ck.show()
            self.autocommit_chk = ck

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
            en.text = 'Revert "%s"<br><br>This reverts commit %s.<br><br>' % \
                      (utf8_to_markup(revert_commit.title),
                       revert_commit.sha)
        elif cherrypick_commit:
            en.text = '%s<br><br>%s<br>(cherry picked from commit %s)<br>' % \
                      (utf8_to_markup(cherrypick_commit.title),
                       utf8_to_markup(cherrypick_commit.message),
                       cherrypick_commit.sha)
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

        if revert_commit:
            label = 'Revert'
        elif cherrypick_commit:
            label = 'Cherry-pick'
        else:
            label = 'Commit'
        bt = Button(self, text=label)
        bt.callback_clicked_add(self.commit_button_cb)
        hbox.pack_end(bt)
        bt.show()

        # show the window and give focus to the editable entry
        self.show()
        en.focus = True

        # load the diff
        if revert_commit:
            repo.request_diff(self.diff_done_cb, revert=True,
                              commit1=revert_commit)
        elif cherrypick_commit:
            repo.request_diff(self.diff_done_cb, commit1=cherrypick_commit)
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
                             auto_commit=self.autocommit_chk.state, 
                             commit_msg=markup_to_utf8(self.msg_entry.text))
        elif self.cherrypick_commit:
            bt.text = 'Cherry-pick'
            self.confirmed = False
            self.repo.cherrypick(self.commit_done_cb, self.cherrypick_commit,
                                 auto_commit=self.autocommit_chk.state, 
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

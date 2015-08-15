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

from efl.evas import Rectangle
from efl.elementary.window import DialogWindow
from efl.elementary.box import Box
from efl.elementary.panes import Panes
from efl.elementary.button import Button
from efl.elementary.check import Check
from efl.elementary.popup import Popup
from efl.elementary.icon import Icon
from efl.elementary.table import Table
from efl.elementary.separator import Separator
from efl.elementary.list import List
from efl.elementary.entry import Entry, markup_to_utf8, utf8_to_markup, \
    ELM_WRAP_NONE, ELM_WRAP_MIXED

from egitu.utils import DiffedEntry, ErrorPopup, \
    EXPAND_BOTH, FILL_BOTH, EXPAND_HORIZ, FILL_HORIZ


class DiscardDialog(Popup):
    def __init__(self, app):
        self.app = app

        Popup.__init__(self, app.win)
        self.part_text_set('title,text', 'Discard local changes')
        self.part_content_set('title,icon', Icon(self, standard='user-trash'))

        # main table
        tb = Table(self, padding=(0,4),
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        self.content = tb
        tb.show()

        # sep
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_BOTH)
        tb.pack(sep, 0, 0, 1, 1)
        sep.show()

        # warning label
        en = Entry(self, editable=False,
                   text='<warning>WARNING: This operation is not reversible!</warning><br>' \
                        'Selected files (or ALL files, if nothing is selected) will be ' \
                        'reverted to the state of the last commit.',
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        tb.pack(en, 0, 1, 1, 1)
        en.show()

        # changes list
        r = Rectangle(self.evas, size_hint_min=(300,200),
                      size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        li = List(self, multi_select=True,
                  size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        li.callback_selected_add(self._list_selection_changed_cb)
        li.callback_unselected_add(self._list_selection_changed_cb)
        tb.pack(li, 0, 2, 1, 1)
        tb.pack(r, 0, 2, 1, 1)

        for path in sorted(self.app.repo.status.changes):
            mod, staged, name, new_name = self.app.repo.status.changes[path]
            icon = Icon(self, standard='git-mod-'+mod)
            check = Check(self, text='', state=staged, disabled=True)
            label = '{} → {}'.format(name, new_name) if new_name else name
            it = li.item_append(label, icon, check)
            it.data['mod'] = mod

        li.go()
        li.show()
        self.file_list = li

        # delete untracked check
        ck = Check(self, text='Also delete untracked files', state=True,
                   size_hint_expand=EXPAND_BOTH, size_hint_align=(0.0,0.5))
        tb.pack(ck, 0, 3, 1, 1)
        ck.show()
        self.untracked_chk = ck

        # sep
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_BOTH)
        tb.pack(sep, 0, 4, 1, 1)
        sep.show()

        # buttons
        bt = Button(self, text='Close')
        bt.callback_clicked_add(lambda b: self.delete())
        self.part_content_set('button1', bt)
        bt.show()

        bt = Button(self, text="Discard EVERYTHING!",
                    content=Icon(self, standard='user-trash'))
        bt.callback_clicked_add(self._confirm_clicked_cb)
        self.part_content_set('button2', bt)
        bt.show()
        self.confirm_btn = bt

        #
        self.show()

    def _list_selection_changed_cb(self, li, item):
        if li.selected_items:
            self.confirm_btn.text = "Discard selected only!"
        else:
            self.confirm_btn.text = "Discard EVERYTHING!"

    def _confirm_clicked_cb(self, btn):
        # cache selection list
        selected_list = self.file_list.selected_items

        # delete untracked (if requested)
        if self.untracked_chk.state == True:
            # li =
            for it in selected_list or self.file_list.items:
                if it.data['mod'] == '?':
                    full_path = os.path.join(self.app.repo.url, it.text)
                    try:
                        os.remove(full_path)
                    except:
                        self.delete()
                        ErrorPopup(self.app.win, 'Cannot delete file', it.text)
                        return

        # list of selected items (untracked excluded)
        li = [ it.text for it in selected_list if it.data['mod'] != '?']

        # WARNING, dangerous path, only untracked was selected
        if len(li) < 1 and len(selected_list) > 0:
            self.app.action_reload_repo()
            self.delete()
            return

        # discard selection or everything if li is empty
        self.app.repo.discard(self._discard_done_cb, li)

    def _discard_done_cb(self, success, err_msg=None):
        self.delete()
        if success:
            self.app.win.update_all()
        else:
            ErrorPopup(self.app.win, 'Operation Failed', utf8_to_markup(err_msg))


class CommitDialog(DialogWindow):
    def __init__(self, app, revert_commit=None, cherrypick_commit=None):
        self.app = app
        self.confirmed = False
        self.revert_commit = revert_commit
        self.cherrypick_commit = cherrypick_commit

        DialogWindow.__init__(self, app.win, 'Egitu', 'Egitu',
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
                      app.repo.status.current_branch.name
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
            app.repo.request_diff(self.diff_done_cb, revert=True,
                                  commit1=revert_commit)
        elif cherrypick_commit:
            app.repo.request_diff(self.diff_done_cb, commit1=cherrypick_commit)
        else:
            app.repo.request_diff(self.diff_done_cb, only_staged=True)

    def diff_done_cb(self, lines, success):
        self.diff_entry.lines_set(lines)

    def commit_button_cb(self, bt):
        if not self.confirmed:
            self.confirmed = True
            bt.text = 'Are you sure?'
        elif self.revert_commit:
            bt.text = 'Revert'
            self.confirmed = False
            self.app.repo.revert(self.commit_done_cb, self.revert_commit,
                                 auto_commit=self.autocommit_chk.state,
                                 commit_msg=markup_to_utf8(self.msg_entry.text))
        elif self.cherrypick_commit:
            bt.text = 'Cherry-pick'
            self.confirmed = False
            self.app.repo.cherrypick(self.commit_done_cb, self.cherrypick_commit,
                                     auto_commit=self.autocommit_chk.state,
                                     commit_msg=markup_to_utf8(self.msg_entry.text))
        else:
            bt.text = 'Commit'
            self.confirmed = False
            self.app.repo.commit(self.commit_done_cb,
                                 markup_to_utf8(self.msg_entry.text))

    def commit_done_cb(self, success, err_msg=None):
        if success:
            self.delete()
            self.app.action_update_header()
            self.app.action_update_dag()
        else:
            self.app.action_reload_repo()
            ErrorPopup(self, 'Operation Failed', utf8_to_markup(err_msg))

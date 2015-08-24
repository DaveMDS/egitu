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

from efl.elementary.entry import Entry, utf8_to_markup, \
    ELM_WRAP_NONE, ELM_WRAP_MIXED
from efl.elementary.icon import Icon
from efl.elementary.image import Image
from efl.elementary.panes import Panes
from efl.elementary.table import Table
from efl.elementary.check import Check
from efl.elementary.button import Button
from efl.elementary.box import Box
from efl.elementary.genlist import Genlist, GenlistItemClass, \
    ELM_OBJECT_SELECT_MODE_ALWAYS, ELM_LIST_COMPRESS

from egitu.utils import options, format_date, GravatarPict, DiffedEntry, \
    EXPAND_BOTH, FILL_BOTH, EXPAND_HORIZ, FILL_HORIZ
from egitu.commit import CommitDialog, DiscardDialog


class DiffViewer(Table):
    def __init__(self, parent, app):
        self.app = app
        self.commit = None
        self.win = parent

        Table.__init__(self, parent,  padding=(5,5))
        self.show()

        # gravatar picture
        self.picture = GravatarPict(self)
        self.picture.size_hint_align = 0.0, 0.0
        self.picture.show()
        self.pack(self.picture, 0, 0, 1, 2)

        # description entry
        self.entry = Entry(self, text='Unknown', line_wrap=ELM_WRAP_MIXED,
                           size_hint_weight=EXPAND_BOTH,
                           size_hint_align=FILL_BOTH,
                           editable=False)
        self.pack(self.entry, 1, 0, 1, 1)
        self.entry.show()

        # action buttons box
        self.action_box = Box(self, horizontal=True,
                              size_hint_weight=EXPAND_HORIZ,
                              size_hint_align=(0.98, 0.98))
        self.pack(self.action_box, 1, 1, 1, 1)
        self.action_box.show()

        # panes
        panes = Panes(self, content_left_size = 0.3, horizontal=True,
                      size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        self.pack(panes, 0, 2, 2, 1)
        panes.show()

        # file list
        self.itc = GenlistItemClass(item_style='default',
                                    text_get_func=self._gl_text_get,
                                    content_get_func=self._gl_content_get)
        self.diff_list = Genlist(self, homogeneous=True, mode=ELM_LIST_COMPRESS,
                                 select_mode=ELM_OBJECT_SELECT_MODE_ALWAYS,
                                 size_hint_weight=EXPAND_BOTH,
                                 size_hint_align=FILL_BOTH)
        self.diff_list.callback_selected_add(self._list_selected_cb)
        panes.part_content_set('left', self.diff_list)

        # diff entry
        self.diff_entry = DiffedEntry(self)
        panes.part_content_set('right', self.diff_entry)

    def _gl_text_get(self, li, part, item_data):
        if isinstance(item_data, tuple): # in real commits
            mod, staged, name, new = item_data
        else: # in local changes (item_data is the path)
            mod, staged, name, new = self.app.repo.status.changes[item_data]
        return '{} → {}'.format(name, new) if new else name

    def _gl_content_get(self, li, part, item_data):
        if isinstance(item_data, tuple): # in real commits
            mod, staged, name, new = item_data
        else: # in local changes (item_data is the path)
            mod, staged, name, new = self.app.repo.status.changes[item_data]

        if part == 'elm.swallow.icon':
            return Icon(self, standard='git-mod-'+mod)
        elif part == 'elm.swallow.end' and staged is not None:
            ck = Check(self, state=staged, propagate_events=False)
            ck.callback_changed_add(self._stage_unstage_check_cb)
            ck.data['path'] = name
            return ck

    def update_action_buttons(self, buttons):
        self.action_box.clear()
        if 'checkout' in buttons:
            bt = Button(self, text='Checkout')
            bt.callback_clicked_add(lambda b: \
                self.app.checkout_ref(self.commit.sha))
            self.action_box.pack_end(bt)
            bt.show()
        if 'revert' in buttons:
            bt = Button(self, text='Revert')
            bt.callback_clicked_add(lambda b: \
                CommitDialog(self.app, revert_commit=self.commit))
            self.action_box.pack_end(bt)
            bt.show()
        if 'cherrypick' in buttons:
            bt = Button(self, text='Cherry-pick')
            bt.callback_clicked_add(lambda b: \
                CommitDialog(self.app, cherrypick_commit=self.commit))
            self.action_box.pack_end(bt)
            bt.show()
        if 'commit' in buttons:
            bt = Button(self, text='Commit',
                        content=Icon(self, standard='git-commit'))
            bt.callback_clicked_add(lambda b: \
                CommitDialog(self.app))
            self.action_box.pack_end(bt)
            bt.show()
        if 'discard' in buttons:
            bt = Button(self, text='Discard',
                        content=Icon(self, standard='user-trash'))
            bt.callback_clicked_add(lambda b: DiscardDialog(self.app))
            self.action_box.pack_end(bt)
            bt.show()

    def commit_set(self, commit):
        self.commit = commit

        self.diff_list.clear()
        self.diff_entry.text = ''

        if commit.special == 'local':
            # the special 'local changes' commit
            text = '<bigger><b>Local changes</b></bigger>'
            self.show_local_status()
            self.update_action_buttons(['commit', 'discard'])
        else:
            # or a real commit
            line1 = '<name>{}</name>  <b>{}</b>  {}<br>'.format(commit.sha[:9],
                     commit.author, format_date(commit.commit_date))
            line2 = line3 = line4 = ''
            if commit.committer and commit.committer != commit.author:
                line2 = '<name>Committed by:</name> <b>{}</b><br>'.format(
                         commit.committer)
            if commit.title:
                line3 = '<bigger><b>{}</b></bigger><br>'.format(
                        utf8_to_markup(commit.title.strip()))
            if commit.message:
                line4 = '<br>{}'.format(utf8_to_markup(commit.message.strip()))
            text = line1 + line2 + line3 + line4
            self.app.repo.request_changes(self._changes_done_cb, commit1=commit)
            self.update_action_buttons(['checkout', 'revert', 'cherrypick'])

        self.entry.text = text
        self.picture.email_set(commit.author_email)

    def show_local_status(self):
        for path in sorted(self.app.repo.status.changes):
            self.diff_list.item_append(self.itc, path)

    def refresh_diff(self):
        if self.diff_list.selected_item:
            self._list_selected_cb(self.diff_list, self.diff_list.selected_item)

    def _stage_unstage_check_cb(self, check):
        path = check.data['path']
        if check.state is True:
            self.app.repo.stage_file(self._stage_unstage_done_cb, path, path)
        else:
            self.app.repo.unstage_file(self._stage_unstage_done_cb, path, path)

    def _stage_unstage_done_cb(self, success, path):
        self.app.action_update_header()
        self.diff_list.realized_items_update()

    def _changes_done_cb(self, success, lines):
        for mod, name, new_name in lines:
            item_data = (mod, None, name, new_name)
            self.diff_list.item_append(self.itc, item_data)
        self.diff_list.first_item.selected = True

    def _list_selected_cb(self, li, item):
        if isinstance(item.data, tuple): # in real commits
            mod, staged, name, new = item.data
        else: # in local changes (item_data is the path)
            mod, staged, name, new = self.app.repo.status.changes[item.data]

        self.app.repo.request_diff(self._diff_done_cb,
                                   ref1=self.commit.sha, path=name)
        self.diff_entry.line_wrap = \
            ELM_WRAP_MIXED if options.diff_text_wrap else ELM_WRAP_NONE
        self.diff_entry.loading_set()

    def _diff_done_cb(self, lines, success):
        self.diff_entry.lines_set(lines)

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

from efl import elementary as elm
from efl.elementary.window import DialogWindow
from efl.elementary.box import Box
from efl.elementary.table import Table
from efl.elementary.frame import Frame
from efl.elementary.button import Button
from efl.elementary.check import Check
from efl.elementary.label import Label
from efl.elementary.entry import Entry, ELM_WRAP_NONE, utf8_to_markup
from efl.elementary.popup import Popup
from efl.elementary.separator import Separator

from egitu.utils import ErrorPopup, ConfirmPupup, RequestPopup, \
    DiffedEntry, SafeIcon, format_date, parseint, \
    EXPAND_BOTH, EXPAND_HORIZ, EXPAND_VERT, FILL_BOTH, FILL_HORIZ, FILL_VERT


class StashSavePopup(Popup):
    def __init__(self, parent, app):
        self.app = app

        Popup.__init__(self, parent)
        self.part_text_set('title,text', 'Save current status')
        self.part_content_set('title,icon', SafeIcon(self, 'git-stash'))

        # main vertical box
        box = Box(self, size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        self.content = box
        box.show()

        # separator
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_HORIZ)
        box.pack_end(sep)
        sep.show()

        # description
        en = Entry(self, single_line=True, scrollable=True,
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        en.part_text_set('guide', 'Stash description (or empty for the default)')
        en.text = 'WIP on ' + app.repo.status.head_describe
        box.pack_end(en)
        en.show()

        # include untracked
        ck = Check(self, text='Include untracked files', state=True,
                   size_hint_expand=EXPAND_HORIZ, size_hint_align=(0.0,0.5))
        box.pack_end(ck)
        ck.show()

        # separator
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_HORIZ)
        box.pack_end(sep)
        sep.show()

        # buttons
        bt = Button(self, text='Close')
        bt.callback_clicked_add(lambda b: self.delete())
        self.part_content_set('button1', bt)
        bt.show()

        bt = Button(self, text='Stash', content=SafeIcon(self, 'git-stash'))
        bt.callback_clicked_add(self._stash_clicked_cb, en, ck)
        self.part_content_set('button2', bt)
        bt.show()

        # focus to the entry and show
        en.select_all()
        en.focus = True
        self.show()

    def _stash_clicked_cb(self, btn, entry, check):
        self.app.repo.stash_save(self._stash_done_cb, entry.text, check.state)

    def _stash_done_cb(self, success, err_msg=None):
        self.delete()
        if success:
            self.app.action_update_all()
        else:
            ErrorPopup(self.app.win, msg=err_msg)


class StashDialog(DialogWindow):
    def __init__(self, parent, app, stash=None):
        self.app = app
        self.stash = stash or app.repo.stash[0]
        self.idx = parseint(stash.ref) if stash else 0

        DialogWindow.__init__(self, app.win, 'egitu-stash', 'stash',
                              size=(500,500), autodel=True)

        # main vertical box (inside a padding frame)
        vbox = Box(self, padding=(0, 6), size_hint_weight=EXPAND_BOTH,
                   size_hint_align=FILL_BOTH)
        fr = Frame(self, style='pad_medium', size_hint_weight=EXPAND_BOTH)
        self.resize_object_add(fr)
        fr.content = vbox
        fr.show()
        vbox.show()

        # header horizontal box
        hbox = Box(self, horizontal=True,
                   size_hint_expand=EXPAND_HORIZ, size_hint_fill=FILL_HORIZ)
        vbox.pack_end(hbox)
        hbox.show()

        # title
        en = Entry(self, editable=False, scrollable=False,
                    size_hint_expand=EXPAND_HORIZ, size_hint_align=(-1,0.0))
        hbox.pack_end(en)
        en.show()
        self.title_entry = en

        # header separator
        sep = Separator(self)
        hbox.pack_end(sep)
        sep.show()

        # navigation table
        tb = Table(self, size_hint_align=(0.5,0.0))
        hbox.pack_end(tb)
        tb.show()

        lb = Label(self)
        tb.pack(lb, 0, 0, 2, 1)
        lb.show()
        self.nav_label = lb

        ic = SafeIcon(self, 'go-previous')
        bt = Button(self, text='Prev', content=ic)
        bt.callback_clicked_add(self._prev_clicked_cb)
        tb.pack(bt, 0, 1, 1, 1)
        bt.show()
        self.prev_btn = bt

        ic = SafeIcon(self, 'go-next')
        bt = Button(self, text='Next', content=ic)
        bt.callback_clicked_add(self._next_clicked_cb)
        tb.pack(bt, 1, 1, 1, 1)
        bt.show()
        self.next_btn = bt

        # diff entry
        self.diff_entry = DiffedEntry(self)
        vbox.pack_end(self.diff_entry)
        self.diff_entry.show()

        # buttons
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_HORIZ)
        vbox.pack_end(sep)
        sep.show()

        hbox = Box(self, horizontal=True,
                   size_hint_expand=EXPAND_HORIZ, size_hint_fill=FILL_BOTH)
        vbox.pack_end(hbox)
        hbox.show()

        bt = Button(self, text='Apply')
        bt.callback_clicked_add(self._apply_clicked_cb)
        hbox.pack_end(bt)
        bt.show()

        bt = Button(self, text='Pop (apply & delete)')
        bt.callback_clicked_add(self._pop_clicked_cb)
        hbox.pack_end(bt)
        bt.show()

        bt = Button(self, text='Branch & Delete',
                    content=SafeIcon(self, 'git-branch'))
        bt.callback_clicked_add(self._branch_clicked_cb)
        hbox.pack_end(bt)
        bt.show()

        bt = Button(self, text='Delete',
                    content=SafeIcon(self, 'user-trash'))
        bt.callback_clicked_add(self._drop_clicked_cb)
        hbox.pack_end(bt)
        bt.show()

        sep = Separator(self, size_hint_expand=EXPAND_HORIZ)
        hbox.pack_end(sep)

        bt = Button(self, text='Close')
        bt.callback_clicked_add(lambda b: self.delete())
        hbox.pack_end(bt)
        bt.show()

        # request the diff and show the dialog
        self.update(self.idx)
        self.show()

    def update(self, idx):
        self.idx = idx
        self.stash = self.app.repo.stash[idx]
        stash_len = len(self.app.repo.stash)

        self.title = self.stash.ref

        self.title_entry.text = \
            '<name>Stash item</> #{}   <name>Created</> {}<br>' \
            '<subtitle>{}</>'.format(idx,
            format_date(self.stash.ts), self.stash.desc)

        self.nav_label.text = \
            '{} {}<br>in the stash'.format(stash_len,
            'items' if stash_len > 1 else 'item')

        self.prev_btn.disabled = (idx == 0)
        self.next_btn.disabled = (idx >= stash_len - 1)

        self.diff_entry.loading_set()
        self.app.repo.stash_request_diff(self._diff_done_cb, self.stash)

    def _prev_clicked_cb(self, btn):
        self.update(self.idx - 1)

    def _next_clicked_cb(self, btn):
        self.update(self.idx + 1)
        
    def _diff_done_cb(self, lines, success):
        self.diff_entry.lines_set(lines)

    def _drop_clicked_cb(self, btn):
        self.app.action_stash_drop(self.stash)
        self.delete()

    def _apply_clicked_cb(self, btn):
        self.app.action_stash_apply(self.stash)
        self.delete()

    def _pop_clicked_cb(self, btn):
        self.app.action_stash_pop(self.stash)
        self.delete()

    def _branch_clicked_cb(self, btn):
        self.app.action_stash_branch(self.stash)
        self.delete()


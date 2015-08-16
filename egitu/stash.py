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

import os

from efl import elementary as elm
from efl.elementary.window import DialogWindow
from efl.elementary.box import Box
from efl.elementary.frame import Frame
from efl.elementary.button import Button
from efl.elementary.check import Check
from efl.elementary.entry import Entry, ELM_WRAP_NONE, utf8_to_markup
from efl.elementary.icon import Icon
from efl.elementary.popup import Popup
from efl.elementary.separator import Separator

from egitu.utils import ErrorPopup, ConfirmPupup, DiffedEntry, format_date, \
    EXPAND_BOTH, EXPAND_HORIZ, EXPAND_VERT, FILL_BOTH, FILL_HORIZ, FILL_VERT


class StashSavePopup(Popup):
    def __init__(self, parent, app):
        self.app = app

        Popup.__init__(self, parent)
        self.part_text_set('title,text', 'Save current status')
        self.part_content_set('title,icon', Icon(self, standard='git-stash'))

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

        bt = Button(self, text='Stash', content=Icon(self, standard='git-stash'))
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

        DialogWindow.__init__(self, app.win, 'Egitu-stash', self.stash.ref,
                              size=(500,500), autodel=True)

        # main vertical box (inside a padding frame)
        vbox = Box(self, padding=(0, 6), size_hint_weight=EXPAND_BOTH,
                   size_hint_align=FILL_BOTH)
        fr = Frame(self, style='pad_medium', size_hint_weight=EXPAND_BOTH)
        self.resize_object_add(fr)
        fr.content = vbox
        fr.show()
        vbox.show()

        # title
        en = Entry(self, editable=False, scrollable=False,
                   text='<subtitle>{}</><br><name>Created: </name>{}'.format(
                         self.stash.desc, format_date(self.stash.ts)),
                   size_hint_expand=EXPAND_HORIZ, size_hint_fill=FILL_HORIZ)
        vbox.pack_end(en)
        en.show()

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

        bt = Button(self, text='Apply (TODO)')
        # bt.callback_clicked_add( ... )
        hbox.pack_end(bt)
        bt.show()

        bt = Button(self, text='Pop (TODO)')
        # bt.callback_clicked_add( ... )
        hbox.pack_end(bt)
        bt.show()

        bt = Button(self, text='Branch (TODO)', content=Icon(self, standard='git-branch'))
        # bt.callback_clicked_add( ... )
        hbox.pack_end(bt)
        bt.show()

        bt = Button(self, text='Delete (drop)',
                    content=Icon(self, standard='user-trash'))
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
        self.app.repo.stash_request_diff(self._diff_done_cb, self.stash)
        self.show()

    def _diff_done_cb(self, lines, success):
        self.diff_entry.lines_set(lines)

    # drop
    def _drop_clicked_cb(self, btn):
        ConfirmPupup(self, ok_cb=self._drop_confirmed_cb,
                     msg='This will delete the stash item:<br>' \
                         '<hilight>{}</hilight>'.format(self.stash.ref))

    def _drop_confirmed_cb(self):
        self.app.repo.stash_drop(self._drop_done_cb, self.stash)

    def _drop_done_cb(self, success, err_msg=None):
        # TODO: reload the dialog instead of deleting
        self.app.action_update_all()
        self.delete()


class StashMenu(object):
    def __init__(self, parent_menu, app):
        self.app = app

        m = parent_menu
        it_stash = m.item_add(None, 'Stash...', 'git-stash')
        if app.repo is None:
            it_stash.disabled = True
        else:
            if app.repo.status.is_clean:
                m.item_add(it_stash, 'Nothing to save, status is clean',
                           'git-stash').disabled = True
            else:
                m.item_add(it_stash, 'Save', 'git-stash',
                           app.action_stash_save)
            m.item_separator_add(it_stash)
            if len(app.repo.stash) > 0:
                for si in app.repo.stash:
                    m.item_add(it_stash, si.desc, None, self._stash_show_cb, si)
                m.item_separator_add(it_stash)
                m.item_add(it_stash, 'Clear', 'user-trash', self._stash_clear_cb)
            else:
                m.item_add(it_stash, 'Nothing stashed so far').disabled = True

    def _stash_clear_cb(self, menu, item):
        t = 'This will delete ALL your stashed stuff<br>' \
            '<warning>WARNING: this operation is irreversible!</warning>'
        ConfirmPupup(self.app.win, msg=t, ok_cb=self._stash_clear_confirmed_cb)

    def _stash_clear_confirmed_cb(self):
        self.app.repo.stash_clear(self._stash_clear_done_cb)

    def _stash_clear_done_cb(self, success, err_msg=None):
        if success:
            self.app.action_update_all()
        else:
            ErrorPopup(self.app.win, msg=err_msg)

    def _stash_show_cb(self, menu, item, stash_item):
        StashDialog(self.app.win, self.app, stash_item)

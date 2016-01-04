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

from efl.elementary.entry import Entry, utf8_to_markup, ELM_WRAP_NONE
from efl.elementary.button import Button
from efl.elementary.separator import Separator
from efl.elementary.popup import Popup
from efl.elementary.table import Table
from efl.elementary.label import Label
from efl.elementary.icon import Icon
from efl.elementary.check import Check

from egitu.utils import ComboBox, CommandOutputEntry, \
    EXPAND_BOTH, FILL_BOTH, EXPAND_HORIZ, FILL_HORIZ


class PushPullBase(Popup):
    def __init__(self, parent, app, title, icon_name):
        self.app = app

        Popup.__init__(self, parent)
        self.part_text_set('title,text', title)
        self.part_content_set('title,icon', Icon(self, standard=icon_name))

        tb = Table(self, padding=(4,4), size_hint_expand=EXPAND_BOTH)
        self.content = tb
        tb.show()
        self.table = tb

        # sep
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_BOTH)
        tb.pack(sep, 0, 0, 2, 1)
        sep.show()

        # remote
        lb = Label(tb, text='Remote', size_hint_align=(0.0, 0.5))
        tb.pack(lb, 0, 1, 1, 1)
        lb.show()

        cb = ComboBox(self, icon=Icon(self, standard='git-remote'))
        cb.callback_selected_add(self.rbranch_populate)
        for remote in app.repo.remotes:
            cb.item_append(remote.name, 'git-remote')
        tb.pack(cb, 1, 1, 1, 1)
        cb.show()
        self.remote_combo = cb

        # remote branch
        lb = Label(tb, text='Remote branch', size_hint_align=(0.0, 0.5))
        tb.pack(lb, 0, 2, 1, 1)
        lb.show()

        cb = ComboBox(self, icon=Icon(cb, standard='git-branch'))
        tb.pack(cb, 1, 2, 1, 1)
        cb.show()
        self.rbranch_combo = cb

        # local branch
        lb = Label(tb, text='Local branch', size_hint_align=(0.0, 0.5))
        tb.pack(lb, 0, 3, 1, 1)
        lb.show()

        en = Entry(tb, disabled=True, single_line=True, scrollable=True,
                   text=app.repo.status.current_branch.name,
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        tb.pack(en, 1, 3, 1, 1)
        en.show()
        self.lbranch_entry = en

        # output entry
        en = CommandOutputEntry(self, min_size=(400, 150))
        tb.pack(en, 0, 4, 2, 1)
        en.show()
        self.output_entry = en

        # sep
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_BOTH)
        tb.pack(sep, 0, 5, 2, 1)
        sep.show()

        # buttons
        bt = Button(self, text='Close')
        bt.callback_clicked_add(lambda b: self.delete())
        self.part_content_set('button1', bt)
        bt.show()
        self.close_btn = bt

        bt = Button(self, text='Action')
        bt.callback_clicked_add(self._action_btn_cb)
        self.part_content_set('button2', bt)
        bt.show()
        self.action_btn = bt

        self.autopopulate()
        self.show()

    def op_start(self):
        self.output_entry.text = None
        self.output_entry.pulse_start()
        self.action_btn.disabled = True
        self.close_btn.disabled = True

    def op_end(self):
        self.output_entry.pulse_stop()
        self.action_btn.disabled = False
        self.close_btn.disabled = False

    def autopopulate(self):
        branch = self.app.repo.status.current_branch
        if branch.is_tracking:
            self.remote_combo.text = branch.remote
            self.rbranch_combo.text = branch.remote_branch
            self.rbranch_populate()
        else:
            self.output_entry.text = '<warning>%s</warning><br>%s' % \
                ('Warning:', 
                 'No tracking information setup for the current branch.<br>'
                 'You must fill the information yourself,<br>'
                 'or setup tracking information in the remote configuration.')

    def rbranch_populate(self, combo=None):
        self.rbranch_combo.clear()
        remote = self.remote_combo.text + '/'
        for branch in self.app.repo.remote_branches:
            if branch.startswith(remote):
                self.rbranch_combo.item_append(branch[len(remote):], 'git-branch')

    def _action_btn_cb(self, bt):
        remote = self.remote_combo.text
        rbranch = self.rbranch_combo.text
        lbranch = self.lbranch_entry.text

        if not remote:
            self.output_entry.error_set('You must specify a remote')
            return

        if not rbranch:
            self.output_entry.error_set('You must specify a remote branch to use')
            return

        if not lbranch:
            self.output_entry.error_set('You must specify a local branch to use')
            return
        
        self.op_start()
        self.action(remote, rbranch, lbranch)
    
    def action(self, remote, rbranch, lbranch):
        pass # implemented in subclasses

    def _action_progress_cb(self, line, sep):
        self.output_entry.append_raw(line, sep)

    def _action_done_cb(self, success):
        self.op_end()
        if success:
            self.app.action_reload_repo()
            self.output_entry.successfull()
        else:
            self.output_entry.failure()


class PullPopup(PushPullBase):
    def __init__(self, parent, app):
        PushPullBase.__init__(self, parent, app,
                              'Fetch changes (pull)', 'git-pull')
        self.remote_combo.guide = 'Where to fetch from'
        self.rbranch_combo.guide = 'The remote branch to fetch'
        self.action_btn.text = 'Pull'
    
    def action(self, remote, rbranch, lbranch):
        self.app.repo.pull(self._action_done_cb, self._action_progress_cb,
                           remote, rbranch, lbranch)


class PushPopup(PushPullBase):
    def __init__(self, parent, app):
        PushPullBase.__init__(self, parent, app,
                              'Push changes to the remote', 'git-push')
        self.remote_combo.guide = 'Where to push to'
        self.rbranch_combo.guide = 'The remote branch to push to'
        self.action_btn.text = 'Push'

        ck = Check(self, text='dry-run (only simulate the operation)', 
                   size_hint_expand=EXPAND_BOTH, size_hint_align=(1.0, 0.5))
        self.table.pack(ck, 0, 6, 2, 1)
        ck.show()
        self.dryrun_chk = ck

    def action(self, remote, rbranch, lbranch):
        self.app.repo.push(self._action_done_cb, self._action_progress_cb,
                           remote, rbranch, lbranch, dry=self.dryrun_chk.state)


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

from efl.evas import Rectangle
from efl.elementary.entry import Entry, utf8_to_markup, ELM_WRAP_NONE
from efl.elementary.button import Button
from efl.elementary.separator import Separator
from efl.elementary.popup import Popup
from efl.elementary.table import Table
from efl.elementary.label import Label
from efl.elementary.icon import Icon
from efl.elementary.progressbar import Progressbar
from efl.elementary.check import Check

from egitu.utils import EXPAND_BOTH, FILL_BOTH, EXPAND_HORIZ, FILL_HORIZ


class PushPullBase(Popup):
    def __init__(self, parent, repo, title, icon_name):
        self.repo = repo

        Popup.__init__(self, parent)
        self.part_text_set('title,text', title)
        self.part_content_set('title,icon', Icon(self, standard=icon_name))
        
        # TODO padding should be (4,4) but it seems buggy for the big entry
        tb = Table(self, padding=(0,4), size_hint_expand=EXPAND_BOTH)
        self.content = tb
        tb.show()
        self.table = tb

        # sep
        sep = Separator(self, horizontal=True, size_hint_expand=EXPAND_BOTH)
        tb.pack(sep, 0, 0, 2, 1)
        sep.show()

        # remote url
        lb = Label(tb, text='Remote', size_hint_align=(0.0, 0.5))
        tb.pack(lb, 0, 1, 1, 1)
        lb.show()

        en = Entry(tb, editable=True, single_line=True, scrollable=True,
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        tb.pack(en, 1, 1, 1, 1)
        en.show()
        self.remote_entry = en

        # remote branch
        lb = Label(tb, text='Remote branch', size_hint_align=(0.0, 0.5))
        tb.pack(lb, 0, 2, 1, 1)
        lb.show()

        en = Entry(tb, editable=True, single_line=True, scrollable=True,
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        tb.pack(en, 1, 2, 1, 1)
        en.show()
        self.rbranch_entry = en

        # local branch
        lb = Label(tb, text='Local branch', size_hint_align=(0.0, 0.5))
        tb.pack(lb, 0, 3, 1, 1)
        lb.show()

        en = Entry(tb, editable=False, single_line=True, scrollable=True,
                   text=repo.current_branch,
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        tb.pack(en, 1, 3, 1, 1)
        en.show()

        # output entry
        en = Entry(tb, scrollable=True, editable=False, line_wrap=ELM_WRAP_NONE,
                   size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        tb.pack(en, 0, 4, 2, 1)
        en.show()
        self.output_entry = en

        r = Rectangle(tb.evas, size_hint_min=(400,200),
                      size_hint_expand=EXPAND_BOTH)
        tb.pack(r, 0, 4, 2, 1)

        # progress wheel
        pb = Progressbar(self, style='wheel', pulse_mode=True,
                         size_hint_expand=EXPAND_BOTH)
        tb.pack(pb, 0, 4, 2, 1)
        self.wheel = pb

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

        self.show()

    def start_pulse(self):
        self.output_entry.text = None
        self.wheel.pulse(True)
        self.wheel.show()
        self.action_btn.disabled = True
        self.close_btn.disabled = True

    def stop_pulse(self):
        self.wheel.pulse(False)
        self.wheel.hide()
        self.action_btn.disabled = False
        self.close_btn.disabled = False

    def _action_btn_cb(self, bt):
        pass
    
    def _action_progress_cb(self, line):
        self.output_entry.entry_append(line + '<br>')
        self.output_entry.cursor_end_set()

    def _action_done_cb(self, success, err_msg=None):
        self.stop_pulse()
        if success:
            self.parent.refresh()
            self.output_entry.entry_insert('<success>Operation successfully completed.</success><br>')
        else:
            self.output_entry.entry_insert('<failure>Error! Something goes wrong.</failure><br>')


class PullPopup(PushPullBase):
    def __init__(self, parent, repo):
        PushPullBase.__init__(self, parent, repo,
                              'Fetch changes (pull)', 'git-pull')
        self.remote_entry.part_text_set('guide', 'Where to fetch from (TODO)')
        self.rbranch_entry.part_text_set('guide', 'The remote branch to fetch (TODO)')
        self.action_btn.text = 'Pull'

    def _action_btn_cb(self, btn):
        self.start_pulse()
        self.repo.pull(self._action_done_cb, self._action_progress_cb)


class PushPopup(PushPullBase):
    def __init__(self, parent, repo):
        PushPullBase.__init__(self, parent, repo,
                              'Push changes to the remote', 'git-push')
        self.remote_entry.part_text_set('guide', 'Where to push to (TODO)')
        self.rbranch_entry.part_text_set('guide', 'The remote branch to push to (TODO)')
        self.action_btn.text = 'Push'

        ck = Check(self, text='dry-run (only simulate the operation)', 
                   size_hint_expand=EXPAND_BOTH, size_hint_align=(1.0, 0.5))
        self.table.pack(ck, 0, 6, 2, 1)
        ck.show()
        self.dryrun_chk = ck

    def _action_btn_cb(self, bt):
        self.start_pulse()
        self.repo.push(self._action_done_cb, self._action_progress_cb,
                       dryrun=self.dryrun_chk.state)


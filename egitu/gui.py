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

import os

from efl import elementary as elm
from efl.evas import Rectangle
from efl.elementary.window import StandardWindow, DialogWindow
from efl.elementary.box import Box
from efl.elementary.button import Button
from efl.elementary.check import Check
from efl.elementary.entry import Entry, utf8_to_markup
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
from efl.elementary.separator import Separator

from egitu.utils import options, theme_resource_get, GravatarPict, \
    KeyBindings, ErrorPopup, recent_history_get, recent_history_push, \
    EXPAND_BOTH, EXPAND_HORIZ, EXPAND_VERT, FILL_BOTH, FILL_HORIZ, FILL_VERT, \
    INFO, HOMEPAGE, AUTHORS, LICENSE, xdg_open
from egitu.dagview import DagGraph
from egitu.diffview import DiffViewer
from egitu.vcs import repo_factory
from egitu import __version__


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

        recents = recent_history_get()
        if recents:
            for recent_url in recents:
                path, name = os.path.split(recent_url)
                item = li.item_append(name)
                item.data['url'] = recent_url
        else:
            item = li.item_append('no recent repository')
            item.disabled = True
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
            # save to recent history
            recent_history_push(repo.url)

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

        # main actions
        self.item_add(None, 'Refresh', 'refresh', self._item_refresh_cb)
        self.item_add(None, 'Open', 'folder', self._item_open_cb)
        self.item_separator_add()

        # general options
        it_gen = self.item_add(None, 'General', 'preference')

        it = self.item_add(it_gen, 'Use relative dates', None,
                           self._item_check_opts_cb, 'date_relative')
        it.content = Check(self, state=options.date_relative)

        it_gravatar = self.item_add(it_gen, 'Gravatar')
        for name in ('mm', 'identicon', 'monsterid', 'wavatar', 'retro'):
            icon = 'arrow_right' if name == options.gravatar_default else None
            self.item_add(it_gravatar, name, icon,  self._item_gravatar_cb)
        self.item_separator_add(it_gravatar)
        self.item_add(it_gravatar, 'Clear icons cache', 'delete',
                      lambda m,i: GravatarPict.clear_icon_cache())

        # dag options
        it_dag = self.item_add(None, 'Dag', 'preference')

        it = self.item_add(it_dag, 'Show remote refs', None,
                           self._item_check_opts_cb, 'show_remotes_in_dag')
        it.content = Check(self, state=options.show_remotes_in_dag)

        it = self.item_add(it_dag, 'Show commit messagges', None,
                           self._item_check_opts_cb, 'show_message_in_dag')
        it.content = Check(self, state=options.show_message_in_dag)

        # diff options
        it_diff = self.item_add(None, 'Diff', 'preference')

        it = self.item_add(it_diff, 'Wrap long lines', None,
                           self._item_wrap_line_cb)
        it.content = Check(self, state=options.diff_text_wrap)

        it_font = self.item_add(it_diff, 'Font face')
        for face in ('Sans', 'Mono'):
            icon = 'arrow_right' if face == options.diff_font_face else None
            self.item_add(it_font, face, icon, self._item_font_face_cb)

        it_font = self.item_add(it_diff, 'Font size')
        for size in (8, 9, 10, 11, 12, 13, 14):
            icon = 'arrow_right' if size == options.diff_font_size else None
            self.item_add(it_font, str(size), icon, self._item_font_size_cb)

        # quit item
        self.item_separator_add()
        self.item_add(None, 'Info', 'info', self._item_info_cb)
        self.item_add(None, 'Quit', 'close', self._item_quit_cb)
        
        x, y, w, h = parent.geometry
        self.move(x, y + h)
        self.show()

    def _item_refresh_cb(self, menu, item):
        self.win.refresh()

    def _item_open_cb(self, menu, item):
        RepoSelector(self.win)

    def _item_check_opts_cb(self, menu, item, opt):
        setattr(options, opt, not item.content.state)
        self.win.graph.populate(self.win.repo)

    def _item_gravatar_cb(self, menu, item):
        if options.gravatar_default != item.text:
            options.gravatar_default = item.text
            GravatarPict.clear_icon_cache()

    def _item_wrap_line_cb(self, menu, item):
        options.diff_text_wrap = not item.content.state
        self.win.diff_view.refresh_diff()

    def _item_font_face_cb(self, menu, item):
        options.diff_font_face = item.text
        self.win.diff_view.refresh_diff()

    def _item_font_size_cb(self, menu, item):
        options.diff_font_size = int(item.text)
        self.win.diff_view.refresh_diff()

    def _item_quit_cb(self, menu, item):
        elm.exit()

    def _item_info_cb(self, menu, item):
        InfoWin(self.win)


class InfoWin(DialogWindow):
    def __init__(self, parent):
        DialogWindow.__init__(self, parent, 'egitu-info', 'Egitu',
                              autodel=True)

        fr = Frame(self, style='pad_large', size_hint_expand=EXPAND_BOTH,
                   size_hint_align=FILL_BOTH)
        self.resize_object_add(fr)
        fr.show()

        hbox = Box(self, horizontal=True, padding=(12,12))
        fr.content = hbox
        hbox.show()

        vbox = Box(self, align=(0.0,0.0), padding=(6,6),
                   size_hint_expand=EXPAND_VERT, size_hint_fill=FILL_VERT)
        hbox.pack_end(vbox)
        vbox.show()

        # icon + version
        ic = Icon(self, standard='egitu', size_hint_min=(64,64))
        vbox.pack_end(ic)
        ic.show()

        lb = Label(self, text='Version: %s' % __version__)
        vbox.pack_end(lb)
        lb.show()

        sep = Separator(self, horizontal=True)
        vbox.pack_end(sep)
        sep.show()

        # buttons
        bt = Button(self, text='Egitu', size_hint_fill=FILL_HORIZ)
        bt.callback_clicked_add(lambda b: self.entry.text_set(INFO))
        vbox.pack_end(bt)
        bt.show()

        bt = Button(self, text='Website',size_hint_align=FILL_HORIZ)
        bt.callback_clicked_add(lambda b: xdg_open(HOMEPAGE))
        vbox.pack_end(bt)
        bt.show()

        bt = Button(self, text='Authors', size_hint_align=FILL_HORIZ)
        bt.callback_clicked_add(lambda b: self.entry.text_set(AUTHORS))
        vbox.pack_end(bt)
        bt.show()

        bt = Button(self, text='License', size_hint_align=FILL_HORIZ)
        bt.callback_clicked_add(lambda b: self.entry.text_set(LICENSE))
        vbox.pack_end(bt)
        bt.show()

        # main text
        self.entry = Entry(self, editable=False, scrollable=True, text=INFO,
                           size_hint_expand=EXPAND_BOTH, size_hint_fill=FILL_BOTH)
        self.entry.callback_anchor_clicked_add(lambda e,i: xdg_open(i.name))
        hbox.pack_end(self.entry)
        self.entry.show()

        self.resize(400, 200)
        self.show()

class EditableDescription(Entry):
    def __init__(self, win):
        self.win = win
        Entry.__init__(self, win, single_line=True,
                       size_hint_weight=EXPAND_HORIZ,
                       size_hint_align=FILL_HORIZ)
        self.callback_clicked_add(self._click_cb)
        self.callback_activated_add(self._done_cb, save=True)
        self.callback_unfocused_add(self._done_cb, save=False)
        self.callback_aborted_add(self._done_cb, save=False)
        self.go_passive()

    def _click_cb(self, entry):
        if not self.editable:
            self.go_active()

    def go_passive(self):
        if hasattr(self, 'orig_text'):
            del self.orig_text
        self.editable = False
        self.scrollable = False
        self.text_style_user_push("DEFAULT='font_size=18'")
        self.tooltip_text_set('Click to edit description')

    def go_active(self):
        self.orig_text = self.text
        self.focus = False
        self.editable = True
        self.scrollable = True
        self.text_style_user_push("DEFAULT='font_size=18'")
        self.tooltip_unset()
        ic = Icon(self, standard='close', size_hint_min=(20,20))
        ic.callback_clicked_add(self._done_cb, False)
        self.part_content_set('end', ic)
        self.focus = True

    def _done_cb(self, entry, save):
        if save is True:
            self.win.repo.description_set(self.text, self._description_set_cb)
        else:
            self.text = self.orig_text
        self.go_passive()

    def _description_set_cb(self, success):
        # TODO alert if fail
        self.text = self.win.repo.description


class EgituWin(StandardWindow):
    def __init__(self):
        self.repo = None
        self.branch_selector = None
        self.caption_label = None
        self.status_label = None
        self.graph = None
        self.diff_view = None

        StandardWindow.__init__(self, 'egitu', 'Efl GIT gUi - Egitu')
        self.autodel_set(True)
        self.callback_delete_request_add(lambda o: elm.exit())

        # main vertical box
        box = Box(self, size_hint_weight = EXPAND_BOTH)
        self.resize_object_add(box)
        box.show()

        # header
        fr = Frame(self, style='outdent_bottom', size_hint_weight=EXPAND_HORIZ,
                   size_hint_align=FILL_BOTH)
        box.pack_end(fr)
        fr.show()

        tb = Table(self, size_hint_weight=EXPAND_HORIZ,
                  size_hint_align=FILL_BOTH)
        fr.content = tb
        tb.show()

        # main menu button
        bt = Button(self, text='Menu')
        bt.content = Icon(self, standard='home')
        bt.callback_clicked_add(lambda b: EgituMenu(self, b))
        tb.pack(bt, 0, 0, 1, 1)
        bt.show()

        # editable description entry
        self.caption_label = EditableDescription(self)
        tb.pack(self.caption_label, 1, 0, 1, 1)
        self.caption_label.show()

        self.branch_selector = Hoversel(self, text='none')
        self.branch_selector.callback_selected_add(self.branch_selected_cb)
        tb.pack(self.branch_selector, 3, 0, 1, 1)
        self.branch_selector.show()

        # status label + button
        self.status_label = lb = Entry(self, single_line=True, editable=False)
        tb.pack(lb, 2, 0, 1, 1)
        lb.show()

        ### Main content (left + right panes)
        panes = Panes(self, content_left_size = 0.5,
                       size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        box.pack_end(panes)
        panes.show()

        # the dag graph inside a scroller on the left
        self.graph = DagGraph(self, self.repo)
        fr = Frame(self, style='pad_medium', content=self.graph)
        scr = Scroller(self, content=fr,
                       size_hint_weight=EXPAND_BOTH, size_hint_align=FILL_BOTH)
        scr.bounce_set(0, 1)
        panes.part_content_set('left', scr)

        # the diff viewer on the right
        self.diff_view = DiffViewer(self, self.repo)
        self.diff_view.size_hint_weight = EXPAND_BOTH
        self.diff_view.size_hint_align = 0.0, 0.0
        panes.part_content_set('right', self.diff_view)
        
        # app keybindings
        binds = KeyBindings(self, verbose=False)
        binds.bind_add(('Control+r', 'F5'), self._binds_cb_refresh)
        binds.bind_add('Control+o', self._binds_cb_open)
        binds.bind_add('Control+q', self._binds_cb_quit)

        self.resize(800, 600)
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
                    self.branch_selector.item_add(branch, 'arrow_right',
                                                  ELM_ICON_STANDARD)
                else:
                    self.branch_selector.item_add(branch)
            self.branch_selector.text = self.repo.current_branch
            ic = Icon(self, file=theme_resource_get('branch.png'))
            self.branch_selector.content = ic
        except:
            self.branch_selector.text = 'Unknown'

        # update window title
        self.title = '%s [%s]' % (self.repo.name, self.repo.current_branch)

        # update repo description
        self.caption_label.text = self.repo.description or \
                                  'Unnamed repository; click to edit.'

        # update the status
        if self.repo.status.ahead == 1 and self.repo.status.is_clean:
            text = '<warning>Ahead by 1 commit</warning>'
        elif self.repo.status.ahead > 1 and self.repo.status.is_clean:
            text = '<warning>Ahead by {} commits</warning>'.format(self.repo.status.ahead)
        elif self.repo.status.is_clean:
            text = '<success>Status is clean!</success>'
            # self.commit_button.hide()
        else:
            text = '<warning>Status is dirty !!!</warning>'
            # self.commit_button.show()

        self.status_label.text = text
        self.status_label.tooltip_text_set(self.repo.status.textual)

    def branch_selected_cb(self, hoversel, item):
        def _switch_done_cb(success, err_msg=None):
            if success:
                self.update_header()
                self.graph.populate(self.repo)
            else:
                ErrorPopup(self, 'Operation Failed', utf8_to_markup(err_msg))

        self.repo.current_branch_set(item.text, _switch_done_cb)

    def show_commit(self, commit):
        self.diff_view.commit_set(self.repo, commit)

    def refresh(self):
        def _refresh_done_cb(success):
            self.update_header()
            self.graph.populate(self.repo)
        self.repo.refresh(_refresh_done_cb)

    def _binds_cb_refresh(self, src, key, event):
        self.refresh()
        return True

    def _binds_cb_open(self, src, key, event):
        RepoSelector(self)
        return True

    def _binds_cb_quit(self, src, key, event):
        elm.exit()
        return True

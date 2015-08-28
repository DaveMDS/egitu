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
import sys

from efl import elementary as elm
from efl.elementary.theme import theme_extension_add
from efl.elementary.entry import utf8_to_markup
from egitu.utils import options, config_path, theme_file_get, KeyBindings
from egitu.gui import EgituWin, RepoSelector

from egitu.vcs import repo_factory
from egitu.utils  import recent_history_push, app_instance_set, \
    AboutWin, ErrorPopup, RequestPopup, ConfirmPupup
from egitu.branches import BranchesDialog, DeleteBranchPopup, MergeBranchPopup
from egitu.tags import TagsDialog
from egitu.remotes import RemotesDialog
from egitu.pushpull import PullPopup, PushPopup
from egitu.stash import StashSavePopup, StashDialog
from egitu.compare import CompareDialog
from egitu.gui import ClonePopup


class EgituApp(object):
    def __init__(self, args):
        self.repo = None
        self.win = EgituWin(self)
        self.win.populate()

        # setup keyboard shortcuts
        binds = KeyBindings(self.win, verbose=False)
        binds.bind_add('F1', self.action_about)
        binds.bind_add(('Control+r', 'F5'), self.action_reload_repo)
        binds.bind_add('Control+o', self.action_open)
        binds.bind_add('Control+q', self.action_quit)
        binds.bind_add('Control+b', self.action_branches)
        binds.bind_add('Control+p', self.action_pull)
        binds.bind_add('Control+Shift+p', self.action_push)
        binds.bind_add('Control+c', self.action_clone)
        binds.bind_add('Control+t', self.action_tags)
        binds.bind_add('Control+s', self.action_stash_save)
        binds.bind_add('Control+Shift+s', self.action_stash_show)
        binds.bind_add('Control+m', self.action_compare)

        # try to load a repo, from command-line or cwd (else show the RepoSelector)
        if not self.try_to_load(os.path.abspath(args[0]) if args else os.getcwd()):
            RepoSelector(self)

    # generic actions    
    def action_quit(self, *args):
        elm.exit()

    def action_about(self, *args):
        AboutWin(self.win)

    # repo actions
    def action_open(self, *args):
        RepoSelector(self)

    def try_to_load(self, path):
        repo = repo_factory(path)
        if repo:
            repo.load_from_url(path, self._load_done_cb, repo)
            return True
        else:
            return False
    
    def _load_done_cb(self, success, repo):
        if success is True:
            # save to recent history
            recent_history_push(repo.url)

            # show the new loaded repo
            self.repo = repo
            self.win.update_all()
        else:
            RepoSelector(self)

    def checkout_ref(self, ref):
        self.repo.checkout(self._checkout_done_cb, ref)

    def _checkout_done_cb(self, success, err_msg=None):
        if success:
            self.action_update_all()
        else:
            ErrorPopup(self.win, 'Operation Failed', utf8_to_markup(err_msg))

    def action_reload_repo(self, *args):
        if self.repo is not None:
            self.repo.refresh(self._reload_done_cb)
    
    def _reload_done_cb(self, success, err_msg=None):
        self.win.update_all()

    # gui update utils
    def action_update_all(self, *args):
        self.win.update_all()
        
    def action_update_dag(self, *args):
        if self.repo is not None:
            self.win.graph.populate()
    
    def action_update_header(self, *args):
        self.win.update_header()

    def action_update_diffview(self, *args):
        self.win.diff_view.refresh_diff()

    def action_show_commit(self, commit):
        self.win.diff_view.show_commit(commit)
        self.win.tree.unselect_local()

    def action_show_local_status(self):
        self.win.graph.populate('HEAD')
        self.win.diff_view.show_local_status()

    def action_show_full_history(self):
        self.win.graph.populate(hilight_ref='HEAD')

    def action_show_branch(self, branch):
        self.win.graph.populate(branch.name, hilight_ref=branch.name)

    def action_show_tag(self, tag):
        self.win.graph.populate(tag.ref, hilight_ref=tag.name)

    # branch actions
    def action_branches(self, *args):
        if self.repo is not None:
            BranchesDialog(self)

    def action_branch_delete(self, branch):
        DeleteBranchPopup(self.win, self, branch)

    def action_branch_merge(self, branch):
        MergeBranchPopup(self.win, self, branch)

    # compare actions
    def action_compare(self, *args, **kargs):
        if self.repo is not None:
            CompareDialog(self.win, self, **kargs)

    # tag actions
    def action_tags(self, *args):
        if self.repo is not None:
            TagsDialog(self.win, self)

    # remote actions
    def action_remotes(self, *args):
        if self.repo is not None:
            RemotesDialog(self)
    
    def action_pull(self, *args):
        if self.repo is not None:
            PullPopup(self.win, self)
    
    def action_push(self, *args):
        if self.repo is not None:
            PushPopup(self.win, self)

    def action_clone(self, *args):
        ClonePopup(self.win, self)

    # stash actions
    def action_stash_save(self, *args):
        # TODO: check if repo is clean
        if self.repo is not None:
            StashSavePopup(self.win, self)

    def action_stash_show(self, *args):
        if self.repo is not None:
            if self.repo.stash:
                StashDialog(self.win, self)
            else:
                ErrorPopup(self.win, 'The stash is empty', 'Nothing to show')

    def action_stash_show_item(self, stash_item):
        StashDialog(self.win, self, stash_item)
        

    def action_stash_apply(self, stash_item):
        def _done_cb(success, err_msg=None):
            if success:
                self.action_update_all()
            else:
                ErrorPopup(self.win, msg=utf8_to_markup(err_msg))

        self.repo.stash_apply(_done_cb, stash_item)

    def action_stash_pop(self, stash_item):
        def _done_cb(success, err_msg=None):
            if success:
                self.action_update_all()
            else:
                ErrorPopup(self.win, msg=utf8_to_markup(err_msg))

        self.repo.stash_pop(_done_cb, stash_item)

    def action_stash_branch(self, stash_item):
        def _confirmed_cb(branch_name):
            self.repo.stash_branch(_done_cb, stash_item, branch_name)

        def _done_cb(success, err_msg=None):
            if success:
                self.action_update_all()
            else:
                ErrorPopup(self.win, msg=utf8_to_markup(err_msg))

        RequestPopup(self.win, _confirmed_cb,
                     'Stash -> branch',
                     'Pop the stash in a newly created branch',
                     'Type the name for the new branch', not_empty=True)

    def action_stash_drop(self, stash_item):
        def _confirmed_cb():
            self.repo.stash_drop(_done_cb, stash_item)

        def _done_cb(success, err_msg=None):
            if success:
                self.action_update_all()
            else:
                ErrorPopup(self.win, msg=utf8_to_markup(err_msg))

        ConfirmPupup(self.win, ok_cb=_confirmed_cb,
                     msg='This will delete the stash item:<br><br>' \
                         '<hilight>{0.ref}</hilight><br>' \
                         '<b>{0.desc}</b>'.format(stash_item))




def main():

    # load config and create necessary folders
    options.load()
    if not os.path.exists(config_path):
        os.makedirs(config_path)

    # init elm
    elm.init()
    theme_extension_add(theme_file_get())

    # Egitu
    app = EgituApp(sys.argv[1:])
    app_instance_set(app) # Ugly :/

    # enter the mainloop
    elm.run()

    # mainloop done, shutdown
    elm.shutdown()
    options.save()

    return 0


if __name__ == "__main__":
    sys.exit(main())


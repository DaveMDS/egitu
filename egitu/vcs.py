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
import time
from datetime import datetime

from efl.ecore import Exe, ECORE_EXE_PIPE_READ, ECORE_EXE_PIPE_ERROR, \
    ECORE_EXE_PIPE_READ_LINE_BUFFERED, ECORE_EXE_PIPE_ERROR_LINE_BUFFERED

from egitu.utils import file_get_contents, file_put_contents


def LOG(text):
    print(text)
    # pass

def repo_factory(url):
    url = os.path.abspath(url) # TODO is this right for real url ??
    LOG("Trying to load a repo from: %s" % url)
    for cls in Repository.__subclasses__():
        backend = cls()
        if backend.check_url(url) is True:
            return backend
    LOG('ERROR: Cannot find a repo at: "%s"' % url)


class Commit(object):
    def __init__(self):
        self.sha = ""
        self.author = ""
        self.author_email = ""
        self.committer = ""
        self.title = ""
        self.message = ""
        self.commit_date = None
        self.parents = []
        self.heads = []
        self.remotes = []
        self.tags = []

    def __str__(self):
        return '<Commit:%s parents:%s heads:%s remotes:%s tags:%s "%s">' % (
                    self.sha[:7],
                    [p[:7] for p in self.parents],
                    self.heads,
                    self.remotes,
                    self.tags,
                    self.title[:20] + ('...' if len(self.title) > 20 else ''))

    def is_a_merge(self):
        return len(self.parents) > 1


class Status(object):
    def __init__(self):
        self.ahead = 0
        self.behind = 0
        self.textual = ''
        self.current_branch = None
        self.changes = [] # list of tuples: (mod, staged, path, new_path=None)

        # HEAD status
        self.head_detached = False
        self.head_to_tag = None
        self.head_to_commit = None

        # special statuses
        self.is_merging = False
        self.is_cherry = False
        self.is_reverting = False
        self.is_bisecting = False

    @property
    def is_clean(self):
        return (len(self.changes) == 0)
    
    @property
    def head_describe(self):
        if self.head_detached is True:
            return 'detached from %s' % (self.head_to_tag or self.head_to_commit[:7])
        elif self.current_branch is not None:
            return self.current_branch.name
        else:
            return 'Unknown'


class Branch(object):
    def __init__(self, name, remote=None, remote_branch=None, is_current=False):
        self.name = name
        self.remote = remote
        self.remote_branch = remote_branch
        self.is_current = is_current

    @property
    def is_tracking(self):
        return True if self.remote_branch else False


class Remote(object):
    def __init__(self, name, url=None, fetch=None):
        self.name = name
        self.url = url
        self.fetch = fetch


### Base class for backends ###################################################
class Repository(object):

    def check_url(self, url):
        """
        Check if the given url is loadable by the backend.

        Args:
            url:
                Local path to check for validity.

        Returns:
            True or False.
        """
        # here implementation must check if url is a valid repo
        raise NotImplementedError("check_url() not implemented in backend")

    def load_from_url(self, url, done_cb, *args):
        """
        Load the given repo and fetch basic info as with refresh().

        Args:
            url:
                Local path from where to load the repo.
            done_cb:
                Function to call when the operation finish.
                Signature: cb(success, *args)
            args:
                All the others arguments passed will be given back in
                the done_cb callback function.
        """
        raise NotImplementedError("load_from_url() not implemented in backend")

    def refresh(self, done_cb, *args):
        """
        Reload the basic info from the repo.

        This is used to read some of the basic info, like tags, branches,
        and so on from the repo. The info will then be available in various
        properties for fast access.

        Args:
            done_cb:
                Function to call when the operation finish.
                Signature: cb(success, *args)
            args:
                All the others arguments passed will be given back in
                the done_cb callback function.
        """
        raise NotImplementedError("refresh not implemented in backend")

    @property
    def url(self):
        """
        The full path of the repo in the local filesystem.
        """
        raise NotImplementedError("name not implemented in backend")

    @property
    def name(self):
        """
        The name of the repo, usually this is the name of the folder
        where the repo live.
        """
        raise NotImplementedError("name not implemented in backend")

    def name_set(self, name, done_cb, *args):
        """
        Change the name of the repo.

        Args:
            name:
                A string to set as the name.
            done_cb:
                Function to call when the operation finish.
                Signature: cb(success, *args)
            args:
                All the others arguments passed will be given back in
                the done_cb callback function.
        """
        raise NotImplementedError("name_set() not implemented in backend")

    @property
    def description(self):
        """
        A short text that describe the repo.
        """
        raise NotImplementedError("description not implemented in backend")

    def description_set(self, description, done_cb, *args):
        """
        Set the description of the repo.

        Args:
            description:
                A string to set as the description.
            done_cb:
                Function to call when the operation finish.
                Signature: cb(success, *args)
            args:
                All the others arguments passed will be given back in
                the done_cb callback function.
        """
        raise NotImplementedError("description_set() not implemented in backend")

    @property
    def status(self):
        """
        The current Status object of the repo.

        Status rapresent local changes, staged or not.

        NOTE: This property is cached, you need to call the refresh() function
        to actually read the value from the repo.
        """
        raise NotImplementedError("status() not implemented in backend")

    def checkout(self, ref, done_cb, *args):
        """
        Move the HEAD to the given ref

        Args:
            ref:
                Can be any git ref (branch, tag or commit sha)
            done_cb:
                Function to call when the operation finish.
                Signature: cb(success, err_msg=None, *args)
            args:
                All the others arguments passed will be given back in
                the done_cb callback function.
        """
        raise NotImplementedError("checkout() not implemented in backend")

    @property
    def branches(self):
        """
        The list of local branches (Branch instance) present in the repository.

        NOTE: This property is cached, you need to call the refresh() function.
        """
        raise NotImplementedError("branches not implemented in backend")

    @property
    def remote_branches(self):
        """
        List of remote branches names.

        NOTE: This property is cached, you need to call the refresh() function.
        """
        raise NotImplementedError("remote_branches not implemented in backend")

    @property
    def tags(self):
        """
        The list of tags name present in the repository.

        NOTE: This property is cached, you need to call the refresh() function
        to actually read the list from the repo.
        """
        raise NotImplementedError("tags not implemented in backend")

    def request_commits(self, done_cb, prog_cb, max_count=100, skip=0):
        """
        Request a list of Commit objects.

        Args:
            done_cb:
                Function to call when the operation finish.
                Signature: cb(success)
            prog_cb:
                Function to call for each commit.
                Signature: cb(commit)
            max_count:
                Maximum number of commit to return.
            skip:
                Start the listing from the N commit.
        """
        raise NotImplementedError("request_commits() not implemented in backend")

    def request_diff(self, done_cb, prog_cb=None, commit1=None, commit2=None,
                     path=None, only_staged=False, revert=False):
        """
        Request the full unified diff between 2 commit.

        If the prog_cb is provided then it will be called for each line of the
        diff, otherwise the lines will be accumulated in a list and returned
        in the done_cb function.

        If commit2 is omitted only the changes that occur in commit1 is returned.
        If also commit1 is omitted all the not-yet-committed changes is returned.

        Args:
            done_cb:
                Function to call when the operation finish.
                Signature: cb(lines, success)
            prog_cb:
                Function to call on each line of the diff.
                Signature: cb(line)
            commit1:
                A Commit object.
            commit2:
                Another Commit object.
            path:
                If given only the diff that occur in that file is reported.
            only_staged:
                If True than only the diff of staged changes is returned,
                otherwise both staged and unstaged diff is reported.
            revert:
                If True and only commit1 is given then the diff of reverting
                commit1 will be calculated
        """
        raise NotImplementedError("request_diff() not implemented in backend")

    def request_changes(self, done_cb, commit1=None, commit2=None):
        """
        Request the changes between 2 commits.

        If commit2 is omitted only the changes that occur in commit1 is returned.
        If also commit1 is omitted all the not-yet-committed changes is returned.

        list_of_changes is a list of tuple with the type of the change,
        the path of the modified file and (in case fo rename) the new path.
        Example:
          [('M', '/path/to/file1', None), 
           ('A', '/path/to/file1', None),
           ('R', '/old/file/path', '/new/file/path')]

        Type of modification can be one of:
        - ?: untracked file
        - A: addition of a file
        - C: copy of a file into a new one
        - D: deletion of a file
        - M: modification of the contents or mode of a file
        - R: renaming of a file
        - T: change in the type of the file
        - U: file is unmerged (you must complete the merge before it can be committed)
        - X: "unknown" change type (most probably a bug, please report it)
        
        Args:
            done_cb:
                Function to call when the operation finish.
                Signature: cb(success, list_of_changes)
            commit1:
                A Commit object.
            commit2:
                Another Commit object.
        """
        raise NotImplementedError("request_changes() not implemented in backend")

    @property
    def remotes(self):
        """
        List of all the remotes configured. (Remote instances)

        NOTE: This property is cached, you need to call the refresh() function
        to actually read the list from the repo.
        """
        raise NotImplementedError("remotes not implemented in backend")

    def remote_get_by_name(self, name):
        """
        Get the Remote instance for the given remote name

        Args:
            name:
                The name of the remote
        """
        raise NotImplementedError("remote_get_by_name not implemented in backend")

    def request_remote_info(self, done_cb, remote_name):
        """
        Request the info for the given remote.
        
        Args:
            done_cb:
                Function to call when the operation finish.
                Signature: cb(success, info, err_msg=None)
            remote_name:
                The short name of the remote to query
        """
        raise NotImplementedError("request_remote_info() not implemented in backend")

    def remote_add(self, done_cb, name, url):
        """
        Add a new remote to the repo
        
        Args:
            done_cb:
                Function to call when the operation finish.
                Signature: cb(success, err_msg=None)
            name:
                The name for the new remote
            url:
                The url for the remote
        """
        raise NotImplementedError("remote_add() not implemented in backend")

    def remote_del(self, done_cb, name):
        """
        Delete the given remote from the repo
        
        Args:
            done_cb:
                Function to call when the operation finish.
                Signature: cb(success, err_msg=None)
            name:
                The name for remote to remove
        """
        raise NotImplementedError("remote_del() not implemented in backend")

    def remote_url_set(self, done_cb, name, new_url):
        """
        Change the url fo rthe given remote
        
        Args:
            done_cb:
                Function to call when the operation finish.
                Signature: cb(success, err_msg=None)
            name:
                The name of the remote to change
            new_url:
                The new url to set
        """
        raise NotImplementedError("remote_url_set() not implemented in backend")

    def stage_file(self, done_cb, path):
        """
        Add a file to the staging area.

        Args:
            done_cb:
                Function to call when the operation finish.
                Signature: cb(success)
            path:
                The path of the file to put in staged area.
        """
        raise NotImplementedError("stage_file() not implemented in backend")

    def unstage_file(self, done_cb, path):
        """
        Remove a file from the staging area.

        Args:
            done_cb:
                Function to call when the operation finish.
                Signature: cb(success)
            path:
                The path of the file to remove from the staged area.
        """
        raise NotImplementedError("unstage_file() not implemented in backend")

    def commit(self, done_cb):
        """
        Perform a commit of the local changes (staged)

        Args:
            done_cb:
                Function to call when the operation finish.
                signature: cb(success, err_msg=None)
        """
        raise NotImplementedError("commit() not implemented in backend")

    def revert(self, done_cb, commit, auto_commit=False, commit_msg=None):
        """
        Perform a revert of the given commit, with optionally autocommit

        Args:
            done_cb:
                Function to call when the operation finish.
                signature: cb(success, err_msg=None)
            commit:
                The Commit object to revert
            auto_commit (bool):
                If True than a commit will also be performed
            commit_msg (str):
                The messagge for the auto commit. Mandatory if auto_commit
                is True
        """
        raise NotImplementedError("revert() not implemented in backend")

    def cherrypick(self, done_cb, commit, auto_commit=False, commit_msg=None):
        """
        Perform a cherry-pick of the given commit in the current branch,
        with optionally autocommit.

        Args:
            done_cb:
                Function to call when the operation finish.
                signature: cb(success, err_msg=None)
            commit:
                The Commit object to cherrypick in current branch
            auto_commit (bool):
                If True than a commit will also be performed
            commit_msg (str):
                The messagge for the auto commit. Mandatory if auto_commit
                is True
        """
        raise NotImplementedError("cherrypick() not implemented in backend")

    def discard(self, done_cb, files=[]):
        """
        Discard all the changes not yet committed.

        Args:
            done_cb:
                Function to call when the operation finish.
                signature: cb(success, err_msg=None)
            files:
                List of paths to revert, if empty ALL the uncommitted changes
                will be discarted.
        """
        raise NotImplementedError("discard() not implemented in backend")

    def pull(self, done_cb, progress_cb, remote, rbranch, lbranch):
        """
        Fetch and merge changes from upsteram in the given branch.

        Args:
            done_cb:
                Function to call when the operation finish.
                signature: cb(success, err_msg=None)
            progress_cb:
                Function to call on each line of output.
                signature: cb(line)
            remote:
                The remote server to fetch from
            rbranch:
                The remote branch to fetch
            lbranch:
                The local branch to merge into
        """
        raise NotImplementedError("pull() not implemented in backend")

    def push(self, done_cb, progress_cb, remote, rbranch, lbranch, dry=False):
        """
        Push local changes to upsteram from the given branch.

        Args:
            done_cb:
                Function to call when the operation finish.
                signature: cb(success, err_msg=None)
            progress_cb:
                Function to call on each line of output.
                signature: cb(line)
            remote:
                The remote server to push to
            rbranch:
                The remote branch to push to
            lbranch:
                The local branch to push
            dry:
                Do not actually perform the push
        """
        raise NotImplementedError("push() not implemented in backend")

    def branch_create(self, done_cb, name, revision, track=False):
        """
        Create a new local branch.
        
        Args:
            done_cb:
                Function to call when the operation finish.
                signature: cb(success, err_msg=None)
            name:
                Name for the new branch
            revision:
                Starting revision to use, can be a branch name, a commit-id
                or a tag name
            track:
                If True also setup tracking information
        """
        raise NotImplementedError("branch_create() not implemented in backend")

    def branch_delete(self, done_cb, name, force=False):
        """
        Delete a local branch.
        
        Args:
            done_cb:
                Function to call when the operation finish.
                signature: cb(success, err_msg=None)
            name:
                Name of the branch to delete
            force:
                Force branch deletion (even if not fully merged)
        """
        raise NotImplementedError("branch_delete() not implemented in backend")

    def branch_merge(self, done_cb, name, fast_forward):
        """
        Merge the given branch in the current one.
        
        Args:
            done_cb:
                Function to call when the operation finish.
                signature: cb(success, err_msg=None)
            name:
                The name of the branch to merge
            fast_forward:
                Must be one of: 'ff', 'no-ff' or 'ff-only'
        """
        raise NotImplementedError("branch_merge() not implemented in backend")

    def tag_delete(self, done_cb, name):
        """
        Delete the given tag.

        Args:
            done_cb:
                Function to call when the operation finish.
                signature: cb(success, err_msg=None)
            name:
                The name of the tag to delete
        """
        raise NotImplementedError("tag_delete() not implemented in backend")

### Git backend ###############################################################
from egitu.utils import options, CmdReviewDialog

CMD_TO_REVIEW = ('commit', 'pull', 'push', 'revert', 'checkout', 'rm', 'add',
    'reset', 'commit', 'merge', 'branch', 'cherry-pick', 'clone', 'tag',
    'remote add', 'remote remove', 'remote set-url')
CMD_TO_EXCLUDE = ('branch -a')

class GitCmd(Exe):
    def __init__(self, local_path, cmd, done_cb=None, line_cb=None, *args):
        self.local_path = local_path
        self.done_cb = done_cb
        self.line_cb = line_cb
        self.args = args
        self.lines = []

        if options.review_git_commands and \
           cmd.startswith(CMD_TO_REVIEW) and not cmd.startswith(CMD_TO_EXCLUDE):
            CmdReviewDialog(cmd, self.start)
        else:
            self.start(cmd)

    def start(self, cmd):
        git_dir = os.path.join(self.local_path, '.git')
        real_cmd = 'git --git-dir="%s" --work-tree="%s" %s' % \
                   (git_dir, self.local_path, cmd)
        
        print("=== GIT " + cmd)
        Exe.__init__(self, real_cmd, 
                     ECORE_EXE_PIPE_READ | ECORE_EXE_PIPE_ERROR | 
                     ECORE_EXE_PIPE_READ_LINE_BUFFERED |
                     ECORE_EXE_PIPE_ERROR_LINE_BUFFERED)
        self.on_data_event_add(self.event_data_cb)
        self.on_error_event_add(self.event_data_cb)
        self.on_del_event_add(self.event_del_cb)

    def event_data_cb(self, exe, event):
        if callable(self.line_cb):
            for line in event.lines:
                self.line_cb(line, *self.args)
        else:
            self.lines += event.lines

    def event_del_cb(self, exe, event):
        if callable(self.done_cb):
            self.done_cb(self.lines, (event.exit_code == 0), *self.args)


class GitCmdRAW(Exe):
    def __init__(self, local_path, cmd, done_cb=None, line_cb=None, *args):
        self.local_path = local_path
        self.done_cb = done_cb
        self.line_cb = line_cb
        self.args = args

        if options.review_git_commands and \
           cmd.startswith(CMD_TO_REVIEW) and not cmd.startswith(CMD_TO_EXCLUDE):
            CmdReviewDialog(cmd, self.start)
        else:
            self.start(cmd)
    
    def start(self, cmd):
        if self.local_path:
            git_dir = os.path.join(self.local_path, '.git')
            real_cmd = 'git --git-dir="%s" --work-tree="%s" %s' % \
                       (git_dir, self.local_path, cmd)
        else:
            real_cmd = 'git %s' % (cmd)

        print("=== GIT " + cmd) # just for debug

        Exe.__init__(self, real_cmd,
                     ECORE_EXE_PIPE_READ | ECORE_EXE_PIPE_ERROR)
        self.on_data_event_add(self.event_data_cb)
        self.on_error_event_add(self.event_data_cb)
        self.on_del_event_add(self.event_del_cb)
        
    def event_data_cb(self, exe, event):
        p1 = p2 = 0
        for c in event.data:
            if c == '\n' or c == '\r':
                self.line_cb(event.data[p1:p2].strip(), c)
                p1 = p2
            p2 += 1
        if p1 != p2-1:
            self.line_cb(event.data[p1:p2].strip(), None)
    
    def event_del_cb(self, exe, event):
        if callable(self.done_cb):
            self.done_cb((event.exit_code == 0), *self.args)


def git_clone(done_cb, progress_cb, url, folder, shallow=False):
    """
    Clone the given url in the given folder

    Args:
        done_cb:
            Function to call when the operation finish.
            signature: cb(success, repo_folder)
        progress_cb:
            Function to call on each line of output.
            signature: cb(line)
        url:
            Path or url to clone
        folder:
            The folder to clone into (must be empty)
        shallow:
            If True than no history will be cloned
    """
    def _cmd_done_cb(success):
        done_cb(success, folder)

    cmd = 'clone -v --progress %s %s "%s"' % ('--depth 1' if shallow else '',
                                              url, folder)
    GitCmdRAW(None, cmd, _cmd_done_cb, progress_cb)


class GitBackend(Repository):
    def __init__(self):
        self._url = ""
        self._name = ""
        self._description = ""
        self._status = None
        self._branches = []
        self._remote_branches = []
        self._tags = []
        self._remotes = []

    def check_url(self, url):
        if url and os.path.isdir(os.path.join(url, '.git')):
            return True
        return False

    def load_from_url(self, url, done_cb, *args):
        if url.endswith(os.sep):
            url = url[:-len(os.sep)]

        self._url = url
        self._name = self._url.split(os.sep)[-1]
        desc_file = os.path.join(self._url, '.git', 'description')
        self._description = file_get_contents(desc_file)
        if self._description.startswith('Unnamed repository'):
            self._description = ''

        os.chdir(url) # to make git diff works :/
        self.refresh(done_cb, *args)

    def refresh(self, done_cb, *args):
        """ Async implementation, all commands spawned at the same time """
        print('\n======== Refreshing repo =========================')
        startup_time = time.time()
        
        self._status = Status()
        sha = open(os.path.join(self._url,'.git','HEAD')).read().strip()
        self._status.head_to_commit = sha

        def _multi_done_cb(success, *args):
            self._op_count -= 1
            if self._op_count == 0:
                print('======== Refreshing done in %.3f seconds ========\n' % \
                      (time.time() - startup_time))
                done_cb(True, *args)

        self._op_count = 5
        self._fetch_status(_multi_done_cb, *args)
        self._fetch_status_text(_multi_done_cb, *args)
        self._fetch_branches_and_tags(_multi_done_cb, *args)
        self._fetch_local_config(_multi_done_cb, *args)
        self._fetch_head_tag(_multi_done_cb, *args)

    """
    def refresh(self, done_cb, *args):
        "" Sync implementation, one command after the other ""
        print('\n======== Refreshing repo =========================')
        startup_time = time.time()
        ops = [self._fetch_status, self._fetch_status_text,
               self._fetch_branches_and_tags, self._fetch_local_config]
        self._status = Status()

        def _multi_done_cb(success):
            if len(ops) > 0:
                func = ops.pop(0)
                func(_multi_done_cb)
            else:
                print('======== Refreshing done in %.3f seconds ========\n' % \
                      (time.time() - startup_time))
                done_cb(True, *args)

        _multi_done_cb(True)
    """

    def _fetch_status(self, done_cb, *args):
        def _cmd_done_cb(lines, success):
            if len(lines) < 1 or not lines[0].startswith('## '):
                done_cb(False)
                return

            # parse the first line (branch info)
            # ex: "## master"
            # ex: "## master...origin/master"
            # ex  "## master...origin/master [ahead 1]"
            # ex: "## HEAD (nessun branch)"
            line = lines.pop(0)[3:]
            if line.startswith('HEAD'):
                self._status.head_detached = True
            elif '[ahead' in line:
                self._status.ahead = int(line.split('[ahead')[1][:-1])
            elif '[behind' in line:
                self._status.behind = int(line.split('[behind')[1][:-1])

            # parse the list of changed files
            for line in lines:
                fname = line[3:]
                if line[0] == '?':   # untracked (added not staged)
                    self._status.changes.append(('?', False, fname, None))
                elif line[0] == 'A': # added and staged
                    self._status.changes.append(('A', True, fname, None))
                elif line[0] == 'D': # deleted and staged
                    self._status.changes.append(('D', True, fname, None))
                elif line[1] == 'D': # deleted not staged
                    self._status.changes.append(('D', False, fname, None))
                elif line[0] == 'M': # modified and staged
                    self._status.changes.append(('M', True, fname, None))
                elif line[1] == 'M': # modified not staged
                    self._status.changes.append(('M', False, fname, None))
                elif line[0] == 'U': # unmerged
                    self._status.changes.append(('U', False, fname, None))
                elif line[0] == 'R': # renamed
                    name, new_name = fname.split(' -> ')
                    self._status.changes.append(('R', True, name, new_name))

            # special statuses
            self._status.is_merging = \
                os.path.exists(os.path.join(self._url, '.git', 'MERGE_HEAD'))
            self._status.is_cherry = \
                os.path.exists(os.path.join(self._url, '.git', 'CHERRY_PICK_HEAD'))
            self._status.is_reverting = \
                os.path.exists(os.path.join(self._url, '.git', 'REVERT_HEAD'))
            self._status.is_bisecting = \
                os.path.exists(os.path.join(self._url, '.git', 'BISECT_LOG'))

            done_cb(success, *args)
        GitCmd(self._url, 'status --porcelain -b -u', done_cb=_cmd_done_cb)

    def _fetch_status_text(self, done_cb, *args):
        def _cmd_done_cb(lines, success):
            self._status.textual = '<br>'.join(lines)
            done_cb(success, *args)
        GitCmd(self._url, 'status', done_cb=_cmd_done_cb)

    def _fetch_head_tag(self, done_cb, *args):
        def _cmd_done_cb(lines, success):
            if success:
                self._status.head_to_tag = lines[0]
            done_cb(success, *args)

        cmd = 'describe --tags --exact-match HEAD'
        GitCmd(self._url, cmd, done_cb=_cmd_done_cb)

    def _fetch_branches_and_tags(self, done_cb, *args):
        def _cmd_line_cb(line):
            objtype, head, refname, upstream = line.split('|')
            # tags
            if refname.startswith('refs/tags/'):
                self._tags.append(refname[10:]) # remove 'ref/tags/'
            # local branches
            elif refname.startswith('refs/heads/'):
                bname = refname[11:] # remove 'refs/heads/'
                b = Branch(bname, is_current=(head == '*'))
                if upstream:
                    split = upstream.split('/')
                    b.remote = split[2]
                    b.remote_branch = '/'.join(split[3:])
                if b.is_current:
                    self.status.current_branch = b
                self._branches.append(b)
            # remote branches
            elif refname.startswith('refs/remotes'):
                self._remote_branches.append(refname[13:]) # remove'refs/remotes/'

        def _cmd_done_cb(lines, success):
            done_cb(success, *args)

        del self._branches[:]
        del self._remote_branches[:]
        del self._tags[:]
        cmd = 'for-each-ref --format="%(objecttype)|%(HEAD)|%(refname)|%(upstream)"'
        GitCmd(self._url, cmd, _cmd_done_cb, _cmd_line_cb)

    def _fetch_local_config(self, done_cb, *args):
        def _cmd_done_cb(lines, success):
            for line in lines:
                key, val = line.split(' ', 1)
                key, name, prop = key.split('.')
                if key == 'remote':
                    r = self.remote_get_by_name(name) 
                    if not r:
                        r = Remote(name)
                        self._remotes.append(r)
                    if prop in ('url', 'fetch'):
                        setattr(r, prop, val)

            done_cb(success, *args)

        del self._remotes[:]
        cmd = 'config --local --get-regexp "remote."'
        GitCmd(self._url, cmd, _cmd_done_cb)

    @property
    def url(self):
        return self._url

    @property
    def name(self):
        return self._name

    # name_set(self, name, done_cb, *args) not implemented

    @property
    def description(self):
        return self._description

    def description_set(self, description, done_cb, *args):
        desc_file = os.path.join(self._url, '.git', 'description')
        if file_put_contents(desc_file, description) is True:
            self._description = description
            done_cb(True, *args)
        else:
            done_cb(False, *args)

    @property
    def status(self):
        return self._status

    def checkout(self, branch, done_cb, *args):
        def _cmd_done_cb(lines, success):
            if success:
                self.refresh(done_cb, *args)
            else:
                done_cb(success, '\n'.join(lines))

        cmd = "checkout %s" % (branch)
        GitCmd(self._url, cmd, _cmd_done_cb)

    @property
    def branches(self):
        return self._branches

    @property
    def remote_branches(self):
        return self._remote_branches

    @property
    def tags(self):
        return self._tags

    def request_commits(self, done_cb, prog_cb, max_count=100, skip=0):

        def _cmd_done_cb(lines, success, lines_buf):
            done_cb(success)

        def _cmd_line_cb(line, lines_buf):
            lines_buf.append(line)
            if line and line[-1] == chr(0x03):
                _parse_commit('\n'.join(lines_buf)[:-1])
                del lines_buf[:]

        def _parse_commit(buf):
            c = Commit()
            (c.sha, c.parents, c.author, c.author_email, c.commit_date,
                c.title, c.message, refs) = buf.split(chr(0x00))
            if c.parents:
                c.parents = c.parents.split(' ')
            if c.commit_date:
                c.commit_date = datetime.fromtimestamp(int(c.commit_date))
            if refs:
                refs = refs.strip().strip(')(').split(', ')
                for ref in refs:
                    if ref.startswith('tag: refs/tags/'):
                        c.tags.append(ref[15:])
                    elif ref.startswith('refs/tags/'):
                        c.tags.append(ref[10:])
                    elif ref == 'HEAD':
                        c.heads.append(ref)
                    elif ref.startswith(('refs/heads/')):
                        c.heads.append(ref[11:])
                    elif ref.startswith('refs/remotes/'):
                        c.remotes.append(ref[13:])
                    else:
                        c.heads.append(ref) # TODO REMOVE ME
                        LOG("UNKNOWN REF: %s" % ref)
            prog_cb(c)

        # fmt = 'format:{"sha":"%H", "parents":"%P", "author":"%an",
        #                "author_email":"%ae", "commit_ts":%ct, "title":"%s",
        #                "body": "%b", "refs":"%d"}'
        # Use ascii char 00 as field separator and char 03 as commits separator
        fmt = '%x00'.join(('%H','%P','%an','%ae','%ct','%s','%b','%d')) + '%x03'
        cmd = "log --pretty='tformat:%s' --decorate=full --all -n %d" % (fmt, max_count)
        if skip > 0: cmd += ' --skip %d' % skip
        GitCmd(self._url, cmd, _cmd_done_cb, _cmd_line_cb, list())

    def request_diff(self, done_cb, prog_cb=None, commit1=None, commit2=None,
                     path=None, only_staged=False, revert=False):
        cmd = 'diff --no-prefix'
        if only_staged:
            cmd += ' --staged'
        if commit2 and commit2.sha and commit1 and commit1.sha:
            cmd += ' %s %s' % (commit1.sha, commit2.sha)
        elif revert and commit1 and commit1.sha:
            cmd += ' %s %s^' % (commit1.sha, commit1.sha)
        elif commit1 and commit1.sha:
            cmd += ' %s^ %s' % (commit1.sha, commit1.sha)
        else:
            cmd += ' HEAD'
        if path is not None:
            cmd += ' -- %s' % path
        GitCmd(self._url, cmd, done_cb, prog_cb)

    def request_changes(self, done_cb, commit1=None, commit2=None):
        def _cmd_done_cb(lines, success):
            L = []
            for line in lines:
                split = line.split('\t')
                if line[0] == 'R':
                    L.append(('R', split[1], split[2]))
                else:
                    L.append((split[0], split[1], None))
            # A: addition of a file
            # C: copy of a file into a new one
            # D: deletion of a file
            # M: modification of the contents or mode of a file
            # R: renaming of a file
            # T: change in the type of the file
            # U: file is unmerged (you must complete the merge before it can be committed)
            # X: "unknown" change type (most probably a bug, please report it)

            # TODO handle unmerged ??

            done_cb(success, L)

        cmd = 'diff --name-status --find-renames'
        if commit2 and commit2.sha and commit1 and commit1.sha:
            cmd += ' %s %s' % (commit1.sha, commit2.sha)
        elif commit1 is not None and commit1.sha:
            cmd += ' %s^ %s' % (commit1.sha, commit1.sha)
        else:
            cmd += ' HEAD'
        GitCmd(self._url, cmd, _cmd_done_cb)

    @property
    def remotes(self):
        return self._remotes

    def remote_get_by_name(self, name):
        for r in self._remotes:
            if r.name == name:
                return r

    def request_remote_info(self, done_cb, remote_name):
        def _cmd_done_cb(lines, success):
            if success:
                done_cb(success, '\n'.join(lines))
            else:
                done_cb(success, None, '\n'.join(lines))

        cmd = 'remote show %s' % remote_name
        GitCmd(self._url, cmd, _cmd_done_cb)

    def remote_add(self, done_cb, name, url):
        def _cmd_done_cb(lines, success):
            self._fetch_local_config(done_cb)

        cmd = 'remote add %s %s' % (name, url)
        GitCmd(self._url, cmd, _cmd_done_cb)

    def remote_del(self, done_cb, name):
        def _cmd_done_cb(lines, success):
            self._fetch_local_config(done_cb)

        cmd = 'remote remove %s' % (name)
        GitCmd(self._url, cmd, _cmd_done_cb)

    def remote_url_set(self, done_cb, name, new_url):
        def _cmd_done_cb(lines, success):
            self._fetch_local_config(done_cb)

        cmd = 'remote set-url %s %s' % (name, new_url)
        GitCmd(self._url, cmd, _cmd_done_cb)

    def stage_file(self, done_cb, path):
        def _cmd_done_cb(lines, success):
            self.refresh(done_cb)
        mod = None
        for _mod, _staged, _path, _new_path in self._status.changes:
            if _path == path: mod = _mod
        if mod == 'D':
            cmd = 'rm ' + path
        else:
            cmd = 'add ' + path
        GitCmd(self._url, cmd, _cmd_done_cb)

    def unstage_file(self, done_cb, path):
        def _cmd_done_cb(lines, success):
            self.refresh(done_cb)
        cmd = 'reset HEAD ' + path
        GitCmd(self._url, cmd, _cmd_done_cb)

    def commit(self, done_cb, msg):
        def _cmd_done_cb(lines, success):
            if success:
                self.refresh(done_cb)
            else:
                done_cb(success, '\n'.join(lines))

        cmd = 'commit -m "{}"'.format(msg.replace('"', '\\"'))
        GitCmd(self._url, cmd, _cmd_done_cb)

    def revert(self, done_cb, commit, auto_commit=False, commit_msg=None):
        def _cmd_done_cb(lines, success):
            if success and auto_commit:
                self.commit(done_cb, commit_msg)
            elif success:
                self.refresh(done_cb)
            else:
                done_cb(success, '\n'.join(lines))

        cmd = 'revert --no-edit --no-commit %s' % commit.sha
        GitCmd(self._url, cmd, _cmd_done_cb)

    def cherrypick(self, done_cb, commit, auto_commit=False, commit_msg=None):
        def _cmd_done_cb(lines, success):
            if success and auto_commit:
                self.commit(done_cb, commit_msg)
            elif success:
                self.refresh(done_cb)
            else:
                done_cb(success, '\n'.join(lines))

        cmd = 'cherry-pick --no-commit %s' % commit.sha
        GitCmd(self._url, cmd, _cmd_done_cb)

    def discard(self, done_cb, files=[]):
        def _cmd_done_cb(lines, success):
            if success:
                self.refresh(done_cb)
            else:
                done_cb(success, '\n'.join(lines))
        if files:
            cmd = 'checkout %s' % (' '.join(files))
        else:
            cmd = 'reset --hard HEAD'
        GitCmd(self._url, cmd, _cmd_done_cb)

    def pull(self, done_cb, progress_cb, remote, rbranch, lbranch):
        cmd = 'pull -v --progress %s %s:%s' % (remote, rbranch, lbranch)
        GitCmdRAW(self._url, cmd, done_cb, progress_cb)

    def push(self, done_cb, progress_cb, remote, rbranch, lbranch, dry=False):
        cmd = 'push -v --progress %s %s %s:%s ' % ('--dry-run' if dry else '',
                                                   remote, lbranch, rbranch)
        GitCmdRAW(self._url, cmd, done_cb, progress_cb)

    def branch_create(self, done_cb, name, revision, track=False):
        def _cmd_done_cb(lines, success):
            if success:
                self.refresh(done_cb)
            else:
                done_cb(success, '\n'.join(lines))

        track = '--track' if track else '--no-track'
        cmd = 'branch %s %s %s' % (track, name, revision)
        GitCmd(self._url, cmd, _cmd_done_cb)

    def branch_delete(self, done_cb, name, force=False):
        def _cmd_done_cb(lines, success):
            if success:
                self.refresh(done_cb)
            else:
                done_cb(success, '\n'.join(lines))

        cmd = 'branch %s %s' % ('-D' if force else '-d', name)
        GitCmd(self._url, cmd, _cmd_done_cb)

    def branch_merge(self, done_cb, name, fast_forward):
        def _cmd_done_cb(lines, success):
            if success:
                self.refresh(done_cb)
            else:
                done_cb(success, '\n'.join(lines))

        cmd = 'merge --no-commit --%s %s' % (fast_forward, name)
        GitCmd(self._url, cmd, _cmd_done_cb)

    def tag_delete(self, done_cb, name):
        def _cmd_done_cb(lines, success):
            if success:
                self.refresh(done_cb)
            else:
                done_cb(success, '\n'.join(lines))

        GitCmd(self._url, 'tag --delete %s' % name, _cmd_done_cb)

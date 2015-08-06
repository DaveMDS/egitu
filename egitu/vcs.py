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
                    self.title[:20])

    def is_a_merge(self):
        return len(self.parents) > 1


class Status(object):
    def __init__(self):
        self.ahead = 0
        self.textual = ''
        self.changes = [] # list of tuples: (mod, staged, path)

    @property
    def is_clean(self):
        return (len(self.changes) == 0)


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

    @property
    def current_branch(self):
        """
        The current branch of the repo.

        NOTE: This property is cached, you need to call the refresh() function
        to actually read the value from the repo.
        """
        raise NotImplementedError("current_branch not implemented in backend")

    def current_branch_set(self, branch, done_cb, *args):
        """
        Change the current branch of the repo.

        Args:
            branch:
                The name of the branch to switch to.
            done_cb:
                Function to call when the operation finish.
                Signature: cb(success, *args)
            args:
                All the others arguments passed will be given back in
                the done_cb callback function.
        """
        raise NotImplementedError("current_branch_set() not implemented in backend")

    @property
    def branches(self):
        """
        The list of branches name present in the repository.

        NOTE: This property is cached, you need to call the refresh() function
        to actually read the list from the repo.
        """
        raise NotImplementedError("branches not implemented in backend")

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

        list_of_changes is a list of tuple with the type of the change and
        the path of the modified file. Example:
        [('M', '/path/to/file1'), ('A', '/path/to/file1')]

        Type of modification can be one of:
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


### Git backend ###############################################################
class GitCmd(Exe):
    def __init__(self, local_path, cmd, done_cb=None, line_cb=None, *args):
        self.done_cb = done_cb
        self.line_cb = line_cb
        self.args = args
        self.lines = []

        git_dir = os.path.join(local_path, '.git')
        real_cmd = 'git --git-dir="%s" --work-tree="%s" %s' % \
                   (git_dir, local_path, cmd)

        print("\n=== GITCMD " + "=" * 69)
        print(real_cmd)
        print("=" * 80)
        Exe.__init__(self, real_cmd, ECORE_EXE_PIPE_READ |
                     ECORE_EXE_PIPE_ERROR | ECORE_EXE_PIPE_READ_LINE_BUFFERED |
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


class GitBackend(Repository):
    def __init__(self):
        self._url = ""
        self._name = ""
        self._description = ""
        self._status = None
        self._current_branch = ""
        self._branches = []
        self._tags = []

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
        def _multi_done_cb(success, *args):
            self._op_count -= 1
            if self._op_count == 0:
                done_cb(True, *args)

        self._status = Status()
        self._op_count = 4
        self._fetch_status(_multi_done_cb, *args)
        self._fetch_status_text(_multi_done_cb, *args)
        self._fetch_branches(_multi_done_cb, *args)
        self._fetch_tags(_multi_done_cb, *args)

    def _fetch_status(self, done_cb, *args):
        def _cmd_done_cb(lines, success):
            if len(lines) < 1 or not lines[0].startswith('## '):
                done_cb(False)
                return

            # parse the first line (current branch + ahead)
            branch = lines.pop(0)[3:]
            if '...' in branch:
                spl = branch.split('...')
                branch = spl[0]
                try:
                    # hmm, this seems wrong. What if the branch name contain some numbers?
                    self._status.ahead = int(''.join([s for s in spl[1] if s.isdigit()]))
                except:
                    self._status.ahead = 0
            self._current_branch =  branch

            # parse the list of changed files
            for line in lines:
                fname = line[3:]
                if line[0] == '?':   # untracked (added not staged)
                    self._status.changes.append(('A', False, fname))
                elif line[0] == 'A': # added and staged
                    self._status.changes.append(('A', True, fname))
                elif line[0] == 'D': # deleted and staged
                    self._status.changes.append(('D', True, fname))
                elif line[1] == 'D': # deleted not staged
                    self._status.changes.append(('D', False, fname))
                elif line[0] == 'M': # modified and staged
                    self._status.changes.append(('M', True, fname))
                elif line[1] == 'M': # modified not staged
                    self._status.changes.append(('M', False, fname))
                # TODO more status

            done_cb(success, *args)
        GitCmd(self._url, 'status --porcelain -b -u', done_cb=_cmd_done_cb)

    def _fetch_status_text(self, done_cb, *args):
        def _cmd_done_cb(lines, success):
            self._status.textual = '<br>'.join(lines)
            done_cb(success, *args)
        GitCmd(self._url, 'status', done_cb=_cmd_done_cb)

    def _fetch_branches(self, done_cb, *args):
        def _cmd_done_cb(lines, success):
            L = []
            for branch in lines:
                if branch.startswith('* '):
                    L.append(branch[2:].strip())
                else:
                    L.append(branch.strip())
            self._branches = L
            done_cb(success, *args)
        GitCmd(self._url, 'branch', _cmd_done_cb)

    def _fetch_tags(self, done_cb, *args):
        def _cmd_done_cb(lines, success):
            self._tags = lines
            done_cb(success, *args)
        GitCmd(self._url, 'tag', _cmd_done_cb)

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

    @property
    def current_branch(self):
        return self._current_branch

    def current_branch_set(self, branch, done_cb, *args):
        def _cmd_done_cb(lines, success):
            # TODO check result
            print(lines)
            self.refresh(done_cb, *args)
        cmd = "checkout %s" % (branch)
        GitCmd(self._url, cmd, _cmd_done_cb)

    @property
    def branches(self):
        return self._branches

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
            L = [ line.split('\t') for line in lines ]
            # A: addition of a file
            # C: copy of a file into a new one
            # D: deletion of a file
            # M: modification of the contents or mode of a file
            # R: renaming of a file
            # T: change in the type of the file
            # U: file is unmerged (you must complete the merge before it can be committed)
            # X: "unknown" change type (most probably a bug, please report it)

            # TODO handle move, rename (unmerged ??)

            done_cb(success, L)

        cmd = 'diff --name-status'
        if commit2 and commit2.sha and commit1 and commit1.sha:
            cmd += ' %s %s' % (commit1.sha, commit2.sha)
        elif commit1 is not None and commit1.sha:
            cmd += ' %s^ %s' % (commit1.sha, commit1.sha)
        else:
            cmd += ' HEAD'
        GitCmd(self._url, cmd, _cmd_done_cb)

    def stage_file(self, done_cb, path):
        def _cmd_done_cb(lines, success):
            self.refresh(done_cb)
        mod = None
        for _mod, _staged, _path in self._status.changes:
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

        cmd = 'commit -m "{}"'.format(msg.replace('"', '\"'))
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

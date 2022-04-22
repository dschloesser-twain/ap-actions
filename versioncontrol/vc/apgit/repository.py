import os
from shutil import ExecError
import shutil
import git
from vc.versioncontrol_interface import *
from typing import cast

import gc

def _map_op_code(op_code: int) -> str:
    if op_code == 32:
        return "downloading"
    if op_code == 256:
        return "updating"
    if op_code == 4:
        return "counting"
    if op_code == 64:
        return "resolving"
    if op_code == 16:
        return "writing"
    if op_code == 8:
        return "compressing"
    return str(op_code)

class _CloneProgress(git.RemoteProgress):
    def __init__(self, progress) -> None:
        super().__init__()
        self.progress = progress

    def update(self, op_code, cur_count, max_count=None, message=''):
        self.progress.update(_map_op_code(op_code), cur_count, max_count)

class _PushProgress(git.RemoteProgress):
    def __init__(self, progress) -> None:
        super().__init__()
        self.progress = progress

    def update(self, op_code, cur_count, max_count=None, message=''):
        self.progress.update(_map_op_code(op_code), cur_count, max_count)

class _PullProgress(git.RemoteProgress):
    def __init__(self, progress) -> None:
        super().__init__()
        self.progress = progress

    def update(self, op_code, cur_count, max_count=None, message=''):
        self.progress.update(_map_op_code(op_code), cur_count, max_count)

class GitRepository(VCRepository):
    repo: git.Repo

    def __del__(self) -> None:
        # GitPython tends to leak memory / keep git.exe processes dangling
        del self.repo 
        gc.collect()
        
        print("\n\nDELETING git repo. If this message does not show up we are leaking memory\n\n")

    @staticmethod
    def is_repo(path: str) -> bool:
        return os.path.exists(os.path.join(path, ".git"))

    @classmethod
    def create(cls, path: str):
        repo = cls()
        repo.repo = git.Repo.init(path)
        repo.repo.git.lfs("install", "--local")
        return repo

    @classmethod
    def clone(cls, remote_url: str, local_path: str, progress: Optional[Progress] = None):
        repo = cls()
        if progress is not None:
            repo.repo = git.Repo.clone_from(remote_url, local_path,  progress = _CloneProgress(progress))
        else:
            repo.repo = git.Repo.clone_from(remote_url, local_path)
            
        repo.repo.git.lfs("install", "--local")
        return repo

    @classmethod
    def load(cls, path: str):
        repo = cls()
        repo.repo = git.Repo(path, search_parent_directories=True)
        repo.repo.git.lfs("install", "--local")
        return repo

    def push(self, progress: Optional[Progress] = None) -> UpdateState:
        branch = self._get_current_branch()
        remote = self._get_default_remote(branch)
        state = UpdateState.OK
        if progress is not None:
            for info in self.repo.remote(remote).push(progress = _PushProgress(progress)):
                if info.flags & git.PushInfo.ERROR:
                    state = UpdateState.ERROR
        else: 
            for info in self.repo.remote(remote).push():
                if info.flags & git.PushInfo.ERROR:
                    state = UpdateState.ERROR
        return state

    def update(self, progress: Optional[Progress] = None, rebase = True) -> UpdateState:
        branch = self._get_current_branch()
        remote = self._get_default_remote(branch)
        state = UpdateState.OK
        try:
            if progress is not None:
                for info in self.repo.remote(remote).pull(progress = _PullProgress(progress), rebase = rebase):
                    if info.flags & git.FetchInfo.ERROR:
                        state = UpdateState.ERROR
            else: 
                for info in self.repo.remote(remote).pull(rebase = rebase):
                    if info.flags & git.FetchInfo.ERROR:
                        state = UpdateState.ERROR
        except Exception as e:
            if self.has_conflicts():
                return UpdateState.CONFLICT
            raise e

        return state

    def restore_files(self, files: list[str]):
        self.repo.git.checkout("--", *files)

    def get_pending_changes(self, staged: bool = False) -> Changes:
        changes = Changes()
        if staged:
            diff = self.repo.head.commit.diff()
        else:
            diff = self.repo.index.diff(None) 
        
        self._get_file_changes(diff, changes)

        if not staged:
            for untracked_file in self.repo.untracked_files:
                changes.new_files.append(Change(path = untracked_file)) 

        return changes

    def stage_all_files(self):
        self.repo.git.add(".")

    def unstage_all_files(self):
        self.repo.git.restore("--staged", ".")

    def stage_files(self, paths: list[str]):
        existing = []
        deleted = []
        for path in paths:
            if os.path.exists(path):
                existing.append(path)
            else:
                deleted.append(path)

        if len(existing) > 0:
            self.repo.index.add(existing)
        if len(deleted) > 0:
            self.repo.index.remove(deleted)

    def unstage_files(self, paths: list[str]):
        self.repo.git.restore("--staged", *paths)

    def commit(self, message: str):
        self.repo.index.commit(message)

    def get_root_path(self):
        return self.repo.working_dir

    def track_lfs(self, extensions: list[str]):
        patterns = ["*" + ext for ext in extensions]
        self.repo.git.lfs("track", patterns)

    def get_conflicts(self):
        conflicts = []
        status_lines = self.repo.git.status(porcelain=True).splitlines()
        for status in status_lines:
            split = status.split()
            if len(split) == 2:
                if split[0] == "UU":
                    conflicts.append(split[1])    

        return conflicts

    def has_conflicts(self):
        status_lines = self.repo.git.status(porcelain=True).split()
        return "UU" in status_lines

    def is_rebasing(self):
        repodir = self._get_repo_internal_dir()
        rebase_dirs = ["rebase-merge", "rebase-apply"]
        for dir in rebase_dirs:
            if os.path.exists(os.path.join(repodir, dir)): return True
        return False

    def continue_rebasing(self):
        self.repo.git(c = "core.editor=true").rebase("--continue")

    def abort_rebasing(self):
        self.repo.git.rebase("--abort")

    def launch_external_merge(self, tool: Optional[str] = None, paths: Optional[list[str]] = None):
        if tool == "vscode" or tool == "code":
            if self._command_exists("code") == False:
                raise Exception("Could not find external Diff Tool")
            self.repo.git.config("merge.tool", "vscode")
            self.repo.git.config("mergetool.vscode.cmd", "code -n --wait $MERGED")
            tool = "vscode"
        if tool is None:
            raise Exception("No tool configured")
        if paths is not None:
            self.repo.git(c = "mergetool.keepBackup=false").mergetool(tool = tool, *paths)
        else:
            self.repo.git(c = "mergetool.keepBackup=false").mergetool(tool = tool)

    def launch_external_diff(self, tool: Optional[str] = None, paths: Optional[list[str]] = None):
        if tool == "vscode" or tool == "code":
            if self._command_exists("code") == False:
                raise Exception("Could not find external Diff Tool")
            self.repo.git.config("diff.tool", "vscode")
            self.repo.git.config("difftool.vscode.cmd", "code -n --wait --diff $LOCAL $REMOTE")
            tool = "vscode"
        if tool is None:
            raise Exception("No tool configured")
        if paths is not None:
            self.repo.git().difftool("--no-prompt", tool = tool, *paths)
            self.repo.git().difftool("--no-prompt", "--cached", tool = tool, *paths)
        else:
            self.repo.git().difftool("--no-prompt", tool = tool)
            self.repo.git().difftool("--no-prompt", "--cached", tool = tool)

    def _command_exists(self, cmd: str):
        return shutil.which(cmd) is not None

    def _get_current_branch(self):
        return self.repo.git.rev_parse("--abbrev-ref", "HEAD")

    def _get_default_remote(self, branch: str):
        return self.repo.git.config("--get", f"branch.{branch}.remote")

    def _get_file_changes(self, diff: git.Diff, changes: Changes):
        for change in diff.iter_change_type("M"):
            changes.modified_files.append(Change(path = change.a_path)) 
        for change in diff.iter_change_type("A"):
            changes.new_files.append(Change(path = change.a_path)) 
        for change in diff.iter_change_type("R"):
            changes.renamed_files.append(Change(path = change.b_path, old_path = change.a_path)) 
        for change in diff.iter_change_type("D"):
            changes.deleted_files.append(Change(path = change.a_path)) 

    def _make_relative_to_repo(self, path: str):
        if os.path.isabs(path):
            return os.path.relpath(path, self.repo.working_dir)
        else:
            return path

    def _get_repo_internal_dir(self):
        return os.path.join(self.repo.working_dir, ".git")
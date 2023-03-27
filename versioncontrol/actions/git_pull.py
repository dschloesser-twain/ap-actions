from threading import local
from git import GitCommandError
import anchorpoint as ap
import apsync as aps
import git_errors
import itertools

import sys, os, importlib
current_dir = os.path.dirname(__file__)
parent_dir = os.path.join(current_dir, "..")
sys.path.insert(0, parent_dir)

from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path
sys.path.remove(parent_dir)
class PullProgress(Progress):
    def __init__(self, progress: ap.Progress) -> None:
        super().__init__()
        self.ap_progress = progress

    def update(self, operation_code: str, current_count: int, max_count: int, info_text: Optional[str] = None):
        if operation_code == "downloading":
            if info_text:
                self.ap_progress.set_text(f"Downloading Files: {info_text}")
            else:
                self.ap_progress.set_text("Downloading Files")
            self.ap_progress.report_progress(current_count / max_count)
        elif operation_code == "updating":
            self.ap_progress.set_text("Updating Files")
            self.ap_progress.report_progress(current_count / max_count)
        else:
            self.ap_progress.set_text("Talking to Server")
            self.ap_progress.stop_progress()

def check_changes_writable(repo, changes):
    for change in itertools.chain(changes.new_files, changes.renamed_files, changes.modified_files, changes.deleted_files):
        path = os.path.join(repo.get_root_path(), change.path)
        if not utility.is_file_writable(path):
            error = f"error: unable to unlink '{change.path}':"
            if not git_errors.handle_error(error):
                ap.UI().show_info("Could not shelve files", f"A file is not writable: {change.path}", duration=6000)
            return False
    return True

def pull_async(channel_id: str, project_path):
    ui = ap.UI()
    try:
        path = get_repo_path(channel_id, project_path)
        repo = GitRepository.load(path)
        if not repo: return

        progress = ap.Progress("Updating Git Changes", show_loading_screen=True, cancelable=False)
        changes = repo.get_pending_changes(False)
        staged_changes = repo.get_pending_changes(True)
        
        stashed_changes = False
        if changes.size() > 0 or staged_changes.size() > 0:
            progress.set_text("Shelving Changed Files")
            if not check_changes_writable(repo, changes):
                return True
            if not check_changes_writable(repo, staged_changes):
                return True
                
            repo.stash(True)
            stashed_changes = True

        progress.set_cancelable(True)
        progress.set_text("Talking to Server")

        state = repo.update(progress=PullProgress(progress), rebase=False)
        progress.set_cancelable(False)
        if state == UpdateState.NO_REMOTE:
            ui.show_info("Branch does not track a remote branch", "Push your branch first")    
        elif state == UpdateState.CONFLICT:
            ui.show_info("Conflicts detected", "Please resolve your conflicts or cancel the pull")    
            ap.refresh_timeline_channel(channel_id)
            ap.vc_resolve_conflicts(channel_id)
            progress.finish()
            return
        elif state == UpdateState.CANCEL:
            ui.show_info("Pull Canceled")
            if stashed_changes:
                progress.set_text("Restoring Shelved Files")
                repo.pop_stash()
        elif state != UpdateState.OK:
            ui.show_error("Failed to update Git Repository")    
        else:
            if repo.is_merging():
                try:
                    repo.continue_merge()
                except Exception as e:
                    if "There is no merge in progress" in str(e):
                        pass
                    
            if stashed_changes:
                progress.set_text("Restoring Shelved Files")
                repo.pop_stash()        

            ui.show_success("Update Successful")
        progress.finish()
    except Exception as e:
        if not git_errors.handle_error(e):
            print(e)
            ui.show_error("Failed to update Git Repository", "Please try again")    
                   
    try:
        ap.vc_load_pending_changes(channel_id, True)
    except:
        ap.vc_load_pending_changes(channel_id)
    ap.refresh_timeline_channel(channel_id)

def resolve_conflicts(channel_id):
    ap.vc_resolve_conflicts(channel_id)

def on_timeline_channel_action(channel_id: str, action_id: str, ctx):
    if action_id == "gitpull":
        ctx.run_async(pull_async, channel_id, ctx.project_path)
    if action_id == "gitcancelmerge":
        from git_conflicts import cancel_merge
        ctx.run_async(cancel_merge, channel_id, ctx.project_path)
        return True
    if action_id == "gitresolveconflicts": 
        ctx.run_async(resolve_conflicts, channel_id)
        return True
    return False
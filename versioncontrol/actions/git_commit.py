import anchorpoint as ap
import apsync as aps

import sys, os
current_dir = os.path.dirname(__file__)
parent_dir = os.path.join(current_dir, "..")
sys.path.insert(0, parent_dir)

from vc.apgit.repository import * 
from vc.apgit.utility import get_repo_path
sys.path.remove(parent_dir)

def stage_files(changes, all_files_selected, repo, lfs, progress):
    def lfs_progress_callback(current, max):
        if progress.canceled:
            return False
        if max > 0:
            progress.report_progress(current / max)
        return True

    to_stage = []
    for change in changes:
        if change.selected:
            to_stage.append(change.path)

    if len(to_stage) == 0:
        return

    progress.set_text("Finding binary files")
    lfs.lfs_track_binary_files(to_stage, repo, lfs_progress_callback)
    if progress.canceled: 
        return

    progress.stop_progress()
    progress.set_text("Preparing your files to be committed. This may take some time")

    def progress_callback(current, max):
        if progress.canceled:
            return False
        progress.set_text("Staging files")
        if max > 0:
            progress.report_progress(current / max)
        return True

    try:
        repo.sync_staged_files(to_stage, all_files_selected, progress_callback)
    except Exception as e:
        submodule_error = False
        submodule_location = ""
        for change in to_stage:
            if os.path.isdir(change):
                gitdir = os.path.join(change, ".git")
                if os.path.exists(gitdir):
                    submodule_error = True
                    submodule_location = gitdir
                    break
        
        if submodule_error:
            rel_path = os.path.relpath(submodule_location,repo.get_root_path())
            d = ap.Dialog()
            d.title = "Your project contains more than one Git repository"
            d.icon = ":/icons/versioncontrol.svg"
            d.add_text(f"A folder in your project contains another Git repository and Git submodules<br>are currently not supported by Anchorpoint.<br><br>To resolve the issue, do the following:<ol><li>Backup the folder <b>{os.path.dirname(rel_path)}</b></li><li>Delete the hidden .git folder: <b>{rel_path}</b></li><li>Commit again</li></ol><br>Do not touch the .git folder in your project root!")
            d.show()
        else:
            raise e

def on_pending_changes_action(channel_id: str, action_id: str, message: str, changes, all_files_selected, ctx):
    import git_lfs_helper as lfs
    if action_id != "gitcommit": return False
    ui = ap.UI()
    progress = ap.Progress("Committing Files", "Depending on your file count and size this may take some time", show_loading_screen=True, cancelable=True)
    try:
        path = get_repo_path(channel_id, ctx.project_path)
        repo = GitRepository.load(path)
        if not repo: return
        stage_files(changes, all_files_selected, repo, lfs, progress)
        if progress.canceled:
            ui.show_success("commit canceled")
            return
        
        progress.stop_progress()
        progress.set_text("Creating the commit. This may take some time")

        staged = repo.get_pending_changes(staged=True)
        changecount = staged.size()
        if changecount == 0:
            ui.show_info("Nothing to commit")
            return

        if len(ctx.username) > 0 and len(ctx.email) > 0:
            repo.set_username(ctx.username, ctx.email, ctx.project_path)

        repo.commit(message)
        ui.show_success("Commit succeeded")
        
    except Exception as e:
        print(str(e))
        ui.show_error("Commit Failed", str(e).splitlines()[0])
        raise e
    finally:
        try:
            ap.vc_load_pending_changes(channel_id, True)
        except:
            ap.vc_load_pending_changes(channel_id)
        ap.refresh_timeline_channel(channel_id)
        return True
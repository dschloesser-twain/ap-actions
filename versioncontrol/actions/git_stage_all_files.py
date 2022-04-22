import anchorpoint as ap
import apsync as aps

import sys, os, importlib
sys.path.insert(0, os.path.join(os.path.split(__file__)[0], ".."))

importlib.invalidate_caches()
from vc.apgit.repository import * 

ctx = ap.Context.instance()
ui = ap.UI()
path = ctx.path

def stage_all():
    repo = GitRepository.load(path)
    if repo is None: return
    repo.stage_all_files()
    ui.show_success("All Files Staged")

ctx.run_async(stage_all)

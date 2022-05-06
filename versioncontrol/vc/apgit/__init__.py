import anchorpoint

try:
    import vc.apgit.utility as utility

    if utility.guarantee_git():
        try: 
            import git
        except:
            ctx = anchorpoint.Context.instance()
            ctx.install("GitPython")
            import git
    else: raise Warning("Git not installed")

except Exception as e:
    raise e
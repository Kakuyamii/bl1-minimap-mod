def hidden_reason(pc, *, allow_pause=False):
    hud = pc.myHUD
    if hud is None:
        return "no vanilla HUD"
    if not hud.bShowHUD:
        return "vanilla HUD disabled"
    if pc.bHideCompassOnHUD:
        return "vanilla compass suppressed"


    if pc.bStatusMenuOpen:
        return "status menu open"
    if not allow_pause and pc.WorldInfo.Pauser is not None:
        return "game paused"
    movie = hud.GetHUDMovie()
    if movie is None:
        return "vanilla HUD movie unavailable"


    if not (movie.bReady[0] or movie.bAwaitingReady[0]):
        return "vanilla player HUD hidden"
    return None

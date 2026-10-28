class HUDLayer:
    def __init__(self, weak_pointer=None):
        if weak_pointer is None:
            from unrealsdk.unreal import WeakPointer
            weak_pointer = WeakPointer
        self.weak_pointer = weak_pointer
        self.pointer = None
        self.previous = None

    def update(self, pc):
        hud = pc.myHUD.GetHUDMovie() if pc.myHUD is not None else None
        old = self.pointer() if self.pointer is not None else None
        if hud != old:
            self.restore()
            if hud is not None:
                self.previous = bool(hud.bKeepTopMost)
                self.pointer = self.weak_pointer(hud)
        if hud is not None:
            hud.bKeepTopMost = True

    def restore(self):
        hud = self.pointer() if self.pointer is not None else None
        if hud is not None:
            hud.bKeepTopMost = self.previous
        self.pointer = self.previous = None

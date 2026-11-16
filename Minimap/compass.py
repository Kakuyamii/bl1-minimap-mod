class CompassVisibility:


    PATH = "p1.bearing._visible"

    def __init__(self, weak_pointer=None):
        if weak_pointer is None:
            from unrealsdk.unreal import WeakPointer
            weak_pointer = WeakPointer
        self._weak_pointer = weak_pointer
        self._movie = None
        self._visible = None

    def restore(self):


        movie = self._movie() if self._movie is not None else None
        if movie is not None:
            movie.SetVariableBool(self.PATH, self._visible)
        self._movie = None
        self._visible = None

    def update(self, pc, show_compass):
        if show_compass or pc is None or pc.myHUD is None:
            self.restore()
            return
        movie = pc.myHUD.GetHUDMovie()
        previous = self._movie() if self._movie is not None else None
        if movie is None:
            self.restore()
            return
        if movie != previous:
            self.restore()

            visible = bool(movie.GetVariableBool(self.PATH))
            pointer = self._weak_pointer(movie)
            self._movie, self._visible = pointer, visible
        movie.SetVariableBool(self.PATH, False)


class EchoPosition:
    path = 'p1.echo._x'
    offset = 228.0

    def __init__(self, weak_pointer):
        self.weak_pointer = weak_pointer
        self.movie = None
        self.original = None
        self.applied = None

    def restore(self):
        movie = self.movie() if self.movie else None
        if movie is not None and movie.GetVariableNumber(self.path) == self.applied:
            movie.SetVariableNumber(self.path, self.original)
        self.movie = None
        self.original = self.applied = None

    def update(self, movie):
        if self.movie and self.movie() != movie:
            self.restore()
        if movie is None or movie.GetVariableNumber('p1.echo._currentframe') < 1:
            return
        current = movie.GetVariableNumber(self.path)
        if self.movie and current == self.applied:
            return
        self.movie = self.weak_pointer(movie)
        self.original = current
        movie.SetVariableNumber(self.path, current - self.offset)
        self.applied = movie.GetVariableNumber(self.path)

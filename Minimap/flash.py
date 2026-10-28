from __future__ import annotations

from importlib import resources
import math

import unrealsdk
from unrealsdk.unreal import WeakPointer
from mods_base import ObjectFlags


def as_value(value):

    if value is None:
        fields = {"Type": 1}
    elif isinstance(value, bool):
        fields = {"Type": 4, "B": value}
    elif isinstance(value, (float, int)):
        number = float(value)
        if not math.isfinite(number):
            raise ValueError("Flash numbers must be finite")
        fields = {"Type": 2, "N": number}
    elif isinstance(value, str):
        fields = {"Type": 3, "S": value}
    else:
        raise TypeError(f"Unsupported Flash argument: {type(value).__name__}")
    return unrealsdk.make_struct("GFxUI.GFxMovie.ASValue", **fields)


class FlashMinimap:


    def __init__(self, asset="assets/minimap.gfx", checkpoint=None):
        self.asset = asset
        self._data = None
        self._movie = self._info = self._owner = self._world = None
        self._viewport = None
        self._started = False
        self._checkpoint = checkpoint or (lambda *args, **kwargs: None)

    @property
    def movie(self):
        return self._movie() if self._movie is not None else None

    def ensure(self, pc):

        world = pc.WorldInfo
        movie = self.movie
        if (movie is not None and self._owner is not None
                and self._owner() == pc and self._world is not None
                and self._world() == world):
            return movie
        self.close()
        if self._data is None:
            self._data = resources.files(__package__).joinpath(self.asset).read_bytes()
            if self._data[:3] not in (b"FWS", b"CWS", b"GFX", b"CFX"):
                self._data = None
                raise ValueError("Minimap asset is not a supported SWF/GFX movie")
        try:


            package = unrealsdk.find_object("Core.Package", "Transient")
            if package is None:
                raise RuntimeError("Could not find the transient asset package")
            self._checkpoint("movie_info.construct.before")
            info = unrealsdk.construct_object("GFxUI.GFxMovieInfo", package,
                                              flags=ObjectFlags.KEEP_ALIVE)
            self._info = WeakPointer(info)
            self._checkpoint("movie_info.construct.after")
            self._checkpoint("movie_info.bytes.before", size=len(self._data))
            raw = info.RawData
            raw.clear()


            raw.extend([0] * len(self._data))
            for index, value in enumerate(self._data):
                raw[index] = value
            path = info._path_name()
            if len(raw) != len(self._data):
                raise RuntimeError("Minimap movie byte upload was incomplete")


            uploaded = bytes(raw[i] for i in range(len(raw)))
            if uploaded != self._data:
                mismatch = next(i for i, (a, b) in enumerate(zip(uploaded, self._data))
                                if a != b)
                raise RuntimeError(f"Minimap movie byte upload mismatch at offset {mismatch}: "
                                   f"expected {self._data[mismatch]}, got {uploaded[mismatch]}")
            if unrealsdk.find_object("GFxUI.GFxMovieInfo", path) != info:
                raise RuntimeError(f"Minimap movie resource cannot be resolved: {path}")
            self._checkpoint("movie_info.bytes.after", path=path,
                             size=len(raw), signature=uploaded[:8].hex(), verified=True)


            self._checkpoint("movie.construct.before", cls="WillowGame.LevelTransitionGFxMovie")
            movie = unrealsdk.construct_object("WillowGame.LevelTransitionGFxMovie", pc,
                                               flags=ObjectFlags.KEEP_ALIVE)
            self._movie = WeakPointer(movie)
            self._checkpoint("movie.construct.after")
            self._owner, self._world = WeakPointer(pc), WeakPointer(world)
            movie.PlayerOwner = pc
            movie.bKeepTopMost = False
            self._checkpoint("movie.set_info.before")
            movie.SetMovieInfo(info)
            self._checkpoint("movie.set_info.after")
            self._checkpoint("movie.start.before")
            if not movie.Start(False):
                raise RuntimeError(f"Scaleform rejected the minimap movie: {path} "
                                   f"({len(info.RawData)} bytes)")
            self._started = True
            self._checkpoint("movie.start.after")
            movie.SetViewScaleMode(2)
            self._checkpoint("movie.scale_mode.after")
        except BaseException:
            self.close()
            raise
        return movie

    def set_viewport(self, x, y, width, height):
        viewport = tuple(int(v) for v in (x, y, width, height))
        if viewport[2] <= 0 or viewport[3] <= 0:
            raise ValueError("Minimap viewport must have positive dimensions")
        movie = self.movie
        if movie is None:
            raise RuntimeError("Minimap movie has not started")
        if viewport != self._viewport:
            self._checkpoint("movie.viewport.before", viewport=viewport)
            movie.SetViewport(*viewport)
            self._checkpoint("movie.viewport.after")
            self._viewport = viewport

    def invoke(self, method, *values):
        movie = self.movie
        if movie is None:
            raise RuntimeError("Minimap movie has not started")
        self._checkpoint("invoke." + method + ".before")
        result = movie.Invoke(method, [as_value(value) for value in values])
        self._checkpoint("invoke." + method + ".after")
        return result

    def show(self):
        if (movie := self.movie) is not None:
            movie.SetVariableBool("_root._visible", True)

    def set_map(self, label):
        return self.invoke("_root.SetMap", str(label))

    def init_dlc(self, frame, package):
        return self.invoke("_root.InitDLC", str(frame), str(package))

    def _number(self, method):
        result = self.invoke(method)
        if result is None or int(result.Type) != 2 or not math.isfinite(float(result.N)):
            raise RuntimeError(f"Minimap movie returned no valid number for {method}")
        return float(result.N)

    def map_dimensions(self):
        return self._number("_root.GetMapWidth"), self._number("_root.GetMapHeight")

    def mask_dimensions(self):
        return self._number("_root.GetMapMaskWidth"), self._number("_root.GetMapMaskHeight")

    def set_view(self, u, v, heading_degrees, rotate, scale_percent):
        return self.invoke("_root.SetView", u, v, heading_degrees,
                           int(bool(rotate)), scale_percent)

    def clear_landmarks(self):
        return self.invoke("_root.ClearLandmarks")

    def add_landmark(self, clip, u, v, rotation, frame):
        result = self.invoke("_root.AddLandmark", clip, u, v, rotation, str(frame))
        return result.S if result is not None and int(result.Type) == 3 else None

    def update_landmark(self, path, u, v, rotation):
        return self.invoke("_root.UpdateLandmark", path, u, v, rotation)

    def update_threats(self, serialized):
        return self.invoke("_root.UpdateThreats", serialized)

    def hide(self):
        if (movie := self.movie) is not None:
            movie.SetVariableBool("_root._visible", False)

    def close(self):

        movie = self.movie
        info = self._info() if self._info is not None else None
        self._movie = self._info = self._owner = self._world = None
        self._viewport = None
        started, self._started = self._started, False
        try:
            if movie is not None:
                try:
                    if started:
                        self._checkpoint("movie.close.before")
                        movie.Close()
                        self._checkpoint("movie.close.after")
                finally:
                    try:
                        movie.PlayerOwner = None
                    finally:
                        movie.ObjectFlags &= ~ObjectFlags.KEEP_ALIVE
        finally:
            if info is not None:
                info.ObjectFlags &= ~ObjectFlags.KEEP_ALIVE

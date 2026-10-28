from __future__ import annotations

import time

import unrealsdk
from unrealsdk import logging
from unrealsdk.hooks import Type
from unrealsdk.unreal import WeakPointer
from mods_base import BoolOption, SliderOption, Game, ObjectFlags, build_mod, command, get_pc, hook

from .compass import CompassVisibility
from .flash import FlashMinimap
from .diagnostics import Diagnostics
from .geometry import Projection, coordinate_scale
from .threats import serialize_threats
from .layering import HUDLayer
from .visibility import hidden_reason

SHOW_COMPASS = BoolOption("Show compass", True, description="Show the original compass alongside the minimap.")
SHOW_MINIMAP = BoolOption("Show minimap", True, description="Show Enhanced's vector map and icons.")
ROTATE_MINIMAP = BoolOption("Rotate minimap", False, description="Rotate the map with the player; keep icons upright.")
ZOOM = SliderOption("Minimap zoom", 400, 100, 1000, 25,
                    description="Map magnification in percent. Higher values show a smaller area.")

_diagnostics = Diagnostics()
_flash = FlashMinimap(checkpoint=_diagnostics.checkpoint)
_compass = CompassVisibility()
_layer = HUDLayer()
_blocked_world = None
_next_threat_update = 0.0
_threat_error = None
_helper = _owner = _world = None
_next_refresh = _retry_at = 0.0
_last_error = None
_status = "Waiting for a playable level"
_map_key = None
_map_ready = False
_marker_signature = None
_marker_paths = []


def _vec(v):
    return float(v.X), float(v.Y), float(v.Z)


def _projection(matrix):
    return Projection(tuple(tuple(float(getattr(row, c)) for c in "XYZW")
                            for row in (matrix.XPlane, matrix.YPlane,
                                        matrix.ZPlane, matrix.WPlane)))


def reset():
    global _helper, _owner, _world, _next_refresh, _retry_at, _status
    global _map_key, _map_ready, _marker_signature, _marker_paths
    global _next_threat_update, _threat_error
    _next_threat_update = 0.0
    _threat_error = None
    obj = _helper() if _helper is not None else None
    _helper = _owner = _world = None
    _map_key, _map_ready, _marker_signature, _marker_paths = None, False, None, []
    _next_refresh = _retry_at = 0.0
    _status = "Waiting for a playable level"
    try:
        _compass.restore()
    finally:
        try:
            try:
                _flash.close()
            finally:
                _layer.restore()
        finally:
            if obj is not None:
                try:
                    obj.MapObjects.clear()
                    obj.PlayerOwner = None
                    obj.Anchor = None
                finally:
                    obj.ObjectFlags &= ~ObjectFlags.KEEP_ALIVE


def _get_helper(pc):
    global _helper, _owner, _world, _next_refresh
    obj = _helper() if _helper is not None else None
    if (obj is None or _owner is None or _owner() != pc
            or _world is None or _world() != pc.WorldInfo):
        reset()
        _diagnostics.checkpoint("helper.construct.before")
        obj = unrealsdk.construct_object("WillowGame.WillowGFxHelperMap", pc,
                                        flags=ObjectFlags.KEEP_ALIVE)
        _helper, _owner, _world = WeakPointer(obj), WeakPointer(pc), WeakPointer(pc.WorldInfo)
        _diagnostics.checkpoint("helper.construct.after")
    now = time.monotonic()
    if now >= _next_refresh:
        obj.MapObjects.clear()
        obj.Anchor = None
        _diagnostics.checkpoint("helper.init.before")
        obj.Init(pc)
        _diagnostics.checkpoint("helper.init.after")
        _next_refresh = now + 2.0
    _diagnostics.checkpoint("helper.update.before")
    obj.UpdateObjects(True)
    _diagnostics.checkpoint("helper.update.after")
    return obj


def _prepare_map(helper):
    global _map_key, _map_ready, _marker_signature, _status
    anchor = helper.Anchor
    if anchor is None or not anchor.MapFrame:
        _status = "This level has no vector map frame"
        return False
    dlc = anchor.DLCMap
    key = (str(anchor.MapFrame), "/ package/" + dlc._path_name() if dlc is not None else "")
    if key != _map_key:
        _map_ready = False
        _marker_signature = None
        if key[1]:

            _flash.init_dlc(key[0], key[1])
        else:
            _flash.set_map(key[0])
        _map_key = key
    if not _map_ready:
        width, height = _flash.map_dimensions()
        if width <= 0 or height <= 0:
            _status = f"Waiting for vector map {key[0]}"
            return False

        sx, sy = coordinate_scale((float(helper.AnchorSize.X), float(helper.AnchorSize.Y)),
                                   (width, height))
        helper.CoordScale = unrealsdk.make_struct("Vector2D", X=sx, Y=sy)
        helper.UpdateObjects(True)
        _flash.invoke("_root.map.SetMapScale", float(ZOOM.value))
        _map_ready = True
    return True


def _update_markers(helper):
    global _marker_signature, _marker_paths
    markers = list(helper.MapObjects)
    signature = tuple((str(m.AS_IconClipPath), str(m.AS_IconClipFrame)) for m in markers)
    if signature != _marker_signature:
        _flash.clear_landmarks()
        _marker_paths = [None] * len(markers)
        _marker_signature = signature
    for i, marker in enumerate(markers):
        path = _marker_paths[i]
        visible = bool(marker.bIsDirty)
        if visible:
            x, y = float(marker.TransformedLocation.X), float(marker.TransformedLocation.Y)
            angle = float(marker.Angle)
            if path is None:
                clip, frame = signature[i]

                clip = clip.removeprefix("map.")
                if not clip or not frame:
                    continue
                path = _flash.add_landmark(clip, x, y, angle, frame)
                _marker_paths[i] = path
            if path:
                _flash.movie.SetVariableBool(path + "._visible", True)
                _flash.update_landmark(path, x, y, angle)
        elif path:
            _flash.movie.SetVariableBool(path + "._visible", False)


def _draw(canvas, pc, helper):
    global _status, _next_threat_update, _threat_error
    _layer.update(pc)
    _flash.ensure(pc)
    if not _prepare_map(helper):
        _flash.hide()
        return
    scale = float(canvas.SizeY) / 1080.0
    width, height = 260 * scale, 220 * scale
    margin = 24 * scale
    _flash.set_viewport(float(canvas.SizeX) - width - margin, margin, width, height)
    uv = _projection(helper.Transform).uv(_vec(pc.Pawn.Location))
    center = (uv[0] * helper.CoordScale.X, uv[1] * helper.CoordScale.Y)
    heading = float(pc.Rotation.Yaw) * 360.0 / 65536.0
    for marker in helper.MapObjects:
        if marker.Player == pc and marker.bIsDirty:
            heading = float(marker.Angle)
            break
    _flash.set_view(*center, heading, ROTATE_MINIMAP.value, float(ZOOM.value))
    _update_markers(helper)
    now = time.monotonic()
    if now >= _next_threat_update:
        try:
            _flash.update_threats(serialize_threats(pc, _projection(helper.Transform), helper.CoordScale))
            _threat_error = None
            _next_threat_update = now + 0.1
        except Exception as exc:
            message = f"{type(exc).__name__}: {exc}"
            if message != _threat_error:
                _diagnostics.error(exc)
                logging.error(f"[Minimap] Enemy markers unavailable; map remains visible: {message}")
            _threat_error = message
            _next_threat_update = now + 5.0
            try:
                _flash.update_threats("")
            except Exception:
                pass
    _flash.show()
    _status = f"Rendering vector map {_map_key[0]}; rotate={ROTATE_MINIMAP.value}"
    if _threat_error:
        _status += f"; enemy markers unavailable: {_threat_error}"


@hook("Engine.GameViewportClient:PostRender", Type.POST)
def render(obj, args, ret, func):
    global _retry_at, _last_error, _status, _blocked_world
    if time.monotonic() < _retry_at:
        return
    try:
        pc = get_pc()
        if pc is None or pc.Pawn is None:
            reset()
            return
        if _blocked_world is not None:
            if _blocked_world() == pc.WorldInfo:
                return
            _blocked_world = None
        reason = hidden_reason(pc)
        if reason is not None:
            _flash.hide()
            _layer.restore()
            _status = f"Minimap hidden: {reason}"
            return
        if SHOW_MINIMAP.value:
            helper = _get_helper(pc)
            _compass.update(pc, SHOW_COMPASS.value)
            _draw(args.Canvas, pc, helper)
        else:
            _layer.restore()
            _compass.update(pc, SHOW_COMPASS.value)
            _flash.hide()
            _status = "Minimap hidden by option"
    except Exception as exc:
        _diagnostics.error(exc)
        try:
            _flash.hide()
        except Exception:
            pass
        message = f"{type(exc).__name__}: {exc}"
        _status = f"Minimap unavailable: {message}"
        if message != _last_error:
            logging.error(f"[Minimap] {_status}. Use minimap_status for diagnostics.")
            _last_error = message
        _retry_at = time.monotonic() + 5.0


@hook("Engine.PlayerController:PreClientTravel", Type.PRE)
def pre_travel(obj, args, ret, func):
    _end_session()


def _end_session():
    global _blocked_world
    if _world is not None:
        _blocked_world = _world
    _diagnostics.record("session.cleanup")
    reset()


@hook("WillowGame.WillowPlayerController:ReturnToTitleScreen", Type.PRE)
def return_to_title(obj, args, ret, func):
    _end_session()


@hook("WillowGame.WillowGameViewportClient:GameSessionEnded", Type.PRE)
def session_ended(obj, args, ret, func):
    _end_session()


@hook("WillowGame.WillowPlayerController:Destroyed", Type.PRE)
def player_destroyed(obj, args, ret, func):
    if _owner is not None and _owner() == obj:
        _end_session()


def enable():
    global _blocked_world
    _blocked_world = None
    try:
        _diagnostics.start()
        logging.info(f"[Minimap] Diagnostics: {_diagnostics.path}")
    except OSError as exc:
        logging.error(f"[Minimap] Could not create diagnostic log: {exc}")


def disable():
    try:
        reset()
    finally:
        _diagnostics.stop()


@command("minimap_status", description="Print minimap runtime diagnostics to the SDK log.")
def status(args):
    logging.info(f"[Minimap 0.2.9] {_status}; diagnostics={_diagnostics.path}")
    obj = _helper() if _helper is not None else None
    if obj is not None:
        logging.info(f"[Minimap] Anchor={obj.Anchor}, CoordScale={obj.CoordScale}, Transform={obj.Transform}")


build_mod(options=[SHOW_COMPASS, SHOW_MINIMAP, ROTATE_MINIMAP, ZOOM],
          auto_enable=True,
          hooks=[render, pre_travel, return_to_title, session_ended, player_destroyed], commands=[status], on_enable=enable,
          on_disable=disable, supported_games=Game.BL1)

# Minimap 0.2.9

Fixes the 0.2.8 regression where the minimap was hidden in gameplay and appeared
in Escape. The viewport-wide AreHudMoviesVisible result is no longer used:
the live report showed it returning false while the player's vanilla HUD was visible.
Visibility follows bShowHUD, native per-player show/hide flags and compass
suppression, with explicit status-menu and pause checks to keep overlays hidden.

The mod's own Show compass option remains independent of Show minimap.
Cinematics that hide the native HUD also hide the minimap; cinematic mode alone
does not force hiding. These transitions need an in-game retest.

Enabled state and options persist through the SDK settings/Minimap.json file.

Cleanup now runs before return-to-title, session end and player destruction, in
addition to travel. Rendering cannot recreate the helper in a world being closed.
Enemy dots use BL1's live pawn list and IsEnemy check; this is not Enhanced's exact
threat-awareness cache. Hidden/dead/friendly pawns are excluded, and the nearest
128 hostile pawns are refreshed at 10 Hz.

## Automatic crash diagnostics

Enabling Minimap creates logs in `Borderlands/sdk_mods/crash dumps/Minimap/`:

- `minimap-<timestamp>-<pid>.jsonl`: durable startup and first-frame checkpoints,
  plus caught Python exceptions. Each entry is flushed before the next native call.
- Matching `.python-fault.txt`: best-effort Python crash traceback, when no other
  component already owns Python's fault handler. It may remain empty.
- `native/`: up to three recent nonempty engine `.dmp` files copied on the next
  game launch/enable from the normal Documents/my games/borderlands log directory.
  Original dumps are preserved. These files may also contain unrelated crashes.

If the game still crashes, send the newest `.jsonl`, matching fault text and newest
`.dmp` from that folder. `minimap_status` prints the active log path. These logs
do not guarantee a full native dump; native faults bypass Python exception handling.

Standalone Python SDK mod for **original Borderlands GOTY (BL1)**. This revision
replaces the 0.1 Canvas terrain overlay with the actual Enhanced vector maps,
frame, icons, and minimap ActionScript extracted from the locally installed game.
There is no terrain-texture rendering path.

## Install / update

Close the game. Replace `Borderlands/sdk_mods/Minimap.sdkmod` with this archive,
keeping its name unchanged. Do not extract it. Start the game and enable Minimap
in the Mods menu. Modern BL1 Python SDK is required.

On this machine the destination is:
`/home/kaku/.local/share/Steam/steamapps/common/Borderlands/sdk_mods/Minimap.sdkmod`.
Disable Minimap to close its movie and restore the compass's prior visibility.
Delete the archive with the game closed to uninstall.

## Options

These match the settings recovered from Enhanced's profile defaults:

| Option | Default | Behavior |
|---|---|---|
| Show compass | On | Preserve the original compass; Off hides it. |
| Show minimap | On | Show the vector minimap. Independent of the compass. |
| Rotate minimap | Off | Rotate the map with the player using Enhanced's code. |
| Minimap zoom | 400% | Magnification from 100% to 1000%; higher values show less area. |

The old terrain range/opacity controls are removed. The new view uses Enhanced's
initial 400% map scale, native aspect correction, icon frames and clipping.

## Validation status

The user confirmed 0.2.7 works fully. Version 0.2.9 passes 36 offline tests.
Check HUD toggles, opening/closing menus, and cinematics that hide the HUD;
confirm the minimap disappears and returns alongside vanilla HUD elements.
Enhanced custom player-waypoint placement remains unimplemented.
Ordinary icons come from original GOTY's native map helper. Local player rendering
is implemented; split-screen is not. DLC map loading uses original installed DLC
movies and needs testing. HUD positioning uses the extracted shear and frame shape
in a dedicated upper-right viewport; full Enhanced HUD/ECHO layout is not ported.

## In-game checklist

1. Enable Minimap in Arid Badlands. Run `minimap_status` in the SDK console if it
   does not appear; retain its output and the SDK log.
2. Verify the blue vector map and outlined frame match the map menu. Compare a
   road, doorway or building and the player position against the full map.
3. Check player, objective, vending, Catch-A-Ride and other available icons. Walk
   past them and check placement; compare with the full map.
4. Turn Rotate minimap on and rotate through a full circle. The player stays
   centered, other icons stay upright, and the N marker follows the frame edge.
5. Toggle both visibility options in all four combinations. Disable the mod and
   confirm the compass returns to its previous visibility.
6. Open inventory/map, pause, travel, die, return to title, reload and disable/
   re-enable. Confirm there is no stale overlay and no repeated SDK error log.
7. Test co-op and each DLC before claiming compatibility.

## Rebuild

```bash
python3 -m unittest discover -s tests -v
python3 tools/build_mod.py Minimap
```

Output: `dist/Minimap.sdkmod`. It contains its own extracted minimap asset; future
backports remain separate packages. Asset reproduction is documented in
`RESEARCH.md` and uses `tools/extract_minimap_assets.py` with the installed
Enhanced `GfxHUD.upk`. Installed game files are never modified by extraction.

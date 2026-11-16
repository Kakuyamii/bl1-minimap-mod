# Version 0.2.9: correct the viewport visibility regression

The user's live 0.2.8 screenshot shows a visible vanilla HUD while minimap_status
reports "vanilla UI hides HUD movies". They report the minimap appears only in
Escape. This disproves treating AreHudMoviesVisible as the actual player's
rendered HUD visibility at our PostRender hook. The underlying cause of that
query's divergent result (UI-stack interpretation, timing or another mod) is
not established. Do not invert it or claim a confirmed engine bug.

Remove that query from hidden_reason entirely. Retain bShowHUD, bHideCompassOnHUD
and native per-player ready/awaiting flags from the saved Ghidra analysis.
Restore the previously working status-menu/Pauser gates so Escape cannot expose
the overlay when the underlying HUD stays alive. This is an explicit overlay
policy, not a claim that every pause makes vanilla HUD invisible.
Tests model gameplay, status menu, pause, return to gameplay, native HUD hiding
and cinematic mode without HUD suppression. No game assets or binaries changed.
Live verification of 0.2.9 is still needed.

# Version 0.2.8: original GOTY HUD visibility

Target: original GOTY x86 unpacked Borderlands.exe, SHA256
cda6661a1f66c52356b70f8505b4a3ca668e1155071374e62dac890857357ff8.
REA opened the original binary with the Ghidra provider. Its full startup analysis
timed out at 330 seconds; focused Ghidra 12.1.4 headless decompilation succeeded.
Evidence is under analysis/minimap/native-hud-visibility and
native-hud-visibility-apply; package metadata is hud-visibility-metadata.json.

Original WillowGame.u UpdateScaleformHUDVisibility selects HideHUD/DisplayHUD
from myHUD.bShowHUD. ToggleHUD calls this update. ClientSetCinematicMode changes
HUD only when bAffectsHUD is set, so bCinematicMode alone is not a hide condition.
WillowHUD.CloseHUDMovie calls HideForPlayer for its player's index.
AreHudMoviesVisible is the original viewport's UI-stack policy; call it directly
to retain its ScreenMovies/ProjectedMovies and Coliseum-overlay exceptions.

Native registration: ShowForPlayer wrapper 0x01582f40 dispatches vtable +0x238,
HideForPlayer 0x01582fa0 dispatches +0x23c. HUD vtable 0x01cf5658 resolves these to
0x01440fb0 / 0x01441040. Hide clears per-player bytes at +0x154 and +0x156;
Show sets the latter before dispatching the animation. Package declarations
bReady and bAwaitingReady are two-entry byte arrays, matching these adjacent
state fields and their ready/awaiting behavior. This field correspondence is
inferred from layout and behavior, not a runtime memory capture.
0x01450cd0 selects aspect-specific root animation labels such as 16_9_off;
a guessed p1._visible flag would not represent this native state.

visibility.py reads the primary player's ready/awaiting flags, bShowHUD,
bHideCompassOnHUD and AreHudMoviesVisible. It keeps no extra UObject references.
The compass suppression property is present in the original package; applying
that specific suppression to the new minimap is our compatibility choice.
The old blanket Pauser/status-menu checks are replaced by the native UI policy.
Tests cover native hide/show/start flags, UI suppression, recovery, and cinematic/
pause flags that do not themselves suppress vanilla HUD. Live transitions remain
unverified. No binary or original package is patched.

# Version 0.2.7: pawn health API and enabled-state persistence

The live 0.2.6 error identifies WillowAIPawn.Health as absent. Original Engine.u
exports Pawn.GetHealth, IsDead and bIsDead. The threat feed now calls GetHealth;
the regression fixture deliberately has no Health field. Enemy-feed exceptions
are caught independently, clear stale dots best-effort, and back off five seconds
while ordinary map rendering continues. Errors remain visible in minimap_status.

The SDK mods_base Mod.auto_enable controls both saving the enabled flag and
restoring it on startup. Our explicit false setting prevented both. Set it true
in metadata and build_mod. The existing JSON contained options but no enabled key;
the update adds enabled=true while preserving options, as requested. Future user
disable operations are saved by the SDK too; no custom persistence handler needed.

# Version 0.2.6: lifecycle, rotation, threats, zoom and layering

The user confirmed 0.2.5 works visually. Their exit failure names the rooted
WillowGFxHelperMap.MapObjectData.Landmark reference as retaining arid_p.TheWorld.
PreClientTravel alone does not cover session shutdown. Original package metadata
confirms WillowPlayerController.ReturnToTitleScreen, Destroyed, and
WillowGameViewportClient.GameSessionEnded. PRE hooks clear helper references and
roots and close the movie; a weak world guard prevents recreation during teardown.
Repeated cleanup preserves that guard. No additional world roots are introduced.

Enhanced Minimap.SetMinimapShouldRotate(false) calls CancelOutIconRotation, resetting
arrow angles. The adapter previously invoked it after UpdateLandmark every frame.
The bridge now sets rotation mode only when changed, and Python applies SetView
before updating markers. Zoom uses the same native Flash scale API (100–1000%).

Original Engine.u declares WorldInfo.PawnList, Pawn.NextPawn and Pawn.IsEnemy.
The new threat feed traverses that live list, filters dead/hidden/deleting/friendly
pawns and projects coordinates with the same Transform and CoordScale. It refreshes
at 10 Hz, bounded to 128 nearest enemies. Enhanced's exact awareness cache is not
recreated. Its original UpdateThreats positioning/hiding code is retained; the
bridge preallocates uniquely named visible clips to avoid its one-clip-per-call
allocation behavior. Threat clips reset when the map frame changes.

GFxUI.u declares bKeepTopMost. The original HUD receives this flag while minimap
is active; the minimap explicitly clears it. The prior HUD value is restored on
hide/disable/travel and when HUD instances change. Runtime dialogue layering still
needs validation, as offline tests establish restoration but not renderer ordering.

Regression tests cover nonempty player markers, view-before-marker ordering, zoom,
hostility filtering, root/reference cleanup, repeated teardown, recreation blocking,
and reversible HUD priority. All new runtime behavior remains to be retested.

# Version 0.2.5: original map marker field name

The 0.2.4 retest reaches _update_markers after movie startup and map preparation,
then raises AttributeError for AS_IconFrame. Original package metadata at
analysis/minimap/packages/original-WillowGFxHelperMap.json declares
MapObjectData.AS_IconClipFrame, AS_IconClipPath and AS_IconPath. Enhanced uses the
same names; AS_IconFrame was a typo in our adapter. All other marker fields read
by the adapter are present in the original metadata. The render regression test
now uses a nonempty marker list with these exact fields, covering both icon
creation and position updates. No fallback silently drops unsupported markers.

# Version 0.2.4: missing mandatory GFX exporter tag

The 2026-10-27 19:59 UTC 0.2.3 log confirms a full byte-for-byte verified upload,
header 47465809c4290300, followed by Start returning false. Upload corruption is
no longer the explanation for this rejection.

Focused Ghidra analysis follows 0x016e46c0 -> 0x016e2c00 -> 0x016e27a0 in the
same unpacked original GOTY executable. For GFX/CFX, the header reader requires
first tag 1000 (ExporterInfo) and exporter version masked with 0xff00 equal to
0x0200. Failure returns zero. The literal strings at 0x01d811b0 and 0x01d811f8
report missing ExporterInfo and expected version 2.x respectively.

The extracted movie instead began with tag 32. Both original and Enhanced HUD
movies begin with identical 15-byte tag data:
`0dfa1402020000000d000003485544`.
The extractor now preserves that source tag first. Binary comparison against the
previous sdkmod proves only the leading 15-byte tag and declared file length
changed; all retained artwork and scripts remain byte-identical. A packaged-asset
regression test checks tag order, exporter version and declared size. Evidence is
in analysis/minimap/native-gfx-parser/016e27a0.c. This corrects a confirmed format
violation; successful in-game rendering still requires a retest.

# Version 0.2.3: array growth clears uploaded movie bytes

The user's 0.2.2 retest rejects Transient.GFxMovieInfo as well, ruling out changing
the resource outer as a sufficient fix. Its diagnostic header is eight zero bytes.
That header used a WrappedArray slice, so the slice alone is not conclusive about
the source buffer. Inspection of both SDK implementations identifies the upload bug:

- [Python array_py_extend](https://github.com/bl-sdk/pyunrealsdk/blob/master/src/pyunrealsdk/unreal_bindings/wrapped_array_methods.cpp)
  calls array_set at the current end, then self.resize(++idx).
- [WrappedArray::resize](https://github.com/bl-sdk/unrealsdk/blob/master/src/unrealsdk/unreal/wrappers/wrapped_array.cpp)
  zero-initializes all new entries after growth. This clears the byte just written.

The bridge allocates zero entries first, then writes by index within the allocated
size. It reads back all bytes by direct indexing (without SDK slices) and requires
exact equality before constructing or starting the movie. Corrupt uploads now fail
with the first mismatching offset rather than reaching Scaleform. The offline array
fixture reproduces zeroing on growth; another test verifies corrupt writes block
movie construction and release the resource root. In-game rendering remains unverified.

# Version 0.2.2: movie resource loading

The installed 0.2.1 diagnostic log from 2026-10-27 14:28 UTC confirms successful
helper Init/UpdateObjects, movie-info creation, RawData upload and concrete movie
construction. Start(False) returns false; the map is never rendered.

Focused Ghidra analysis of the same original GOTY unpacked executable:
- 0x00539560 (GFxMovie vtable 0x01a5f600 + 0x11c) builds MovieInfo's object path.
- 0x00539320 and 0x0052e0f0 load the movie from that path.
- 0x0052de10 prefixes `/ package/` and replaces dots with slashes.
- 0x0052dc00, the installed file opener, reverses the URL using 0x00524670,
  resolves GFxMovieInfo with 0x005e21b0, and exposes its RawData through a memory
  file (0x00518c40). Therefore transient byte-backed assets are supported by
  the loader, provided resource lookup and Flash parsing succeed.

The prior asset was a child of a player controller, creating a level/subobject
path. The bridge now uses the existing Core.Package Transient as its asset outer,
producing a simple package asset path. It verifies SDK lookup and byte count,
and records path/header evidence before Start. Actor-path incompatibility is the
working hypothesis, not a proven runtime root cause. A successful Start and visible
rendering still require in-game verification; Flash compatibility remains another
possible cause if the new resource path is also rejected.

Generated decompilation: analysis/minimap/native-gfx-loader/,
native-gfx-resource/ and native-gfx-open/. Original game files remain untouched.

# Version 0.2.1: startup crash diagnosis

Three nonempty engine minidumps from 2026-10-27 (11:14:07, 11:14:56, 11:16:16)
agree: exception 0xc0000005 at 0x005c4f24, read address0x4, EAX=0.
The saved ESP points directly to return address0x005dbe29. Disassembly shows that
return follows the error-reporting call in UObject allocation's abstract-class
branch (routine0x005dbbd0). Ghidra recovers the guard testing ClassFlags bit0x1;
the branch resolves the localization key `Core.Abstract`. Its reporting function
dereferences a null argument, producing the observed secondary fault. The rest
of the stack was scanned for module pointers, not asserted as a fully unwound trace.

Serialized original-game class flags confirm GFxUI.GFxMovie=0x08000093 and
WillowGame.WillowGFxMovie=0x08000093 (both abstract). GFxMovieInfo=0x08001092
is concrete. LevelTransitionGFxMovie=0x12 is concrete and contains zero function
overrides; it inherits the same movie implementation without credits/menu startup
handlers. The bridge now constructs that concrete subclass. It does not modify
engine class flags or overwrite any existing movie. Scale-mode configuration now
follows Start, and Close is not called on a movie whose Start did not succeed.

Evidence and parser: `analysis/minimap/crash/`, including per-dump SHA-256 identities,
exception/register records and focused Ghidra output. The normal game SDK log had
no Minimap exception entry; one of four engine dump files was empty. Durable
startup checkpoints and best-effort Python fault output now live under the installed
SDK's `crash dumps/Minimap` directory. This identifies and removes the observed
construction bug, but does not establish successful rendering after that fix.

# Version 0.2: vector artwork and settings

The user verified 0.1 in-game and identified that the terrain image was the wrong
presentation. The map menu / Enhanced minimap uses Flash vector artwork, not
LevelLandmarkAnchor.Texture. The current renderer removes the Canvas terrain path.

## Extracted visual and logic evidence

Enhanced `Packages/Interface/GfxHUD.upk` SHA-256:
`07db64f4853cd8d38f9de04cc46e0c95976156983da52002ca26f42bc66e6cb7`.
Embedded HUD GFX SHA-256:
`4c5e523b4d2662c29bcb5014f16129a290154768eeebe099139dbbb42157dec7`.

Using JPEXS 26.4.0, extraction retains the dependency closure of minimap sprite
187 (`minimap_frame`): characters 81–187, AS2 class sprite 1037, original export
names and both original DoInitAction payloads. Timeline 178 contains the named
base-game map frames. There are no external bitmap imports in this closure.
The new standalone root exposes the original class to the SDK. Its artwork and
class bytecode are retained, not redrawn or recompiled from decompiled source.
`tools/flash/bridge.as` is the small newly compiled adapter. The original parent
HUD's four-degree shear is applied to the extracted frame.

`Minimap.as` supplies SetMapFrame, SetMapScale, SetMapCenter, UpdateLandmark,
AddLandmark, SetMinimapShouldRotate, edge objective/waypoint placement and north
marker movement. These functions live in the packaged `assets/minimap.gfx`.
The isolated asset still requires a live test in original GOTY's Scaleform engine.

## Native and profile evidence

Ghidra resolves Enhanced HUD UpdateMinimap to `0x1413e7970`: it updates map
objects, threats and Flash. ApplyFlash `0x1413b6230` centers at
`(-u*ClipSize.X, -v*ClipSize.Y)`, using scaled vector-map dimensions.
Enhanced InitMapFrameVars `0x141392590` and original `0x0141cca0` apply the same
aspect correction: fx=AnchorSize.X/mapWidth, fy=AnchorSize.Y/mapHeight;
CoordScale=(max(1,fx/fy),max(1,fy/fx)). The original helper supplies icon clip/frame
names and transformed marker positions. Native player Angle is yaw*360/65536.
Initial Scales[CurrentScaleIdx] is 400%; rotation is performed in Flash.

Enhanced's profile settings are ShowCompass (126, default1), ShowMinimap (127,
default1), MinimapShouldRotate (159, default0), all integer Off/On mappings.
Original has no matching profile constants; SDK options store their equivalents.
The original compass clip `p1.bearing._visible` is controlled reversibly, restoring
its captured value on toggle, disable and travel. Other HUD state is not forced on.

Local evidence: `analysis/minimap/settings/README.md`, `profile-settings.json`,
focused Ghidra exports beneath settings/, `native-icons/`, and
`analysis/minimap/visuals/` (scripts, tag inventory, source manifest and verification).
REA selected the Ghidra provider for this pass, but its whole-program request hit
the startup deadline; targeted Ghidra headless decompilation supplied the additional
native findings. Earlier completed REA records remain in rea-inline-evidence.json.

## Reproduction

`python3 tools/extract_minimap_assets.py <Enhanced/WillowGame/CookedPC/Packages/Interface/GfxHUD.upk>`
requires Java/Javac and `.tools/ffdec/ffdec.jar` (26.4.0). It checks the exact source
hashes, extracts into analysis/, builds through `tools/flash/ExtractMinimap.java`
and writes `src/Minimap/assets/minimap.gfx`. The asset is build-specific. The SDK
constructs transient GFxMovieInfo/GFxMovie objects from these bytes; native movie
loading is a remaining runtime validation point. No installed game file is patched.

Enemy cache integration and Enhanced-specific custom waypoint population are still
open. Full Enhanced HUD positioning, split-screen and DLC behavior are not claimed.

---

# Minimap reconstruction evidence — 0.1 investigation

## Scope and identities

Static investigation of the user's installed Steam editions. Original GOTY is
32-bit, Unreal package version 584/license 58; Enhanced is 64-bit, version
594/license 58. These identities apply to the inspected files, not every release.

SHA-256 of original installed executables:

- GOTY: `71b58c404a5124b984a1ca42ab906479b57b5ad7b02944840433f2fed09dc42a`
- Enhanced: `57c5dc7b2636097a8aa9bd63749be91062941926bc04935310972cda02a9ef56`

SteamStub obscured native code in the installed files. Private analysis copies
were unpacked with Steamless 3.1.0.5; installed files were left unchanged.
Unpacked hashes:

- GOTY: `cda6661a1f66c52356b70f8505b4a3ca668e1155071374e62dac890857357ff8`
- Enhanced: `856f46d08801668d7b265e4c6716bf4e7d6ab448b22f79ff9b4410043cec722f`

## Confirmed static findings

REA 6.8.0 with Ghidra 12.1.4 analyzed Enhanced. Focused Ghidra decompilation
also analyzed both editions without whole-program autoanalysis. Decompiled
types and names are inferred; no runtime behavior was observed.

1. Enhanced's `WillowGFxHelperMinimap` extends `WillowGFxHelperMap`. Package
   bytecode sets `bIsMinimap` and calls the inherited initializer.
2. Original GOTY already has the map helper, map anchors and terrain textures.
   Its initializer finds landmarks, objects and players. `InitMapFrame` is a
   separate Flash-dependent operation, which this mod does not invoke.
3. Original `UpdateObjects` at `0x01416240` recomputes its transform through
   `0x014140b0`; anchor transform construction is at `0x0146bd60`.
   The latter uses anchor location, rotation, scale and texture dimensions.
4. Original conversion at `0x01414000` transforms world position and maps the
   resulting local axes as `u = local_y + 0.5`, `v = 0.5 - local_x`, followed
   by `CoordScale`. This mod fixes CoordScale to (1,1) for Canvas texture UVs.
5. Enhanced minimap vtable `0x141ed10d0` identifies actual implementations:
   ApplyFlash `0x1413b6230`, FindWaypoint `0x1413c2350`, UpdateThreats
   `0x1413eab00`. Registration wrappers dispatch virtually; decompiling only
   those wrappers does not reveal the implementation.
6. Enhanced UpdateThreats transforms positions from `0x141487bd0`. That
   collector reads a native cache, filters flagged entries and scans at most
   18 slots. An equivalent original-GOTY SDK-accessible position cache has
   **not** been identified. Enemy markers are therefore not implemented.

REA evidence IDs (complete returned records retained locally):

- ApplyFlash: `ev_9521f421695ebd8ef479642f9173a00bb6d248e67ae968980bb7a9bcb1dd9a46`
- UpdateThreats: `ev_0b06d21fefbfc298721777d8fc4df3940fcd4de948244b0608bfe2e387588947`
- FindWaypoint: `ev_92fa0bcf115d4f1c7df782cceeab1399cefdfe2cc3814e3a53d80b6a2257c4fb`
- Threat collector: `ev_d68c611e3c6f9a3392e01e8681a2a7120c99d526b9b1c74c5c17ae2fd8ceadca`

## Implementation choices and open questions

The SDK constructs a separate original-game helper and draws its terrain and
markers through Canvas. The full-map helper owned by the game is not modified.
The view is fixed to map axes; it is not necessarily compass north on every
level. Simple marker artwork and two-second enumeration are reconstruction
choices, not claims about Enhanced behavior. Full texture alignment, helper
lifetime and marker correctness require runtime validation. Native functions
can crash the process; Python exception handling cannot catch such a crash.

## Local reproduction material

Generated/private material is under `analysis/minimap/`, excluded from Git and
from the sdkmod. `packages/inspect_package.py` and `dump_properties.py` decode
the UE3 metadata; package hashes are in `packages/SHA256SUMS`.
`unpacked/reproduce.py` and its README record private-copy preparation.
`native-original/`, `native-transform/`, `native-minimap/` and `native-threat/`
contain focused decompilations. `rea-inline-evidence.json` contains complete
returned REA records. `sdk-api.md` records installed SDK source references.

`tools/FocusedDecompile.java` runs via `tools/ghidra-headless` with `-noanalysis`,
`-scriptPath "$PWD/tools"`, and `-postScript FocusedDecompile.java <output-dir>
<hex-address> ...`. Use a private unpacked copy with `-import`, a temporary
project directory/name, and `-deleteProject`. The official REA bridge provides
full autoanalysis; its first query can take many minutes for these executables.

SDK references: https://bl-sdk.github.io/developing/ and
https://github.com/bl-sdk/willow1-mod-manager . Local package inspection verified
the seven-argument original Canvas.DrawTile signature and archive root naming.

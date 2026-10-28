# Minimap

A Python SDK mod that backports the **Borderlands GOTY Enhanced minimap** to **original Borderlands GOTY**.

## Options

| Option | Default | Description |
| --- | --- | --- |
| Show compass | On | Show or hide the original compass independently of the minimap. Ported from enhanced |
| Show minimap | On | Show or hide the minimap. Ported from enhanced |
| Rotate minimap | Off | Rotate the map with the player. When off, the map stays north-up and the player arrow rotates. Ported from enhanced |
| Minimap zoom | 400% | Set zoom between 100% and 1000%. Higher values show a smaller area. Custom |

The default 400% zoom matches Enhanced's recovered initial map scale.

## Compatibility and limitations

- Split-screen is not supported.
- Enhanced's custom player-waypoint placement is not implemented.
- Enemy markers use original GOTY's hostile-pawn detection; they may differ from Enhanced's threat awareness.
- DLC maps and co-op need broader testing.
- The complete Enhanced HUD layout is not included.

## Troubleshooting and issue making

If the minimap does not appear, check that the mod and **Show minimap** are enabled, then run this in the SDK console:

```
minimap_status
```
Logs go to Borderlands/sdk_mods/crash dumps/Minimap/. Send those there on the issues board!

## AI disclosure

This mod was developed with substantial assistance from OpenAI Codex. 
AI assisted with writing and revising code, reverse-engineering analysis using REA and Ghidra, tests, documentation, and debugging.
I thoroughly tested the mod in-game and provided feedback that fixed the issues that arised.

AI assistance does not guarantee correctness or compatibility. The limitations and testing status above apply.
I made it with this out of a need for it for personal use, if you do not feel comfortable with use of AI it's entirely fine if you don't want to play the mod because of that.
I made it using a free trial and did not bother with credits at any point. 0 Money went into the pockets of s*m altman.

## Credits

- [Borderlands Python SDK](https://github.com/bl-sdk/willow1-mod-manager)
- [REA](https://github.com/morluto/rea) and [Ghidra](https://github.com/NationalSecurityAgency/ghidra) for reverse-engineering tools
- Borderlands GOTY Enhanced by Blind Squirrel for the original minimap artwork and behavior
- Gearbox for the original game

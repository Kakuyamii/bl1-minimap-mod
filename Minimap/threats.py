from math import isfinite


def serialize_threats(pc, projection, scale):
    player = pc.Pawn
    pawn = pc.WorldInfo.PawnList
    seen = set()
    enemies = []


    while pawn is not None and len(seen) < 4096:
        identity = pawn._path_name()
        if identity in seen:
            break
        seen.add(identity)
        following = pawn.NextPawn
        if (pawn != player and not pawn.bDeleteMe and not pawn.bHidden
                and pawn.GetHealth() > 0 and pawn.IsEnemy(player)):
            pos = pawn.Location
            u, v = projection.uv((pos.X, pos.Y, pos.Z))
            u, v = u * scale.X, v * scale.Y
            if isfinite(u) and isfinite(v):
                origin = player.Location
                distance = sum((a-b)**2 for a, b in zip(
                    (pos.X, pos.Y, pos.Z), (origin.X, origin.Y, origin.Z)))
                enemies.append((distance, u, v))
        pawn = following

    enemies.sort()
    return "|".join(f"{i},{u:.7f},{v:.7f}" for i, (_, u, v) in enumerate(enemies[:128]))

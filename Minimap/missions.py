import math

import unrealsdk


def mission_markers(pc, projection, scale):
    markers = {}
    for actor in unrealsdk.find_all('WillowGame.WillowInteractiveObject', exact=False):
        if actor is None or actor.WorldInfo != pc.WorldInfo or actor.bDeleteMe or not len(actor.MissionDirectives):
            continue
        if actor.GetRedeemableMissions(pc, [])[0] > 0:
            frame = 'turnin'
        elif actor.GetEligibleMissions(pc, [])[0] > 0:
            frame = 'newmission'
        else:
            continue
        location = actor.Location
        u, v = projection.uv((location.X, location.Y, location.Z))
        pos = (u * scale.X, v * scale.Y)
        if all(math.isfinite(value) for value in pos) and markers.get(pos) != 'turnin':
            markers[pos] = frame
    return [('maps.landmarks', frame, True, u, v, 0.0) for (u, v), frame in markers.items()]

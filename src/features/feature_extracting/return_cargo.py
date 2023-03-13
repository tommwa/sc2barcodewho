import sc2reader


def get_return_cargo_info(events):
    """
    returns 1 if return cargo was used, otherwise 0.
    """
    # IMPROVEMENT: see if it is used at home or just to send home scout that picked up minerals. and for all game to see if key is bound, 2 things to look at. could also see what is done when probe is holding a mineral (not great for other races, but does it matter?)
    # IMPROVEMENT: see if it is done after sending back workers to mineral fields or INSTEAD of sending back to mineral field.
    # IMPROVEMENT: see if it is done before sending into a gas guyser
    n = 0
    for event in events:
        if isinstance(event, sc2reader.events.game.CommandEvent):
            if event.ability_name == "ReturnCargo":
                return {"return cargo used": 1}
    return {"return cargo used": 0}

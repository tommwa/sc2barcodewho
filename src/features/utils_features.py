# utility functions related to the features.
import os
import json
from collections import defaultdict


def add_feature_name_suffix(features, suffix):
    renamed_dict = {}
    for key in features:
        new_key = key + str(suffix)
        renamed_dict[new_key] = features[key]
    return renamed_dict


def get_cut_events(player, game_part="all", cutting_time=30):
    """
    purpose is to get events before or after a given time. This can be used for example when making a feature for
    earlygame spamming patterns or excluding earlygame spamming.
    @param player: the player object from the sc2reader replay object
    @param game_part: option to get all/start/end of replay decided by cutting point in seconds
    @param cutting_time: decides where to cut the game_part if not 'all' (seconds)
    @return:
    """
    filtered_events = []
    if game_part == "all":
        return player.events
    elif game_part == "start":
        for event in player.events:
            if event.frame < 22.4 * cutting_time:  # 22.4 frames per second
                filtered_events.append(event)
            else:
                return filtered_events
    elif game_part == "end":
        reached_cutting_time = False
        for event in player.events:
            if reached_cutting_time:
                filtered_events.append(event)
            elif event.frame > 22.4 * cutting_time:
                filtered_events.append(event)
                reached_cutting_time = True
        return filtered_events


def add_name_to_toon_dict(program_path, toon, name):
    # load toon_dict from file
    dict_path = os.path.join(program_path, "database", "toon_handle_to_names.txt")
    with open(dict_path, "r") as infile:
        toon_dict = json.load(infile)
    toon_dict = defaultdict(list, toon_dict)
    # update the variable
    if name in toon_dict[toon]:
        return
    else:
        toon_dict[toon].append(name)
    # update the file
    with open(dict_path, "w") as outfile:
        json.dump(toon_dict, outfile)

import json
import os
import platform
import re
from pathlib import Path

import yaml
import numpy as np
import sc2reader


def toon_race_to_race(toon_race):
    """For example the toon_race might be "('2-S2-1-788178', 'Zerg')" and I want to return 'Zerg'"""
    if toon_race.endswith("'Zerg')"):
        return "Zerg"
    elif toon_race.endswith("'Protoss')"):
        return "Protoss"
    elif toon_race.endswith("'Terran')"):
        return "Terran"
    # Unfortunately race can be written in other languages.
    else:
        x = re.findall("(?<=', ').*(?='\\))", toon_race)
        if len(x) == 1:
            race = x[0]
            if race == "Терраны":
                return "Terran"
            elif race == "Протоссы":
                return "Protoss"
            elif race == "Зерги":
                return "Zerg"
            else:
                print(f"race toon in new language: {toon_race}")
                return race
        else:
            print(f"unknown race for race toon: {toon_race}")
            return "Unknown Race"


def toon_race_to_toon(toon_race):
    """For example the toon_race might be "('2-S2-1-788178', 'Zerg')" and I want to return '2-S2-1-788178'"""

    if toon_race.endswith("'Zerg')"):
        return toon_race[2:-10]
    elif toon_race.endswith("'Protoss')"):
        return toon_race[2:-13]
    elif toon_race.endswith("'Terran')"):
        return toon_race[2:-12]
    # Unfortunately race can be written in other languages.
    else:
        x = re.findall("(?<=\\(').*(?=', ')", toon_race)
        assert len(x) == 1
        return x[0]


def is_barcode(name):
    """
    A barcode is a name that consists only of capital i or lower case L since these letters are identical in BattleNet.
    """
    for c in name:
        if c in ["l", "I"]:
            continue
        else:
            return False
    return True


def get_toon_dict(data_path):
    dict_path = os.path.join(data_path, "toon_handle_to_names.txt")
    with open(dict_path, "r") as infile:
        toon_dict = json.load(infile)
    return toon_dict


def camera_distance(base_loc, loc2):
    """
    Measures the distance between two camera event location as tuples of (x, y) coordinates.

    Note that base_loc can have the value False if it is unknown. (was never selected in the earlygame).
    """
    if base_loc is False:
        return 0  # Will be detected as main_base, but I might just sort out these games since this is bad data.
    return np.sqrt(
        (base_loc[0] - loc2[0]) * (base_loc[0] - loc2[0]) + (base_loc[1] - loc2[1]) * (base_loc[1] - loc2[1])
    )


def load_config(program_path):
    filename = os.path.join(program_path, "config", "config.yaml")
    with open(filename, "r") as f:
        config = yaml.load(f, Loader=yaml.SafeLoader)
    return config


def set_config(program_path, config):
    filename = os.path.join(program_path, "config", "config.yaml")
    with open(filename, 'w') as f:
        yaml.safe_dump(config, f, sort_keys=False)


def get_replays_recursively(config=False, filter_update_time=False, folder_path=False):
    """This function is called either using config or a set folder path."""
    if not folder_path:
        folder_path = config["options"]["REPLAY_FOLDER_PATH"]
    list_of_replay_paths = []
    for root, subdirs, files in os.walk(folder_path):
        for file in files:
            if file.endswith(".SC2Replay"):
                list_of_replay_paths.append(os.path.join(root, file))

    # Display message if no replays are found.
    if len(list_of_replay_paths) == 0:
        print(
            f"No replays found in {folder_path}"
            f", This path can be updated manually in config/config.yaml or set with the GUI interface."
        )

    # Filepaths length 259 and longer struggle on Windows, need to rewrite them.
    # Unfortunately a lot of replay packs have very deep folders with very long names so this is a common occurrence.
    if platform.system() == "Windows":
        for i, path in enumerate(list_of_replay_paths):
            if len(path) > 259:
                list_of_replay_paths[i] = Path("\\\\?\\" + path)

    # Sort replays, start with oldest
    list_of_replay_paths.sort(key=lambda x: os.path.getmtime(x))
    latest_replay_time = os.path.getmtime(list_of_replay_paths[-1])

    # Remove all replays before or at the same time as filter_update_time since they have already been processed, if we
    # want this
    if config:
        if not config["options"]["LOAD_OLD_REPLAYS"]:
            if filter_update_time is not False:
                list_of_replay_paths = [p for p in list_of_replay_paths if (os.path.getmtime(p) > filter_update_time)]

    return list_of_replay_paths, latest_replay_time


def get_most_recent_replay_filename(config):
    folder_path = config["options"]["REPLAY_FOLDER_PATH"]
    list_of_replay_paths = get_replays_recursively(config=config)[0]
    list_of_replay_paths.sort(key=lambda x: os.path.getmtime(x))
    print(f"The most recent replay is {list_of_replay_paths[-1]}")
    return list_of_replay_paths[-1], os.path.getmtime(list_of_replay_paths[-1])


def replay_is_relevant(replay):
    """
    function used to filter out irrelevant replays.
    it is irrelevant if it:
        - is shorter than 3 minutes
        - was played from replay
        - does not include exactly 2 non AI players
    @param replay: sc2reader.resources.Replay
    @return: Bool
    """
    # check that it is longer than 3 min
    if replay.game_length.seconds < 180:
        return False
    # check that it was not played from replay
    for event in replay.events:
        if type(event) == sc2reader.events.game.HijackReplayGameEvent:
            return False
    # check that it includes exactly 2 non AI players
    if len(replay.players) != 2:
        return False
    for player in replay.players:
        if type(player) == sc2reader.objects.Computer:
            return False
    return True


def try_load_replay(replay_path):
    try:
        return sc2reader.load_replay(replay_path)
    except Exception:
        print(f"Unable to parse the replay with sc2reader. The given filepath was: {replay_path}")
        return False

# Holds main function for feature extraction.
from features.feature_extracting.return_cargo import get_return_cargo_info
from features.feature_extracting.camera_features import get_all_camera_features


def extract_features(player, early_events):
    # basic info features
    feature_dict = dict()
    feature_dict["toon"] = player.toon_handle
    feature_dict["race"] = player.play_race
    feature_dict["apm"] = player.avg_apm
    # prep for more advanced features
    events = player.events
    # add features from my more advanced functions
    feature_dict = {**feature_dict, **get_all_camera_features(player, events)}
    feature_dict = {**feature_dict, **get_return_cargo_info(events)}
    return feature_dict

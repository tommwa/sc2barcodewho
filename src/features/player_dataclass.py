from features.main_features import extract_features
from features.utils_features import get_cut_events
from features.feature_extracting.replay_n_grams import extract_n_grams


class PlayerData:
    """
    self.toon_race: str((toon, race))
    self.features: Dict of features, {feat_1_name: feat_1, ...}
    self.n_grams: List of dataframes, each dataframe has 3 columns, "replay_id", "toon_race", "sparse_n_gram" where
    sparse_n_gram is a scipy sparse csr array.
    self.replay_id: The replay hash.
    """

    def __init__(self, config, player=None, replay_id=None, complete_data=None):
        """
        Call either with player (sc2reader replay.player) and replay_id or with complete_data.

        @param complete_data: a dict with all the required data, this is typically used from the database where
        the replay sc2reader player object is not accessible.
        """
        assert ((player is not None) and (replay_id is not None)) or complete_data is not None
        if (player is not None) and (replay_id is not None):
            self.toon_race = str((player.toon_handle, player.play_race))
            early_events = get_cut_events(player, "start", cutting_time=30)
            self.features = extract_features(player, early_events)
            self.n_grams = extract_n_grams(config, early_events, replay_id, self.toon_race)
            self.replay_id = replay_id
        elif complete_data is not None:
            self.features = complete_data["features"]
            self.n_grams = complete_data["n_grams"]
            self.toon_race = complete_data["toon_race"]
            self.replay_id = complete_data["replay_id"]

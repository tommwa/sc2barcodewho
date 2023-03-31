from classifiers.nearest_neighbour import mean_feature_classify
from classifiers.n_gram_classifier import n_gram_classify
from utils.utils import toon_race_to_race, toon_race_to_toon, get_toon_dict, replay_is_relevant, try_load_replay
from features.player_dataclass import PlayerData
from features.evaluate_features import get_feature_relevances
from database.replay_hash import ReplayHash


def classify_replay_filepath(config, replay_filepath, dbms, to_visualize, data_path):
    toon_dict = get_toon_dict(data_path)
    replay_hash = ReplayHash.hash_replay(replay_filepath)
    replay = try_load_replay(replay_filepath)
    if replay is False:
        return False, False
    if not replay_is_relevant(replay):
        print(
            f"Replay is irrelevant, e.g. too short or consists of AI player, will not be classified. The given filepath was {replay_filepath}"
        )
        return False, False
    for player in replay.players:
        player_data = PlayerData(config, player=player, replay_id=replay_hash)
        if player_data.features["toon"] in config["options"]["TOONS_TO_IGNORE"]:
            print(f"Ignoring player {toon_dict[player_data.features['toon']]} because their toon ({player_data.features['toon']}) is set in config.yaml to be ignored.")
            continue
        classify_PlayerData(config, toon_dict, player_data, dbms, to_visualize)


def classify_PlayerData(config, toon_dict, player_data: PlayerData, dbms, to_visualize: bool,
                        pre_calculated_feature_relevances=False):
    """
    Performs the classification of one of the players in a replay using its player_data and a given dbms.

    Can also return extra information for other functions such as for visualization.

    @param to_visualize: Whether to create visualizations of the result.
    @param player_data: PlayerData instance.
    @param dbms: DBMS instance.
    @param pre_calculated_feature_relevances: optionally input these pre-calculated. It makes a lot of sense to
    calculate it here in natural use, but it will be repetitive and slow down the accuracy tests too much.
    @return: estimate, non_barcode_estimate.
    """

    # N-gram classify
    race = toon_race_to_race(player_data.toon_race)
    dbms_stats_race_filtered = dbms.get_race_filter_stats(race)
    n_players = len(dbms_stats_race_filtered["n_gram"][0])  # 0 because this is a list with the n n-grams
    if n_players < 10:
        print(
            "There are less than 10 players of this race in your database, perhaps you should consider loading more replays, see installation / config in README.md"
        )
    n_gram_means_race = dbms_stats_race_filtered["n_gram"]

    toon_estimate, non_barcode_toon_estimate = n_gram_classify(
        config, toon_dict, player_data, n_gram_means_race, to_visualize=to_visualize
    )

    # Feature classify
    if pre_calculated_feature_relevances is False:
        feature_relevances = get_feature_relevances(dbms.rep_feats.features)
    else:
        feature_relevances = pre_calculated_feature_relevances
    features_mean_race = dbms_stats_race_filtered["features"]["mean"]
    features_std_race = dbms_stats_race_filtered["features"]["std"]
    features_general_race = dbms_stats_race_filtered["features"]["general"]
    features_overall_stats = dbms.rep_feats.get_overall_stats()
    feat_toon_estimate, feat_non_barcode_toon_estimate = mean_feature_classify(config, toon_dict, player_data,
                                                                               features_mean_race, feature_relevances,
                                                                               to_visualize=to_visualize)


    if to_visualize:
        toon = toon_race_to_toon(player_data.toon_race)
        if toon in toon_dict:
            print(f"Name history of this account: {toon_dict[toon]}")
        else:
            print("This player was not previously in the database (maybe new account).")
            print(f"Name history of this account: None")
        print("---------------------------------------------------------------------------")

    return feat_toon_estimate, feat_non_barcode_toon_estimate

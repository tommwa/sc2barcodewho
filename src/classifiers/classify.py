from classifiers.nearest_neighbour import find_nearest_neighbour
from classifiers.n_gram_classifier import n_gram_classify
from utils.utils import toon_race_to_race, toon_race_to_toon, get_toon_dict, replay_is_relevant, try_load_replay
from features.player_dataclass import PlayerData
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
        classify_PlayerData(config, toon_dict, player_data, dbms, to_visualize)


def classify_PlayerData(config, toon_dict, player_data: PlayerData, dbms, to_visualize: bool):
    """
    Performs the classification of one of the players in a replay using its player_data and a given dbms.

    Can also return extra information for other functions such as for visualization.

    @param to_visualize: Whether to create visualizations of the result.
    @param player_data: PlayerData instance.
    @param dbms: DBMS instance.
    @return: estimate, non_barcode_estimate.
    """

    # Get a dbms for race only.
    race = toon_race_to_race(player_data.toon_race)
    dbms_means_race_filtered = dbms.get_race_filter_means(race)
    n_gram_means_race = dbms_means_race_filtered["n_gram"]
    features_mean_race = dbms_means_race_filtered["features"]

    # a, b, toon_estimate, non_barcode_toon_estimate = find_nearest_neighbour(toon_dict, config, player_data, dbms, to_visualize)
    toon_estimate, non_barcode_toon_estimate = n_gram_classify(
        config, toon_dict, player_data, n_gram_means_race, to_visualize=to_visualize
    )

    if to_visualize:
        toon = toon_race_to_toon(player_data.toon_race)
        if toon in toon_dict:
            print(f"Name history of this account: {toon_dict[toon]}")
        else:
            print("This player was not previously in the database (maybe new account).")
            print(f"Name history of this account: None")
        print("---------------------------------------------------------------------------")

    return toon_estimate, non_barcode_toon_estimate

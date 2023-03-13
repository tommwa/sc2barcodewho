from classifiers.classify import classify_PlayerData


def test_classification_accuracy(
    config, toon_dict, dbms, n_sample_games, columns_to_remove, profile_mode, max_games_to_use
):
    """
    Tests the classification accuracy, note that this will be easier with less people in the database.

    Note that if the barcodes are classified as
    the actual barcodes of this player that is technically a correct behaviour but I have no way of knowing that.
    Therefore, in this function we ignore barcodes (they are not yielded in the dbms test generator and we only look at
    the top non-barcode estimated guess)

    @param profile_mode: Just for profiling: only tests 10 replays.
    @param n_sample_games: The number of samples we take from each player. If a player has fewer games than this they
    will be ignored, and if they have more we will only take this many test samples.
    """
    n_trials = 0
    n_correct = 0

    profile_i = 0
    for test_player_data, test_dbms in dbms.get_test_replay_db_pairs(n_sample_games, max_games_to_use):
        n_trials += 1
        test_dbms.rep_feats.drop_columns(columns_to_remove)

        toon_estimate, non_barcode_toon_estimate = classify_PlayerData(
            config, toon_dict, test_player_data, test_dbms, to_visualize=False
        )
        if non_barcode_toon_estimate == test_player_data.toon_race:
            n_correct += 1
        if profile_mode:
            profile_i += 1
        if profile_i >= 3:
            break

    acc = n_correct / n_trials
    return acc, n_trials

import pandas as pd
import numpy as np


def get_feature_relevances(replay_features):
    """
    Takes mean variance of each feature within each player divided by the overall variance for all players. Could be more
    statistically advanced, but I just want a rough estimate of the spread within a player divided by spread overall.
    - extract the variance and add it to the within_player_variances N-1 times, but max 4 times to avoid
        over-representation of common players like myself.
        This scaling of 1-4 is motivated by the fact that a variance taken from a big sample set more accurately
        represents an average variance, it would require assumptions of the distributions priors to do anything
        more advanced.
    - To avoid the overall variance to be heavily impacted by players with a large number of replays each player only
    sends features from 4 random games for the calculation of the total variance.
    Will return NaN value if total variance is 0, shows that the feature always has the same value (or at least with the randomized 4 games of each person).
    @param replay_features: dict with keys being (toon, race) and values being a pandas DataFrame with the features
    from each of their games.
    @return: {feature: within_player_variances.mean() / total_variance}.
    """
    within_player_variances = pd.DataFrame()
    max_four_of_each_df = pd.DataFrame()
    for toon_race in replay_features:
        # first find variance for this player
        df_player = replay_features[toon_race]
        n_replays = len(df_player.index)
        if n_replays == 1:
            continue
        df_player = df_player.select_dtypes(include=np.number)
        within_player_var = df_player.var()
        for i in range(min(n_replays - 1, 4)):
            within_player_variances = pd.concat(
                [within_player_variances, within_player_var.to_frame().T], ignore_index=True
            )

        # add first 4 games to df that will later calculate total_variance.
        df_player = df_player.sample(frac=1).reset_index(drop=True)  # shuffle
        df_player = df_player.iloc[:4]
        max_four_of_each_df = pd.concat([max_four_of_each_df, df_player], ignore_index=True)
    total_variance = max_four_of_each_df.var()
    return within_player_variances.mean() / total_variance

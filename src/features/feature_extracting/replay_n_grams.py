import pandas as pd
from scipy import sparse
import numpy as np
import sc2reader

from utils.utils import camera_distance


def extract_n_grams(config, early_events, replay_id, toon_race):
    # TODO: test this function when its done with an empty early_events list, should work. (just debug and load a new replay)
    n_grams = []
    # hyperparams
    # Transform events to ids: a list of a unique id (int) for each type of event.
    ids, base = events_to_ids(config, early_events)
    for n in range(1, config['hyperparams']['HIGHEST_N'] + 1):  # n as in n_gram.
        # Get the n_gram_vector from the current replay
        n_gram_vector = n_gram(ids, n, base)
        # Update sparse_n_gram
        df_addition = pd.DataFrame()
        df_addition["replay_id"] = [replay_id]
        df_addition["toon_race"] = [toon_race]
        df_addition["sparse_n_gram"] = [n_gram_vector]
        n_grams.append(df_addition)
    return n_grams


def n_gram(int_list, N, base):
    """
    Transforms a list of integers into the n_grams, but represents each n_gram as a single unique integer.
    Base is then the number of possible unique integers in the input list.
    """

    def array_to_vector_idx(v, base):
        """
        Transforms a number from other base to regular base 10.
        @param v: vector, for example [3, 5, 7]
        @param base: numerical base used in transformation, for example 20
        @return: in this example, returns 3*20^0 + 5*20^1 + 7*20^2.
        """
        multiplier = [base**i for i in range(len(v))]
        return np.dot(v, multiplier)

    s = sparse.dok_array((1, base**N), dtype=np.float32)
    for i in range(len(int_list) - N + 1):
        s[0, array_to_vector_idx(int_list[i : i + N], base)] += 1
    s = s.tocsr()
    return s


def events_to_ids(config, events):
    """

    Numerical order of events and how many different types of each:
    Selection - 4 different ones: base, worker, many workers, other
    CommandManagerStateEvent (repeated Command) - 1
    CommandEvent - 1
    ControlGroupEvent - 5: set, get, remove, steal set, steal add (steal set / steal add might be in reversed order)
    CameraEvent_N - 3: unique cam, repeated cam, main base cam
    other - 1
    """
    # Prep.
    # Help with mapping from event to int
    break_N = 1
    SelectionEvent_N = 4
    CommandManagerStateEvent_N = 1
    CommandEvent_N = 1
    ControlGroupEvent_N = 5
    CameraEvent_N = 4
    break_start = 0  # This has to be 0 for the trim_zeros to work at the end.
    SelectionEvent_start = break_start + break_N
    CommandManagerStateEvent_start = SelectionEvent_start + SelectionEvent_N
    CommandEvent_start = CommandManagerStateEvent_start + CommandManagerStateEvent_N
    ControlGroupEvent_start = CommandEvent_start + CommandEvent_N
    CameraEvent_start = ControlGroupEvent_start + ControlGroupEvent_N
    others_start = CameraEvent_start + CameraEvent_N
    base = others_start + 1

    # Save all camera data since I need all of it before I can start classifying.
    base_location = False
    locations = []

    ids = np.zeros(len(events), dtype=int)
    break_idxs = []
    for i, event in enumerate(events):
        if event.frame - events[max(i - 1, 0)].frame >= config['hyperparams']['BREAKTIME']:
            break_idxs.append(i)


        if _is_startup_event(event):
            ids[i] = -1
            continue

        elif isinstance(event, sc2reader.events.game.SelectionEvent):
            # 0 = base, 1 = single worker, 2 = multiple workers, 3 = other
            ids[i] = SelectionEvent_start
            selection = event.objects
            if len(selection) == 1:
                if selection[0].is_worker:
                    ids[i] = SelectionEvent_start + 1
                elif selection[0].is_building:
                    if selection[0].minerals > 200:
                        ids[i] = SelectionEvent_start
                        if not base_location:
                            base_location = selection[0].location
                else:
                    ids[i] = SelectionEvent_start + 3
            else:
                only_workers = True
                for obj in selection:
                    if not obj.is_worker:
                        ids[i] = SelectionEvent_start + 3
                        only_workers = False
                        break
                if only_workers:
                    ids[i] = SelectionEvent_start + 2
            continue

        elif isinstance(event, sc2reader.events.game.CommandManagerStateEvent):
            ids[i] = CommandManagerStateEvent_start
            continue

        elif isinstance(event, sc2reader.events.game.CommandEvent):
            ids[i] = CommandEvent_start
            continue

        elif isinstance(event, sc2reader.events.game.ControlGroupEvent):
            # update_type: 0=set, 1=add, 2=get, 3=remove (when stolen to another),
            # 4/5 are create-steal/add-steal (or the other way around i don't remember atm).
            ids[i] = ControlGroupEvent_start + event.update_type
            continue

        elif isinstance(event, sc2reader.events.game.CameraEvent):
            # IMPROVEMENT: write this function, I want 0 = unique, 1 = repeated, 2 = main base repeated,
            # 3 = main base unique
            ids[i] = -10  # will be changed later
            locations.append(event.location)
            continue

        else:
            ids[i] = others_start
            continue

    #   Swap all camera events from -10 to their proper value now that I have all of them.
    # First figure out which locations are repeated, make a set
    repeated_locations_set = set()
    seen_once = set()
    for loc in locations:
        if loc in seen_once:
            repeated_locations_set.add(loc)
        else:
            seen_once.add(loc)
    # Use this data along with camera distance to main base_location to classify the camera events
    main_base_radius = 10
    updated_camera_ids = []
    for loc in locations:
        dist = camera_distance(base_location, loc)
        if loc in repeated_locations_set:
            if dist < main_base_radius:
                updated_camera_ids.append(CameraEvent_start + 2)
            else:
                updated_camera_ids.append(CameraEvent_start + 1)
        else:
            if dist < main_base_radius:
                updated_camera_ids.append(CameraEvent_start + 3)
            else:
                updated_camera_ids.append(CameraEvent_start + 0)
    # Swap out all -10 values to updated_camera_ids
    ids[ids == -10] = updated_camera_ids

    # SPEEDUP: instead of transforming back and forth to list it might be neater to find a way to insert into numpy array...
    # insert break actions at given indexes.
    ids = list(ids)
    for i in reversed(break_idxs):  # reverse order so insertions do not affect the indexes afterwards
        ids.insert(i, break_start)

    ids = np.array(ids, dtype=int)
    # remove all starting events = -1
    ids = ids[ids != -1]

    # finally remove all starting zeros that were put as a "break" before
    ids = np.trim_zeros(ids, "f")
    return ids, base


def _is_startup_event(event):
    if isinstance(event, sc2reader.events.message.ChatEvent):
        return True
    if isinstance(event, sc2reader.events.message.ProgressEvent):
        return True
    if isinstance(event, sc2reader.events.game.UserOptionsEvent):
        return True
    return False

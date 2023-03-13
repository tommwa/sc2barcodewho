from collections import defaultdict
import sc2reader
from features.utils_features import get_cut_events, add_feature_name_suffix


def get_camera_event_chains(events, min_chain_length=0):
    """
    Helper function to get the chains of camera events which is broken by any other type of event eg selection event
    @return: list, [chain1, chain2, ...] where chain = [cam1, cam2, ...] where cam = [camera_event, camera_location_id]
    The camera event coordinates are given by camera_event.x etc
    The camera location id is meant to identify if the location has been visited before, numbered by 0,1,2,3,4,...
    where 0 means it is a unique location and 1 is the most visited and 2 is the second most visited etc.
    """
    camera_counter = defaultdict(int)
    chains = []
    cameras = []
    for event in events:
        if type(event) == sc2reader.events.game.CameraEvent:
            camera_counter[str(event.x) + ", " + str(event.y)] += 1
            cameras.append([event])
        else:
            if len(cameras) > min_chain_length:
                chains.append(cameras)
            if len(cameras) > 0:
                cameras = []
    # figure out the ranking for each camera location, 0 visited only once, 1 most visited, 2 second most visited etc
    sorted_camera_counter = sorted(list(camera_counter.items()), key=lambda x: -x[1])
    cam_to_ranking = {}
    for i in range(len(sorted_camera_counter)):
        cam = sorted_camera_counter[i][0]
        if sorted_camera_counter[i][1] == 1:
            cam_to_ranking[cam] = 0
        else:
            cam_to_ranking[cam] = i + 1
    # add this ranking into the chain
    for chain in chains:
        for lst in chain:
            cam = str(lst[0].x) + ", " + str(lst[0].y)
            lst.append(cam_to_ranking[cam])
    return chains


def get_basic_camera_features(camera_chains):
    """
    Simply getting some simple camera features:
        - average distance of a side scroll, i find this by checking that x or y is 0 and it is an unrepeated camera
        location since a centered base camera will be 0 in x/y direction on some maps,
        this distance is highly correlated with speed so i ignore speed
        - fraction of unrepeated side scrolls compared to all movements
    @param camera_chains: list, [chain1, chain2, ...] where chain = [cam1, cam2, ...] where cam = [camera_event, camera_location_id]
        The camera event coordinates are given by camera_event.x etc
        The camera location id is meant to identify if the location has been visited before, numbered by 0,1,2,3,4,...
        where 0 means it is a unique location and 1 is the most visited and 2 is the second most visited etc.
    @return: dict with all the features per replay-player.
    """
    return_dict = dict()
    # count total number of camera moves, total and chains
    n_camera_moves = 0
    n_chains = 0
    n_equal_frames = 0
    previous_frame = -1
    for chain in camera_chains:
        n_chains += 1
        n_camera_moves += len(chain)
        for cam in chain:
            frame = cam[0].frame
            if frame == previous_frame:
                n_equal_frames += 1
            else:
                previous_frame = frame

    n_side_scrolls = 0
    distances_side_scrolls = []
    prev_x = "unknown"
    prev_y = "unknown"
    for chain in camera_chains:
        for i in range(len(chain)):
            cam = chain[i][0]
            camera_location_id = chain[i][1]
            x = cam.x
            y = cam.y
            if camera_location_id != 0:  # it is a repeated camera, eg base
                prev_x = "unknown"
                prev_y = "unknown"
                continue
            elif i == 0:
                prev_x = x
                prev_y = y
                continue
            elif prev_x != "unknown" and prev_y != "unknown":
                distance = ((x - prev_x) ** 2 + (y - prev_y) ** 2) ** 0.5
                distances_side_scrolls.append(distance)
                if x == prev_x or y == prev_y:
                    n_side_scrolls += 1
                prev_x = x
                prev_y = y
            else:  # not repeated, not the first in chain and they are set to unknown
                prev_x = x
                prev_y = y
    # final fixing of return variables
    if len(distances_side_scrolls) == 0:
        return_dict["distances_side_scrolls_mean"] = 0
    else:
        return_dict["distances_side_scrolls_mean"] = sum(distances_side_scrolls) / len(distances_side_scrolls)
    if n_camera_moves == 0:
        return_dict["percentage_side_scrolls"] = 0
        return_dict["average_chain_length"] = 0
        return_dict["percentage_equal_frame_cams"] = 0
    else:
        return_dict["percentage_side_scrolls"] = n_side_scrolls / n_camera_moves
        return_dict["average_chain_length"] = n_camera_moves / n_chains
        return_dict["percentage_equal_frame_cams"] = n_equal_frames / n_camera_moves
    return return_dict


def get_recurrent_camera_features(camera_chains):
    """
    This is just a simple function for now, ideally I want to connect the camera locations to base locations on a map basis automatically so I know which base is being selected.
    """
    return_dict = dict()
    # reformat the data a bit for this purpose
    location_id_and_frame_list = []
    for chain in camera_chains:
        for cam in chain:
            location_id = cam[1]
            frame = cam[0].frame
            location_id_and_frame_list.append([location_id, frame])
    # get features
    non_zero_jumps = 0
    previous_zero = False
    for e in location_id_and_frame_list:
        loc_id = e[0]
        if not previous_zero:
            if loc_id != 0:
                non_zero_jumps += 1
        if loc_id == 0:
            previous_zero = True
        else:
            previous_zero = False
    return_dict["non_zero_jumps"] = non_zero_jumps
    return return_dict


def get_all_camera_features(player, events):
    camera_chains = get_camera_event_chains(events)
    early_camera_chains = get_camera_event_chains(get_cut_events(player, "start", 30))
    return {
        **get_basic_camera_features(camera_chains),
        **get_recurrent_camera_features(camera_chains),
        **add_feature_name_suffix(get_basic_camera_features(early_camera_chains), "_earlygame"),
        **add_feature_name_suffix(get_recurrent_camera_features(early_camera_chains), "_earlygame"),
    }  # merge the dicts

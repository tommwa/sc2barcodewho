import ast
import hashlib
import os


class ReplayHash:
    """
    Keeps track of hashes replays. A replay is hashed by md5 hashing the byte reading of the entire replay,
    so that it does not have to be loaded by sc2reader.

    Note that replays that are considered irrelevant (eg too short or AI players) will be in the replay_hahes list
    to prevent repeated parsing; in other words not all replays in the replay hashes list have data in the database.

    Could probably be made faster by only hashing part(s) of the replay file,
    although currently it only takes a few seconds for a thousand replays.
    self.hashes is a set with the replay hashes (strings)

    self.hashes: set of the replay hashes.
    """

    def __init__(self, data_path):
        self.data_path = data_path
        self.file_path = os.path.join(data_path, "replay_hashes.txt")
        self.hashes = set()

    def save_to_file(self):
        with open(self.file_path, "w") as outfile:
            outfile.write(str(self.hashes))

    def load_from_file(self):
        with open(self.file_path, "r") as infile:
            self.hashes = ast.literal_eval(infile.read())

    def reset_file(self):
        with open(self.file_path, "w") as outfile:
            outfile.write(str(set()))

    def in_db(self, replay_hash):
        return replay_hash in self.hashes

    def add_hash(self, replay_hash):
        self.hashes.add(replay_hash)

    def remove_replay(self, replay_hash):
        assert replay_hash in self.hashes
        self.hashes.remove(replay_hash)

    @staticmethod
    def hash_replay(replay_path):
        with open(replay_path, "rb") as infile:
            data = infile.read()
        return hashlib.md5(data).hexdigest()

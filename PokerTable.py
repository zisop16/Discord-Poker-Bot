from PokerGame import *
from DataManager import *
from dotenv import load_dotenv, find_dotenv
import os

class PokerTable:
    running = []
    def __init__(self, options, data_manager):
        game = PokerGame()
        game.sb = options["sb"]
        game.bb = options["bb"]
        game.ante = options["ante"]
        game.seats = options["seats"]
        self.game = game
        self.time_bank = options["time_bank"]
        self.min_buy = options["min_buy"]
        self.max_buy = options["max_buy"]
        self.match_stack = options["match_stack"]
        self.players = [None for seat in range(game.seats)]
        self.data_manager = data_manager

    def buyin(self, userID, seat, stack):
        max_chips = self.max_buy * self.game.bb
        min_chips = self.min_buy * self.game.bb
        if self.match_stack:
            max_chips = max(max_chips, max(self.game.stacks))
        if stack < min_chips or stack > max_chips:
            return False
        player_chips = self.data_manager.get_chips(userID)
        if stack > player_chips:
            return False
        try: 
            self.game.buyin(seat, stack)
        except SeatOccupiedException:
            return False
        self.players[seat] = userID
        return True

    def sitin(self, userID):
        if not (userID in self.players):
            return False
        seat = self.players.index(userID)
        try: 
            self.game.sitin(seat)
        except (NoChipsException, SeatNotOccupiedException):
            return False
        return True

    def open(self):
        pass

    def close(self):
        pass


if __name__ == '__main__':
    command = "-paycheck"
    load_dotenv(find_dotenv())
    password = os.getenv("MONGO_PASS")
    manager = DataManager(password)
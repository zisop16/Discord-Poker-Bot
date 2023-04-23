from PokerGame import *
from DataManager import *
from dotenv import load_dotenv, find_dotenv
import os

def close(channelID):
    if channelID in PokerTable.running:
        table = PokerTable.running[channelID]
        if table.game.hand_running():
            return False
        table.close()
        del PokerTable.running[channelID]
        return table
    return False

class PokerTable:
    running = {}
    def __init__(self, name, channelID, runnerID, options, data_manager):
        game = PokerGame()
        game.sb = options["sb"]
        game.bb = options["bb"]
        game.ante = options["ante"]
        game.seats = options["seats"]
        self.name = name
        self.game = game
        self.time_bank = options["time_bank"]
        self.min_buy = options["min_buy"]
        self.max_buy = options["max_buy"]
        self.match_stack = options["match_stack"]
        self.players = [None for seat in range(game.seats)]
        self.data_manager = data_manager
        self.runnerID = runnerID
        PokerTable.running[channelID] = self

    def buyin(self, userID, seat, stack):
        if userID in self.players:
            return False
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
            self.data_manager.remove_chips(userID, stack)
        except (SeatOccupiedException, InvalidSeatException):
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
    
    def sitout(self, userID):
        if not (userID in self.players):
            return False
        seat = self.players.index(userID)
        try:
            self.game.sitout(seat)
        except (SeatNotOccupiedException, InvalidSitOutException):
            return False
        return True
    
    def cashout(self, userID):
        if not (userID in self.players):
            return False
        seat = self.players.index(userID)
        try:
            chips = self.game.cashout(seat)
            self.data_manager.add_chips(userID, chips)
            self.players[seat] = None
        except (SeatNotOccupiedException, InvalidSitOutException):
            return False
        return -1 if chips == 0 else chips
    
    def close(self):
        for playerID in self.players:
            if playerID == None:
                continue
            self.cashout(playerID)


if __name__ == '__main__':
    command = "-paycheck"
    load_dotenv(find_dotenv())
    password = os.getenv("MONGO_PASS")
    manager = DataManager(password)
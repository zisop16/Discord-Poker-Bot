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

def card_to_string(card):
    suit = card.suit
    rank = card.rank
    match(suit):
        case 1:
            suit = "<:poker_spade:1099565925872697384>"
        case 2:
            suit = "<:poker_heart:1099565940594704484>"
        case 3:
            suit = "<:poker_diamond:1099565951193718885>"
        case 4:
            suit = "<:poker_club:1099565962157637632>"
    match(rank):
        case 10:
            rank = "T"
        case 11:
            rank = "J"
        case 12:
            rank = "Q"
        case 13:
            rank = "K"
        case 14:
            rank = "A"
        case _:
            rank = str(rank)
    return f"{rank} {suit}"

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
    
    def acting_player(self):
        return self.players[self.game.action_permissions[0]]
    
    def state(self):
        """_summary_

        Returns:
            string: string containing game state information
        """
        game = self.game
        pot = game.pot
        text = ""
        if game.street != Streets.Preflop:
            text += "Board:\n"
            for card in game.board:
                text += f"{card_to_string(card)} "
            text += '\n'
        text += f"Pot: {pot} chips\nCurrent Bets:\n"
        for seat in game.active_seats:
            text += f"<@{self.players[seat]}>: {game.current_bets[seat]} chips\n"
        text += f"Action on: <@{self.acting_player()}>"
        return text

    def sitin(self, userID):
        if not (userID in self.players):
            return False
        seat = self.players.index(userID)
        try: 
            self.game.sitin(seat)
        except (NoChipsException, SeatNotOccupiedException, InvalidSitInException):
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
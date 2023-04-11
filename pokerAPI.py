from pokereval.card import Card
from pokereval.hand_evaluator import HandEvaluator
from more_itertools import chunked

class PokerGame:
    def __init__(self):
        self.game_type = "No-Limit Hold'em"
        self.hands = []
        self.board = []
        self.bb = 2
        self.sb = 1
        self.ante = 0
        self.pot = self.sb + self.bb + self.ante
        self.seats = 6
        # Stacks of each player
        self.stacks = [0 for i in range(self.seats)]
        # Chips placed into the pot from each player on current betting round
        self.current_bets = [0 for i in range(self.seats)]
        self.occupied_seats = set()
        self.active_seats = set()
        # Seat with the dealer button
        self.dealer = None
        self.previous_raise = self.bb
        # Current bet placed by the most recent player
        self.current_bet = self.bb
        # Seats which still have hands in play
        self.remaining_hands = set()
        # List of seats yet to act, in order, as tuples
        # Ex: [(1, True), (2, False), (4, False)]
        # Means that seat 1 is yet to act and MAY place a bet, and seats 2 and 4 are yet to act and may NOT place a bet
        self.action_sequence = []


    def buyin(self, seat, stack):
        if seat in self.occupied_seats:
            raise ValueError("Seat is occupied")
        self.stacks[seat] = stack
        self.occupied_seats.add(seat)

    def addon(self, seat, amount):
        if not (seat in self.occupied_seats):
            raise ValueError("Seat is not occupied")
        self.stacks[seat] += amount

    def sitin(self, seat):
        if not (seat in self.occupied_seats):
            raise ValueError("Seat is not occupied")
        if self.stacks[seat] == 0:
            raise ValueError("Seat has no chips")
        self.active_seats.add(seat)
        
    """
    Returns a list of Cards given a string sequence of names like 'AsTd5c'
    """
    def cards(self, names):
        return [self.card(name) for name in chunked(names, 2)]

    """
    Returns a Card given a string name like 'As'
    """
    def card(self, name):
        return Card(name[0], name[1])

    """
    Given list of holecards and board,
    Return list of the winning hands
    """
    def winner(self, holecards, board):
        scores = [HandEvaluator.evaluate_hand(hole, board) for hole in holecards]
        max_score = max(scores)
        winners = [hole for (hole, score) in zip(holecards, scores) if score == max_score]
        return winners
    
    def deal(self, num_hands=1):
        pass
    def fold(self):
        pass
    def bet(self, chips):
        acting_player = self.action_sequence[0][0]
        reopen_action = True
        if ((chips * 10) % 1) != 0:
            raise ValueError("Invalid Bet")
        raise_req = self.current_bet + self.previous_raise
        if chips < raise_req:
            raise ValueError("Invalid Bet")
        self.previous_raise = chips - self.current_bet
        player_previous_bet = self.current_bets[self.acting_player]
        additional_chips = chips - player_previous_bet
        self.current_bet = chips
        self.stacks[self.acting_player] -= additional_chips
        self.current_bets[self.acting_player] = chips
         
    def call(self):
        pass
    def check(self):
        pass

if __name__ == '__main__':
    game = PokerGame()

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
        self.stacks = [0 for i in range(6)]
        self.occupied_seats = set()
        self.active_seats = set()
        self.dealer = None
        self.seats = 6
        self.previous_raise = self.bb
        self.current_bet = self.bb

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
        if ((chips * 10) % 1) != 0:
            raise ValueError("Invalid Bet")
         
    def call(self):
        pass
    def check(self):
        pass

if __name__ == '__main__':
    game = PokerGame()

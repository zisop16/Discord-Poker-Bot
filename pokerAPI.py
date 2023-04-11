from pokereval.card import Card
from pokereval.hand_evaluator import HandEvaluator
from more_itertools import chunked
import random

class SeatOccupiedException(Exception):
    pass
class SeatNotOccupiedException(Exception):
    pass
class NoChipsException(Exception):
    pass
class NoPlayersException(Exception):
    pass
class InvalidBetException(Exception):
    pass
class ShortStackException(Exception):
    pass
class InvalidCheckException(Exception):
    pass

"""
Append value into array of numbers, maintaining small -> large order of array
"""
def inorder_append(num_arr, val):
    for ind, num in enumerate(num_arr):
        if num < val:
            continue
        num_arr.insert(ind, val)
        return
    num_arr.append(val)

"""
Returns a Card given a string name like 'As'
"""
def card(name):
    return Card(name[0], name[1])

"""
Returns a list of Cards given a string sequence of names like 'AsTd5c'
"""
def cards(names):
    return [card(name) for name in chunked(names, 2)]

"""
Given list of holecards and board,
Return list of the winning hands
"""
def winner(holecards, board):
    scores = [HandEvaluator.evaluate_hand(hole, board) for hole in holecards]
    max_score = max(scores)
    winners = [hole for (hole, score) in zip(holecards, scores) if score == max_score]
    return winners

class PokerGame:
    def __init__(self):
        self.game_type = "No-Limit Hold'em"
        self.hands = []
        self.board = []
        # List of addons like (2, 200) queued for next hand as (seat, chips)
        self.addons = []
        self.bb = 2
        self.sb = 1
        self.ante = 0
        self.pot = 0
        self.seats = 6
        # Stacks of each player
        self.stacks = [0 for i in range(self.seats)]
        # Chips placed into the pot from each player on current betting round
        self.current_bets = [0 for i in range(self.seats)]
        self.occupied_seats = []
        self.active_seats = []
        # Seat with the dealer button
        self.dealer = None
        self.previous_raise = 0
        # Current bet placed by the most recent player
        self.current_bet = 0
        # Seats which still have hands in play
        self.remaining_hands = []
        # List of seats yet to act, in order
        self.action_permissions = []

    def buyin(self, seat, stack):
        if seat in self.occupied_seats:
            raise SeatOccupiedException
        self.stacks[seat] = stack
        inorder_append(self.occupied_seats, seat)

    def addon(self, seat, amount):
        if not (seat in self.occupied_seats):
            raise SeatNotOccupiedException
        self.stacks[seat] += amount

    def sitin(self, seat):
        if not (seat in self.occupied_seats):
            raise SeatNotOccupiedException
        if self.stacks[seat] == 0:
            raise NoChipsException
        inorder_append(self.active_seats, seat)

    # Returns number of players sitting in
    def num_remaining(self):
        return len(self.remaining_hands)
    
    def deal(self):
        if self.num_remaining() < 2:
            raise NoPlayersException
        if self.dealer == None:
            self.dealer = random.sample(self.active_seats)
        if self.num_remaining() == 2:
            self.deal_headsup()
        else:
            self.deal_ring()

    def open_action(self, seat_ind, include_final=False):
        if not include_final:
            if seat_ind == 0:
                seats = self.remaining_hands[0:len(self.remaining_hands)-1]
            else:
                seats = self.remaining_hands[seat_ind:] + self.remaining_hands[:seat_ind-1]
        else:
            seats = self.remaining_hands[seat_ind:] + self.remaining_hands[:seat_ind]
        for seat in seats:
            if not (seat in self.action_permissions):
                self.action_permissions.push(seat)

    def deal_headsup(self):
        pass

    def deal_ring(self):
        # Index of dealer
        dealer_ind = self.active_seats.index(self.dealer)
        # Index of UTG is 3 forward
        utg_ind = (dealer_ind + 3) % self.num_remaining()
        self.open_action(utg_ind, include_final=True)

        sb_ind = (dealer_ind + 1) % self.num_remaining()
        sb_seat = self.active_seats[sb_ind]
        sb_stack = self.stacks[sb_seat]
        sb = min(self.sb, sb_stack)
        # If the BB cannot pay 1 chip more than the ante, they will be forced to sit out
        bb_ind = (dealer_ind + 2) % self.num_remaining()
        bb_seat = self.active_seats[bb_ind]
        bb_stack = self.stacks[bb_seat]
        after_ante = bb_stack - self.ante
        if after_ante < 1:
            raise ShortStackException
        bb = min(self.bb, bb_stack)
        self.stacks[bb_seat] -= self.ante
        self.stacks[bb_seat] -= bb
        self.stacks[sb_seat] -= sb
        self.current_bets[bb_seat] = bb
        self.current_bets[sb_seat] = sb
        self.pot += self.ante
        
    def fold(self):
        acting_player = self.action_permissions[0]
        # Remove the player's bets from the bet pool and add it to the pot
        self.pot += self.current_bets[acting_player]
        self.current_bets[acting_player] = 0
        # Remove the acting player's seat from the remaining hands list of active seats
        del self.remaining_hands[self.remaining_hands.index(acting_player)]
        self.action_forward()

    def bet_perms(self):
        acting_player = self.action_permissions[0]
        difference = self.current_bet - self.current_bets[acting_player]
        return difference >= self.previous_raise
    
    def may_act(self):
        acting_player = self.action_permissions[0]
        return self.stacks[acting_player] != 0

    def bet(self, chips):
        if not self.bet_perms():
            raise InvalidBetException
        # Seat number of currently acting player
        acting_player = self.action_permissions[0]
        # Bets must be made with integer quantities
        if (chips % 1) != 0:
            raise InvalidBetException
        player_previous_bet = self.current_bets[acting_player]
        additional_chips = chips - player_previous_bet
        raise_req = self.current_bet + self.previous_raise
        legal_raise = chips >= raise_req
        allin = additional_chips >= self.stacks[acting_player]
        # If the bet is less than allin, and the bet is not a legal raise, then
        # Is an invalid bet
        if not (legal_raise or allin):
            raise InvalidBetException
        if legal_raise:
            self.previous_raise = chips - self.current_bet
        self.current_bet = chips
        self.stacks[acting_player] -= additional_chips
        self.current_bets[acting_player] = chips
        self.action_forward(reopen=True)

    def action_forward(self, reopen=False):
        # Remove the most recent actor from the action sequence, and get their seat number
        previous_actor = self.action_permissions.pop(0)
        if reopen:
            actor_ind = self.remaining_hands.index(previous_actor)
            next_ind = (actor_ind + 1) % self.num_remaining()
            self.open_action(next_ind)
        while not self.may_act():
            self.action_permissions.pop(0)

    def call(self):
        pass
    
    def may_check(self):
        acting_player = self.action_permissions[0]
        return self.current_bets[acting_player] == self.current_bet
    
    def check(self):
        if not self.may_check():
            raise InvalidCheckException
        self.action_forward()

if __name__ == '__main__':
    game = PokerGame()

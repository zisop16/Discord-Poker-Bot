from pokereval.card import Card
from pokereval.hand_evaluator import HandEvaluator
from more_itertools import chunked
from enum import Enum
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
class InvalidShowdownException(Exception):
    pass
class InvalidCallException(Exception):
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

class Streets(Enum):
    Preflop = 0
    Flop = 1
    Turn = 2
    River = 3
    End = 4

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

def deck():
    suits = ['c', 'h', 's', 'd']
    ranks = ['2', '3', '4', '5', '6', '7', '8', '9', 'T', 'J', 'Q', 'K', 'A']
    names = ""
    for rank in ranks:
        for suit in suits:
            names += f"{rank}{suit}"
    shuffled = cards(names)
    random.shuffle(shuffled)
    return shuffled

class PokerGame:
    def __init__(self):
        self.game_type = "No-Limit Hold'em"
        # List of tuples of 2 cards like [AcAd, Ts9s, 5d2c] for all seats dealt in
        self.hands = []
        # List of cards on board, indices: flop = 0-2, turn = 3, river = 4
        self.board = []
        # List of addons like (2, 200) queued for next hand as (seat, chips)
        self.addons = []
        self.deck = None
        self.bb = 2
        self.sb = 1
        self.ante = 0
        self.pot = 0
        self.seats = 6
        self.street = Streets.End
        # Whether or not the next bet on the current street will have been the first bet
        # Ex: preflop the initial bet is the open raise
        self.initial_bet = True
        self.chips_invested = [0 for i in range(self.seats)]
        # Stacks of each player
        self.stacks = [0 for i in range(self.seats)]
        # Chips placed into the pot from each player on current betting round
        self.current_bets = [0 for i in range(self.seats)]
        # Seats which contain a player but are not necessarily bought in or sitting in
        self.occupied_seats = []
        # Seats which are bought in and not sitting out
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

    """
    Return list of winning seats given all holecards and board for live hands
    """
    def winners(self):
        if self.street != Streets.River:
            raise InvalidShowdownException()
        live_hands = [(seat, hand) for seat, hand in enumerate(self.hands) if seat in self.remaining_hands]
        scores = [HandEvaluator.evaluate_hand(hand, self.board) for seat, hand in live_hands]
        max_score = max(scores)
        winners = [seat for ((seat, hand), score) in zip(live_hands, scores) if score == max_score]
        return winners

    # Invest chips from stack of seat into the pot, as a bet or a call
    def invest(self, seat, chips):
        self.current_bets[seat] += chips
        self.chips_invested[seat] += chips
        self.stacks[seat] -= chips

    # Determine if seat is blind and should be able to place a bet
    # Even though they've already put out a blind bet
    def is_blind(self, seat):
        if self.street != Streets.Preflop:
            return False
        
        num_active = len(self.active_seats)
        dealer_ind = self.active_seats.index(self.dealer)
        heads_up = num_active == 2
        if heads_up:
            sb_ind = dealer_ind
            bb_ind = dealer_ind + 1
        else:
            sb_ind = dealer_ind + 1
            bb_ind = dealer_ind + 2

        sb_ind %= num_active
        bb_ind %= num_active
        sb = self.active_seats[sb_ind]
        bb = self.active_seats[bb_ind]
        is_sb = seat == sb
        if is_sb:
            return self.current_bets[sb] == self.sb
        is_bb = seat == bb
        if is_bb:
            return self.current_bets[bb] == self.bb
        
        return False

    def buyin(self, seat, stack):
        if seat in self.occupied_seats:
            raise SeatOccupiedException()
        self.stacks[seat] = stack
        inorder_append(self.occupied_seats, seat)

    def addon(self, seat, amount):
        if not (seat in self.occupied_seats):
            raise SeatNotOccupiedException()
        self.stacks[seat] += amount

    def sitin(self, seat):
        if not (seat in self.occupied_seats):
            raise SeatNotOccupiedException()
        if self.stacks[seat] == 0:
            raise NoChipsException()
        inorder_append(self.active_seats, seat)

    # Returns number of players with hands remaining in play
    def num_remaining(self):
        return len(self.remaining_hands)
    
    def deal(self):
        self.deck = deck()
        self.initial_bet = True
        for seat in range(self.seats):
            if seat in self.active_seats:
                hand = (self.deck.pop(), self.deck.pop())
                self.hands.append(hand)
            else:
                self.hands.append(None)

        self.remaining_hands = [seat for seat in self.active_seats]
        if self.num_remaining() < 2:
            raise NoPlayersException()
        if self.dealer == None:
            self.dealer = random.sample(self.active_seats, 1)[0]
        self.street = Streets.Preflop
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
                self.action_permissions.append(seat)

    def deal_headsup(self):
        dealer_ind = self.active_seats.index(self.dealer)
        self.open_action(dealer_ind, include_final=True)
        sb_ind = dealer_ind
        bb_ind = (dealer_ind + 1) % 2
        sb_seat = self.active_seats[sb_ind]
        bb_seat = self.active_seats[bb_ind]
        sb_stack = self.stacks[sb_seat]
        bb_stack = self.stacks[bb_seat]

        after_ante = bb_stack - self.ante
        if after_ante < 1:
            raise ShortStackException()
        
        sb = min(self.sb, sb_stack)
        bb = min(self.bb, bb_stack)
        self.stacks[bb_seat] -= self.ante
        self.pot += self.ante
        self.invest(bb_seat, bb)
        self.invest(sb_seat, sb)

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
            raise ShortStackException()
        bb = min(self.bb, bb_stack)
        self.stacks[bb_seat] -= self.ante
        self.pot += self.ante
        self.invest(bb_seat, bb)
        self.invest(sb_seat, sb)
        
    def fold(self):
        acting_player = self.action_permissions[0]
        # Remove the player's bets from the bet pool and add it to the pot
        self.pot += self.current_bets[acting_player]
        self.current_bets[acting_player] = 0
        # Remove the acting player's seat from the remaining hands list of active seats
        del self.remaining_hands[self.remaining_hands.index(acting_player)]
        self.action_forward()

    # Determine whether the current acting player is able to initiate a new bet
    def may_bet(self):
        # The initial ability to bet on a given street is always granted
        if self.initial_bet:
            return True
        acting_player = self.action_permissions[0]
        difference = self.current_bet - self.current_bets[acting_player]
        action_open = difference >= self.previous_raise
        
        return action_open or self.is_blind(acting_player)
    
    # Determine whether the current acting player has chips remaining to take an action
    def may_act(self):
        acting_player = self.action_permissions[0]
        return self.stacks[acting_player] != 0

    def bet(self, chips):
        if not self.may_bet():
            raise InvalidBetException()
        # Seat number of currently acting player
        acting_player = self.action_permissions[0]
        # Bets must be made with positive integer quantities, and bets must exceed the current bet
        if (chips % 1) != 0 or chips <= 0 or chips <= self.current_bet:
            raise InvalidBetException()
        player_previous_bet = self.current_bets[acting_player]
        additional_chips = chips - player_previous_bet
        # A player should not bet more additional chips than they have in their stack
        additional_chips = min(self.stacks[acting_player], additional_chips)
        raise_req = self.current_bet + self.previous_raise
        legal_raise = chips >= raise_req
        allin = additional_chips >= self.stacks[acting_player]
        # If the bet is less than allin, and the bet is not a legal raise, then
        # Is an invalid bet
        if not (legal_raise or allin):
            raise InvalidBetException()
        if legal_raise:
            self.previous_raise = chips - self.current_bet
        self.initial_bet = False
        self.current_bet = chips
        self.invest(acting_player, additional_chips)
        self.action_forward(reopen=True)

    # Move action forward to next street
    def next_street(self):
        self.current_bet = 0
        self.previous_raise = self.bb
        self.initial_bet = True
        for bet in self.current_bets:
            self.pot += bet
        self.current_bets = [0 for i in range(self.seats)]
        first_to_act = self.first_to_act(self.remaining_hands)
        self.open_action(first_to_act, include_final=True)

        match (self.street):
            case Streets.Preflop:
                for i in range(3):
                    self.board.append(self.deck.pop())
                next = Streets.Flop
            case Streets.Flop:
                self.board.append(self.deck.pop())
                next = Streets.Turn
            case Streets.Turn:
                self.board.append(self.deck.pop())
                next = Streets.River
            case Streets.River:
                
                self.showdown()
                self.street = Streets.End
                return
        self.street = next

        # If first to act is already allin, 
        # Move the action forward to the next player who may act
        if not self.may_act():
            self.action_forward()

    # Determine if all players remaining in the hand are allin
    def players_allin(self):
        not_allin = []
        for seat in self.remaining_hands:
            if self.stacks[seat] != 0:
                not_allin.append(seat)
                if len(not_allin) == 2:
                    return False
        # If there is one player not allin, he must have called the largest allin bet
        # In order for the hand to be currently allin
        if len(not_allin) == 1:
            largest_invested = max(self.chips_invested)
            seat = not_allin[0]
            player_invested = self.chips_invested[seat]
            if player_invested < largest_invested:
                return False
        return True

    def showdown(self):
        # Ordered list of tuples (seat, chips_invested) sorted by chips_invested
        invested = [(seat, chips) for (seat, chips) in enumerate(self.chips_invested)]
        # Sort chips_invested by number of chips, from least to greatest
        invested = sorted(invested, key=lambda data: data[1])
        first_pot = True
        # Shitty algorithm for calculating sidepots
        while True:
            should_break = False
            # Calculating next side pot, ignore all seats who have 0 chips invested
            while invested[0][1] == 0:
                curr_seat = invested[0][0]
                # Players who have no chips invested in subsequent pots should not be included as possible winners for those pots
                if curr_seat in self.remaining_hands:
                    self.remaining_hands.remove(curr_seat)
                invested.pop(0)
                if len(invested) == 1:
                    # If only one person remains after removing all people with no chips invested,
                    # Then stop calculating sidepots
                    should_break = True
                    break
            if should_break:
                break
            curr_chips_req = invested[0][1]
            curr_pot = curr_chips_req * len(invested)
            # The winner of the main pot is always awarded the ante
            if first_pot:
                curr_pot += self.ante
                first_pot = False
            for i in range(len(invested)):
                curr_seat, curr_chips = invested[i]
                invested[i] = curr_seat, curr_chips - curr_chips_req
            curr_pot_winners = self.winners()
            num_winners = len(curr_pot_winners)
            for winner in curr_pot_winners:
                self.stacks[winner] += curr_pot // num_winners
            remainder = curr_pot % num_winners
            # The remainder is distributed with priority going to the small blind,
            # Rotating clockwise
            minimum_seat = self.first_to_act(curr_pot_winners)
            minimum_ind = curr_pot_winners.index(minimum_seat)

            for chip in range(remainder):
                curr_ind = (minimum_ind + chip) % num_winners
                self.stacks[curr_pot_winners[curr_ind]] += 1

        # Return extra chips to deep stacked player's stack
        final_seat, extra_chips = invested[0]
        self.stacks[final_seat] += extra_chips

    def first_to_act(self, seats):
        # Weird modulus algorithm to find seat closest to SB
        minimum_seat = None
        minimum = None
        for seat in seats:
            adjusted = seat
            if adjusted > self.dealer:
                adjusted -= self.seats
            if minimum == None:
                minimum_seat, minimum = seat, adjusted
                continue
            if adjusted < minimum:
                minimum_seat, minimum = seat, adjusted
        return minimum_seat

    def action_forward(self, reopen=False):
        if self.num_remaining() == 1:
            remaining_player = self.remaining_hands[0]
            self.stacks[remaining_player] += self.pot + sum(self.current_bets)
            self.street = Streets.End
            return

        # Remove the most recent actor from the action sequence, and get their seat number
        previous_actor = self.action_permissions.pop(0)
        if reopen:
            actor_ind = self.remaining_hands.index(previous_actor)
            next_ind = (actor_ind + 1) % self.num_remaining()
            self.open_action(next_ind)
        # If there are players left to act, skip the actions for players who are already allin
        if len(self.action_permissions) != 0:
            while not self.may_act():
                self.action_permissions.pop(0)
        # If no players are left, or the hand is allin, move to the next street
        if len(self.action_permissions) == 0 or self.players_allin():
            self.next_street()

    def may_call(self):
        return not self.may_check()

    def call(self):
        if not self.may_call():
            raise InvalidCallException()
        acting_player = self.action_permissions[0]
        difference = self.current_bet - self.current_bets[acting_player]
        # Players may call off their stack and no more
        investment = min(self.stacks[acting_player], difference)
        self.invest(acting_player, investment)
        self.action_forward()
    
    def may_check(self):
        acting_player = self.action_permissions[0]
        return self.current_bets[acting_player] == self.current_bet
    
    def check(self):
        if not self.may_check():
            raise InvalidCheckException()
        self.action_forward()

if __name__ == '__main__':
    game = PokerGame()
    game.buyin(0, 200)
    game.sitin(0)
    game.buyin(1, 250)
    game.sitin(1)
    game.buyin(2, 180)
    game.sitin(2)

    # Preflop
    game.deal()
    game.bet(5)
    game.fold()
    game.call()

    # Flop
    game.check()
    game.bet(2)
    game.bet(8)
    game.call()

    # Turn
    game.check()
    game.bet(30)
    game.call()
    print(game.pot)


    # River
    game.check()
    game.bet(200)
    game.call()

    for stack in game.stacks:
        print(stack)
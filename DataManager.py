from pymongo import MongoClient
from dotenv import load_dotenv, find_dotenv
import os
import time
from enum import Enum

class Type(Enum):
    intT = 1
    boolT = 2

options_types = {
    "min_buy": Type.intT,
    "max_buy": Type.intT,
    "match_stack": Type.boolT,
    "bb": Type.intT,
    "sb": Type.intT,
    "ante": Type.intT,
    "seats": Type.intT,
    "time_bank": Type.intT
}

def default_table_options():
    options = {
        "min_buy": 40,
        "max_buy": 100,
        "match_stack": 0,
        "bb": 2,
        "sb": 1,
        "ante": 0,
        "seats": 6,
        "time_bank": 30
    }
    return options

def get_options_string(options):
    order = ["min_buy", "max_buy", "match_stack", "bb", "sb", "ante", "seats", "time_bank"]
    final = ""
    for option in order:
        curr_setting = options[option]
        final += str(curr_setting) + ','
    if final[len(final) - 1] == ',':
        final = final[:len(final) - 1]
    return final

def eval_options_string(string_options):
    order = ["min_buy", "max_buy", "match_stack", "bb", "sb", "ante", "seats", "time_bank"]
    option_arr = string_options.split(',')
    num_options = len(order)
    if len(option_arr) != num_options:
        return False
    options = {}
    for option, setting in zip(order, option_arr):
        required_type = options_types[option]
        acceptable = False
        match(required_type):
            case Type.intT:
                if setting.isnumeric():
                    acceptable = True
                    setting = int(setting)
                break
            case Type.boolT:
                if setting.isnumeric() and (setting == '0' or setting == '1'):
                    acceptable = True
                    setting = int(setting)
                break
        if not acceptable:
            return False
        options[option] = setting
    return options


class DataManager:
    free_chips = 200
    def __init__(self, password):
        api_url = f"mongodb+srv://zisop16:{password}@cluster0.khfjusz.mongodb.net/?retryWrites=true&w=majority"
        cluster = MongoClient(api_url)
        db = cluster["Poker"]
        self.player_data = db["PlayerData"]
        self.channel_data = db["Channels"]

    def user_data(self, userID):
        result = self.player_data.find_one({"_id": userID})
        return result

    def generate_chips(self, userID):
        """_summary_
        Attempt to give free_chips to user, with cooldown wait_time
        Args:
            userID (int): User's Discord ID

        Returns:
            tuple(bool, int): Whether user received, and remaining time before the user is able to receive free chips
        """
        self.safe_add(userID)
        data = self.user_data(userID)
        last_pay = data["last_paycheck"]
        curr_time = time.time()
        wait_time = 3600
        remaining_time = max(wait_time - (curr_time - last_pay), 0)
        may_receive = remaining_time == 0
        if may_receive:
            self.add_chips(userID, DataManager.free_chips)
            query = {"_id": userID}
            command = {
                "$set": {
                    "last_paycheck": curr_time
                }       
            }
            self.player_data.update_one(query, command)
        return may_receive, remaining_time

    def add_user(self, userID):
        """_summary_
        Add user to database
        Args:
            userID (int): User's Discord ID
        """
        post = {
            "_id": userID,
            "chips": 0,
            # Unix time of last time user asked for free chips
            "last_paycheck": 0,
            "tables": {}
        }
        self.player_data.insert_one(post)

    def user_exists(self, userID):
        """_summary_
        Determine if user exists in database
        Args:
            userID (int): User's Discord ID

        Returns:
            bool: Whether the user exists
        """
        return self.user_data(userID) is not None
    
    def table_exists(self, userID, table_name):
        """_summary_
        Determine if table exists in user's game tables
        Args:
            userID (int): User's Discord ID
            table_name (string): Name of table

        Returns:
            bool: Whether the table exists
        """
        data = self.user_data(userID)
        tables = data["tables"]
        return table_name.lower() in tables
    
    def get_table(self, userID, table_name):
        data = self.user_data(userID)
        tables = data["tables"]
        table_name = table_name.lower()
        return tables[table_name] if table_name in tables else False
    
    def safe_add(self, userID):
        """_summary_
        Add user to database, if they do not yet exist
        Args:
            userID (int): User's Discord ID
        """
        if not self.user_exists(userID):
            self.add_user(userID)

    def get_chips(self, userID):
        """_summary_
        Get user's chips balance
        Args:
            userID (int): User's discord ID

        Returns:
            int: number of chips in balance
        """
        self.safe_add(userID)
        data = self.user_data(userID)
        chips = data["chips"]
        return chips
    
    def remove_chips(self, userID, chips):
        """_summary_
        Remove chips from a user's balance
        Args:
            userID (int): User's discord ID
            chips (int): Number of chips
        """
        self.add_chips(userID, -chips)

    def add_chips(self, userID, chips):
        """_summary_
        Add chips to a user's balance
        Args:
            userID (int): User's discord ID
            chips (int): Number of chips
        """
        self.safe_add(userID)
        query = {"_id": userID}
        command = {
            "$inc": {
                "chips": chips
            }       
        }
        self.player_data.update_one(query, command)

    def set_chips(self, userID, chips):
        """_summary_
        Set user's chips balance to certain amount
        Args:
            userID (int): User's discord ID
            chips (int): Number of chips
        """
        self.safe_add(userID)
        query = {"_id": userID}
        command = {
            "$set": {
                "chips": chips
            }       
        }
        self.player_data.update_one(query, command)

    def create_table(self, userID, table_name, options):
        """_summary_
        List of table options:
        min_buy = # of BB, < max_buy, > 5, 
        max_buy = # of BB, > min_buy, <= 500
        match_stack = (0 == off) or (1 == on)
        bb = # of chips, > 1
        sb = # of chips, > 0, <= bb
        ante = # of chips, >= 0, <= bb
        seats = # of seats, >= 2, <= 9
        time_bank = # of seconds, >= 10, or (infinity == -1)

        Args:
            userID (int): User's discord ID
            table_name (string): Table's name
            options (dict): Dict of all table options
        """
        self.safe_add(userID)
        max_tables = 10
        if len(self.get_all_tables(userID)) >= max_tables:
            return False
        # Make sure all table names are case insensitive
        table_name = table_name.lower()
        query = {"_id": userID}
        command = {
            "$set": {
                f"tables.{table_name}": options
            }
        }
        self.player_data.update_one(query, command)
        return True
    
    def delete_table(self, userID, table_name):
        self.safe_add(userID)
        table_name = table_name.lower()
        query = {"_id": userID}
        command = {
            "$unset": {
                f"tables.{table_name}": 0
            }
        }
        self.player_data.update_one(query, command)

    def get_table_names(self, userID):
        return self.get_all_tables(userID).keys()

    def get_all_tables(self, userID):
        data = self.user_data(userID)
        tables = data["tables"]
        return tables

    def get_options(self, userID, table_name):
        table_name = table_name.lower()
        return self.get_all_tables(userID)[table_name]
    
    def initialize_channels(self):
        post = {
            "_id": "channels",
            "arr": []
        }
        self.channel_data.insert_one(post)

    def channel_enabled(self, channelID):
        query = {"_id": "channels"}
        channels = self.channel_data.find_one(query)["arr"]
        return channelID in channels
    
    def disable_channel(self, channelID):
        if not self.channel_enabled(channelID):
            return
        query = {"_id": "channels"}
        command = {"$pull": {"arr": channelID}}
        self.channel_data.update_one(query, command)
    
    def enable_channel(self, channelID):
        if self.channel_enabled(channelID):
            return
        query = {"_id": "channels"}
        command = {"$push": {"arr": channelID}}
        self.channel_data.update_one(query, command)

if __name__ == '__main__':
    load_dotenv(find_dotenv())
    password = os.getenv("MONGO_PASS")
    manager = DataManager(password)
    
    random_id = 36
    dog_id = 336060423713325056
    general = 853046140412493848
    
    manager.disable_channel(general)
    
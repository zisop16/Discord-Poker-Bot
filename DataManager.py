from pymongo import MongoClient
from dotenv import load_dotenv, find_dotenv
import os

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

def options_string(options):
    pass

class DataManager:
    def __init__(self, password):
        api_url = f"mongodb+srv://zisop16:{password}@cluster0.khfjusz.mongodb.net/?retryWrites=true&w=majority"
        cluster = MongoClient(api_url)
        db = cluster["Poker"]
        self.collection = db["PlayerData"]

    def add_user(self, userID):
        """_summary_
        Add user to database
        Args:
            userID (int): User's Discord ID
        """
        post = {
            "_id": userID,
            "chips": 0,
            "tables": {}
        }
        self.collection.insert_one(post)

    def user_exists(self, userID):
        """_summary_
        Determine if user exists in database
        Args:
            userID (int): User's Discord ID

        Returns:
            bool: Whether the user exists
        """
        result = self.collection.find_one({"_id": userID})
        return result is not None
    
    def table_exists(self, userID, table_name):
        """_summary_
        Determine if table exists in user's game tables
        Args:
            userID (int): User's Discord ID
            table_name (string): Name of table

        Returns:
            bool: Whether the table exists
        """
        result = self.collection.find_one({"_id": userID})
        tables = result["tables"]
        return table_name in tables
    
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
        result = self.collection.find_one({"_id": userID})
        chips = result["chips"]
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
        self.collection.update_one(query, command)

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
        self.collection.update_one(query, command)

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
        # Make sure all table names are case insensitive
        table_name = table_name.lower()
        query = {"_id": userID}
        command = {
            "$set": {
                f"tables.{table_name}": options
            }
        }
        self.collection.update_one(query, command)

    def get_table_names(self, userID):
        return self.get_all_tables(userID).keys()

    def get_all_tables(self, userID):
        result = self.collection.find_one({"_id": userID})
        tables = result["tables"]
        return tables

    def get_options(self, userID, table_name):
        table_name = table_name.lower()
        return self.get_all_tables(userID)[table_name]

if __name__ == '__main__':
    load_dotenv(find_dotenv())
    password = os.getenv("MONGO_PASS")
    manager = DataManager(password)
    random_id = 36
    dog_id = 336060423713325056
    options = default_table_options()
    manager.create_table(dog_id, "DogTable", options)
    manager.set_chips(dog_id, 450)

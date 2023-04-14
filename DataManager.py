from pymongo import MongoClient
from dotenv import load_dotenv, find_dotenv
import os

class DataManager:
    def __init__(self, password):
        api_url = f"mongodb+srv://zisop16:{password}@cluster0.khfjusz.mongodb.net/?retryWrites=true&w=majority"
        cluster = MongoClient(api_url)
        db = cluster["Poker"]
        self.collection = db["PlayerData"]

    def add_user(self, userID):
        post = {
            "_id": userID,
            "chips": 0,
            "tables": []
        }
        self.collection.insert_one(post)

    def exists(self, userID):
        result = self.collection.find_one({"_id": userID})
        return result is not None
    
    def safe_add(self, userID):
        if not self.exists(userID):
            self.add_user(userID)

    def get_chips(self, userID):
        self.safe_add(userID)
        result = self.collection.find_one({"_id": userID})
        chips = result["chips"]
        return chips
    
    def remove_chips(self, userID, chips):
        self.add_chips(userID, -chips)

    def add_chips(self, userID, chips):
        self.safe_add(userID)
        query = {"_id": userID}
        command = {
            "$inc": {
                "chips": chips
            }       
        }
        self.collection.update_one(query, command)

    def set_chips(self, userID, chips):
        self.safe_add(userID)
        query = {"_id": userID}
        command = {
            "$set": {
                "chips": chips
            }       
        }
        self.collection.update_one(query, command)

    def create_table(userID, table_name, options):

        pass

    def get_options(userID, table_name):

        pass

if __name__ == '__main__':
    load_dotenv(find_dotenv())
    password = os.getenv("MONGO_PASS")
    manager = DataManager(password)
    random_id = 36
    dog_id = 336060423713325056
    manager.set_chips(dog_id, 450)

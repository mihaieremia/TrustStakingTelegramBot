import pymongo


class Database:
    def __init__(self):
        self.client = pymongo.MongoClient(
            "mongodb+srv://dragos:Ao3myNA5TAA9AJvzwHxPNq2ZP7pza8T@cluster0.hdusz.mongodb.net/telegramBot?retryWrites=true&w=majority")
        self.db = self.client.devTelegramBot

        self.users = self.db.users
        self.wallets = self.db.wallets

    def add_user(self, user_id):
        self.users.insert_one({"_id": user_id, "availableSpace": 0})

    def add_wallet(self, user_id, wallet_address):
        self.wallets.insert_one({"_id": wallet_address, "user": user_id})

    def get_user(self, user_id):
        return self.users.find_one({"_id": user_id})

    def get_subscribed_users(self, subscription):
        return self.users.find({subscription: {"$gt": 0}})

    def subscribe(self, user_id, subscription, min_amount):
        self.users.update_one({"_id": user_id}, {"$set": {subscription: min_amount}})

    def unsubscribe(self, user_id, subscription):
        self.users.update_one({"_id": user_id}, {"$set": {subscription: 0}})

    def is_subscribed(self, user_id, subscription):
        user = self.get_user(user_id)
        return user[subscription] != 0

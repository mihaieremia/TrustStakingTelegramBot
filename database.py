import re
from datetime import datetime, timedelta
import pymongo
from utils import db_token

class Database:
    def __init__(self):
        self.client = pymongo.MongoClient(db_token)
        self.db = self.client.devTelegramBot

        self.users = self.db.users
        self.wallets = self.db.wallets

    def add_user(self, user_id):
        self.users.insert_one({"_id": user_id, "availableSpace": 0})
        return True

    def add_wallet(self, user_id, wallet_address, label):
        if self.get_wallet_byAddress(user_id, wallet_address) is None:
            self.wallets.insert_one(
                {"address": wallet_address, "user": user_id, "label": label, 'available': 0, 'active': 0,
                 'claimable': 0, 'totalRewards': 0, 'last_update': datetime.now() - timedelta(minutes=5)})
            return True
        return False

    def update_wallet(self, user_id, wallet_address, available, active, claimable, totalRewards):
        self.wallets.update_one({"user": user_id, 'address': wallet_address}, {
            "$set": {'available': available, 'active': active, 'claimable': claimable, 'totalRewards': totalRewards, 'last_update': datetime.now()}})

    def get_wallet(self, user_id, label):
        if label is None:
            return self.wallets.find_one({"user": user_id, "label": {"$type": 10}})
        regx = re.compile(label)
        return self.wallets.find_one({"user": user_id, "label": regx})


    def get_wallet_byAddress(self, user_id, address):
        return self.wallets.find_one({"user": user_id, "address": address})

    def delete_wallet(self, user_id, address):
        r = self.wallets.delete_one({"user": user_id, "address": address})
        return r.deleted_count == 1

    def get_wallets(self, user_id):
        return self.wallets.find({"user": user_id})

    def set_label(self, user_id, wallet_address, label):
        t = self.wallets.find_one({"user": user_id, "address": wallet_address})
        self.wallets.update_one({"user": user_id, 'address': wallet_address}, {
            "$set": {'label': label}})

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

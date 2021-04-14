import re
from datetime import datetime, timedelta
import pymongo
from utils import db_token, default_agency


class Database:
    def __init__(self):
        self.client = pymongo.MongoClient(db_token)
        self.db = self.client.devTelegramBot

        self.users = self.db.users
        self.wallets = self.db.wallets

    def add_user(self, user_id):
        self.users.insert_one({"_id": user_id, "availableSpace": []})
        return True

    def add_wallet(self, user_id, wallet_address, label):
        if self.get_wallet_by_address(user_id, wallet_address) is None:
            self.wallets.insert_one(
                {"address": wallet_address, "user": user_id, "label": label, 'available': 0, 'agencies': {},
                 'last_update': datetime.now() - timedelta(minutes=5)})
            return True
        return False

    def update_wallet(self, user_id, wallet_address, available, delegated_agencies):
        self.wallets.update_one({"user": user_id, 'address': wallet_address}, {
            "$set": {'available': available, 'agencies': delegated_agencies, 'last_update': datetime.now()},
            '$unset': {'active': 1, 'claimable': 1, 'totalRewards': 1}})

    def get_wallet(self, user_id, label):
        if label is None:
            return self.wallets.find_one({"user": user_id, "label": {"$type": 10}})
        regx = re.compile(label)
        return self.wallets.find_one({"user": user_id, "label": regx})

    def get_wallet_by_address(self, user_id, address):
        return self.wallets.find_one({"user": user_id, "address": address})

    def delete_wallet(self, user_id, address):
        r = self.wallets.delete_one({"user": user_id, "address": address})
        return r.deleted_count == 1

    def get_wallets(self, user_id):
        return self.wallets.find({"user": user_id})

    def set_label(self, user_id, wallet_address, label):
        self.wallets.update_one({"user": user_id, 'address': wallet_address}, {
            "$set": {'label': label}})

    def get_user(self, user_id):
        return self.users.find_one({"_id": user_id})

    def get_subscribed_users(self, subscription):
        return self.users.find({subscription: {"$not": {"$size": 0}}})

    def subscribe(self, user_id, subscription, agency):
        self.users.update_one({"_id": user_id}, {"$push": {subscription: agency}})

    def unsubscribe(self, user_id, subscription, agency):
        user_subscription = self.users.find_one({"_id": user_id})[subscription]
        user_subscription.remove(agency)
        self.users.update_one({"_id": user_id}, {"$set": {subscription: user_subscription}})

    def is_subscribed(self, user_id, subscription, agency):
        return agency in self.get_agency_subscribed(user_id, subscription)

    def get_agency_subscribed(self, user_id, subscription):
        user = self.get_user(user_id)
        return user[subscription]


    def set_user_agency(self, user_id, agency):
        self.users.update_one({"_id": user_id},
                              {"$set": {'fav_agency': {'last_update': datetime.now(), 'name': agency}}})

    def get_user_agency(self, user_id):
        user = self.get_user(user_id)
        if user is None:
            self.add_user(user_id)
            user = self.get_user(user_id)
        try:
            return user['fav_agency']
        except KeyError:
            self.set_user_agency(user_id, default_agency)
            return {'last_update': datetime.now(), 'name': default_agency}


telegramDb = Database()



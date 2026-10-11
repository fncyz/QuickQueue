from rest_framework.throttling import UserRateThrottle


class ChatRateThrottle(UserRateThrottle):
    scope = "chat"


class AccountDeletionRateThrottle(UserRateThrottle):
    scope = "account_deletion"

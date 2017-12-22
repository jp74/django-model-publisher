

# PublisherStateModel.action choice keys:
ACTION_PUBLISH = "publish"
ACTION_UNPUBLISH = "unpublish"

# PublisherStateModel.state choice keys:
STATE_REQUEST  = "request"
STATE_REJECTED = "rejected"
STATE_ACCEPTED = "accepted"
STATE_DONE = "done"


##############################################################################
# permissions


# used in <publisher-model>.Meta.default_permissions:

# user permission to (un-)publish a object directly & accept/reject a (un-)publish request:
PERMISSION_CAN_PUBLISH = "can_publish"


##############################################################################
# request.POST keys:


# A User with 'can_publish' permission can save&publish in one step:
POST_SAVE_AND_PUBLISH_KEY = "_save_published"


# request (un-)publish submit names:
POST_ASK_PUBLISH_KEY = "_ask_publish"
POST_ASK_UNPUBLISH_KEY = "_ask_unpublish"


# reply (un-)publish submit names:
POST_REPLY_REJECT_KEY = "_reply_reject"
POST_REPLY_ACCEPT_KEY = "_reply_accept"

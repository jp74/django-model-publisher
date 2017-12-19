

# PublisherStateModel.action choice keys:
ACTION_PUBLISH = "publish"
ACTION_UNPUBLISH = "unpublish"

# PublisherStateModel.state choice keys:
STATE_REQUEST  = "request"
STATE_REJECTED = "rejected"
STATE_ACCEPTED = "accepted"
STATE_DONE = "done"

PERMISSION_MODEL_CAN_PUBLISH = "can_publish"

# user permission to publish/unpublish a object directly:
PERMISSION_DIRECT_PUBLISHER = "direct_publisher"

# user permission to create a publish/unpublish request:
PERMISSION_ASK_REQUEST = "ask_publisher_request"

# user permission to accept/reject a publish/unpublish request:
PERMISSION_REPLY_REQUEST = "reply_publisher_request"

# A User with 'can_publish' permission can save&publish in one step:
POST_SAVE_AND_PUBLISH_KEY = "_save_published"

# request publish/unpublish submit names:
POST_ASK_PUBLISH_KEY = "_ask_publish"
POST_ASK_UNPUBLISH_KEY = "_ask_unpublish"

# reply publish/unpublish submit names:
POST_REPLY_REJECT_KEY = "_reply_reject"
POST_REPLY_ACCEPT_KEY = "_reply_accept"


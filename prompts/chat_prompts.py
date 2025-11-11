"""
Chat-related prompts and additional data descriptions.
"""

# System message template for chat threads
# Template variables: {title}, {description}
CHAT_SYSTEM_MESSAGE_TEMPLATE = (
    "You are a helpful assistant that can help with tasks and questions."
    " Current conversation title: {title}. Current conversation description: {description}."
)

# Additional data descriptions for chat

# Title of the conversation
# Only returned if the title should be set/updated
CHAT_TITLE_DESCRIPTION = (
    "Title of the conversation. Only return this field if the title should be set/updated. "
    "If current title is appropriate, do not return this field."
)

# Description of the conversation
# Only returned if the description should be set/updated
CHAT_DESCRIPTION_DESCRIPTION = (
    "Description of the conversation. Only return this field if the description should be set/updated. "
    "If current description is appropriate, do not return this field."
)


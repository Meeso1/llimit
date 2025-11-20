"""
Base LLM service prompts and instructions for additional data handling.
"""

# Base system message for LLM interactions
BASE_SYSTEM_MESSAGE = "You are a helpful assistant."

# Instructions for additional data format (appended to system message when additional_data is requested)
ADDITIONAL_DATA_INSTRUCTIONS_TEMPLATE = """

When responding, you may include additional structured data using the following format:
<additional_data key=[NAME]>[VALUE]</additional_data>
[KEY] should be substituted by the name of additional data field (without square brackets).
Example:
\t<additional_data key=conversation_title>Counting 'R's in 'strawberry'</additional_data>
Only include additional data that was requested in this prompt.
All additional data fields should be included in the response, unless otherwise specified by their description.
All additional data values should be plain text, unless otherwise specified.
All additional data specified should have non-empty value (if it is included in the response). This is very important.

Additional data requested:
"""

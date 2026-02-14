import tiktoken


class TokenizationService:
    """Service for tokenizing text and counting tokens"""

    def __init__(self) -> None:
        self._encoder: tiktoken.Encoding | None = None

    def _get_encoder(self) -> tiktoken.Encoding:
        """Get or create an encoder for the specified tokenizer"""
        if self._encoder is not None:
            return self._encoder

        self._encoder = tiktoken.get_encoding("cl100k_base")
        return self._encoder

    def count_tokens(self, text: str) -> int:
        """
        Count the number of tokens in the given text.
        
        Args:
            text: The text to tokenize
            tokenizer: The tokenizer to use (e.g., "GPT", "Claude", "Other")
            
        Returns:
            Number of tokens in the text
        """
        encoder = self._get_encoder()
        return len(encoder.encode(text))

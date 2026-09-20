"""
Thai-aware tokenization with special token preservation.

This module provides tokenization for Thai text that preserves important
tokens like section numbers, Thai numerals, and abbreviations.
"""
import re
import logging
from typing import List, Optional

from .logging import get_logger


class ThaiTokenizer:
    """Thai-aware tokenization with special token preservation.
    
    This tokenizer uses pythainlp for Thai word segmentation while preserving
    special tokens like:
    - Thai section numbers (e.g., "ข้อ ๒๑", "๒๑.๑")
    - Thai numerals (๐-๙)
    - Thai abbreviations (e.g., "ก.พ.ว.", "ก.ค.ว.")
    
    If pythainlp fails, it falls back to whitespace tokenization.
    """
    
    def __init__(self, logger: Optional[logging.Logger] = None):
        """Initialize Thai tokenizer.
        
        Args:
            logger: Optional logger instance. If None, creates a new logger.
        """
        self.logger = logger or get_logger(__name__)
        
        # Regex patterns for special tokens
        # Thai numerals: ๐-๙
        self.thai_numeral_pattern = re.compile(r'[๐-๙]+')
        
        # Thai abbreviations: ก.พ.ว., ก.ค.ว., etc.
        self.thai_abbrev_pattern = re.compile(r'[ก-ฮ]\.(?:[ก-ฮ]\.)+')
        
        # Section numbers: ข้อ ๒๑, ข้อ ๒๑.๑, etc.
        self.section_pattern = re.compile(r'ข้อ\s*[๐-๙]+(?:\.[๐-๙]+)*')
        
        self.logger.debug("ThaiTokenizer initialized")
    
    def tokenize(self, text: str) -> List[str]:
        """Tokenize Thai text preserving special tokens.
        
        This method:
        1. Protects special tokens (section numbers, abbreviations) with placeholders
        2. Tokenizes the text using pythainlp
        3. Restores protected tokens
        4. Falls back to whitespace tokenization if pythainlp fails
        
        Args:
            text: Input text to tokenize
            
        Returns:
            List of tokens
            
        Examples:
            >>> tokenizer = ThaiTokenizer()
            >>> tokenizer.tokenize("ข้อ ๒๑ ขั้นตอนการแต่งตั้ง")
            ['ข้อ', '๒๑', 'ขั้นตอน', 'การ', 'แต่งตั้ง']
            
            >>> tokenizer.tokenize("ก.พ.ว. มีอำนาจ")
            ['ก.พ.ว.', 'มี', 'อำนาจ']
        """
        if not text or not text.strip():
            return []
        
        try:
            # Step 1: Protect special tokens by replacing with placeholders
            protected_tokens = {}
            protected_text = text
            
            # Protect section numbers (e.g., "ข้อ ๒๑", "๒๑.๑")
            for match in self.section_pattern.finditer(text):
                token = match.group()
                placeholder = f"__SECTION_{len(protected_tokens)}__"
                protected_tokens[placeholder] = token
                protected_text = protected_text.replace(token, placeholder, 1)
            
            # Protect abbreviations (e.g., "ก.พ.ว.")
            for match in self.thai_abbrev_pattern.finditer(protected_text):
                token = match.group()
                placeholder = f"__ABBREV_{len(protected_tokens)}__"
                protected_tokens[placeholder] = token
                protected_text = protected_text.replace(token, placeholder, 1)
            
            # Step 2: Tokenize using pythainlp
            try:
                from pythainlp.tokenize import word_tokenize
                tokens = word_tokenize(protected_text, engine='newmm')
            except ImportError:
                self.logger.warning(
                    "pythainlp not available. Using whitespace tokenization."
                )
                tokens = protected_text.split()
            
            # Step 3: Restore protected tokens
            restored_tokens = []
            for token in tokens:
                if token in protected_tokens:
                    restored_tokens.append(protected_tokens[token])
                elif token.strip():  # Filter out empty tokens
                    restored_tokens.append(token)
            
            self.logger.debug(
                f"Tokenized text into {len(restored_tokens)} tokens"
            )
            return restored_tokens
            
        except Exception as e:
            self.logger.warning(
                f"Tokenization failed: {e}. Using whitespace fallback.",
                exc_info=True
            )
            # Fallback to whitespace tokenization
            return text.split()

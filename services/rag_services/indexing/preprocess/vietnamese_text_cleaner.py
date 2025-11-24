"""
Vietnamese Text Cleaner - Fix PDF extraction issues

Fixes:
1. Unicode normalization (NFC) for Vietnamese diacritics
2. Fix "vỡ chữ" (character splitting) from PyPDF2
3. Remove header/footer boilerplate
4. Smart whitespace normalization

For Knowledge Graph: Ensures clean, parseable text for entity extraction
"""

import re
import unicodedata
from typing import Optional, List, Tuple


class VietnameseTextCleaner:
    """
    Clean Vietnamese text extracted from PDF.
    
    Designed to work with PyPDF2/pdfplumber output and prepare text
    for Knowledge Graph entity extraction.
    """
    
    # Common header/footer patterns in UIT documents
    HEADER_PATTERNS = [
        r'ĐẠI\s+HỌC\s+QUỐC\s+GIA\s+TP\.?\s*HCM.*?THÔNG\s+TIN',
        r'TRƯỜNG\s+ĐẠI\s+HỌC\s+CÔNG\s+NGHỆ\s+THÔNG\s+TIN',
        r'UNIVERSITY\s+OF\s+INFORMATION\s+TECHNOLOGY',
    ]
    
    FOOTER_PATTERNS = [
        r'Trang\s+\d+/\d+',
        r'Page\s+\d+\s+of\s+\d+',
        r'Trang\s+\d+\s+trên\s+\d+',
    ]
    
    BOILERPLATE_PATTERNS = [
        r'CỘNG\s+HÒA\s+XÃ\s+HỘI\s+CHỦ\s+NGHĨA\s+VIỆT\s+NAM',
        r'Độc\s+lập\s+[-–]\s+Tự\s+do\s+[-–]\s+Hạnh\s+phúc',
        r'SOCIALIST\s+REPUBLIC\s+OF\s+VIETNAM',
        r'Independence\s+[-–]\s+Freedom\s+[-–]\s+Happiness',
    ]
    
    # Table of Contents (TOC) patterns - artifacts from PDF extraction
    TOC_PATTERNS = [
        # Pattern: "Điều 7. Chương trình đào tạo ............ 8"
        # Match: Title text followed by 3+ dots and optional page number
        r'\.{3,}\s*\d*$',  # Trailing dots with optional page number at end of line
        r'\.{3,}',  # Any sequence of 3+ dots (general cleanup)
    ]
    
    def __init__(self, remove_headers: bool = True, remove_footers: bool = True):
        """
        Initialize cleaner.
        
        Args:
            remove_headers: Remove document headers
            remove_footers: Remove page numbers and footers
        """
        self.remove_headers = remove_headers
        self.remove_footers = remove_footers
    
    def clean(self, text: str, page_num: Optional[int] = None) -> str:
        """
        Main cleaning pipeline.
        
        Args:
            text: Raw text from PDF
            page_num: Page number (for footer removal)
            
        Returns:
            Cleaned text
        """
        if not text:
            return ""
        
        # Step 1: Unicode normalization
        text = self._normalize_unicode(text)
        
        # Step 2: Fix "vỡ chữ" (character splitting)
        text = self._fix_character_splitting(text)
        
        # Step 3: Remove Table of Contents artifacts (CRITICAL for clean indexing)
        text = self._remove_toc_artifacts(text)
        
        # Step 4: Remove headers/footers
        if self.remove_headers:
            text = self._remove_headers(text)
        
        if self.remove_footers:
            text = self._remove_footers(text, page_num)
        
        # Step 5: Remove boilerplate
        text = self._remove_boilerplate(text)
        
        # Step 6: Normalize whitespace
        text = self._normalize_whitespace(text)
        
        # Step 7: Final cleanup
        text = self._final_cleanup(text)
        
        return text.strip()
    
    def _normalize_unicode(self, text: str) -> str:
        """
        Normalize Unicode to NFC form.
        
        Critical for Vietnamese: ensures diacritics are combined properly.
        Example: "Ế" (combining) → "Ế" (precomposed)
        """
        return unicodedata.normalize('NFC', text)
    
    def _fix_character_splitting(self, text: str) -> str:
        """
        Fix "vỡ chữ" issue from PyPDF2.
        
        Pattern: "CH Ế" → "CHẾ", "ĐÀO T ẠO" → "ĐÀO TẠO"
        
        Strategy:
        1. Remove spaces before Vietnamese diacritics
        2. Fix common Vietnamese compound characters
        """
        # Vietnamese vowels with diacritics (combining marks)
        vietnamese_diacritics = (
            r'[ẠẢẤẦẨẪẬẮẰẲẴẶẸẺẼẾỀỂỄỆỈỊỌỎỐỒỔỖỘỚỜỞỠỢỤỦỨỪỬỮỰỲỴÝỶỸ'
            r'ạảấầẩẫậắằẳẵặẹẻẽếềểễệỉịọỏốồổỗộớờởỡợụủứừửữựỳỵýỷỹ]'
        )
        
        # Pattern 1: Remove space before diacritic
        # "CH Ế" → "CHẾ"
        text = re.sub(
            rf'(\w)\s+({vietnamese_diacritics})',
            r'\1\2',
            text
        )
        
        # Pattern 2: Fix common Vietnamese digraphs/trigraphs
        # "TH Ô" → "THÔ", "NGH Ĩ" → "NGHĨ"
        common_patterns = [
            (r'CH\s+([AEIOUYÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸ])', r'CH\1'),
            (r'GH\s+([AEIOUYÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸ])', r'GH\1'),
            (r'NGH\s+([AEIOUYÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸ])', r'NGH\1'),
            (r'TH\s+([AEIOUYÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸ])', r'TH\1'),
            (r'TR\s+([AEIOUYÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸ])', r'TR\1'),
            (r'PH\s+([AEIOUYÀÁẠẢÃÂẦẤẬẨẪĂẰẮẶẲẴÈÉẸẺẼÊỀẾỆỂỄÌÍỊỈĨÒÓỌỎÕÔỒỐỘỔỖƠỜỚỢỞỠÙÚỤỦŨƯỪỨỰỬỮỲÝỴỶỸ])', r'PH\1'),
        ]
        
        for pattern, replacement in common_patterns:
            text = re.sub(pattern, replacement, text, flags=re.IGNORECASE)
        
        return text
    
    def _remove_toc_artifacts(self, text: str) -> str:
        """
        Remove Table of Contents artifacts from PDF extraction.
        
        Fixes patterns like:
        - "Điều 7. Chương trình đào tạo ............ 8" → "Điều 7. Chương trình đào tạo"
        - "Chương 2. TỔ CHỨC ................................. 10" → "Chương 2. TỔ CHỨC"
        
        This is CRITICAL for clean vector embeddings.
        """
        for pattern in self.TOC_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.MULTILINE)
        
        return text
    
    def _remove_headers(self, text: str) -> str:
        """Remove common document headers."""
        for pattern in self.HEADER_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        return text
    
    def _remove_footers(self, text: str, page_num: Optional[int] = None) -> str:
        """Remove page numbers and footers."""
        for pattern in self.FOOTER_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE)
        
        # If page number is known, remove it specifically
        if page_num:
            text = re.sub(rf'\b{page_num}\b', '', text)
        
        return text
    
    def _remove_boilerplate(self, text: str) -> str:
        """Remove common boilerplate text."""
        for pattern in self.BOILERPLATE_PATTERNS:
            text = re.sub(pattern, '', text, flags=re.IGNORECASE | re.DOTALL)
        return text
    
    def _normalize_whitespace(self, text: str) -> str:
        """
        Normalize whitespace intelligently.
        
        - Multiple spaces → single space
        - Multiple newlines → double newline (preserve paragraph breaks)
        - Tabs → spaces
        """
        # Replace tabs with spaces
        text = text.replace('\t', ' ')
        
        # Replace multiple spaces with single space (but not newlines)
        text = re.sub(r' +', ' ', text)
        
        # Replace 3+ newlines with double newline
        text = re.sub(r'\n{3,}', '\n\n', text)
        
        # Remove spaces at start/end of lines
        text = re.sub(r'[ ]+\n', '\n', text)
        text = re.sub(r'\n[ ]+', '\n', text)
        
        return text
    
    def _final_cleanup(self, text: str) -> str:
        """Final cleanup steps."""
        # Remove lines with only numbers (often pagination artifacts)
        text = re.sub(r'\n\d+\n', '\n', text)
        
        # Remove very short lines (< 3 chars) that are likely artifacts
        lines = text.split('\n')
        cleaned_lines = [
            line for line in lines
            if len(line.strip()) == 0 or len(line.strip()) >= 3
        ]
        text = '\n'.join(cleaned_lines)
        
        return text
    
    def clean_batch(self, pages: List[Tuple[str, int]]) -> List[Tuple[str, int]]:
        """
        Clean multiple pages.
        
        Args:
            pages: List of (text, page_num) tuples
            
        Returns:
            List of (cleaned_text, page_num) tuples
        """
        return [
            (self.clean(text, page_num), page_num)
            for text, page_num in pages
        ]


# Convenience function
def clean_vietnamese_text(
    text: str,
    page_num: Optional[int] = None,
    remove_headers: bool = True,
    remove_footers: bool = True
) -> str:
    """
    Quick clean function.
    
    Args:
        text: Raw text from PDF
        page_num: Page number
        remove_headers: Remove headers
        remove_footers: Remove footers
        
    Returns:
        Cleaned text
    """
    cleaner = VietnameseTextCleaner(
        remove_headers=remove_headers,
        remove_footers=remove_footers
    )
    return cleaner.clean(text, page_num)


# Demo
if __name__ == "__main__":
    # Test case 1: Vỡ chữ
    test1 = "QUY CH Ế ĐÀO T ẠO THEO H ỌC CH Ế TÍN CH Ỉ"
    print("Test 1: Vỡ chữ")
    print(f"  Input:  {test1}")
    print(f"  Output: {clean_vietnamese_text(test1)}")
    print()
    
    # Test case 2: Header/footer
    test2 = """
    ĐẠI HỌC QUỐC GIA TP.HCM
    TRƯỜNG ĐẠI HỌC CÔNG NGHỆ THÔNG TIN
    
    QUY CHẾ ĐÀO TẠO
    
    Điều 1: Phạm vi điều chỉnh
    
    Trang 1/27
    """
    print("Test 2: Header/footer")
    print(f"  Input:  {repr(test2[:100])}")
    print(f"  Output: {clean_vietnamese_text(test2, page_num=1)}")
    print()
    
    # Test case 3: Unicode normalization
    test3 = "Điề\u0323u 1"  # Combining diacritics
    print("Test 3: Unicode normalization")
    print(f"  Input:  {repr(test3)}")
    print(f"  Output: {repr(clean_vietnamese_text(test3))}")
    print()
    
    # Test case 4: Table of Contents artifacts (NEW)
    test4 = "Điều 7. Chương trình đào tạo ................................ ................................ ................................ ............ 8"
    print("Test 4: TOC artifacts")
    print(f"  Input:  {test4}")
    print(f"  Output: {clean_vietnamese_text(test4)}")
    print()
    
    # Test case 5: Multiple TOC patterns
    test5 = """
    Điều 10. Chế độ học tập của sinh viên ................................ ............................ 11
    Chương 2. TỔ CHỨC ĐÀO TẠO ............... 10
    """
    print("Test 5: Multiple TOC patterns")
    print(f"  Input:  {test5}")
    print(f"  Output: {clean_vietnamese_text(test5)}")


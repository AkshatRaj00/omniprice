import re
from difflib import SequenceMatcher
from typing import Tuple, Set

class CrossStoreMatcher:
    @staticmethod
    def tokenize(text: str) -> Set[str]:
        cleaned = re.sub(r'[^\w\s]', ' ', text.lower())
        return {w for w in cleaned.split() if len(w) > 1}

    @classmethod
    def token_set_ratio(cls, s1: str, s2: str) -> float:
        """Calculates overlap ratio independent of word order."""
        t1 = cls.tokenize(s1)
        t2 = cls.tokenize(s2)
        if not t1 or not t2:
            return 0.0
        
        intersection = t1.intersection(t2)
        return len(intersection) / len(t1)

    @classmethod
    def sequence_similarity(cls, s1: str, s2: str) -> float:
        return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()

    @classmethod
    def evaluate_match(
        cls, 
        target_query: str, 
        target_variant: str, 
        candidate_title: str, 
        candidate_price: int = None
    ) -> Tuple[bool, int]:
        """
        Calculates multi-dimensional semantic match score.
        Returns: (is_valid_match, confidence_score_0_to_100)
        """
        if not candidate_title:
            return False, 0

        # Dimension 1: Token Set Precision
        t_ratio = cls.token_set_ratio(target_query, candidate_title)
        
        # Dimension 2: Exact Subsequence Alignment
        s_ratio = cls.sequence_similarity(target_query, candidate_title)

        # Weighted Ensemble Score
        base_score = (t_ratio * 0.70) + (s_ratio * 0.30)
        final_score = int(base_score * 100)

        # Dimension 3: Hard Variant Constraint Enforcement
        if target_variant:
            variant_clean = target_variant.lower().replace("-", "")
            cand_clean = candidate_title.lower().replace("-", "").replace(" ", "")
            
            if variant_clean not in cand_clean:
                # Heavy penalty: If sizes or volume don't match, this is a different SKU
                final_score -= 30

        # An entity match in retail requires at least 50% verified confidence
        is_match = final_score >= 50
        return is_match, max(0, min(100, final_score))

# Alias for compatibility with industrial architecture
IndustrialMatcher = CrossStoreMatcher
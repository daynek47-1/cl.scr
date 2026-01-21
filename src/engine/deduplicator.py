"""Smart Bonus Deduplication with Fingerprinting and Fuzzy Matching"""
import logging
import re
from typing import Optional, Dict, List
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
import dateparser

from ..models import Bonus

logger = logging.getLogger(__name__)


class BonusDeduplicator:
    """
    Handles deduplication of bonuses across mirror sites with safety checks

    Strategy:
    1. Exact Match: Use SHA256 fingerprint of title+description
    2. Fuzzy Match: Use SequenceMatcher for similar but not identical bonuses
    3. Safety Checks: Prevent merging bonuses with different numbers or Roman numerals
    4. Parent-Child: Link fuzzy-matched bonuses to a parent record

    Safety Features:
    - Number protection: "Bonus 100" will NOT match "Bonus 200" even if 80%+ similar
    - Roman numeral protection: "Tier I" will NOT match "Tier II"
    """

    def __init__(self, db: Session, fuzzy_threshold: float = 0.80):
        self.db = db
        self.fuzzy_threshold = fuzzy_threshold  # Similarity threshold (0.0-1.0, default 80%)

    def find_or_create_bonus(
        self,
        mirror_site_id: int,
        parsed_bonus: Dict,
        pv_score: float,
        is_beatable: bool
    ) -> tuple[Bonus, bool]:
        """
        Find existing bonus or create new one

        Returns: (Bonus object, is_new: bool)
        """
        # Generate fingerprint
        fingerprint = Bonus.generate_fingerprint(
            parsed_bonus['title'],
            parsed_bonus.get('description', '')
        )

        # 1. Check for exact match by fingerprint
        existing = self.db.query(Bonus).filter(
            Bonus.fingerprint == fingerprint,
            Bonus.is_active == True
        ).first()

        if existing:
            # Update existing bonus
            logger.debug(f"Found exact match for: {parsed_bonus['title'][:50]}")
            self._update_bonus(existing, mirror_site_id, parsed_bonus, pv_score, is_beatable)
            return existing, False

        # 2. Check for fuzzy match
        fuzzy_parent = self._find_fuzzy_match(parsed_bonus['title'])

        # Parse expiration date
        expiration_date = self._parse_expiration_date(
            parsed_bonus.get('expiration_date') or parsed_bonus.get('description', '')
        )

        # 3. Create new bonus
        new_bonus = Bonus(
            mirror_site_id=mirror_site_id,
            fingerprint=fingerprint,
            parent_bonus_id=fuzzy_parent.id if fuzzy_parent else None,
            title=parsed_bonus['title'],
            description=parsed_bonus.get('description', ''),
            raw_data=parsed_bonus.get('raw_data', ''),
            bonus_amount=parsed_bonus.get('bonus_amount'),
            currency=parsed_bonus.get('currency', 'USD'),
            rollover=parsed_bonus.get('rollover'),
            max_withdrawal=parsed_bonus.get('max_withdrawal'),
            min_deposit=parsed_bonus.get('min_deposit'),
            max_bet=parsed_bonus.get('max_bet'),
            time_limit_days=parsed_bonus.get('time_limit_days'),
            game_restrictions=parsed_bonus.get('game_restrictions'),
            bonus_code=parsed_bonus.get('bonus_code'),
            requires_code=parsed_bonus.get('requires_code', False),
            pv_score=pv_score,
            is_beatable=is_beatable,
            expiration_date=expiration_date,
            is_expired=False,
            url=parsed_bonus.get('url'),
            is_active=True,
            seen_on_sites=1
        )

        self.db.add(new_bonus)
        self.db.flush()  # Get ID without committing

        logger.info(f"Created new bonus: {new_bonus.title[:50]} (PV: {pv_score}, Beatable: {is_beatable})")

        if fuzzy_parent:
            logger.debug(f"Linked to parent bonus ID: {fuzzy_parent.id}")

        return new_bonus, True

    def _find_fuzzy_match(self, title: str) -> Optional[Bonus]:
        """
        Find fuzzy match for bonus title with safety checks

        Uses SequenceMatcher (difflib) and prevents dangerous merges:
        - Different numbers: "Bonus 100" vs "Bonus 200" → NO MATCH
        - Different Roman numerals: "Tier I" vs "Tier II" → NO MATCH
        """
        # Get all active bonuses (parent bonuses only to avoid deep nesting)
        candidates = self.db.query(Bonus).filter(
            Bonus.is_active == True,
            Bonus.parent_bonus_id == None  # Only check parent bonuses
        ).all()

        best_match = None
        best_score = 0.0

        title_lower = title.lower()

        for candidate in candidates:
            candidate_lower = candidate.title.lower()

            # Calculate similarity using SequenceMatcher
            score = SequenceMatcher(None, title_lower, candidate_lower).ratio()

            if score >= self.fuzzy_threshold and score > best_score:
                # SAFETY CHECK: Prevent merging bonuses with different numbers
                if not self._safe_to_merge_numbers(title, candidate.title):
                    logger.debug(
                        f"Blocked fuzzy match due to different numbers: "
                        f"'{title[:30]}' vs '{candidate.title[:30]}' (similarity: {score:.2%})"
                    )
                    continue

                # SAFETY CHECK: Prevent merging bonuses with different Roman numerals
                if not self._safe_to_merge_roman_numerals(title, candidate.title):
                    logger.debug(
                        f"Blocked fuzzy match due to different Roman numerals: "
                        f"'{title[:30]}' vs '{candidate.title[:30]}' (similarity: {score:.2%})"
                    )
                    continue

                best_score = score
                best_match = candidate

        if best_match:
            logger.debug(
                f"Fuzzy match found: '{title[:30]}' -> '{best_match.title[:30]}' "
                f"(similarity: {best_score:.2%})"
            )

        return best_match

    def _safe_to_merge_numbers(self, title1: str, title2: str) -> bool:
        """
        Check if two titles with numbers can be safely merged

        Returns False if they contain different numbers (e.g., "100" vs "200")
        Returns True if they have the same numbers or no numbers
        """
        # Extract all numbers from both titles
        numbers1 = set(re.findall(r'\d+', title1))
        numbers2 = set(re.findall(r'\d+', title2))

        # If both have numbers, they must be the same
        if numbers1 and numbers2:
            # Check for any differing numbers
            if numbers1 != numbers2:
                # They have different numbers
                return False

        return True

    def _safe_to_merge_roman_numerals(self, title1: str, title2: str) -> bool:
        """
        Check if two titles with Roman numerals can be safely merged

        Returns False if they contain different Roman numerals (e.g., "I" vs "II")
        Returns True if they have the same Roman numerals or none
        """
        # Roman numeral pattern (common ones: I, II, III, IV, V, VI, VII, VIII, IX, X)
        roman_pattern = r'\b(I{1,3}|IV|V|VI{0,3}|IX|X)\b'

        # Extract Roman numerals (case-insensitive)
        romans1 = set(re.findall(roman_pattern, title1.upper()))
        romans2 = set(re.findall(roman_pattern, title2.upper()))

        # If both have Roman numerals, they must be the same
        if romans1 and romans2:
            if romans1 != romans2:
                # They have different Roman numerals
                return False

        return True

    def _update_bonus(
        self,
        bonus: Bonus,
        mirror_site_id: int,
        parsed_bonus: Dict,
        pv_score: float,
        is_beatable: bool
    ):
        """Update existing bonus with new data"""
        from datetime import datetime

        # Update last seen
        bonus.last_seen = datetime.utcnow()

        # Increment seen count if this is a different mirror site
        if bonus.mirror_site_id != mirror_site_id:
            bonus.seen_on_sites += 1

        # Update PV score if it changed significantly
        if abs((bonus.pv_score or 0) - pv_score) > 5:
            bonus.pv_score = pv_score
            bonus.is_beatable = is_beatable
            logger.debug(f"Updated PV score for '{bonus.title[:30]}': {pv_score}")

        # Update other fields if they're more complete
        if parsed_bonus.get('description') and len(parsed_bonus['description']) > len(bonus.description or ''):
            bonus.description = parsed_bonus['description']

        if parsed_bonus.get('max_withdrawal') and not bonus.max_withdrawal:
            bonus.max_withdrawal = parsed_bonus['max_withdrawal']
            # Recalculate PV with new info
            from datetime import datetime
            bonus.updated_at = datetime.utcnow()

        self.db.flush()

    def _parse_expiration_date(self, text: str) -> Optional:
        """
        Parse expiration date from text

        Handles formats like:
        - "Valid until Jan 30, 2024"
        - "Expires: 2024-01-30"
        - "Valid for 30 days"
        """
        from datetime import datetime

        if not text:
            return None

        try:
            # Try to find date patterns
            import re

            # Pattern 1: "until DATE" or "expires DATE"
            patterns = [
                r'(?:until|expires?|valid\s+until|ends?)\s*:?\s*([A-Za-z]+\s+\d{1,2},?\s+\d{4})',
                r'(?:until|expires?|valid\s+until|ends?)\s*:?\s*(\d{4}-\d{2}-\d{2})',
                r'(?:until|expires?|valid\s+until|ends?)\s*:?\s*(\d{1,2}[/-]\d{1,2}[/-]\d{2,4})',
            ]

            for pattern in patterns:
                match = re.search(pattern, text, re.IGNORECASE)
                if match:
                    date_str = match.group(1)
                    parsed_date = dateparser.parse(date_str)
                    if parsed_date:
                        logger.debug(f"Parsed expiration date: {parsed_date} from '{date_str}'")
                        return parsed_date

            # Pattern 2: "Valid for N days"
            days_match = re.search(r'valid\s+for\s+(\d+)\s+days?', text, re.IGNORECASE)
            if days_match:
                from datetime import timedelta
                days = int(days_match.group(1))
                expiration = datetime.utcnow() + timedelta(days=days)
                logger.debug(f"Calculated expiration: {expiration} ({days} days from now)")
                return expiration

        except Exception as e:
            logger.debug(f"Could not parse expiration date from: '{text[:100]}': {e}")

        return None

    def mark_expired_bonuses(self) -> int:
        """
        Check all bonuses and mark expired ones

        Returns: Number of bonuses marked as expired
        """
        from datetime import datetime

        bonuses_to_check = self.db.query(Bonus).filter(
            Bonus.is_active == True,
            Bonus.expiration_date != None,
            Bonus.is_expired == False
        ).all()

        expired_count = 0

        for bonus in bonuses_to_check:
            if datetime.utcnow() > bonus.expiration_date:
                bonus.is_expired = True
                bonus.is_active = False
                expired_count += 1
                logger.info(f"Marked bonus as expired: {bonus.title[:50]}")

        if expired_count > 0:
            self.db.commit()
            logger.info(f"Marked {expired_count} bonuses as expired")

        return expired_count

    def get_duplicate_stats(self) -> Dict:
        """Get statistics on duplicate bonuses"""
        total_bonuses = self.db.query(Bonus).filter(Bonus.is_active == True).count()

        parent_bonuses = self.db.query(Bonus).filter(
            Bonus.is_active == True,
            Bonus.parent_bonus_id == None
        ).count()

        duplicate_bonuses = self.db.query(Bonus).filter(
            Bonus.is_active == True,
            Bonus.parent_bonus_id != None
        ).count()

        # Bonuses seen on multiple sites
        multi_site_bonuses = self.db.query(Bonus).filter(
            Bonus.is_active == True,
            Bonus.seen_on_sites > 1
        ).count()

        return {
            'total_bonuses': total_bonuses,
            'unique_bonuses': parent_bonuses,
            'duplicate_bonuses': duplicate_bonuses,
            'multi_site_bonuses': multi_site_bonuses,
            'deduplication_rate': round((duplicate_bonuses / total_bonuses * 100), 2) if total_bonuses > 0 else 0
        }

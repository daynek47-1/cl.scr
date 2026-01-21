"""Perceived Value (PV) Calculator - The V14 Beatability Algorithm"""
import logging
import math
from typing import Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class PVCalculator:
    """
    Calculates the Perceived Value (PV) score for bonuses using the V14 algorithm

    The V14 algorithm uses a sophisticated non-linear formula that accounts for:
    - Logarithmic scaling of bonus amount (diminishing returns)
    - Power scaling of rollover requirements (exponential penalty)
    - Max withdrawal with square root scaling

    V14 Formula:
        PV = (10 * log2(bonus_amount + 1) * sqrt(max_withdrawal)) /
             (pow(rollover, 1.25) * log10(bonus_amount + 10))

    This creates a more realistic model where:
    - Bonus size has logarithmic efficiency (bigger isn't always better)
    - High rollovers are penalized exponentially
    - Max withdrawal provides sub-linear utility

    Higher PV = Higher relative average value
    """

    def __init__(
        self,
        use_v14: bool = None,
        bonus_weight: float = None,
        rollover_weight: float = None,
        withdrawal_weight: float = None
    ):
        # Use V14 by default (can fall back to simple linear for testing)
        self.use_v14 = use_v14 if use_v14 is not None else os.getenv('USE_V14_FORMULA', 'true').lower() == 'true'

        # Legacy weights (only used if not using V14)
        self.bonus_weight = bonus_weight or float(os.getenv('PV_BONUS_WEIGHT', 1.0))
        self.rollover_weight = rollover_weight or float(os.getenv('PV_ROLLOVER_WEIGHT', 0.5))
        self.withdrawal_weight = withdrawal_weight or float(os.getenv('PV_MAX_WITHDRAWAL_WEIGHT', 0.3))

        logger.info(
            f"PV Calculator initialized: "
            f"algorithm={'V14 (sophisticated)' if self.use_v14 else 'Linear (simple)'}"
        )

    def calculate(
        self,
        bonus_amount: Optional[float],
        rollover: Optional[float] = None,
        max_withdrawal: Optional[float] = None
    ) -> Dict:
        """
        Calculate PV score for a bonus using V14 algorithm or simple linear

        Returns:
            {
                'pv_score': float,
                'is_beatable': bool,
                'rating': str,
                'components': dict
            }
        """
        if not bonus_amount or bonus_amount <= 0:
            return {
                'pv_score': 0.0,
                'is_beatable': False,
                'rating': 'Invalid',
                'components': {}
            }

        if self.use_v14:
            return self._calculate_v14(bonus_amount, rollover, max_withdrawal)
        else:
            return self._calculate_linear(bonus_amount, rollover, max_withdrawal)

    def _calculate_v14(
        self,
        bonus_amount: float,
        rollover: Optional[float],
        max_withdrawal: Optional[float]
    ) -> Dict:
        """
        V14 Algorithm - Sophisticated non-linear PV calculation

        Formula:
            PV = (10 * log2(mw + 1) * sqrt(ba)) / (pow(ro, 1.25) * log10(ba + 10))

        Where:
            mw = max_withdrawal (defaults to bonus_amount if not set)
            ba = bonus_amount
            ro = rollover (defaults to 1 if not set to avoid division by zero)
        """
        # Handle defaults
        mw = max_withdrawal if max_withdrawal and max_withdrawal > 0 else bonus_amount
        ro = rollover if rollover and rollover > 0 else 1.0

        try:
            # Numerator: Reward component
            # - log2(ba + 1): Logarithmic scaling of bonus amount (diminishing returns on size)
            # - sqrt(mw): Square root of max withdrawal (scaling for potential payout)
            # Correction V14.1: User clarified log component applies to amount
            numerator = 10 * math.log2(bonus_amount + 1) * math.sqrt(mw)

            # Denominator: Penalty component
            # - pow(ro, 1.25): Exponential rollover penalty (high rollovers severely penalized)
            # - log10(ba + 10): Logarithmic bonus size adjustment (prevents huge bonuses dominating)
            denominator = math.pow(ro, 1.25) * math.log10(bonus_amount + 10)

            # Final PV score
            pv_score = numerator / denominator

            # Component breakdown for transparency
            components = {
                'bonus_factor': round(10 * math.log2(bonus_amount + 1), 2),
                'withdrawal_factor': round(math.sqrt(mw), 2),
                'rollover_penalty': round(math.pow(ro, 1.25), 2),
                'size_adjustment': round(math.log10(bonus_amount + 10), 2),
                'numerator': round(numerator, 2),
                'denominator': round(denominator, 2)
            }

        except (ValueError, ZeroDivisionError) as e:
            logger.error(f"V14 calculation error: {e}")
            pv_score = 0.0
            components = {}

        # Determine beatability
        is_beatable = self._is_beatable_v14(bonus_amount, ro, mw, pv_score)

        # Rating
        rating = self._get_rating_v14(pv_score, ro)

        return {
            'pv_score': round(pv_score, 2),
            'is_beatable': is_beatable,
            'rating': rating,
            'components': components,
            'algorithm': 'V14'
        }

    def _calculate_linear(
        self,
        bonus_amount: float,
        rollover: Optional[float],
        max_withdrawal: Optional[float]
    ) -> Dict:
        """Simple linear calculation (legacy/testing)"""
        bonus_contribution = bonus_amount * self.bonus_weight

        rollover_penalty = 0.0
        if rollover and rollover > 0:
            rollover_penalty = rollover * self.rollover_weight

        withdrawal_bonus = 0.0
        if max_withdrawal and max_withdrawal > 0:
            withdrawal_bonus = max_withdrawal * self.withdrawal_weight

        pv_score = bonus_contribution - rollover_penalty + withdrawal_bonus

        is_beatable = self._is_beatable(bonus_amount, rollover, max_withdrawal, pv_score)
        rating = self._get_rating(pv_score, rollover or 0)

        return {
            'pv_score': round(pv_score, 2),
            'is_beatable': is_beatable,
            'rating': rating,
            'components': {
                'bonus_contribution': round(bonus_contribution, 2),
                'rollover_penalty': round(rollover_penalty, 2),
                'withdrawal_bonus': round(withdrawal_bonus, 2)
            },
            'algorithm': 'Linear'
        }

    def _is_beatable_v14(
        self,
        bonus_amount: float,
        rollover: float,
        max_withdrawal: float,
        pv_score: float
    ) -> bool:
        """
        V14 beatability determination (more sophisticated)

        Criteria:
        1. PV score must be >= 20 (V14 scores are typically higher range)
        2. Rollover must be reasonable (< 60x for V14)
        3. Rollover-to-withdrawal ratio must be acceptable
        """
        if pv_score < 20:
            return False

        # Rollover too high
        if rollover > 60:
            return False

        # Check rollover efficiency: rollover shouldn't be more than 2x the withdrawal limit
        if rollover > (max_withdrawal / bonus_amount) * 2:
            return False

        return True

    def _get_rating_v14(self, pv_score: float, rollover: float) -> str:
        """
        V14 rating system (adjusted for higher score range)

        Excellent: PV > 200 and rollover < 30
        Good: PV > 100 or (PV > 50 and rollover < 40)
        Fair: PV > 20
        Poor: PV <= 20
        """
        if pv_score > 200 and rollover < 30:
            return 'Excellent'
        elif pv_score > 100 or (pv_score > 50 and rollover < 40):
            return 'Good'
        elif pv_score > 20:
            return 'Fair'
        else:
            return 'Poor'

    def _is_beatable(
        self,
        bonus_amount: float,
        rollover: Optional[float],
        max_withdrawal: Optional[float],
        pv_score: float
    ) -> bool:
        """Legacy linear beatability check"""
        if pv_score <= 0:
            return False

        if rollover and rollover > 50:
            return False

        if max_withdrawal and max_withdrawal < bonus_amount * 0.5:
            return False

        return True

    def _get_rating(self, pv_score: float, rollover: float) -> str:
        """Legacy linear rating"""
        if pv_score > 100 and rollover < 30:
            return 'Excellent'
        elif pv_score > 50 or (pv_score > 0 and rollover < 40):
            return 'Good'
        elif pv_score > 0:
            return 'Fair'
        else:
            return 'Poor'

    def compare_bonuses(self, bonus1: Dict, bonus2: Dict) -> Dict:
        """
        Compare two bonuses based on PV scores

        Returns which bonus is better and by how much
        """
        pv1 = self.calculate(
            bonus1.get('bonus_amount'),
            bonus1.get('rollover'),
            bonus1.get('max_withdrawal')
        )

        pv2 = self.calculate(
            bonus2.get('bonus_amount'),
            bonus2.get('rollover'),
            bonus2.get('max_withdrawal')
        )

        difference = pv1['pv_score'] - pv2['pv_score']

        return {
            'bonus1_pv': pv1['pv_score'],
            'bonus2_pv': pv2['pv_score'],
            'difference': round(difference, 2),
            'better_bonus': 1 if difference > 0 else 2 if difference < 0 else 0,
            'verdict': self._get_comparison_verdict(difference)
        }

    def _get_comparison_verdict(self, difference: float) -> str:
        """Get human-readable comparison verdict"""
        if abs(difference) < 5:
            return "About equal"
        elif difference > 50:
            return "Bonus 1 significantly better"
        elif difference > 0:
            return "Bonus 1 better"
        elif difference < -50:
            return "Bonus 2 significantly better"
        else:
            return "Bonus 2 better"

    def get_optimal_play_estimate(self, bonus_amount: float, rollover: float) -> Dict:
        """
        Estimate the "work" required to clear a bonus

        Returns estimated total wagering and time investment
        """
        if not bonus_amount or not rollover:
            return {
                'total_wagering_required': 0,
                'estimated_hours': 0,
                'feasibility': 'N/A'
            }

        total_wagering = bonus_amount * rollover

        # Assume average bet of $5 and 30 bets per hour
        avg_bet = 5
        bets_per_hour = 30

        total_bets_needed = total_wagering / avg_bet
        estimated_hours = total_bets_needed / bets_per_hour

        # Feasibility assessment
        if estimated_hours < 10:
            feasibility = 'Very Feasible'
        elif estimated_hours < 25:
            feasibility = 'Feasible'
        elif estimated_hours < 50:
            feasibility = 'Challenging'
        else:
            feasibility = 'Very Difficult'

        return {
            'total_wagering_required': round(total_wagering, 2),
            'estimated_hours': round(estimated_hours, 1),
            'feasibility': feasibility
        }

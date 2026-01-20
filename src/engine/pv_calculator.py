"""Perceived Value (PV) Calculator - The Beatability Algorithm"""
import logging
from typing import Dict, Optional
import os
from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)


class PVCalculator:
    """
    Calculates the Perceived Value (PV) score for bonuses

    The PV score determines if a bonus is mathematically "beatable" for a player.

    Formula:
        PV = (bonus_amount * bonus_weight)
             - (rollover * rollover_weight)
             + (max_withdrawal * withdrawal_weight)

    Higher PV = More beatable / valuable bonus
    """

    def __init__(
        self,
        bonus_weight: float = None,
        rollover_weight: float = None,
        withdrawal_weight: float = None
    ):
        # Load weights from environment or use defaults
        self.bonus_weight = bonus_weight or float(os.getenv('PV_BONUS_WEIGHT', 1.0))
        self.rollover_weight = rollover_weight or float(os.getenv('PV_ROLLOVER_WEIGHT', 0.5))
        self.withdrawal_weight = withdrawal_weight or float(os.getenv('PV_MAX_WITHDRAWAL_WEIGHT', 0.3))

        logger.info(
            f"PV Calculator initialized: "
            f"bonus_weight={self.bonus_weight}, "
            f"rollover_weight={self.rollover_weight}, "
            f"withdrawal_weight={self.withdrawal_weight}"
        )

    def calculate(
        self,
        bonus_amount: Optional[float],
        rollover: Optional[float] = None,
        max_withdrawal: Optional[float] = None
    ) -> Dict:
        """
        Calculate PV score for a bonus

        Returns:
            {
                'pv_score': float,
                'is_beatable': bool,
                'rating': str,  # 'Excellent', 'Good', 'Fair', 'Poor'
                'components': {
                    'bonus_contribution': float,
                    'rollover_penalty': float,
                    'withdrawal_bonus': float
                }
            }
        """
        if not bonus_amount or bonus_amount <= 0:
            return {
                'pv_score': 0.0,
                'is_beatable': False,
                'rating': 'Invalid',
                'components': {
                    'bonus_contribution': 0.0,
                    'rollover_penalty': 0.0,
                    'withdrawal_bonus': 0.0
                }
            }

        # Calculate components
        bonus_contribution = bonus_amount * self.bonus_weight

        rollover_penalty = 0.0
        if rollover and rollover > 0:
            rollover_penalty = rollover * self.rollover_weight

        withdrawal_bonus = 0.0
        if max_withdrawal and max_withdrawal > 0:
            withdrawal_bonus = max_withdrawal * self.withdrawal_weight

        # Final PV score
        pv_score = bonus_contribution - rollover_penalty + withdrawal_bonus

        # Determine beatability
        is_beatable = self._is_beatable(bonus_amount, rollover, max_withdrawal, pv_score)

        # Rating
        rating = self._get_rating(pv_score, rollover or 0)

        return {
            'pv_score': round(pv_score, 2),
            'is_beatable': is_beatable,
            'rating': rating,
            'components': {
                'bonus_contribution': round(bonus_contribution, 2),
                'rollover_penalty': round(rollover_penalty, 2),
                'withdrawal_bonus': round(withdrawal_bonus, 2)
            }
        }

    def _is_beatable(
        self,
        bonus_amount: float,
        rollover: Optional[float],
        max_withdrawal: Optional[float],
        pv_score: float
    ) -> bool:
        """
        Determine if bonus is beatable

        Criteria:
        1. PV score must be positive
        2. Rollover must be reasonable (< 50x)
        3. If max_withdrawal exists, it should be >= bonus_amount
        """
        if pv_score <= 0:
            return False

        # Rollover too high
        if rollover and rollover > 50:
            return False

        # Max withdrawal too restrictive
        if max_withdrawal and max_withdrawal < bonus_amount * 0.5:
            # Can only withdraw less than half the bonus
            return False

        return True

    def _get_rating(self, pv_score: float, rollover: float) -> str:
        """
        Get human-readable rating

        Excellent: PV > 100 and rollover < 30
        Good: PV > 50 or (PV > 0 and rollover < 40)
        Fair: PV > 0
        Poor: PV <= 0
        """
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

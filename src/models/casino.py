"""Database models for Casino Bonus Intelligence Engine"""
from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean, Enum, Index
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
import hashlib
from .database import Base


class SiteHealth(enum.Enum):
    """Health states for mirror sites"""
    ACTIVE = "active"           # Working sites checked regularly
    PURGATORY = "purgatory"     # Failed sites checked less frequently
    PRUNED = "pruned"          # Dead sites rarely checked


class MirrorSite(Base):
    """Mirror site (alternative URL for casino)"""
    __tablename__ = "mirror_sites"

    id = Column(Integer, primary_key=True, index=True)
    url = Column(String(500), unique=True, nullable=False, index=True)
    merchant_id = Column(String(100))  # Extracted from site HTML

    # Authentication tracking (Swarm Strategy)
    username = Column(String(100))  # Last successful username for this site
    alts_tried = Column(Text)  # JSON array of all usernames attempted

    # Health tracking
    health_status = Column(Enum(SiteHealth), default=SiteHealth.ACTIVE, index=True)
    consecutive_failures = Column(Integer, default=0)
    last_success = Column(DateTime)
    last_attempt = Column(DateTime)
    last_scraped = Column(DateTime)

    # Metadata
    name = Column(String(255))  # Friendly name if available
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    bonuses = relationship("Bonus", back_populates="mirror_site", cascade="all, delete-orphan")

    def __repr__(self):
        return f"<MirrorSite(url='{self.url}', health='{self.health_status.value}')>"

    def mark_success(self):
        """Mark site as successfully scraped"""
        self.health_status = SiteHealth.ACTIVE
        self.consecutive_failures = 0
        self.last_success = datetime.utcnow()
        self.last_scraped = datetime.utcnow()
        self.updated_at = datetime.utcnow()

    def mark_failure(self, threshold=5):
        """Mark site as failed and update health status"""
        self.consecutive_failures += 1
        self.last_attempt = datetime.utcnow()
        self.updated_at = datetime.utcnow()

        if self.consecutive_failures >= threshold:
            if self.health_status == SiteHealth.ACTIVE:
                self.health_status = SiteHealth.PURGATORY
            elif self.health_status == SiteHealth.PURGATORY:
                self.health_status = SiteHealth.PRUNED


class Bonus(Base):
    """Casino bonus offer with Perceived Value (PV) tracking"""
    __tablename__ = "bonuses"
    __table_args__ = (
        Index('idx_fingerprint', 'fingerprint'),
        Index('idx_pv_score', 'pv_score'),
    )

    id = Column(Integer, primary_key=True, index=True)
    mirror_site_id = Column(Integer, ForeignKey("mirror_sites.id"), nullable=False)

    # Deduplication
    fingerprint = Column(String(64), index=True)  # SHA256 hash of bonus text
    parent_bonus_id = Column(Integer, ForeignKey("bonuses.id"), nullable=True)  # For fuzzy-matched duplicates

    # Bonus details
    title = Column(String(500), nullable=False)
    description = Column(Text)
    raw_data = Column(Text)  # Original JSON/text from API

    # Financial values
    bonus_amount = Column(Float)  # Dollar amount of bonus
    currency = Column(String(10), default="USD")

    # Critical PV factors
    rollover = Column(Float)  # How many times you must bet (e.g., 35x)
    max_withdrawal = Column(Float)  # Maximum you can withdraw

    # Additional terms
    min_deposit = Column(Float)
    max_bet = Column(Float)
    time_limit_days = Column(Integer)
    game_restrictions = Column(Text)

    # Bonus code
    bonus_code = Column(String(100))
    requires_code = Column(Boolean, default=False)

    # Perceived Value (PV) Score - THE KEY METRIC
    pv_score = Column(Float, index=True)  # Calculated relative average value
    is_beatable = Column(Boolean, default=False)  # Quick flag for high relative value bonuses

    # Expiration tracking
    expiration_date = Column(DateTime)
    is_expired = Column(Boolean, default=False)
    
    # Claim tracking
    is_claimed = Column(Boolean, default=False)
    claimed_at = Column(DateTime, nullable=True)

    # Metadata
    url = Column(String(500))
    is_active = Column(Boolean, default=True)

    # Tracking
    first_seen = Column(DateTime, default=datetime.utcnow)
    last_seen = Column(DateTime, default=datetime.utcnow)
    seen_on_sites = Column(Integer, default=1)  # Number of mirror sites showing this bonus
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    mirror_site = relationship("MirrorSite", back_populates="bonuses")
    duplicates = relationship("Bonus", backref="parent_bonus", remote_side=[id])

    def __repr__(self):
        return f"<Bonus(title='{self.title[:30]}', pv={self.pv_score}, beatable={self.is_beatable})>"

    @staticmethod
    def generate_fingerprint(title: str, description: str = "") -> str:
        """Generate SHA256 fingerprint for deduplication"""
        text = f"{title}|{description}".lower().strip()
        return hashlib.sha256(text.encode()).hexdigest()

    def calculate_pv_score(self, bonus_weight=1.0, rollover_weight=0.5, withdrawal_weight=0.3):
        """
        Calculate Perceived Value (PV) - the beatability score

        Formula: PV = (bonus_amount * bonus_weight) - (rollover * rollover_weight) + (max_withdrawal * withdrawal_weight)

        Higher PV = More beatable bonus
        """
        if not self.bonus_amount:
            self.pv_score = 0.0
            self.is_beatable = False
            return

        pv = self.bonus_amount * bonus_weight

        # Penalize high rollover requirements
        if self.rollover:
            pv -= (self.rollover * rollover_weight)

        # Reward high max withdrawal limits
        if self.max_withdrawal:
            pv += (self.max_withdrawal * withdrawal_weight)

        self.pv_score = round(pv, 2)

        # Mark as beatable if PV score is positive and rollover is reasonable
        self.is_beatable = (pv > 0 and (self.rollover or 0) < 50)

    def check_expiration(self):
        """Check if bonus has expired"""
        if self.expiration_date:
            self.is_expired = datetime.utcnow() > self.expiration_date


class SessionCache(Base):
    """Session token cache (6-hour validity)"""
    __tablename__ = "session_cache"

    id = Column(Integer, primary_key=True, index=True)
    mirror_site_url = Column(String(500), unique=True, nullable=False, index=True)

    # Session credentials
    access_token = Column(String(500))
    access_id = Column(String(100))
    merchant_id = Column(String(100))

    # Session metadata
    cookies = Column(Text)  # JSON-serialized cookies
    created_at = Column(DateTime, default=datetime.utcnow)
    expires_at = Column(DateTime)  # 6 hours from creation
    is_valid = Column(Boolean, default=True)

    def __repr__(self):
        return f"<SessionCache(site='{self.mirror_site_url}', valid={self.is_valid})>"

    def is_expired(self) -> bool:
        """Check if session is expired"""
        return datetime.utcnow() > self.expires_at if self.expires_at else True


class WorkerLog(Base):
    """Individual worker activity log"""
    __tablename__ = "worker_logs"

    id = Column(Integer, primary_key=True, index=True)
    worker_id = Column(Integer, index=True)
    mirror_site_url = Column(String(500))

    # Worker activity
    action = Column(String(100))  # "login", "api_call", "parsing", etc.
    status = Column(String(50))  # "success", "failed", "retrying"
    error_message = Column(Text)
    proxy_used = Column(String(100))

    # Timing
    timestamp = Column(DateTime, default=datetime.utcnow)
    duration_ms = Column(Float)

    def __repr__(self):
        return f"<WorkerLog(worker={self.worker_id}, action='{self.action}', status='{self.status}')>"


class ScrapeRun(Base):
    """Complete scrape run cycle"""
    __tablename__ = "scrape_runs"

    id = Column(Integer, primary_key=True, index=True)
    run_number = Column(Integer, index=True)  # Sequential run counter
    run_type = Column(String(50))  # "standard", "retest", "resurrection"

    # Statistics
    sites_checked = Column(Integer, default=0)
    sites_successful = Column(Integer, default=0)
    sites_failed = Column(Integer, default=0)
    bonuses_found = Column(Integer, default=0)
    bonuses_new = Column(Integer, default=0)
    bonuses_updated = Column(Integer, default=0)
    bonuses_deduped = Column(Integer, default=0)

    # Timing
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime)
    duration_seconds = Column(Float)

    # Errors
    errors = Column(Text)  # JSON list of errors

    def __repr__(self):
        return f"<ScrapeRun(#{self.run_number}, type='{self.run_type}', bonuses={self.bonuses_found})>"

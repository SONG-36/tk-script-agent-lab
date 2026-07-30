from enum import StrEnum


class VerificationStatus(StrEnum):
    VERIFIED = "VERIFIED"
    UNVERIFIED = "UNVERIFIED"
    REJECTED = "REJECTED"


class ReferencePlatform(StrEnum):
    TIKTOK = "TIKTOK"
    AMAZON = "AMAZON"
    YOUTUBE = "YOUTUBE"
    LOCAL = "LOCAL"
    OTHER = "OTHER"


class InsightType(StrEnum):
    HOOK = "HOOK"
    STRUCTURE = "STRUCTURE"
    SCENE = "SCENE"
    ACTION = "ACTION"
    PACING = "PACING"
    VOICEOVER = "VOICEOVER"
    CAPTION = "CAPTION"
    CTA = "CTA"
    OTHER = "OTHER"


class ReviewDecisionType(StrEnum):
    PENDING = "PENDING"
    APPROVED = "APPROVED"
    REJECTED = "REJECTED"
    REVISION_REQUIRED = "REVISION_REQUIRED"

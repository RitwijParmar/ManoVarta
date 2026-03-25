from django.db import models


class LanguageChoice(models.TextChoices):
    ENGLISH = "en", "English"
    HINDI = "hi", "Hindi"
    HINGLISH = "hinglish", "Hinglish"


class SpeakerChoice(models.TextChoices):
    ASSISTANT = "assistant", "Assistant"
    USER = "user", "User"


class ReviewStatus(models.TextChoices):
    DRAFT = "draft", "Draft"
    DOUBLE_ANNOTATED = "double_annotated", "Double annotated"
    CONSENSUS_FINAL = "consensus_final", "Consensus final"


class SafetyLevel(models.TextChoices):
    NONE = "none", "None"
    REVIEW = "review", "Review"
    URGENT = "urgent", "Urgent"


class PatientProfile(models.Model):
    patient_id = models.CharField(max_length=40, unique=True)
    preferred_language = models.CharField(max_length=12, choices=LanguageChoice.choices)
    age = models.PositiveIntegerField()
    occupation = models.CharField(max_length=120)
    disclosure_style = models.CharField(max_length=80, blank=True)
    background_profile = models.JSONField(default=dict, blank=True)
    symptom_profile = models.JSONField(default=dict, blank=True)
    nuance_tags = models.JSONField(default=list, blank=True)
    notes = models.TextField(blank=True)

    class Meta:
        ordering = ["patient_id"]

    def __str__(self) -> str:
        return f"{self.patient_id} ({self.preferred_language})"


class Conversation(models.Model):
    conversation_id = models.CharField(max_length=40, unique=True)
    patient = models.ForeignKey(PatientProfile, null=True, blank=True, on_delete=models.SET_NULL, related_name="conversations")
    language = models.CharField(max_length=12, choices=LanguageChoice.choices)
    occupation = models.CharField(max_length=120, blank=True)
    generation_source = models.CharField(max_length=80, default="synthetic_profile_guided")
    review_status = models.CharField(max_length=24, choices=ReviewStatus.choices, default=ReviewStatus.DRAFT)
    background_profile = models.JSONField(default=dict, blank=True)
    symptom_profile = models.JSONField(default=dict, blank=True)
    annotator_notes = models.TextField(blank=True)
    confidence_notes = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["conversation_id"]

    def __str__(self) -> str:
        return self.conversation_id


class Turn(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="turns")
    turn_id = models.PositiveIntegerField()
    speaker = models.CharField(max_length=12, choices=SpeakerChoice.choices)
    text = models.TextField()
    language_tag = models.CharField(max_length=12, choices=LanguageChoice.choices)
    notes = models.CharField(max_length=255, blank=True)

    class Meta:
        ordering = ["conversation", "turn_id"]
        unique_together = ("conversation", "turn_id")

    def __str__(self) -> str:
        return f"{self.conversation.conversation_id} turn {self.turn_id}"


class EvidenceSpan(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name="evidence_spans")
    turn = models.ForeignKey(Turn, on_delete=models.CASCADE, related_name="evidence_spans")
    span_id = models.CharField(max_length=40)
    questionnaire = models.CharField(max_length=8)
    item_id = models.CharField(max_length=64)
    text_span = models.TextField()
    polarity = models.CharField(max_length=12)
    score_hint = models.PositiveSmallIntegerField()
    annotator = models.CharField(max_length=80, blank=True)
    rationale = models.TextField(blank=True)

    class Meta:
        ordering = ["conversation", "turn", "span_id"]

    def __str__(self) -> str:
        return f"{self.span_id} - {self.item_id}"


class AssessmentSnapshot(models.Model):
    conversation = models.OneToOneField(Conversation, on_delete=models.CASCADE, related_name="assessment_snapshot")
    item_scores = models.JSONField(default=dict, blank=True)
    phq9_labels = models.JSONField(default=dict, blank=True)
    gad7_labels = models.JSONField(default=dict, blank=True)
    totals = models.JSONField(default=dict, blank=True)
    unresolved_items = models.JSONField(default=list, blank=True)

    def __str__(self) -> str:
        return f"Assessment for {self.conversation.conversation_id}"


class SafetyReview(models.Model):
    conversation = models.OneToOneField(Conversation, on_delete=models.CASCADE, related_name="safety_review")
    level = models.CharField(max_length=12, choices=SafetyLevel.choices, default=SafetyLevel.NONE)
    cues = models.JSONField(default=list, blank=True)
    action_note = models.TextField(blank=True)
    needs_human_review = models.BooleanField(default=False)

    def __str__(self) -> str:
        return f"Safety {self.level} for {self.conversation.conversation_id}"

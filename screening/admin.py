from django.contrib import admin

from screening.models import AssessmentSnapshot, Conversation, EvidenceSpan, PatientProfile, SafetyReview, Turn


class TurnInline(admin.TabularInline):
    model = Turn
    extra = 0
    ordering = ("turn_id",)


class EvidenceSpanInline(admin.TabularInline):
    model = EvidenceSpan
    extra = 0


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("patient_id", "preferred_language", "age", "occupation", "disclosure_style")
    list_filter = ("preferred_language", "disclosure_style")
    search_fields = ("patient_id", "occupation")


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = ("conversation_id", "language", "generation_source", "review_status", "updated_at")
    list_filter = ("language", "review_status", "generation_source")
    search_fields = ("conversation_id", "annotator_notes")
    inlines = [TurnInline, EvidenceSpanInline]


@admin.register(AssessmentSnapshot)
class AssessmentSnapshotAdmin(admin.ModelAdmin):
    list_display = ("conversation",)


@admin.register(SafetyReview)
class SafetyReviewAdmin(admin.ModelAdmin):
    list_display = ("conversation", "level", "needs_human_review")
    list_filter = ("level", "needs_human_review")

from django.contrib import admin

from screening.models import AssessmentSnapshot, Conversation, EvidenceSpan, PatientProfile, SafetyReview, Turn


class TurnInline(admin.TabularInline):
    model = Turn
    extra = 0
    ordering = ("turn_id",)


class EvidenceSpanInline(admin.TabularInline):
    model = EvidenceSpan
    extra = 0


class SafetyReviewInline(admin.StackedInline):
    model = SafetyReview
    extra = 0


class AssessmentSnapshotInline(admin.StackedInline):
    model = AssessmentSnapshot
    extra = 0


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = ("patient_id", "preferred_language", "age", "occupation", "disclosure_style", "nuance_count")
    list_filter = ("preferred_language", "disclosure_style")
    search_fields = ("patient_id", "occupation", "notes")

    def nuance_count(self, obj):
        return len(obj.nuance_tags or [])


@admin.register(Conversation)
class ConversationAdmin(admin.ModelAdmin):
    list_display = (
        "conversation_id",
        "patient",
        "language",
        "review_status",
        "safety_level",
        "evidence_count",
        "updated_at",
    )
    list_filter = ("language", "review_status", "generation_source")
    search_fields = ("conversation_id", "annotator_notes", "patient__patient_id", "occupation")
    autocomplete_fields = ("patient",)
    inlines = [TurnInline, EvidenceSpanInline, SafetyReviewInline, AssessmentSnapshotInline]
    actions = ("mark_double_annotated", "mark_consensus_final")

    @admin.display(ordering="safety_review__level")
    def safety_level(self, obj):
        if hasattr(obj, "safety_review"):
            return obj.safety_review.level
        return "none"

    @admin.display(ordering="evidence_spans")
    def evidence_count(self, obj):
        return obj.evidence_spans.count()

    @admin.action(description="Mark selected conversations as double annotated")
    def mark_double_annotated(self, request, queryset):
        queryset.update(review_status="double_annotated")

    @admin.action(description="Mark selected conversations as consensus final")
    def mark_consensus_final(self, request, queryset):
        queryset.update(review_status="consensus_final")


@admin.register(AssessmentSnapshot)
class AssessmentSnapshotAdmin(admin.ModelAdmin):
    list_display = ("conversation", "phq_total", "gad_total", "unresolved_count")
    search_fields = ("conversation__conversation_id",)

    def phq_total(self, obj):
        return obj.totals.get("PHQ9", 0)

    def gad_total(self, obj):
        return obj.totals.get("GAD7", 0)

    def unresolved_count(self, obj):
        return len(obj.unresolved_items or [])


@admin.register(SafetyReview)
class SafetyReviewAdmin(admin.ModelAdmin):
    list_display = ("conversation", "level", "needs_human_review")
    list_filter = ("level", "needs_human_review")
    search_fields = ("conversation__conversation_id", "action_note")


@admin.register(EvidenceSpan)
class EvidenceSpanAdmin(admin.ModelAdmin):
    list_display = ("span_id", "conversation", "item_id", "questionnaire", "score_hint", "annotator")
    list_filter = ("questionnaire", "polarity", "annotator")
    search_fields = ("span_id", "conversation__conversation_id", "text_span", "item_id")


@admin.register(Turn)
class TurnAdmin(admin.ModelAdmin):
    list_display = ("conversation", "turn_id", "speaker", "language_tag")
    list_filter = ("speaker", "language_tag")
    search_fields = ("conversation__conversation_id", "text")

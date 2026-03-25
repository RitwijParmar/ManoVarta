from django.core.management.base import BaseCommand

from manovarta_core.safety import SafetyMonitor
from manovarta_core.scoring import ConversationScorer
from manovarta_core.schemas import Turn as RuntimeTurn
from screening.models import AssessmentSnapshot, Conversation, SafetyReview


class Command(BaseCommand):
    help = "Recompute item scores and safety flags from stored conversation turns."

    def handle(self, *args, **options):
        scorer = ConversationScorer()
        safety_monitor = SafetyMonitor()

        for conversation in Conversation.objects.prefetch_related("turns").all():
            runtime_turns = [
                RuntimeTurn(
                    turn_id=turn.turn_id,
                    speaker=turn.speaker,
                    text=turn.text,
                    language_tag=turn.language_tag,
                    notes=turn.notes or None,
                )
                for turn in conversation.turns.order_by("turn_id")
            ]
            safety_flag = safety_monitor.assess(runtime_turns)
            snapshot = scorer.analyze(runtime_turns, conversation.language, safety_flag)

            AssessmentSnapshot.objects.update_or_create(
                conversation=conversation,
                defaults={
                    "item_scores": {item_id: score.value for item_id, score in snapshot.items.items()},
                    "phq9_labels": {
                        item_id: score.value
                        for item_id, score in snapshot.items.items()
                        if score.questionnaire == "PHQ9"
                    },
                    "gad7_labels": {
                        item_id: score.value
                        for item_id, score in snapshot.items.items()
                        if score.questionnaire == "GAD7"
                    },
                    "totals": snapshot.totals,
                    "unresolved_items": snapshot.unresolved_items,
                },
            )
            SafetyReview.objects.update_or_create(
                conversation=conversation,
                defaults={
                    "level": snapshot.safety.level,
                    "cues": snapshot.safety.cues,
                    "action_note": snapshot.safety.rationale or "",
                    "needs_human_review": snapshot.safety.needs_human_review,
                },
            )

        self.stdout.write(self.style.SUCCESS("Conversation snapshots rebuilt."))

from django.core.management.base import BaseCommand

from manovarta_core.profiles import load_seed_conversations, load_seed_profiles
from screening.models import AssessmentSnapshot, Conversation, EvidenceSpan, PatientProfile, SafetyReview, Turn


class Command(BaseCommand):
    help = "Load seed patient profiles and annotated conversations."

    def handle(self, *args, **options):
        profile_index = {}
        for profile in load_seed_profiles():
            obj, _ = PatientProfile.objects.update_or_create(
                patient_id=profile["patient_id"],
                defaults={
                    "preferred_language": profile["language"],
                    "age": profile["age"],
                    "occupation": profile["occupation"],
                    "disclosure_style": profile.get("disclosure_style", ""),
                    "background_profile": profile.get("background_profile", {}),
                    "symptom_profile": profile.get("symptom_profile", {}),
                    "nuance_tags": profile.get("nuance_tags", []),
                    "notes": profile.get("notes", ""),
                },
            )
            profile_index[obj.patient_id] = obj

        for payload in load_seed_conversations():
            conversation, _ = Conversation.objects.update_or_create(
                conversation_id=payload["conversation_id"],
                defaults={
                    "patient": profile_index.get(payload.get("patient_id")),
                    "language": payload["language"],
                    "occupation": payload.get("occupation", ""),
                    "generation_source": payload.get("generation_source", "synthetic_profile_guided"),
                    "review_status": payload.get("review_status", "draft"),
                    "background_profile": payload.get("background_profile", {}),
                    "symptom_profile": payload.get("symptom_profile", {}),
                    "annotator_notes": payload.get("annotator_notes", ""),
                    "confidence_notes": payload.get("confidence_notes", {}),
                },
            )
            conversation.turns.all().delete()
            conversation.evidence_spans.all().delete()

            turn_index = {}
            for turn in payload.get("conversation_turns", []):
                turn_obj = Turn.objects.create(
                    conversation=conversation,
                    turn_id=turn["turn_id"],
                    speaker=turn["speaker"],
                    text=turn["text"],
                    language_tag=turn["language_tag"],
                    notes=turn.get("notes", ""),
                )
                turn_index[turn_obj.turn_id] = turn_obj

            for span in payload.get("evidence_spans", []):
                EvidenceSpan.objects.create(
                    conversation=conversation,
                    turn=turn_index[span["turn_id"]],
                    span_id=span["span_id"],
                    questionnaire=span["questionnaire"],
                    item_id=span["item_id"],
                    text_span=span["text_span"],
                    polarity=span["polarity"],
                    score_hint=span["score_hint"],
                    annotator=span.get("annotator", ""),
                    rationale=span.get("rationale", ""),
                )

            item_scores = {}
            item_scores.update(payload.get("phq9_item_labels", {}))
            item_scores.update(payload.get("gad7_item_labels", {}))
            AssessmentSnapshot.objects.update_or_create(
                conversation=conversation,
                defaults={
                    "item_scores": item_scores,
                    "phq9_labels": payload.get("phq9_item_labels", {}),
                    "gad7_labels": payload.get("gad7_item_labels", {}),
                    "totals": {
                        "PHQ9": sum(payload.get("phq9_item_labels", {}).values()),
                        "GAD7": sum(payload.get("gad7_item_labels", {}).values()),
                    },
                    "unresolved_items": payload.get("confidence_notes", {}).get("low_confidence_items", []),
                },
            )
            safety_flag = payload.get("safety_flag", {})
            SafetyReview.objects.update_or_create(
                conversation=conversation,
                defaults={
                    "level": safety_flag.get("level", "none"),
                    "cues": safety_flag.get("cues", []),
                    "action_note": safety_flag.get("action_note", ""),
                    "needs_human_review": safety_flag.get("level", "none") != "none",
                },
            )

        self.stdout.write(self.style.SUCCESS("Seed data loaded."))

from argparse import Namespace

from tools.run_vertex_aya_continue import (
    build_worker_args,
    default_output_root,
    default_training_container,
    join_gcs_uri,
    normalize_bucket_uri,
    parse_gcs_uri,
    region_group,
)


def test_normalize_bucket_uri_accepts_plain_bucket_name():
    assert normalize_bucket_uri("my-vertex-bucket") == "gs://my-vertex-bucket"


def test_normalize_bucket_uri_rejects_paths():
    try:
        normalize_bucket_uri("gs://my-vertex-bucket/path")
    except ValueError as exc:
        assert "must not include a path" in str(exc)
    else:  # pragma: no cover
        raise AssertionError("Expected normalize_bucket_uri to reject path prefixes")


def test_parse_and_join_gcs_uri_round_trip():
    uri = join_gcs_uri("gs://demo-bucket", "manovarta", "vertex-runs", "job-1")
    assert uri == "gs://demo-bucket/manovarta/vertex-runs/job-1"
    assert parse_gcs_uri(uri) == ("demo-bucket", "manovarta/vertex-runs/job-1")


def test_default_output_root_uses_display_name_under_default_prefix():
    assert default_output_root("gs://demo-bucket", "job-1") == "gs://demo-bucket/manovarta/vertex-runs/job-1"


def test_default_training_container_tracks_region_group():
    assert region_group("us-central1") == "us"
    assert region_group("europe-west4") == "europe"
    assert region_group("asia-south1") == "asia"
    assert default_training_container("us-central1").startswith("us-docker.pkg.dev/")


def test_build_worker_args_carries_core_settings():
    args = Namespace(
        extractor_model="CohereLabs/aya-expanse-8b",
        extractor_epochs=1,
        extractor_batch_size=2,
        extractor_grad_accum=16,
        extractor_max_length=2048,
        extractor_save_steps=20,
        extractor_max_new_tokens=800,
        smoke_limit=6,
        disable_extractor_4bit=False,
    )

    worker_args = build_worker_args(
        args,
        "gs://demo-bucket/daic",
        "gs://demo-bucket/init_adapter",
        "gs://demo-bucket/output-root",
    )

    assert "--daic-root" in worker_args
    assert "gs://demo-bucket/daic" in worker_args
    assert "--init-adapter" in worker_args
    assert "gs://demo-bucket/init_adapter" in worker_args
    assert "--gcs-output-root" in worker_args
    assert "gs://demo-bucket/output-root" in worker_args
    assert "--disable-extractor-4bit" not in worker_args


def test_build_worker_args_can_disable_4bit():
    args = Namespace(
        extractor_model="CohereLabs/aya-expanse-8b",
        extractor_epochs=1,
        extractor_batch_size=1,
        extractor_grad_accum=8,
        extractor_max_length=1536,
        extractor_save_steps=10,
        extractor_max_new_tokens=900,
        smoke_limit=8,
        disable_extractor_4bit=True,
    )

    worker_args = build_worker_args(
        args,
        "gs://demo-bucket/daic",
        "gs://demo-bucket/init_adapter",
        "gs://demo-bucket/output-root",
    )

    assert "--disable-extractor-4bit" in worker_args

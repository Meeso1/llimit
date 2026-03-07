"""Functions for loading and converting the GAIA benchmark dataset."""
from datasets import load_dataset
from huggingface_hub import snapshot_download

from evaluation.gaia.models import GaiaAnnotatorMetadata, GaiaConfig, GaiaSample, GaiaSplit


def load_gaia(
    config: GaiaConfig = "2023_level1",
    split: GaiaSplit = "validation",
) -> tuple[list[GaiaSample], str]:
    """Load the GAIA dataset and return typed samples along with the local data directory."""
    data_dir = snapshot_download(repo_id="gaia-benchmark/GAIA", repo_type="dataset")
    dataset = load_dataset(data_dir, config, split=split)
    samples = [_convert_sample(dict(row)) for row in dataset]
    return samples, data_dir


def _convert_sample(raw: dict) -> GaiaSample:
    """Convert a raw dataset row into a typed GaiaSample."""
    meta: dict = raw.get("Annotator Metadata") or {}

    def _int(value: str | None) -> int:
        try:
            return int(value or "0")
        except ValueError:
            return 0

    return GaiaSample(
        task_id=raw["task_id"],
        question=raw["Question"],
        level=raw["Level"],
        final_answer=raw["Final answer"],
        file_name=raw["file_name"] or None,
        file_path=raw["file_path"] or None,
        annotator_metadata=GaiaAnnotatorMetadata(
            steps=meta.get("Steps", ""),
            number_of_steps=_int(meta.get("Number of steps")),
            time_taken=meta.get("How long did this take?", ""),
            tools=meta.get("Tools", ""),
            number_of_tools=_int(meta.get("Number of tools")),
        ),
    )

"""Typed representations of GAIA benchmark dataset samples."""
from dataclasses import dataclass
from typing import Literal

from evaluation.gaia.tools import GaiaTool


GaiaLevel = Literal["1", "2", "3"]
GaiaConfig = Literal["2023_level1", "2023_level2", "2023_level3"]
GaiaSplit = Literal["validation", "test"]


@dataclass
class GaiaAnnotatorMetadata:
    """Metadata provided by human annotators for a GAIA sample."""

    steps: str
    number_of_steps: int
    time_taken: str
    tools: list[GaiaTool]
    number_of_tools: int


@dataclass
class GaiaSample:
    """A single sample from the GAIA benchmark dataset."""

    task_id: str
    question: str
    level: GaiaLevel
    final_answer: str
    file_name: str | None
    file_path: str | None
    annotator_metadata: GaiaAnnotatorMetadata

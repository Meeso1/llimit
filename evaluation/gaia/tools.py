"""Capability taxonomy for GAIA benchmark tasks.

Defines the canonical GaiaTool type, the mapping from raw annotator strings to canonical
values, per-task overrides for cases where annotations are ambiguous, and the parse_tools()
helper used by the dataset loader.
"""
import re
from typing import Literal


GaiaTool = Literal[
    "web_search",           # web browsing and/or search engine access
    "web_file_download",    # downloading an arbitrary file from a URL (may be blocked by providers)
    "calculator",
    "image_input",          # reading / interpreting an image file
    "pdf_input",            # reading a PDF file
    "excel_input",          # reading a spreadsheet file
    "powerpoint_input",     # reading a PowerPoint file
    "audio_input",          # listening to / transcribing an audio file
    "video_input",          # watching a locally-provided video file
    "youtube",              # accessing a YouTube video by URL or by name
    "python",               # executing code (Python, C++, etc.)
    "text_file_input",      # reading a plain-text or structured-text file (txt, docx, xml, jsonld…)
    "google_maps",
    "none",
    "other",                # catch-all for unrecognised raw strings
]

# Maps normalised raw tool strings (lowercase, no trailing punctuation) to canonical GaiaTool values.
# Keys are the raw annotator strings after lowercasing and stripping leading numbering / trailing ".".
_TOOL_CANONICAL_MAP: dict[str, GaiaTool] = {
    # web browser — same capability as search engine for an LLM agent
    "a web browser": "web_search",
    "(optional) web browser": "web_search",
    "web browser": "web_search",
    # search / reference — merged with web_browser
    "a search engine": "web_search",
    "(optional) search engine": "web_search",
    "search engine": "web_search",
    "google search": "web_search",
    "access to wikipedia": "web_search",
    "wikipedia": "web_search",
    "access to the internet archive, web.archive.org": "web_search",
    "access to academic journal websites": "web_search",
    # google_translate is just a website; browsable via web_search
    "google translate access": "web_search",
    # graph interaction on Connected Papers is browsable via web_search
    "graph interaction tools": "web_search",
    # cuneiform number system lookup, answerable via web search or model knowledge
    "bablyonian cuniform -> arabic legend": "web_search",
    # calculator
    "a calculator": "calculator",
    "calculator": "calculator",
    "calculator (or ability to count)": "calculator",
    "calculator (or use excel)": "calculator",
    "calculator or counting function": "calculator",
    "counter": "calculator",
    "computer algebra system": "calculator",    # numerical iteration, no code execution needed
    # image input / OCR
    "color recognition": "image_input",
    "computer vision": "image_input",
    "computer vision or ocr": "image_input",
    "gif parsing tools": "image_input",
    "image processing tools": "image_input",
    "image recognition": "image_input",
    "image recognition and processing tools": "image_input",
    "image recognition software": "image_input",
    "image recognition tools": "image_input",
    "image recognition tools (to identify and parse a figure with three axes)": "image_input",
    "image recognition/ocr": "image_input",
    "image search tools": "image_input",
    "ocr": "image_input",
    "tool to extract text from images": "image_input",
    "bass note data": "image_input",            # reading sheet music notation from an image
    # excel / spreadsheet input
    "access to excel files": "excel_input",
    "csv file access": "excel_input",
    "excel": "excel_input",
    "excel file access": "excel_input",
    "microsoft excel": "excel_input",
    "microsoft excel / google sheets": "excel_input",
    "spreadsheet editor": "excel_input",
    "xlsx file access": "excel_input",
    # pdf input
    "pdf access": "pdf_input",
    "pdf reader": "pdf_input",
    "pdf reader/extracter": "pdf_input",
    "pdf viewer": "pdf_input",
    # audio input (transcription / listening — no audio editing required)
    "a speech-to-text audio processing tool": "audio_input",
    "a speech-to-text tool": "audio_input",
    "audio capability": "audio_input",
    "audio processing software": "audio_input",
    # video input (locally-provided video file — not YouTube)
    "video capability": "video_input",
    "video parsing": "video_input",
    "video processing software": "video_input",
    "video recognition tools": "video_input",
    # youtube
    "access to youtube": "youtube",
    "youtube": "youtube",
    "youtube player": "youtube",
    # python / code execution
    "a python ide": "python",
    "c++ compiler": "python",
    "code/data analysis tools": "python",
    "file handling": "python",                  # programmatic file manipulation, always paired with python tasks
    "python": "python",
    "python compiler": "python",
    # plain-text / structured-text file input (reading only, no editing)
    "jsonld file access": "text_file_input",
    "markdown": "text_file_input",
    "text editor": "text_file_input",
    "word document access": "text_file_input",
    "xml file access": "text_file_input",
    # downloading a specific file from a URL — distinct from general web browsing
    "a file interface": "web_file_download",
    # powerpoint input
    "powerpoint viewer": "powerpoint_input",
    # maps
    "access to google maps": "google_maps",
    "google maps": "google_maps",
    # none / trivial — tasks solvable by the model itself without external tools
    "a word reversal tool / script": "none",    # reversing a string is trivial for any LLM
    "natural language processor": "none",       # tasks annotated this way are answered via web browsing
    "rubik's cube model": "none",               # pure spatial-reasoning puzzle, no external tool needed
    "text processing/diff tool": "none",        # comparing two pieces of text, no external tool needed
    "unlambda compiler (optional)": "none",     # optional tool; syntax can be looked up
    "no tools required": "none",
    "none": "none",
}


# Per-task capability overrides. These replace the annotator-inferred tool list entirely
# for tasks where the annotation label is shared across wildly different actual requirements,
# or where the annotation missed a capability that is clearly needed by the question.
GAIA_TASK_TOOL_OVERRIDES: dict[str, list[GaiaTool]] = {
    # Boggle solver: the question explicitly points to a word list at a GitHub URL that must be
    # downloaded as a raw file. The annotator used "a file interface" but that label is too vague;
    # the real requirement is fetching an arbitrary file from the internet.
    "851e570a-e3de-4d84-bcfa-cc85578baa59": ["web_file_download", "python", "web_search"],
    # Python→C++: a Python script (embedded in an attached image) outputs a URL. The agent must
    # download C++ source code from that URL and compile/run it — pure file download from a dynamic
    # URL, not general web browsing. The annotator listed "File handling" (→ python) but missed
    # that the file lives at an internet URL produced at runtime.
    "b7f857e4-d8aa-4387-af2a-0e844df5b9d8": ["web_file_download", "python", "image_input"],
    # Merriam-Webster Word of the Day lookup: annotated with "audio capability" but the question
    # asks about a quoted writer on a web page — no audio file or audio processing involved.
    "5188369a-3bbe-43d8-8b94-11558f909a08": ["web_search"],
    # Markdown table in question body: "markdown" annotation referred to the question format,
    # not a file to be opened — no external tool is needed.
    "6f37996b-2ac7-44b0-8e68-6d28256631b4": ["none"],
    # YouTube tasks annotated as "video_processing" / "audio_processing" + "web_browser" instead
    # of "youtube". All of the following require watching a specific YouTube video.
    "a1e91b78-d3d8-4675-bb8d-62741b4b68a6": ["youtube"],
    "9d191bce-651d-4746-be2d-7ef8ecadb9c2": ["youtube"],
    "0383a3ee-47a7-41a4-b493-519bdefe0488": ["youtube", "web_search"],   # BBC Earth YouTube video
    "8b3379c0-0981-4f5b-8407-6444610cb212": ["youtube", "web_search"],   # Nat Geo YouTube short
    "00d579ea-0889-4fd9-a771-2c8d79835c8d": ["youtube", "web_search"],   # The Thinking Machine YouTube
    "0512426f-4d28-49f0-be77-06d05daec096": ["youtube", "audio_input"],  # YouTube 360 VR with narration
}


def parse_tools(raw: str) -> list[GaiaTool]:
    """Parse a raw annotator tools string into a list of canonical GaiaTool values."""
    tools: list[GaiaTool] = []
    for line in raw.strip().splitlines():
        line = re.sub(r"^\d+\.\s*", "", line).strip().rstrip(".")
        if not line:
            continue
        canonical = _TOOL_CANONICAL_MAP.get(line.lower(), "other")
        tools.append(canonical)
    return tools or ["none"]

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
UPLOADS_DIR = DATA_DIR / "uploads"
DB_PATH = DATA_DIR / "academic_assistant.db"

# Ensure directories exist
DATA_DIR.mkdir(parents=True, exist_ok=True)
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)

# Project Information
PROJECT_INFO = {
    "title": "AI Academic Assistant: Intelligent PDF Analysis and Scheme-Based Answer Generation",
    "description": "Intelligent academic question answering, rubrics calculation, and student evaluation engine."
}

# Marking Scheme Specifications according to standard academic guidelines
MARK_SCHEMES = {
    2: {
        "label": "2 Marks (Short Answer)",
        "expected_length": "30 - 60 words (3-5 sentences / bullet points)",
        "breakdown": [
            {"component": "Crisp Definition / Statement / Principle", "marks": 1.0},
            {"component": "Key Feature, Formula, or Standard Example", "marks": 1.0}
        ],
        "diagram_required": False,
        "description": "Precise, conceptual definition or core equation without unnecessary filler."
    },
    5: {
        "label": "5 Marks (Medium Answer)",
        "expected_length": "120 - 200 words (structured paragraphs or 4-6 points)",
        "breakdown": [
            {"component": "Introduction & Definition", "marks": 1.0},
            {"component": "Core Explanation / Working Principle (3-4 points)", "marks": 2.5},
            {"component": "Schematic / Syntax / Formula / Example", "marks": 1.5}
        ],
        "diagram_required": "Optional / Recommended if architectural or schematic",
        "description": "Structured explanation covering fundamentals, working, and a relevant example or simple block diagram."
    },
    10: {
        "label": "10 Marks (Long Answer)",
        "expected_length": "350 - 550 words (comprehensive technical essay)",
        "breakdown": [
            {"component": "Introduction & Conceptual Background", "marks": 1.5},
            {"component": "Neat Labeled Diagram / Architecture / Flowchart", "marks": 3.0},
            {"component": "Detailed Working / Algorithm / Derivation / Mechanism", "marks": 3.5},
            {"component": "Real-world Example, Pros/Cons or Complexity Analysis", "marks": 2.0}
        ],
        "diagram_required": True,
        "description": "Comprehensive academic answer with neat labeled diagram, in-depth technical explanation, and analytical insights."
    },
    15: {
        "label": "15 Marks (Comprehensive / Essay Answer)",
        "expected_length": "600 - 900 words (thorough multi-section treatise)",
        "breakdown": [
            {"component": "Introduction & Theoretical Foundation", "marks": 2.0},
            {"component": "Comprehensive Architecture & Labeled Diagram", "marks": 4.0},
            {"component": "In-depth Component Analysis & Operation Workflow", "marks": 5.0},
            {"component": "Mathematical Formulation / Algorithm & Code / Case Study", "marks": 2.5},
            {"component": "Comparison Table, Advantages, Limitations & Summary", "marks": 1.5}
        ],
        "diagram_required": True,
        "description": "Exhaustive multi-part answer for full-module coverage, rigorous diagrams, algorithms, and comparative analysis."
    }
}

# Supported LLM Models
GEMINI_MODELS = [
    "gemini-2.5-flash",
    "gemini-2.5-pro",
    "gemini-1.5-flash"
]

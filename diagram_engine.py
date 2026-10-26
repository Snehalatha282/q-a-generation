import re
from typing import Dict, Any, Optional, Tuple

class DiagramEngine:
    """
    Programmatic diagram generation engine.
    Supports Mermaid.js, SVG rendering, and ASCII diagrams for academic answers.
    """

    EXPLICIT_DIAGRAM_PATTERNS = [
        r'\bdiagrams?\b',
        r'\bflow\s*charts?\b',
        r'\bschematics?\b',
        r'\barchitectures?\b',
        r'\bblock\s*diagrams?\b',
        r'\bdraw\b',
        r'\bdrawing\b',
        r'\bsketch(?:es)?\b',
        r'\bstate\s*transition\s*diagrams?\b',
        r'\bsequence\s*diagrams?\b',
        r'\btiming\s*diagrams?\b',
        r'\bcircuit\s*diagrams?\b',
        r'\bgraphical\s*representation\b',
        r'\billustrate\s+(?:it\s+)?with\s+(?:a\s+)?diagram\b',
        r'\bdiagrammatic(?:ally)?\b'
    ]

    NEGATIVE_DIAGRAM_PATTERNS = [
        r'\bwithout\s+(?:any\s+)?diagrams?\b',
        r'\bno\s+diagrams?\b',
        r'\bexclude\s+diagrams?\b',
        r'\bdo\s+not\s+draw\b',
        r'\bwithout\s+(?:a\s+)?sketch\b',
        r'\bpurely\s+theoretical(?:ly)?\b'
    ]

    @classmethod
    def should_include_diagram(cls, question: str, marks: int = 10, forced: bool = False) -> bool:
        """
        Determines if a diagram is strictly required according to the question.
        Returns True ONLY if the question explicitly asks for a diagram, schematic,
        flowchart, architecture, or drawing. If not requested, returns False.
        """
        if forced:
            return True

        if not question or not question.strip():
            return False

        q_lower = question.lower().strip()

        # Check for explicit negative indicators (e.g., 'without diagram')
        for neg_pat in cls.NEGATIVE_DIAGRAM_PATTERNS:
            if re.search(neg_pat, q_lower):
                return False

        # Check if question explicitly requests a diagram, architecture, or drawing
        for pat in cls.EXPLICIT_DIAGRAM_PATTERNS:
            if re.search(pat, q_lower):
                return True

        # If the question does not ask for a diagram, do not require any diagram
        return False

    @classmethod
    def sanitize_mermaid_code(cls, code: str) -> str:
        """Cleans and validates Mermaid.js code strings to prevent syntax crashes."""
        if not code:
            return ""

        # Remove markdown fences if model returned them
        code = re.sub(r"^```(?:mermaid)?", "", code, flags=re.MULTILINE)
        code = re.sub(r"```$", "", code, flags=re.MULTILINE).strip()

        # Ensure it has a valid Mermaid header
        valid_headers = ["graph", "flowchart", "sequenceDiagram", "classDiagram", "stateDiagram", "erDiagram", "gantt", "pie"]
        has_valid_header = any(code.strip().startswith(h) for h in valid_headers)

        if not has_valid_header:
            # Default to flowchart TD
            code = f"flowchart TD\n{code}"

        # Fix unescaped brackets inside labels
        # e.g., A[Process (P1)] -> A["Process (P1)"]
        code = re.sub(r'\[([^"\]\n]*\([^\)\n]*\)[^"\]\n]*)\]', r'["\1"]', code)

        return code

    @classmethod
    def generate_html_embed(cls, mermaid_code: str, title: str = "Academic Concept Diagram") -> str:
        """Generates an embeddable HTML snippet containing Mermaid.js with clean styling."""
        clean_code = cls.sanitize_mermaid_code(mermaid_code)
        
        # HTML template with Mermaid.js CDN
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
            <style>
                body {{
                    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
                    background: transparent;
                    margin: 0;
                    padding: 12px;
                    display: flex;
                    flex-direction: column;
                    align-items: center;
                }}
                .diagram-card {{
                    background: #ffffff;
                    border: 1px solid #e2e8f0;
                    border-radius: 12px;
                    padding: 18px;
                    width: 95%;
                    box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.05);
                }}
                .diagram-title {{
                    font-size: 14px;
                    font-weight: 600;
                    color: #1e293b;
                    margin-bottom: 12px;
                    border-bottom: 2px solid #3b82f6;
                    padding-bottom: 4px;
                    display: inline-block;
                }}
                .mermaid {{
                    display: flex;
                    justify-content: center;
                    overflow-x: auto;
                }}
            </style>
        </head>
        <body>
            <div class="diagram-card">
                <div class="diagram-title">📊 {title}</div>
                <div class="mermaid">
{clean_code}
                </div>
            </div>
            <script>
                mermaid.initialize({{
                    startOnLoad: true,
                    theme: 'default',
                    themeVariables: {{
                        primaryColor: '#e0f2fe',
                        primaryTextColor: '#0369a1',
                        primaryBorderColor: '#0284c7',
                        lineColor: '#64748b',
                        secondaryColor: '#f1f5f9',
                        tertiaryColor: '#ffffff'
                    }}
                }});
            </script>
        </body>
        </html>
        """
        return html_content

    @classmethod
    def generate_default_diagram_for_topic(cls, topic: str) -> str:
        """Generates a contextual academic diagram if LLM did not provide one."""
        topic_lower = topic.lower()

        if "paging" in topic_lower or "memory" in topic_lower:
            return """flowchart LR
    subgraph CPU ["CPU Operation"]
        VA["Logical Address<br/>[Page # (p) | Offset (d)]"]
    end
    subgraph MMU ["Memory Management Unit (MMU)"]
        PT["Page Table<br/>(Frame Reference: f)"]
    end
    subgraph RAM ["Physical RAM"]
        PA["Physical Address<br/>[Frame # (f) | Offset (d)]"]
        MEM["Physical Frame in Memory"]
    end
    VA -->|Page Number p| PT
    PT -->|Frame Number f| PA
    VA -.->|Direct Offset d| PA
    PA --> MEM
    style CPU fill:#dbeafe,stroke:#2563eb,stroke-width:2px
    style MMU fill:#fef3c7,stroke:#d97706,stroke-width:2px
    style RAM fill:#dcfce7,stroke:#16a34a,stroke-width:2px"""

        elif "tcp" in topic_lower or "osi" in topic_lower or "layer" in topic_lower:
            return """flowchart TD
    subgraph Model ["Layered Architecture"]
        L7["Application Layer (HTTP, DNS, FTP)"]
        L4["Transport Layer (TCP, UDP - Port Addressing)"]
        L3["Network Layer (IP - Logical Addressing & Routing)"]
        L2["Data Link Layer (MAC - Framing & Flow Control)"]
        L1["Physical Layer (Bits, Cables & Signal Transmission)"]
    end
    L7 --> L4 --> L3 --> L2 --> L1
    style L7 fill:#eff6ff,stroke:#3b82f6
    style L4 fill:#f0fdf4,stroke:#22c55e
    style L3 fill:#fffbeb,stroke:#eab308
    style L2 fill:#fdf4ff,stroke:#d946ef
    style L1 fill:#f8fafc,stroke:#64748b"""

        elif "process" in topic_lower or "state" in topic_lower:
            return """stateDiagram-v2
    [*] --> New: Process Created
    New --> Ready: Admitted by Long-term Scheduler
    Ready --> Running: Dispatched by Short-term Scheduler
    Running --> Ready: Interrupt / Time Slice Expired
    Running --> Waiting: I/O or Event Wait
    Waiting --> Ready: I/O or Event Completed
    Running --> Terminated: Exit / Completed
    Terminated --> [*]"""

        elif any(w in topic_lower for w in ["database", "er", "acid"]):
            return """flowchart TD
    subgraph Transaction ["ACID Properties"]
        A["Atomicity<br/>(All or Nothing - Rollback/Commit)"]
        C["Consistency<br/>(Preserves Integrity Constraints)"]
        I["Isolation<br/>(Concurrency Control & Locking)"]
        D["Durability<br/>(WAL & Recovery Management)"]
    end
    style A fill:#fee2e2,stroke:#ef4444
    style C fill:#fef3c7,stroke:#f59e0b
    style I fill:#e0e7ff,stroke:#6366f1
    style D fill:#dcfce7,stroke:#10b981"""

        elif any(w in topic_lower for w in ["regular expression", "regex", "automata", "dfa", "nfa", "finite state"]):
            return """stateDiagram-v2
    direction LR
    [*] --> q0: Start
    q0 --> q1: Read 'a'
    q1 --> q1: Loop 'a' (Kleene Star *)
    q1 --> q2: Read 'b'
    q2 --> [*]: Accept / Match"""

        elif any(w in topic_lower for w in ["sorting", "merge sort", "divide and conquer"]):
            return """flowchart TD
    subgraph Divide ["Divide Phase"]
        A["Unsorted Array [38, 27, 43, 3, 9, 82, 10]"] --> B1["Left [38, 27, 43, 3]"]
        A --> B2["Right [9, 82, 10]"]
    end
    subgraph Conquer ["Conquer & Merge"]
        B1 --> C1["Sorted Left [3, 27, 38, 43]"]
        B2 --> C2["Sorted Right [9, 10, 82]"]
        C1 --> D["Final Merged & Sorted Array [3, 9, 10, 27, 38, 43, 82]"]
        C2 --> D
    end
    style A fill:#fee2e2,stroke:#ef4444
    style D fill:#dcfce7,stroke:#16a34a"""

        else:
            return ""

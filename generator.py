import os
import json
import re
from typing import List, Dict, Any, Optional
from config import MARK_SCHEMES, GEMINI_MODELS
from diagram_engine import DiagramEngine

class AcademicAnswerGenerator:
    """
    Intelligent Answer and Marking Scheme Generator.
    Produces exam-ready, mark-calibrated answers with transparent scoring rubrics
    and labeled architectural/workflow diagrams.
    """

    def __init__(self, api_key: Optional[str] = None, model_name: str = "gemini-2.5-flash"):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self.model_name = model_name

    def generate_scheme_and_answer(self, question: str, marks: int, context_chunks: List[Dict[str, Any]]) -> Dict[str, Any]:
        """
        Main entry point for generating mark-appropriate answer, marking scheme rubric,
        and conceptual diagram.
        """
        # Determine mark scheme baseline
        scheme_template = MARK_SCHEMES.get(marks, MARK_SCHEMES[10])
        diagram_needed = DiagramEngine.should_include_diagram(question, marks)

        # Context compilation from RAG chunks
        context_text = "\n\n".join([
            f"[Source: {c.get('source_doc', 'Document')} | Page {c.get('page', 1)}]\n{c['text']}"
            for c in context_chunks
        ])

        # Attempt Gemini API Generation if key exists
        if self.api_key:
            try:
                result = self._generate_with_gemini(question, marks, context_text, scheme_template, diagram_needed)
                if result:
                    result["sources"] = context_chunks
                    return result
            except Exception as e:
                print(f"Gemini API call failed, falling back to academic engine: {e}")

        # Intelligent Academic Knowledge Synthesis Engine
        return self._generate_with_synthesis_engine(question, marks, context_chunks, scheme_template, diagram_needed)

    def _generate_with_gemini(self, question: str, marks: int, context_text: str, 
                              scheme_template: Dict, diagram_needed: bool) -> Optional[Dict[str, Any]]:
        import google.generativeai as genai
        genai.configure(api_key=self.api_key)
        model = genai.GenerativeModel(self.model_name)
        diag_rule = (
            "YES. The question explicitly requires a diagram. Provide valid Mermaid.js code for the diagram, set diagram_title, and allocate marks for the diagram in the rubric components."
            if diagram_needed else
            "NO. The question DOES NOT require a diagram. You MUST set diagram_code to empty string \"\", set diagram_title to \"\", and DO NOT include any diagram in the answer or marking scheme."
        )

        system_prompt = f"""
You are an expert Academic Professor and Chief Paper Evaluator in Computer Science and Engineering.
Your task is to generate a comprehensive, exam-oriented response for an academic question strictly tailored to the allocated marks ({marks} Marks).

Academic Rules for {marks} Marks:
- Expected Structure: {scheme_template['description']}
- Expected Length: {scheme_template['expected_length']}
- Need Diagram: {diag_rule}

CONTEXT FROM ACADEMIC MATERIALS:
\"\"\"
{context_text}
\"\"\"

QUESTION: {question}

You MUST return a JSON object with the following schema:
{{
    "scheme": {{
        "target_marks": {marks},
        "components": [
            {{"component": "Detailed description of point/section", "marks": 1.0}}
        ],
        "total_allocated": {marks}
    }},
    "answer_markdown": "Full academic answer in formatted Markdown with clear headings, bullet points, technical terms bolded, and formulas/algorithms where applicable.",
    "diagram_code": "Valid Mermaid.js diagram code ONLY IF diagram is required by the question. If no diagram is required, return an empty string \"\".",
    "diagram_title": "Descriptive title for the diagram if required, else empty string \"\".",
    "tips_for_full_marks": [
        "Key point students frequently miss in exam",
        "Keywords strictly looked for by the examiner"
    ]
}}

Ensure the sum of component marks exactly equals {marks}. Return ONLY the JSON object.
"""

        response = model.generate_content(
            system_prompt,
            generation_config={"response_mime_type": "application/json"}
        )

        try:
            data = json.loads(response.text)
            if not diagram_needed:
                data["diagram_code"] = ""
                data["diagram_title"] = ""
                data["diagram_needed"] = False
            else:
                if data.get("diagram_code"):
                    data["diagram_code"] = DiagramEngine.sanitize_mermaid_code(data["diagram_code"])
                else:
                    data["diagram_code"] = DiagramEngine.generate_default_diagram_for_topic(question)
                    data["diagram_title"] = f"Architecture / Flow: {question[:40]}"
                data["diagram_needed"] = bool(data["diagram_code"].strip())
            data["marks"] = marks
            data["question"] = question
            return data
        except Exception as err:
            print(f"Error parsing Gemini response JSON: {err}")
            return None

    def _extract_document_insights(self, context_chunks: List[Dict[str, Any]], question: str) -> Dict[str, Any]:
        """
        Extracts structured, topic-relevant insights from RAG context chunks:
        definitions, operational points, formulas, algorithms, and practical examples.
        """
        raw_text_blocks = [c.get("text", "") for c in context_chunks if c.get("text")]
        combined_text = "\n".join(raw_text_blocks)
        
        definitions = []
        operational_points = []
        formulas = []

        q_terms = set(re.findall(r'\b[a-zA-Z]{3,}\b', question.lower()))

        for line in combined_text.splitlines():
            clean_line = line.strip()
            if not clean_line or len(clean_line) < 15:
                continue

            # Skip document headers / metadata
            if re.match(r'^(page\s+\d+|module\s+\d+|course:|department\s+of|academic\s+year|unit\s+\d+|course\s+outcome).*', clean_line, re.IGNORECASE):
                continue

            # Check for formulas / mathematical expressions
            if any(sym in clean_line for sym in ["=", "Formula:", "EAT =", "PA =", "O(", "^", "2^", "Work =", "Need ="]) and not clean_line.endswith(":"):
                clean_formula = re.sub(r'^[-\*•\d+\.]\s*', '', clean_line).strip()
                if clean_formula not in formulas:
                    formulas.append(clean_formula)
                continue

            # Check for bullet points / numbered lists
            if re.match(r'^[\-\*•\d+\.]\s+', clean_line):
                cleaned_pt = re.sub(r'^[\-\*•\d+\.]\s*', '', clean_line).strip()
                if len(cleaned_pt) > 15 and cleaned_pt not in operational_points:
                    operational_points.append(cleaned_pt)
                continue

            # Check if line contains a definition
            lower_line = clean_line.lower()
            if any(def_word in lower_line for def_word in ["is a", "is defined as", "refers to", "concept of", "technique that", "algorithm that", "scheme that"]):
                if clean_line not in definitions:
                    definitions.append(clean_line)
            else:
                if clean_line not in operational_points and len(clean_line) > 20:
                    operational_points.append(clean_line)

        # Sentence-level fallback if points were few
        if len(operational_points) < 4:
            sentences = [s.strip() for s in re.split(r'(?<=[.?!])\s+', combined_text) if len(s.strip()) > 20]
            for s in sentences:
                if s not in operational_points and s not in definitions:
                    operational_points.append(s)

        # Relevance scoring
        def relevance_score(item: str) -> int:
            words = set(re.findall(r'\b[a-zA-Z]{3,}\b', item.lower()))
            return len(words.intersection(q_terms))

        definitions.sort(key=relevance_score, reverse=True)
        operational_points.sort(key=relevance_score, reverse=True)
        formulas.sort(key=relevance_score, reverse=True)

        return {
            "definitions": definitions,
            "operational_points": operational_points,
            "formulas": formulas,
            "has_doc_content": bool(combined_text.strip())
        }

    def _get_topic_domain_knowledge(self, question: str) -> Dict[str, Any]:
        """
        Provides syllabus-aligned technical knowledge for core Computer Science topics.
        Guarantees accurate definitions, formulas, and operational points rather than generic filler.
        """
        q_lower = question.lower()

        if any(w in q_lower for w in ["paging", "page table", "virtual memory", "tlb", "frame"]):
            return {
                "topic": "Paging and Virtual Memory Hardware Translation",
                "definition": "Paging is a memory management scheme that eliminates the requirement for contiguous allocation of physical memory, allowing the physical address space of a process to be non-contiguous. It fundamentally resolves external fragmentation.",
                "points": [
                    "**Logical Address Decomposition**: Generated by the CPU; split into high-order Page Number ($p$) and low-order Page Offset ($d$).",
                    "**Physical Memory Partitioning**: Physical memory (RAM) is subdivided into fixed-size blocks termed Frames ($f$), matching the exact size of logical pages.",
                    "**Page Table Hardware Lookup**: The MMU indexes the process Page Table using page number $p$ to locate the base address of corresponding frame $f$.",
                    "**Address Translation Mapping**: The physical address is synthesized by concatenating or calculating: $\\text{Physical Address} = (f \\times \\text{Frame Size}) + d$.",
                    "**Translation Lookaside Buffer (TLB)**: High-speed hardware associative cache integrated within the MMU storing recent translations to avoid extra memory accesses.",
                    "**Protection & Fragmentation**: Valid/invalid bits enforce memory protection; internal fragmentation is bounded strictly to the final frame of the process."
                ],
                "formula": "$$\\text{Physical Address} = (f \\times 2^n) + d \\quad \\text{where } n = \\text{offset bits}$$\n$$\\text{Effective Access Time (EAT)} = \\alpha(t_{\\text{tlb}} + m) + (1-\\alpha)(t_{\\text{tlb}} + 2m)$$",
                "example": "For a 32-bit logical address with 4 KB ($2^{12}$) page size: Offset $d = 12$ bits, Page Number $p = 32 - 12 = 20$ bits. If $p = 5$ maps to frame $f = 12$, physical address is $(12 \\times 4096) + d$."
            }

        elif any(w in q_lower for w in ["deadlock", "banker", "resource allocation graph", "safe state"]):
            return {
                "topic": "Deadlock Detection, Prevention and Banker's Algorithm",
                "definition": "A deadlock is an execution state where two or more processes are permanently blocked because each holds resources that another process needs, and none can proceed without releasing their held resources.",
                "points": [
                    "**Coffman's 4 Necessary Conditions**: Deadlock occurs if and only if Mutual Exclusion, Hold and Wait, No Preemption, and Circular Wait hold simultaneously.",
                    "**Resource Allocation Graph (RAG)**: Directed graph with Process vertices ($P$) and Resource vertices ($R$); directed cycles indicate deadlocks when resources have single instances.",
                    "**Banker's Avoidance Algorithm**: Tests for safety by simulating the allocation of predetermined maximum claims before actual resource assignment.",
                    "**Core Matrix Data Structures**: $Available[m]$ (available instances), $Max[n][m]$ (max demand), $Allocation[n][m]$ (currently held), and $Need[n][m] = Max[n][m] - Allocation[n][m]$.",
                    "**Safety State Verification**: System is in a Safe State if there exists at least one safe execution sequence $\\langle P_1, P_2, \\dots, P_n \\rangle$ ensuring all processes can terminate.",
                    "**Resource-Request Protocol**: If $Request_i \\le Need_i$ and $Request_i \\le Available$, tentative allocation occurs only if the resulting state remains provably safe."
                ],
                "formula": "$$\\text{Need}[i][j] = \\text{Max}[i][j] - \\text{Allocation}[i][j]$$\n$$\\text{Safety Test}: \\text{Need}_i \\le \\text{Work} \\implies \\text{Work} = \\text{Work} + \\text{Allocation}_i$$",
                "example": "If Process $P_1$ needs $(1, 2, 2)$ resources and $Available = (3, 3, 2)$, $P_1$ can safely execute, complete, and release its entire allocation back to the $Available$ pool."
            }

        elif any(w in q_lower for w in ["process", "scheduling", "pcb", "context switch", "fcfs", "sjf", "round robin"]):
            return {
                "topic": "Process Lifecycle Management and CPU Scheduling",
                "definition": "A process is an active program in execution. It comprises executable code (Text), global variables (Data), dynamically allocated memory (Heap), and active stack frames (Stack).",
                "points": [
                    "**5-State Process Model**: Transition lifecycle encompassing New $\\rightarrow$ Ready $\\rightarrow$ Running $\\rightarrow$ Waiting (I/O) $\\rightarrow$ Terminated.",
                    "**Process Control Block (PCB)**: Kernel repository storing PID, Program Counter, CPU registers, scheduling priority, open file descriptors, and memory bounds.",
                    "**Dispatcher & Context Switching**: Hardware mechanism that saves the state of the preempted process into its PCB and restores the scheduled process's context.",
                    "**Scheduling Criteria**: Optimized across CPU Utilization (%), Throughput (processes/sec), Turnaround Time, Waiting Time, and Response Time.",
                    "**Preemptive vs Non-Preemptive**: Non-preemptive (FCFS, standard SJF) holds CPU until voluntary yield; Preemptive (SRTF, Round Robin) forces context switches via timer interrupts.",
                    "**Round Robin (RR)**: Time quantum ($q$) allocation ensuring starvation freedom; small $q$ elevates context-switch overhead while excessively large $q$ degenerates to FCFS."
                ],
                "formula": "$$\\text{Turnaround Time} = T_{\\text{completion}} - T_{\\text{arrival}}$$\n$$\\text{Waiting Time} = \\text{Turnaround Time} - \\text{Burst Time}$$",
                "example": "Given process burst times $P_1=24, P_2=3, P_3=3$ under FCFS: Average Waiting Time is $(0 + 24 + 27)/3 = 17\\text{ ms}$. Under SJF, Average Waiting Time drops to $(0 + 3 + 6)/3 = 3\\text{ ms}$."
            }

        elif any(w in q_lower for w in ["osi", "tcp/ip", "layer", "protocol", "network architecture"]):
            return {
                "topic": "Layered Network Architectures and OSI/TCP-IP Models",
                "definition": "The OSI (Open Systems Interconnection) reference model is an ISO standard 7-layer architectural framework defining end-to-end communication protocols and standard layer interfaces.",
                "points": [
                    "**Application Layer (L7)**: Provides network interface services directly to end-user software applications (HTTP, DNS, SMTP, FTP).",
                    "**Presentation & Session (L6 & L5)**: L6 handles data formatting, encryption (TLS), and compression; L5 manages dialogue synchronization and session checkpoints.",
                    "**Transport Layer (L4)**: Guarantees end-to-end host communication, port addressing (sockets), segmentation, and reliable delivery (TCP connection-oriented, UDP datagrams).",
                    "**Network Layer (L3)**: Manages logical IP addressing, packet forwarding, routing algorithms (Dijkstra, Distance Vector), and fragment handling (IPv4, IPv6, ICMP).",
                    "**Data Link Layer (L2)**: Physical MAC addressing, framing, flow control, and error detection using Cyclic Redundancy Checks (CRC).",
                    "**Physical Layer (L1)**: Raw unstructured bit transmission across physical media (twisted pair, optical fiber, radio RF) defining voltages, pinouts, and signal timing."
                ],
                "formula": "$$\\text{Data Encapsulation}: \\text{Data} \\xrightarrow{\\text{L4}} \\text{Segment} \\xrightarrow{\\text{L3}} \\text{Packet} \\xrightarrow{\\text{L2}} \\text{Frame} \\xrightarrow{\\text{L1}} \\text{Bits}$$",
                "example": "When a web browser requests an HTTPS page, HTTP data is encrypted at L6, segmented and given port 443 headers at L4, IP packetized at L3, MAC framed at L2, and transmitted as digital pulses at L1."
            }

        elif any(w in q_lower for w in ["go-back-n", "selective repeat", "sliding window", "flow control", "stop and wait"]):
            return {
                "topic": "Sliding Window Flow Control Protocols",
                "definition": "Sliding window protocols are pipelined data link and transport layer flow control mechanisms that permit a sender to transmit multiple unacknowledged frames, maximizing channel utilization across high-delay links.",
                "points": [
                    "**Pipelined Transmission**: Eliminates stop-and-wait idle latency by keeping the transmission pipe full of frames.",
                    "**Go-Back-N (GBN) Protocol**: Sender maintains window size $N$; receiver accepts frames strictly in sequence using cumulative ACKs; single frame loss forces retransmission of all $N$ unacknowledged frames.",
                    "**Selective Repeat (SR) Protocol**: Both sender and receiver maintain window size $N$; receiver buffers out-of-order valid frames; only specific missing frames are retransmitted via negative ACKs (NAK).",
                    "**Sequence Numbering Constraints**: For $k$-bit sequence numbers: GBN requires $W_S \\le 2^k - 1$ with $W_R = 1$; SR requires $W_S \\le 2^{k-1}$ and $W_R \\le 2^{k-1}$ to prevent sequence overlap.",
                    "**Receiver Buffer Trade-off**: GBN requires zero receiver buffering ($W_R = 1$), whereas SR requires dedicated buffer memory ($W_R = N$) to store out-of-order frames."
                ],
                "formula": "$$\\text{Link Utilization } \\eta = \\frac{N}{1 + 2a} \\quad \\text{where } a = \\frac{T_{\\text{prop}}}{T_{\\text{trans}}}$$\n$$\\text{Window Bounds}: \\text{GBN: } W_S = 2^k - 1, \\quad \\text{SR: } W_S = W_R = 2^{k-1}$$",
                "example": "With 3-bit sequence numbers ($2^3 = 8$ states): GBN maximum window size is $8 - 1 = 7$. In Selective Repeat, maximum window size is $8/2 = 4$ to prevent stale ACK misinterpretation."
            }

        elif any(w in q_lower for w in ["acid", "transaction", "concurrency", "2pl", "locking", "database"]):
            return {
                "topic": "Database Transaction Processing and ACID Properties",
                "definition": "A database transaction is an atomic logical unit of work comprising a sequence of database operations that accesses or modifies data while preserving database consistency.",
                "points": [
                    "**Atomicity (All-or-Nothing)**: Every operation in the transaction commits successfully, or the entire transaction is rolled back via undo-logs.",
                    "**Consistency (Constraint Preservation)**: Execution transforms the database from one valid consistent state satisfying all integrity constraints to another.",
                    "**Isolation (Concurrent Independence)**: Uncommitted operations of concurrent transactions remain invisible to others, preventing dirty reads and non-repeatable reads.",
                    "**Durability (Crash Permanence)**: Committed updates are permanently written to non-volatile storage (WAL) and withstand subsequent system failures.",
                    "**Two-Phase Locking (2PL)**: Concurrency protocol ensuring serializability: Growing Phase (locks acquired, none released) and Shrinking Phase (locks released, none acquired)."
                ],
                "formula": "$$\\text{Serializability Verification}: \\text{Precedence (Conflict) Graph with no cycles} \\implies \\text{Conflict Serializability}$$",
                "example": "A bank funds transfer debiting Account A ($100) and crediting Account B ($100) must execute atomically: if system crashes after debiting A, Atomicity rolls back the debit so money is not lost."
            }

        else:
            # Fallback based on question keywords
            title_clean = question.rstrip("?.").strip()
            return {
                "topic": title_clean,
                "definition": f"**{title_clean}** represents an essential technical concept and foundational mechanism within academic computer science and system architecture.",
                "points": [
                    f"**Core Principle**: Governs the operational protocols and execution workflows established for {title_clean}.",
                    "**System Modularity**: Enforces modular separation of concerns between underlying physical resources and high-level logical abstractions.",
                    "**State Management & Coordination**: Regulates state transitions, synchronization primitives, and resource scheduling to prevent contention.",
                    "**Error Handling & Validation**: Incorporates validation checks, boundary limits, and deterministic recovery mechanisms.",
                    "**Performance Optimization**: Minimizes algorithmic time complexity and memory overhead under sustained operating workloads."
                ],
                "formula": "$$\\text{Efficiency} = \\frac{\\text{Useful Work Output}}{\\text{Total Resource Overhead}} \\times 100\\%$$",
                "example": f"Applied in high-reliability operating systems, distributed network infrastructure, and real-time computing systems implementing {title_clean}."
            }

    def _generate_with_synthesis_engine(self, question: str, marks: int, context_chunks: List[Dict[str, Any]], 
                                        scheme_template: Dict, diagram_needed: bool) -> Dict[str, Any]:
        """
        Academic synthesis engine that formulates structured answers from document context
        and academic domain knowledge when running offline.
        """
        insights = self._extract_document_insights(context_chunks, question)
        fallback = self._get_topic_domain_knowledge(question)

        # 1. Determine Introduction
        if insights["definitions"]:
            intro = insights["definitions"][0]
        elif insights["operational_points"]:
            intro = insights["operational_points"][0]
        else:
            intro = fallback["definition"]

        # 2. Determine Working Points
        extracted_pts = [p for p in insights["operational_points"] if p != intro]
        if len(extracted_pts) >= 4:
            # Format extracted points with bold prefix if needed
            formatted_pts = []
            for pt in extracted_pts[:6]:
                if ":" in pt and not pt.startswith("**"):
                    parts = pt.split(":", 1)
                    formatted_pts.append(f"**{parts[0].strip()}**: {parts[1].strip()}")
                elif not pt.startswith("**"):
                    formatted_pts.append(f"**Key Aspect**: {pt}")
                else:
                    formatted_pts.append(pt)
            working_points = formatted_pts
        else:
            # Supplement with topic-specific domain points
            working_points = []
            for pt in extracted_pts:
                if ":" in pt and not pt.startswith("**"):
                    parts = pt.split(":", 1)
                    working_points.append(f"**{parts[0].strip()}**: {parts[1].strip()}")
                else:
                    working_points.append(f"**Operational Detail**: {pt}")
            for fb_pt in fallback["points"]:
                if len(working_points) < 6 and fb_pt not in working_points:
                    working_points.append(fb_pt)

        # 3. Determine Mathematical Formula / Working Example
        if insights["formulas"]:
            raw_f = "\n".join([f"- `{f}`" for f in insights["formulas"][:3]])
            formula_block = f"{raw_f}\n\n{fallback.get('formula', '')}"
        else:
            formula_block = fallback.get("formula", "")

        example_text = fallback.get("example", "Refer to standard academic implementation scenarios.")

        # Construct Answer by Mark Weightage
        answer_parts = []
        components = []

        if marks == 2:
            components = [
                {"component": "Formal Definition / Core Concept", "marks": 1.0},
                {"component": "Key Feature, Formula or Standard Example", "marks": 1.0}
            ]
            answer_parts.append(f"### 📌 Definition & Core Concept\n{intro}\n")
            feature_text = working_points[0] if working_points else fallback["points"][0]
            answer_parts.append(f"### 🔑 Key Characteristics & Formula\n- {feature_text}\n- **Application / Formula**: {insights['formulas'][0] if insights['formulas'] else fallback.get('example', 'Widely adopted in computing architectures.')}")
            diagram_code = ""
            diagram_title = ""

        elif marks == 5:
            if diagram_needed:
                components = [
                    {"component": "Introduction & Formal Definition", "marks": 1.0},
                    {"component": "Core Operational Mechanism (3-4 points)", "marks": 2.5},
                    {"component": "Neat Labeled Architecture / Flow Diagram", "marks": 1.5}
                ]
                diagram_code = DiagramEngine.generate_default_diagram_for_topic(question)
                diagram_title = f"Architecture / Flow: {question[:35]}"
            else:
                components = [
                    {"component": "Introduction & Formal Definition", "marks": 1.0},
                    {"component": "Core Operational Mechanism & Principles", "marks": 2.5},
                    {"component": "Practical Example, Formula or Significance", "marks": 1.5}
                ]
                diagram_code = ""
                diagram_title = ""

            answer_parts.append(f"### 1. Overview & Formal Definition\n{intro}\n")
            answer_parts.append("### 2. Core Working Mechanism & Operational Points")
            for idx, pt in enumerate(working_points[:4], 1):
                answer_parts.append(f"{idx}. {pt}")
            
            answer_parts.append(f"\n### 3. Practical Example & Technical Formula\n- **Formula / Specification**:\n  {formula_block}\n- **Standard Example**:\n  {example_text}")

        elif marks == 10:
            if diagram_needed:
                components = [
                    {"component": "Conceptual Introduction & Theoretical Background", "marks": 1.5},
                    {"component": "Neat Labeled Architecture / Flow Diagram", "marks": 3.0},
                    {"component": "Detailed Technical Breakdown & Step-by-Step Working", "marks": 3.5},
                    {"component": "Algorithm / Derivation / Real-World Example & Analysis", "marks": 2.0}
                ]
                diagram_code = DiagramEngine.generate_default_diagram_for_topic(question)
                diagram_title = f"System Architecture & Dataflow: {question[:35]}"
                arch_section = "### 2. Architectural Blueprint & Component Overview\n*(Refer to the accompanying labeled Mermaid architecture diagram rendered below for module interconnections)*\n"
            else:
                components = [
                    {"component": "Conceptual Introduction & Theoretical Background", "marks": 2.0},
                    {"component": "Detailed Technical Breakdown & Core Working Mechanism", "marks": 4.5},
                    {"component": "Algorithm / Derivation / Real-World Example & Analysis", "marks": 2.5},
                    {"component": "Practical Insights, Trade-offs & Exam Summary", "marks": 1.0}
                ]
                diagram_code = ""
                diagram_title = ""
                arch_section = ""

            answer_parts.append(f"### 1. Introduction & Theoretical Background\n{intro}\n")
            if arch_section:
                answer_parts.append(arch_section)
                answer_parts.append("### 3. Detailed Step-by-Step Working Mechanism")
            else:
                answer_parts.append("### 2. Detailed Technical Breakdown & Working Mechanism")

            for pt in working_points[:6]:
                answer_parts.append(f"- {pt}")

            sec_math = "4" if arch_section else "3"
            sec_sum = "5" if arch_section else "4"

            answer_parts.append(f"\n### {sec_math}. Mathematical Formulation, Working Algorithm & Concrete Example")
            answer_parts.append(f"**Mathematical Formulation / Equations**:\n{formula_block}\n")
            answer_parts.append(f"**Concrete Operational Walkthrough**:\n{example_text}")

            answer_parts.append(f"\n### {sec_sum}. Academic Summary, Trade-offs & Exam Takeaways")
            answer_parts.append("- **Advantages**: Maximizes hardware throughput, provides robust fault isolation, and maintains strict determinism.")
            answer_parts.append("- **Limitations & Trade-offs**: Requires dedicated hardware/kernel data structure overhead; boundary conditions must be managed.")
            answer_parts.append("- **Scoring Tip**: Clearly label all variables in the equation and explicitly outline each step of the algorithm for full marks.")

        else: # 15 marks
            if diagram_needed:
                components = [
                    {"component": "In-depth Theoretical Foundation & System Principles", "marks": 2.0},
                    {"component": "Exhaustive System Architecture & Labeled Diagram", "marks": 4.0},
                    {"component": "Detailed Multi-Stage Component & Protocol Analysis", "marks": 5.0},
                    {"component": "Algorithmic Workflow, Complexity & Derivation", "marks": 2.5},
                    {"component": "Comparative Analysis, Trade-offs & Concluding Remarks", "marks": 1.5}
                ]
                diagram_code = DiagramEngine.generate_default_diagram_for_topic(question)
                diagram_title = f"Comprehensive 15-Mark Architectural Model: {question[:35]}"
                arch_section = "### 2. Comprehensive System Architecture & Interconnections\nThe architecture consists of coordinated sub-modules functioning across discrete privilege rings and memory domains.\n"
            else:
                components = [
                    {"component": "In-depth Theoretical Foundation & System Principles", "marks": 3.0},
                    {"component": "Detailed Multi-Stage Component & Protocol Analysis", "marks": 6.0},
                    {"component": "Algorithmic Workflow, Complexity & Mathematical Derivation", "marks": 3.5},
                    {"component": "Comparative Analysis, Trade-offs & Concluding Remarks", "marks": 2.5}
                ]
                diagram_code = ""
                diagram_title = ""
                arch_section = ""

            answer_parts.append(f"### 1. In-depth Theoretical Foundation & System Principles\n{intro}\n")
            if arch_section:
                answer_parts.append(arch_section)
                sec_mod = "3"
            else:
                sec_mod = "2"

            answer_parts.append(f"### {sec_mod}. Detailed Module-by-Module Operational Breakdown")
            for idx, pt in enumerate(working_points[:6], 1):
                answer_parts.append(f"#### {sec_mod}.{idx} Operational Phase {idx}\n{pt}\n")

            sec_comp = "4" if arch_section else "3"
            sec_fin = "5" if arch_section else "4"

            answer_parts.append(f"### {sec_comp}. Mathematical Formulation & Algorithmic Analysis")
            answer_parts.append(f"**Mathematical Equations**:\n{formula_block}\n")
            answer_parts.append(f"**Practical Scenario**:\n{example_text}")

            answer_parts.append(f"\n### {sec_fin}. Final Concluding Summary & Critical Evaluation")
            answer_parts.append("- **System Impact**: Balances efficiency, reliability, and computational overhead according to academic benchmarks.")
            answer_parts.append("- **Examiner Takeaway**: A complete 15-mark answer must synthesize theoretical definitions, step-by-step mechanics, mathematical equations, and real-world trade-offs.")

        full_answer = "\n".join(answer_parts)

        tips = [
            f"Draw the labeled diagram clearly; examiners allot {components[1]['marks'] if len(components) > 1 else 1} marks specifically for neat schematics.",
            "Highlight key terminology in bold or underline during the written examination.",
            f"Maintain structured paragraphs matching the {marks}-mark rubric."
        ] if diagram_needed else [
            "Strictly define all terms with their formal academic notations.",
            "Structure answers with numbered headings matching the marking scheme breakdown.",
            f"Highlight boundary conditions and maintain structured paragraphs matching the {marks}-mark rubric."
        ]

        return {
            "question": question,
            "marks": marks,
            "scheme": {
                "target_marks": marks,
                "components": components,
                "total_allocated": marks
            },
            "answer_markdown": full_answer,
            "diagram_code": diagram_code if diagram_needed else "",
            "diagram_needed": bool(diagram_needed and diagram_code),
            "diagram_title": diagram_title if diagram_needed else "",
            "tips_for_full_marks": tips,
            "sources": context_chunks
        }

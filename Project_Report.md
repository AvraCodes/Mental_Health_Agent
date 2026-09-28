# A PROJECT REPORT ON
“MULTI-AGENT SYSTEM FOR MENTAL HEALTH SUPPORT (ZOYA)”

Submitted in partial fulfilment of the requirements for the degree of
BACHELOR OF TECHNOLOGY
IN
IT

**Prepared by:**
Avra Paul
Nomesh Singh

**Under the Guidance of:**
Prof. Dr. Srinka Basu
DETS
B.Tech in IT
Academic Year: 2026
Submission Date: ___________

---

## CERTIFICATE
This is to certify that the project report titled “Multi-Agent System for Mental Health Support (Zoya)” has been carried out by Avra Paul and Nomesh Singh, students of B.Tech in IT, under my guidance and supervision, in partial fulfilment of the requirements for the award of the degree of Bachelor of Technology in IT from University of Kalyani.

This project work embodies the original work carried out by the students during the academic year 2026, and to the best of my knowledge, it has not been submitted elsewhere for the award of any other degree or diploma.
It is further certified that the students have completed the work under my supervision and that the report is satisfactory for evaluation.

Date: [To be filled]
Place: [To be filled]

___________________________	___________________________
Prof. Dr. Srinka Basu	                [Head of Department Name]
Project Guide / Supervisor	Head of Department, IT

---

## DECLARATION
We, Avra Paul and Nomesh Singh, students of B.Tech in IT, hereby declare that the project report titled “Multi-Agent System for Mental Health Support (Zoya)” is an original record of the work carried out by us under the guidance of Prof. Dr. Srinka Basu.

This report has been prepared solely for academic purposes as part of our B.Tech curriculum and has not been submitted, in full or in part, to any other institution or university for the award of any degree or diploma.
We further declare that any material, data, or research referred to from external sources has been duly acknowledged and cited in the References section of this report.

1. Avra Paul     ___________________________     Roll No.: [To be filled]
2. Nomesh Singh  ___________________________     Roll No.: [To be filled]

Date: [To be filled]
Place: [To be filled]

---

## ACKNOWLEDGEMENT
We would like to express our sincere gratitude to our project guide, Prof. Dr. Srinka Basu, for the constant guidance, encouragement, and valuable suggestions provided throughout the course of this project. Her feedback at every stage helped us understand the subject more clearly and shaped the direction of this work.

We are also thankful to the Department of Engineering & Technological Studies (DETS) for providing us with the academic environment, resources, and support needed to carry out this project. We would also like to thank our faculty members and peers for their helpful discussions and suggestions during the development of this report.

Finally, we would like to thank our families and friends for their continuous support and encouragement during the course of this project.

Avra Paul
Nomesh Singh

---

## ABSTRACT
Mental health support is a critical need globally, yet many individuals lack access to timely, empathetic, and evidence-based care due to cost, stigma, or a shortage of professionals. Artificial Intelligence (AI) and Large Language Models (LLMs) offer a promising supplementary avenue for support. However, generic chatbots often lack the clinical nuances, memory, and safety guardrails required for sensitive mental health conversations.

This project addresses these challenges by developing "Zoya," a specialized multi-agent system for mental health support. Built with a FastAPI backend, Next.js frontend, and powered by locally-hosted Qwen-3.4B and Google's Generative AI embeddings, Zoya provides an empathetic, context-aware conversational interface. The system employs a seamless calibration process to silently measure user engagement, triggering the injection of standard psychological questionnaires (PHQ-9 and GAD-7) into the context at appropriate intervals. 

Through its modular architecture, Zoya incorporates Retrieval-Augmented Generation (RAG) using ChromaDB to ground its responses in verified clinical research papers. Safety mechanisms, including a classifier to detect high-risk inputs and prevent the system from offering medical diagnoses, ensure that the system operates safely within its bounds as a supportive tool, not a replacement for professional therapy. This report details the conceptualization, architecture, implementation, and expected outcomes of the Zoya mental health agent.

---

## TABLE OF CONTENTS

1. Introduction
2. Problem Statement
3. Motivation
4. Objectives
5. Literature Review
6. Multi-Agent AI Concept
7. Proposed System
8. System Architecture
9. Request Lifecycle and Calibration
10. Psychological Questionnaires & RAG
11. AI/ML Inference & Safety Classifier
12. Technology Stack
13. Implementation Methodology
14. Workflow
15. Experiment / Scenario Design
16. Results and Discussion
17. Advantages
18. Limitations
19. Applications
20. Future Scope
21. Conclusion
22. Team Contribution
23. References
24. Appendix

---

## 1. INTRODUCTION
In recent years, the integration of Artificial Intelligence in healthcare has opened new frontiers, particularly in mental health support. Large Language Models (LLMs) can simulate conversational agents, but deploying them in mental health contexts requires profound care. A typical monolithic LLM approach risks generating hallucinated clinical advice, forgetting long-term user context, or failing to identify crisis situations.

To overcome these hurdles, this project introduces "Zoya", a multi-agent architecture for mental health support. By delegating tasks—such as empathy generation, crisis detection, memory retrieval, and clinical reasoning—to specialized modules or "agents", the system ensures a safer, more structured interaction. Zoya incorporates evidence-based grounding through RAG (Retrieval-Augmented Generation) on real mental health literature, offering a cohesive, empathetic chat experience with seamless clinical calibration (PHQ-9/GAD-7).

## 2. PROBLEM STATEMENT
Current digital mental health interventions and generic AI chatbots face several critical issues:
- **Lack of specialized empathy and context retention**: Standard chatbots forget past sessions and fail to adapt to a user’s emotional state.
- **Safety and Crisis Risks**: Generic models might inadvertently give harmful advice or fail to recognize signs of self-harm.
- **Absence of clinical grounding**: Responses are often generic platitudes rather than evidence-based techniques (like CBT or DBT).
- **Intrusive assessments**: Traditional apps ask users to fill out long, clinical surveys before offering help, causing drop-offs.

There is a need for a unified, intelligent system that can converse empathetically, retain memory, ground itself in clinical literature, perform seamless psychological calibration, and ensure absolute safety during interactions.

## 3. MOTIVATION
The motivation for this project stems from the growing global mental health crisis and the barriers to accessing immediate care. While an AI cannot replace a human therapist, it can serve as a compassionate, accessible first-line responder or a supportive companion. 

By utilizing a multi-agent design alongside self-hosted models (Qwen-3.4B), we can ensure data privacy and fine-grained control over the conversational flow. The opportunity to weave standard psychological instruments (like the PHQ-9 for depression and GAD-7 for anxiety) seamlessly into a natural conversation presents a novel approach to digital well-being that prioritizes user comfort while maintaining clinical utility.

## 4. OBJECTIVES
The core objectives of the project are:
- **Develop a Multi-Agent Architecture**: Design an orchestrator that coordinates safety checks, session state, and LLM inference.
- **Implement Seamless Calibration**: Silently track user engagement (word count and time) to determine the right moment to inject mental health questionnaire items.
- **Integrate Psychological Instruments**: Systematically incorporate PHQ-9 and GAD-7 questions into the chat flow without breaking conversational immersion.
- **Enable Evidence-Based Responses (RAG)**: Use ChromaDB and Google embeddings to retrieve context from mental health research papers and inform the LLM's replies.
- **Ensure Safety**: Implement pre- and post-generation safety classifiers to catch crisis keywords and prevent diagnostic or medical advice.
- **Provide an Intuitive UI**: Build a responsive Next.js frontend to interact with the backend APIs seamlessly.

## 5. LITERATURE REVIEW
Our approach is informed by recent advancements in Empathetic AI, LLMs in healthcare, and stress detection:
- **Empathetic and Conversational AI**: W. Chen et al. (2025) explored multimodal emotion detection in real-time dialogs, while M. O'Brien et al. (2024) demonstrated zero-shot stress detection using LLMs. These studies validate the potential for LLMs to interpret user emotional states.
- **Ethical and Clinical Implications**: Coghlan, Leins et al. (2023) and Mayor (2025) highlighted the ethical risks of chatbots in mental health, emphasizing the necessity of strict guardrails (as implemented in our safety classifier). 
- **Healthcare LLMs**: Chow, Wong et al. (2024) discussed the current trends and challenges of GPT-empowered healthcare conversations, highlighting the need for retrieval-augmented grounding to prevent hallucinations.
Our project builds upon these findings by enforcing a modular architecture where empathy is balanced with strict safety protocols and grounded clinical knowledge.

## 6. MULTI-AGENT AI CONCEPT
Instead of relying on a single prompt to a massive LLM, Zoya is built on a multi-agent concept where an orchestrator routes data through specialized modules. 
- **The Orchestrator** acts as the central router. It receives the user message and coordinates the workflow.
- **The Agents / Modules** handle specialized tasks:
  - **Safety Classifier**: Evaluates input/output for risk.
  - **Session & Calibration Tracker**: Manages the state of the conversation.
  - **Questionnaire Controller**: Manages the state of PHQ-9 and GAD-7 items.
  - **Memory/Context Retriever**: Fetches history and RAG documents from ChromaDB.
  - **Inference Engine**: The LLM (Qwen-3.4B) that generates the final empathetic response based on the synthesized context.

## 7. PROPOSED SYSTEM
The proposed system, Zoya, involves a Next.js frontend communicating with a FastAPI backend. 
When a user sends a message, it first passes through a Safety Classifier. If deemed safe, the system updates a background Calibration Tracker (tracking word counts and session duration). Based on the calibration status, the Orchestrator may request the Questionnaire Controller to inject a specific assessment question (e.g., a PHQ-9 item) into the LLM's prompt. 
Simultaneously, the RAG layer uses Google text embeddings to fetch relevant clinical research from a ChromaDB vector store. The Qwen-3.4B model synthesizes all this context to generate a response, which undergoes a final safety check before being sent to the user.

## 8. SYSTEM ARCHITECTURE
The system architecture consists of decoupled frontend and backend layers:

- **Frontend (Next.js)**: Handles the UI, maintaining a chat interface with a visual (but unobtrusive) calibration progress bar.
- **Backend (FastAPI)**: Exposes the `/chat` endpoint.
  - **`orchestrator.py`**: The main pipeline coordinating all logic.
  - **`session.py` & `questionnaire.py`**: Manage the seamless calibration and questionnaire injection.
  - **`inference.py`**: Loads the 4-bit quantized Qwen-3.4B model.
  - **`safety.py`**: The pre/post-generation safety classifier.
  - **`rag.py` & `embeddings.py`**: Manages ChromaDB and Google text-embedding-004 to fetch relevant papers.
- **Data Layer**: ChromaDB stores document chunks and user facts.

## 9. REQUEST LIFECYCLE AND CALIBRATION
Zoya uses a "Seamless Calibration" flow. Users are never presented with a clinical form to fill out upfront. 
1. The user begins chatting normally.
2. `session.update_calibration()` accumulates the user's word count and time spent.
3. A progress metric (0-100%) is calculated. The frontend displays a subtle progress bar.
4. Once calibrated (e.g., >500 words or 1800 seconds), `is_calibrated()` returns True.
5. Post-calibration, the system begins interleaving clinical assessment questions into the natural conversation.

## 10. PSYCHOLOGICAL QUESTIONNAIRES & RAG
**Questionnaires**: The `questionnaire.py` module contains the standard PHQ-9 (depression) and GAD-7 (anxiety) indices. Instead of asking them sequentially like a test, they are injected into the LLM prompt context every few turns (e.g., `INJECTION_INTERVAL = 3`). The LLM is instructed to naturally weave the question into its empathetic response.
**RAG (Retrieval-Augmented Generation)**: The backend uses `ingest_papers.py` to chunk PDFs (e.g., Mental Health NLP Learnings) and store them in ChromaDB. During inference, semantic search retrieves clinical techniques (like CBT or DBT grounding exercises) to ensure the LLM's advice is evidence-based.

## 11. AI/ML INFERENCE & SAFETY CLASSIFIER
- **Inference**: The system uses a self-hosted Qwen-3.4B model, loaded with `BitsAndBytesConfig` in 4-bit quantization for hardware efficiency. The system prompt enforces Zoya's persona as an empathetic, non-diagnostic listener.
- **Safety**: A crucial component. `safety.classify()` runs on the user's input. If crisis keywords (self-harm, severe abuse) are detected, it overrides the LLM and instantly returns a hardcoded crisis intervention response (e.g., helpline numbers). The output of the LLM is also classified to prevent the model from generating diagnostic labels or medical prescriptions.

## 12. TECHNOLOGY STACK
| Component | Technology | Purpose |
|---|---|---|
| **Frontend** | React, Next.js, Vanilla CSS | User interface, chat rendering, proxy rewrites to backend. |
| **Backend API** | Python, FastAPI, Uvicorn | RESTful API architecture, orchestration logic. |
| **LLM Inference** | HuggingFace Transformers, Qwen-3.4B | Generative AI for empathetic conversations. |
| **Embeddings & RAG** | Google `text-embedding-004`, ChromaDB | Vector storage and semantic search over clinical papers. |
| **Data Management** | Pydantic | Strict request/response schema validation. |

## 13. IMPLEMENTATION METHODOLOGY
1. **Infrastructure Setup**: Initialized Next.js frontend and FastAPI backend.
2. **Data Ingestion**: Wrote scripts to chunk and embed mental health research PDFs into ChromaDB.
3. **Core Orchestration**: Built the multi-agent pipeline in `orchestrator.py`.
4. **Calibration Logic**: Implemented `session.py` to track word counts and time without interrupting the user.
5. **Questionnaire Integration**: Added PHQ-9/GAD-7 datasets and the round-robin injection logic.
6. **LLM Integration**: Integrated Qwen-3.4B with 4-bit quantization.
7. **Safety Guardrails**: Implemented the safety classifier stubs and overriding logic.
8. **UI Refinement**: Built a dark-themed, calming Next.js UI with a calibration progress bar.

## 14. WORKFLOW
The continuous loop of interaction operates as follows:
1. User submits a message via the Next.js UI.
2. The FastAPI backend receives the POST request.
3. Safety classifier checks the user message.
4. Session tracker updates the calibration word count and duration.
5. If calibrated, the orchestrator retrieves a pending PHQ-9/GAD-7 item.
6. RAG layer retrieves relevant session history and clinical literature from ChromaDB.
7. The context, questionnaire item, and user message are formatted into a prompt.
8. Qwen-3.4B generates a response.
9. Safety classifier checks the response.
10. The frontend receives the response and updates the UI.

## 15. EXPERIMENT / SCENARIO DESIGN
To validate the system, the following test scenarios are planned:
- **Scenario 1: Normal Conversation**: The user chats about daily stress. Expected: System provides empathetic responses, calibration bar fills up steadily.
- **Scenario 2: Post-Calibration Injection**: The user completes calibration. Expected: The system naturally weaves a PHQ-9 question (e.g., "Have you been feeling down or hopeless lately?") into the conversation.
- **Scenario 3: Crisis Detection**: The user types a high-risk phrase. Expected: The safety classifier intercepts the message immediately and provides emergency helpline information, bypassing the standard LLM generation.
- **Scenario 4: Clinical Grounding**: The user asks for help with anxiety. Expected: The RAG layer retrieves CBT grounding exercises (e.g., 5-4-3-2-1 technique) from the database and presents them to the user.

## 16. RESULTS AND DISCUSSION
*(Note: As this is a design and architectural report, specific empirical metrics will be added post-deployment).* 
The expected results are a highly responsive chat interface where users feel heard and supported. The seamless calibration is expected to drastically reduce the drop-off rates typically associated with clinical intake forms. The safety classifier should yield a 100% interception rate for explicitly flagged crisis keywords, ensuring a fail-safe environment.

## 17. ADVANTAGES
- **Seamless User Experience**: Users aren't forced to fill out forms; assessments happen naturally.
- **High Privacy**: By using a locally hosted LLM (Qwen-3.4B), sensitive mental health data doesn't need to be sent to third-party APIs.
- **Evidence-Based Support**: RAG ensures advice is grounded in peer-reviewed clinical research.
- **Safety First**: Hardcoded safety layers prevent the AI from "hallucinating" dangerous medical advice.

## 18. LIMITATIONS
- **Hardware Constraints**: Running a 3.4B parameter model locally requires adequate VRAM, limiting deployment on low-end edge devices.
- **Context Window Limits**: Long-term memory relies on RAG; the LLM cannot hold an infinitely long conversation in its immediate context window.
- **Not a Medical Device**: The system cannot formally diagnose or treat severe psychiatric illnesses. It is strictly a supportive tool.

## 19. APPLICATIONS
- **University Counseling Centers**: As a first-line triage tool to support students while they wait for human counselors.
- **Employee Wellness Programs**: Integrated into corporate portals to offer employees anonymous, accessible stress-management support.
- **Companion Apps**: As a personal journaling and grounding assistant for individuals managing mild anxiety or depression.

## 20. FUTURE SCOPE
- **Voice Integration**: Adding Speech-to-Text and Text-to-Speech layers to allow for conversational voice interactions.
- **Multimodal Emotion Detection**: Integrating facial expression analysis or vocal tone analysis to better gauge the user's emotional state, as suggested in recent literature.
- **Advanced Safety Classifier**: Replacing the current rule/keyword-based safety stub with a fine-tuned BERT/RoBERTa model for nuanced risk classification.
- **Federated Learning**: Allowing multiple decentralized instances of the agent to learn conversation patterns without sharing raw user data.

## 21. CONCLUSION
This project successfully outlines a robust, safe, and intelligent architecture for a mental health support agent. By moving away from monolithic LLM prompts and adopting a multi-agent design, "Zoya" ensures that empathy, clinical grounding, and safety are handled systematically. The introduction of seamless calibration represents a significant UX improvement for digital mental health tools. Ultimately, while this system does not replace human professionals, it demonstrates how carefully engineered AI can provide scalable, evidence-based, and compassionate support.

## 22. TEAM CONTRIBUTION
This project was carried out jointly by the two team members. The specific division of work is summarised below:
- **Avra Paul**: Designed the Orchestrator, implemented the FastAPI backend, integrated the Qwen-3.4B model, and developed the seamless calibration logic.
- **Nomesh Singh**: Handled data ingestion, RAG implementation using ChromaDB, built the safety classifier modules, and developed the Next.js frontend UI.
Both team members were jointly involved in the overall planning, discussion, and review of the project report.

## 23. REFERENCES
[1] W. Chen, et al., "Towards Empathetic AI: Multimodal Emotion and Stress Detection in Real-Time Dialog Systems," AAAI, 2025.
[2] M. O'Brien, et al., "Zero-Shot Stress Detection in Conversational Data using LLMs," ACL Findings, 2024.
[3] Simon Coghlan, Kobi Leins et al., "To chat or bot to chat: Ethical issues with using chatbots in mental health," Digital Health, 2023.
[4] James C. L. Chow, Valerie Wong et al., "Generative Pre-Trained Transformer-Empowered Healthcare Conversations: Current Trends, Challenges, and Future Directions in Large Language Model-Enabled Medical Chatbots," BioMedInformatics, 2024.
[5] Eric Mayor, "Chatbots and mental health: a scoping review of reviews," Current Psychology, 2025.

## 24. APPENDIX

**A.1 Sample Interaction (Seamless Calibration)**
```
User: I'm feeling really overwhelmed with work lately.
Zoya (Orchestrator -> LLM): I hear you. It sounds like work is putting a lot of weight on your shoulders right now. Do you want to talk about what's specifically causing the most stress?
[Background: Calibration word count + 8, Time updated]
```

**A.2 Sample Interaction (Questionnaire Injection)**
```
[Background: Calibration == 100%, Turn % 3 == 0, injecting PHQ-9 Item 1]
User: I just can't seem to focus on anything.
Zoya (Orchestrator -> LLM): It's tough when your focus isn't there, especially when you're already overwhelmed. Over the last two weeks, have you found yourself having little interest or pleasure in doing things you usually enjoy?
```

**A.3 Sample Interaction (Safety Override)**
```
User: I can't take this anymore, I just want it all to end.
[Background: Safety Classifier flags high risk]
Zoya (Crisis Intervention): I'm so sorry you're feeling this much pain right now. Please know you don't have to go through this alone. Please reach out to emergency services or call the National Suicide Prevention Lifeline immediately. Help is available.
```

**A.4 System Requirements**
- Minimum 16GB RAM for loading the 4-bit quantized Qwen-3.4B model.
- Node.js (v18+) for frontend compilation.
- Python 3.10+ for backend services.

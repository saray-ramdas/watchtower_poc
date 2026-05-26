Problem Statement
As LLM usage increases, sending user prompts containing Personally Identifiable Information (PII) directly to AI models creates privacy and security risks. Users may unintentionally or intentionally request sensitive information belonging to others, such as bank account details or personal identifiers. The challenge is to develop a secure framework that performs security validation, masks sensitive information, and safely manages prompt flow before interacting with LLMs.
Project Overview – Watch Tower Setup
The project aims to build a Watch Tower security framework that acts as a protective layer between users and LLMs. The system first performs security checks to validate user requests and enforce guardrails, ensuring that unauthorized access or requests are restricted (for example, User 1 should not be able to request User 2's bank account details).
After the security validation, the system performs PII masking using Microsoft Presidio and Qwen to detect and anonymize sensitive information. This entire security and masking process takes place in the local LLM setup (using Groq).
Once the prompt is secured and sanitized, it is forwarded to the Orchestrator (Super Admin), which acts as the second LLM (also using Groq) and manages the workflow using LangGraph.
The multi-agent architecture consists of:
Orchestrator (Super Admin) – coordinates and manages all agents
Savings Agent -  get bal and get years_in_bank
Prize Money Agent - checks eligibility
Response Agent - sends response yes or no
Reasoning and Action Agent (ReAct) – handles malicious intent users
The framework also includes security guardrails, SDK setup, and a UI comparison showing outputs with and without the Watch Tower setup, allowing users to observe the difference between direct LLM interactions and privacy-protected, security-enabled processing.
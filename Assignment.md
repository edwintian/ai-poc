Capstone Assignment: Building an Interactive LLM-Powered Solution
🎯 Objective
Develop a web-based application that enables citizens to interact seamlessly with publicly available information regarding a specific process or transaction with the government. The application should consolidate information or data from multiple official or trustworthy sources, facilitate a deeper understanding through interactive engagements, and present the relevant information in a way that is customised based on user inputs and in highly effective formats for users to consume.

1. Web Application
✅ Required
A fully functional, deployed web application accessible via a URL, demonstrating all required features and the two specified use cases.

The suggested platform for deploying the web application is Streamlit Community Cloud.
It is recommended to password protect the application.
2. Documentation (As Pages within the Streamlit App)
In addition to the webpages that include the required features and functionality, your Streamlit app MUST contain the following two additional pages:

"About Us" Page
A detailed page outlining the project scope, objectives, data sources, and features.
"Methodology" Page
A comprehensive explanation of the data flows and implementation details.
A flowchart illustrating the process flow for each use case in the application. Each use case should have its own flowchart.

Problem Statement
Ordinary employees in Singapore face employment contracts that are long, jargon-filled and hard to decipher; they often cannot tell whether key terms are included, whether any clause is unusual, or whether the contract complies with Singapore employment requirements. This opacity can lead to unintended commitments, unfair terms, and disputes that erode trust and complicate onboarding. How might we empower everyday workers to understand, verify, and compare their contracts for clarity, completeness, and regulatory compliance before signing, without requiring expensive legal review?

Proposed Solution
An AI-powered service where users uploads their employment contract and recieve a simple, easy-to-understand analysis based on Singapore employment laws and official Ministry of Manpower (MOM) guidance.

Can do RAG usingg Employment Act: https://share.google/CzjFq2gEAEOn1Xzbq

An LLM is well suited for a Singapore employment-contract checker because it can understand complex, inconsistent legal and contractual language, extract important terms such as salary, working hours, leave, notice periods and deductions, and explain them in plain English. Combined with RAG, the LLM can retrieve the latest information from authoritative sources such as MOM and compare the contract against those requirements, while a rules engine handles deterministic checks. The LLM should not be treated as the source of legal truth; instead, it acts as the intelligent layer that understands the contract, identifies potentially relevant issues, explains them clearly, highlights uncertainty, and suggests questions for the employee to ask, with every important finding linked back to the relevant official source.

# Implementation Brief: Singapore Employment Contract Checker

## 1. Project Overview

Build a Streamlit application that helps employees in Singapore understand their employment contracts before signing.

The app will use an LLM and Retrieval-Augmented Generation (RAG) to explain contract terms in plain English, identify potential issues, and answer questions using official Singapore employment legislation and Ministry of Manpower (MOM) guidance.

**Target users:** Everyday employees and job seekers in Singapore.

**Primary objective:** Help users understand their contractual obligations and identify terms they may need to clarify before signing.

## 2. Core Use Cases

### Use Case 1: Employment Contract Health Check

**User story:** As an employee, I want to upload my employment contract and receive a simple analysis of its key terms and potential issues before signing.

**Requirements:**

* Allow users to upload PDF employment contracts.
* Extract and summarise key terms:

  * Salary and payment frequency
  * Working hours and overtime
  * Annual leave and sick leave
  * Probation and notice periods
  * Salary deductions
  * Termination provisions
  * Confidentiality and non-compete clauses
* Identify potentially concerning, ambiguous, inconsistent, or relevant missing terms.
* Explain findings in plain English.
* Show supporting contract excerpts and links to relevant official sources.
* Suggest questions the employee may wish to ask their employer.

**Finding statuses**

Every finding must use exactly one of these three statuses:

* `Consistent`: Available evidence supports the finding, and no issue was identified by the specific check performed.
* `Needs Attention`: A potentially concerning, ambiguous, inconsistent, or relevant missing term has been identified.
* `Unable to Assess`: There is insufficient information, context, or evidence to reach a reliable conclusion.

Do not use additional statuses such as `Missing`, `Compliant`, or `Potentially Non-Compliant`. Represent missing information as a finding with one of the three statuses above.

A missing clause does not automatically constitute a legal violation. Assess whether its absence matters under the applicable requirements and circumstances.

For each finding, display:

* Employment term
* Status
* Extracted contract wording, where available
* Plain-English explanation
* Reason for the assessment
* Relevant official source and citation, where applicable
* Suggested question for the employer, where appropriate

### Use Case 2: Interactive Contract Q&A

**User story:** As an employee, I want to ask questions about my uploaded contract and receive understandable answers grounded in my contract and official Singapore employment guidance.

**Requirements:**

* Provide a simple chat interface after a contract has been uploaded.
* Allow natural-language questions, such as:

  * "How much notice must I give if I resign?"
  * "Can my employer deduct money from my salary?"
  * "Am I entitled to overtime pay?"
  * "What happens if I resign during probation?"
* Retrieve relevant passages from both the uploaded contract and the existing legal knowledge base.
* Generate concise, plain-English answers based on the retrieved evidence.
* Display relevant contract excerpts, page references where available, and official source links.
* Clearly communicate uncertainty and avoid guessing when evidence is insufficient.
* Preserve recent conversation history using `st.session_state`.

Reuse the same document extraction, embedding model, vector database, and RAG pipeline as Use Case 1. Do not build a separate knowledge base.

## 3. Technology Stack

Use:

* Python
* Streamlit
* An API-accessible LLM
* PyMuPDF or pdfplumber for PDF text extraction
* An embedding model
* FAISS or Chroma as the vector store
* Pydantic or equivalent for structured output validation
* pytest for basic automated tests

Keep the implementation simple and modular. Store credentials in environment variables or Streamlit secrets, never directly in source code.

If no LLM provider has been selected, make the provider configurable and document the required setup.

## 4. RAG Knowledge Base

Use authoritative Singapore employment sources:

* Employment Act 1968: https://sso.agc.gov.sg/Act/EmA1968
* MOM employment practices: https://www.mom.gov.sg/employment-practices
* MOM contract of service guidance: https://www.mom.gov.sg/employment-practices/contract-of-service

Verify source accessibility and current content before indexing.

Implement a basic RAG pipeline:

1. Ingest relevant official documents.
2. Extract and chunk text while preserving source titles, URLs, and section identifiers.
3. Generate embeddings and store chunks in a vector database.
4. Retrieve relevant passages for contract analysis and user questions.
5. Generate answers grounded in the retrieved evidence.
6. Display citations linking to the original sources.

The LLM must not be treated as the source of legal truth. Distinguish statutory requirements from general guidance and contractual considerations. Never invent legal citations.

Provide a simple way to initialise or rebuild the knowledge base. If automatic source ingestion is impractical, support manually downloaded official documents and document the process.

## 5. Analysis Architecture

Keep three logical components.

**Document parser**

* Extract contract text from PDF files.
* Preserve page references where possible.
* Handle invalid, empty, or unreadable documents gracefully.

**RAG pipeline**

* Retrieve relevant contract passages and official legal sources.
* Generate plain-English explanations with evidence.
* Return citations and indicate when the evidence is insufficient.

**Optional deterministic rules engine**

* Implement a small number of well-defined checks where applicable.
* Verify relevant employee circumstances before applying statutory requirements.
* Return `Unable to Assess` when required information is insufficient.
* Avoid inferring legal compliance merely because a clause exists.

The LLM may identify and explain potential issues, but deterministic rules should handle checks that can be expressed reliably as explicit conditions.

## 6. Streamlit UI

Create a clean, approachable interface with two tabs or pages.

### Contract Health Check

* PDF uploader
* Optional employment context fields where needed
* Analyze button and simple progress feedback
* Summary of extracted key terms
* Findings table using the three agreed statuses
* Expandable contract excerpts and explanations
* Relevant official source links

### Ask Your Contract

* Chat input and conversation history
* Answers grounded in the uploaded contract and legal knowledge base
* Supporting contract excerpts and official citations
* Clear handling of insufficient evidence

Include a brief disclaimer that the app provides educational information and is not a substitute for professional legal advice.

Avoid rerunning the entire analysis on every UI interaction. Use Streamlit session state and caching where appropriate.

## 7. Privacy and Error Handling

For this capstone prototype:

* Do not log full contract contents by default.
* Keep API keys outside source code.
* Avoid retaining uploaded documents longer than necessary.
* Provide a way to clear the current session's contract and results.
* Explain when document content is sent to an external LLM provider.
* Handle invalid PDFs, empty documents, API errors, retrieval failures, and malformed LLM responses.
* Never fabricate findings or citations when a service fails.

Document the prototype's privacy limitations rather than claiming production-grade security.

## 8. Testing

Include basic tests for:

* PDF extraction
* Empty-document handling
* Structured output validation
* Retrieval and citation formatting
* The three finding statuses
* Error handling

Use synthetic sample contracts to demonstrate:

* Clearly stated employment terms
* Relevant missing information
* Ambiguous clauses
* Potentially concerning deductions
* Different notice periods and leave arrangements

Use mocked LLM responses for automated tests where practical to avoid unnecessary API costs.

## 9. Project Structure

Use a simple, modular structure such as:

```text
singapore-contract-checker/
├── app.py
├── src/
│   ├── document_parser.py
│   ├── knowledge_base.py
│   ├── rag_pipeline.py
│   ├── contract_analyser.py
│   ├── rules_engine.py
│   └── schemas.py
├── data/
│   └── knowledge_base/
├── tests/
├── sample_contracts/
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

Adapt the structure to the existing repository if applicable. Avoid unnecessary abstractions.

## 10. Acceptance Criteria

The application is complete when:

1. A user can upload a PDF and receive a structured contract health check.
2. Key employment terms are extracted and summarised.
3. Each finding uses exactly one of the three agreed statuses: `Consistent`, `Needs Attention`, or `Unable to Assess`.
4. Findings include understandable explanations and relevant evidence.
5. Legal claims are supported by retrieved official sources where applicable.
6. A user can ask follow-up questions about their contract and receive grounded answers.
7. Both use cases reuse the same RAG pipeline.
8. Errors and insufficient evidence are handled without fabricated answers.
9. Basic automated tests and setup documentation are provided.

## 11. Instructions to Claude

Please inspect the existing repository first, if available, and implement the application rather than providing only a tutorial or architecture proposal.

Build Use Case 1 first, then implement Use Case 2 by reusing the same backend components.

Prioritise a working end-to-end MVP over extensive abstractions or extra features. Do not implement contract comparison, user accounts, advanced agent workflows, or other deferred features unless explicitly requested.

Do not replace actual document processing or retrieval with hardcoded example results. If API credentials or external services are unavailable, implement the integration and explain how to configure it.

Run the available tests and provide:

* Instructions to install and run the application
* Required environment variables
* Knowledge-base setup instructions
* A summary of implemented functionality
* Any known limitations or incomplete components

Make sensible implementation decisions without asking questions unless something genuinely blocks progress.


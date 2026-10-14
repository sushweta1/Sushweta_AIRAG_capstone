# Stakeholder Map — FastAPI Knowledge Assistant

## 1. Primary User

The primary users are developers who are learning or using FastAPI and need quick, reliable answers while developing Python API applications.

They may need information about topics such as request validation, dependencies, asynchronous programming, testing, and deployment. Instead of manually navigating multiple FastAPI documentation pages, they need a concise answer that is grounded in the relevant official documentation.

## 2. Secondary Stakeholders

Secondary stakeholders include:

- **Development teams and technical mentors** — their work is augmented because the assistant can help developers independently resolve common FastAPI questions.
- **Documentation and knowledge owners** — their documentation provides the source material used by the assistant and must remain accurate and current.
- **Security and governance stakeholders** — act as gatekeepers by ensuring that the AI application follows appropriate security, privacy, and responsible-AI practices.
- **Project sponsors and technical leadership** — need evidence that the assistant provides useful and reliable answers without introducing unacceptable quality or operational risks.

## 3. Before-AI Workflow

Today, a developer with a FastAPI question typically searches the official documentation, navigates between multiple pages, reads examples, and determines which information applies to the problem being solved.

If the answer is not immediately clear, the developer may perform additional searches or ask another developer or technical mentor for help.

This process can require several searches and document reviews for a single question, increasing the time required to find information and potentially causing the same common questions to be researched repeatedly.

## 4. Desired After-State

With the FastAPI Knowledge Assistant, a developer can ask a natural-language question and receive a concise answer grounded in the selected FastAPI documentation.

The assistant should retrieve relevant information from the documentation, generate an answer based on that evidence, and provide source information where applicable.

If the available documentation does not provide sufficient evidence, the assistant should indicate that it is unsure rather than inventing an answer. This should reduce manual searching while preserving accuracy and traceability.

## 5. Top 3 Sponsor Metrics

1. **Answer Quality**  
   Measure the percentage of responses that meet defined accuracy, groundedness, and format criteria using a representative golden-set evaluation.

2. **Time to Find Information**  
   Compare the time required to obtain an answer using the FastAPI Knowledge Assistant with the time required to manually search the selected FastAPI documentation.

3. **Unsupported-Answer Handling**  
   Measure how reliably the assistant identifies questions that cannot be answered from the available documentation instead of generating unsupported information.
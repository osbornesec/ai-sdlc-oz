# AI Contextual Processing Logic for Markdown Documents

This document outlines the expected AI behavior for understanding and interacting with Markdown documents that may contain specialized `ai-chat` and `ai-qa` blocks. The goal is to enable the AI to be context-aware, leveraging the document's content and structure to provide more relevant and helpful responses.

## 1. General Contextual Understanding

The AI should possess a foundational understanding of the document it is currently processing or interacting with.

*   **Scope Awareness:**
    *   The AI should recognize whether it's operating within a specific project, repository, or a standalone document.
    *   It should be able to access and consider other relevant documents within the same scope (e.g., other files in a `docs/` directory, related project files if explicitly referenced or discoverable).
*   **Document Type Awareness:**
    *   The AI should attempt to identify the type or purpose of the Markdown document (e.g., PRD, technical design, tutorial, task list, general notes).
    *   This understanding helps tailor the AI's responses and suggestions to be more appropriate for the document's context. For example, when processing a PRD, questions about user stories might be more relevant than implementation details.
*   **User Query Context:**
    *   When a user asks a question, the AI should consider the content immediately surrounding the cursor position or any selected text as primary context.
    *   It should also consider the broader context of the section and the entire document to provide comprehensive answers.

## 2. Handling `ai-chat` Blocks

`ai-chat` blocks represent conversational exchanges. The AI's interaction with these blocks depends on the user's intent.

*   **Reading/Understanding:**
    *   The AI should parse `ai-chat` blocks as transcripts of conversations.
    *   It should understand the roles (e.g., `user:`, `assistant:`, or other defined personas) and the flow of dialogue.
    *   This content can be used as context for answering user questions about the discussion captured in the chat.
*   **Contributing to Existing `ai-chat` Blocks:**
    *   If a user places their cursor within an existing `ai-chat` block and asks a question or makes a statement, the AI should understand that the user intends to continue that specific conversation.
    *   The AI's response should be formatted as a new entry in the chat block, following the established persona (e.g., `assistant:`).
*   **Generating New `ai-chat` Blocks:**
    *   Users might ask the AI to summarize a discussion, document a decision-making process, or brainstorm ideas. In such cases, the AI can generate a new `ai-chat` block to capture this interaction.

## 3. Handling `ai-qa` Blocks

`ai-qa` blocks represent question-answer pairs. These can be user-initiated or AI-initiated.

*   **User-Initiated Q&A (Reading/Understanding):**
    *   The AI should parse `ai-qa` blocks, recognizing the `question:` and `answer:` parts.
    *   This content serves as a knowledge base. If a user asks a question that is already answered in an `ai-qa` block, the AI can point to or summarize that existing answer.
*   **AI-Initiated Q&A / Proactive Suggestions:**
    *   **Contextual Triggers:** The AI can proactively identify terms, concepts, or sections within the Markdown document that might warrant further explanation or clarification for the user.
    *   **Offering Explanation:** Upon identifying such a trigger, the AI can propose an explanation by generating an `ai-qa` block.
        *   The `question:` part would be formulated by the AI, offering to explain the term/concept (e.g., "AI: I notice 'OAuth 2.0' is mentioned. Would you like a brief explanation?").
        *   The `answer:` part would initially be empty or contain a placeholder.
    *   **User Confirmation:** The user can then confirm if they want the explanation (e.g., by typing "Yes" or interacting with a UI element).
    *   **Generating the Answer:** If confirmed, the AI generates the detailed answer within the `answer:` part of the `ai-qa` block.

## 4. "Explain This" Feature

The "Explain This" feature is a specific type of user-initiated Q&A, often invoked via a context menu or command when the user selects a piece of text.

*   **Input to AI:**
    *   The selected text from the Markdown document.
    *   The surrounding context (paragraph, section) to help the AI understand how the term is being used.
*   **AI Processing:**
    *   The AI's goal is to explain the selected text *in the context of the document*.
    *   It should first check if an existing `ai-qa` block in the document already explains the term adequately.
    *   If not, it should generate a new explanation.
*   **Expected Output:**
    *   The AI should generate an `ai-qa` block.
    *   The `question:` part will be formulated based on the selected text (e.g., "User (via 'Explain This'): Can you explain 'Data Sharding'?").
    *   The `answer:` part will contain the AI's explanation, tailored to the context.
    *   This new `ai-qa` block would typically be inserted near the selected text or at a location specified by the user.

## 5. Guided Refinement

Guided refinement refers to the AI's ability to help users improve the content of the Markdown document based on its understanding and specialized knowledge (e.g., if the AI is primed as a "PRD reviewer" or "Technical Writer").

*   **Identifying Areas for Improvement:**
    *   Based on its role or specific instructions (like those in prompt templates for PRD reviews), the AI can identify areas in the document that are unclear, ambiguous, incomplete, or inconsistent.
*   **Suggesting Changes or Asking Clarifying Questions:**
    *   The AI can make suggestions directly (e.g., "This section on User Roles could be more detailed. Consider adding specific permissions for each role.").
    *   It can also ask clarifying questions, potentially using `ai-chat` or `ai-qa` blocks to interact with the user about a specific part of the document. For example, in an `ai_sdlc/prompts/02-prd-plus.prompt.yml` context, the AI would pose questions to challenge assumptions in a PRD.
*   **Incorporating Feedback:**
    *   The user's responses to these suggestions or questions should be used by the AI to further refine its understanding and help the user update the document.
    *   The AI might propose specific text changes or additions based on the dialogue.

This contextual processing logic aims to make AI a more integrated and intelligent partner in the document creation and maintenance lifecycle.

# Feature: Contextual Chat & Q&A within AI-SDLC Documents

## 1. Introduction

The Contextual Chat & Q&A feature enhances your experience working with AI-SDLC documents (like PRDs, architectural designs, task lists, etc.) by providing real-time, context-aware assistance directly within your Markdown files.

This means you can "talk" to an AI about the document you're working on, ask questions, seek clarifications, or even have the AI proactively suggest improvements or explanations, all without leaving your editor. The AI understands the content of your document and uses that understanding to give you relevant and helpful responses.

These interactions are captured in special Markdown blocks: `ai-chat` for ongoing discussions and `ai-qa` for specific question-answer pairs.

## 2. Using the `ai-chat` Block

The `ai-chat` block is designed to embed discussion threads or conversational exchanges with an AI assistant directly within your Markdown document. This is useful for capturing design discussions, brainstorming, or clarifying requirements in context.

**Syntax:**

To start or continue a discussion, you can use the following format:

```markdown
```ai-chat
User: [Your question or comment related to the document]
AI: [AI's response, informed by the document's content]
User: [Your follow-up]
AI: [AI's further response]
```
```

**How it Works:**
When you type a question or comment within an `ai-chat` block (following the `User:` prefix), the AI will read your query and the surrounding document content. It will then generate a response, typically prefixed with `AI:`, that is relevant to both your query and the document's context.

**Example:**

Imagine you're working on a Product Requirements Document (PRD) and have a question about a user story:

```markdown
## User Stories

*   **US-003:** As a registered user, I want to receive email notifications for important account activity (e.g., password change, new login from an unrecognized device) so that I am aware of potential security issues.

    ```ai-chat
    User: For US-003, are we sure about notifying for *every* new login from an unrecognized device? Could that be too noisy if a user travels frequently?
    AI: That's a valid concern. We could refine this to notify for unrecognized devices and also consider adding a "trust this device" option. Alternatively, we could make the sensitivity of this notification configurable by the user.
    User: Let's explore the "trust this device" option. That seems like a good balance.
    ```
```

## 3. Using the `ai-qa` Block

The `ai-qa` block is used for specific question-and-answer interactions. This can be for questions you explicitly ask the AI, for the AI to proactively offer explanations or suggestions, or as a result of using an "Explain This" feature.

**Syntax for User Questions:**

You can ask the AI to explain a term or concept within the context of the current document.

```markdown
```ai-qa
User: Can you explain the 'microservices architecture' mentioned in section 2.1 in the context of this project's scalability goals?
AI: In the context of this project, the 'microservices architecture' is proposed to enhance scalability by allowing independent scaling of individual services based on demand. For example, if the user authentication service experiences high load, we can scale it up without affecting the order processing service, optimizing resource use and maintaining performance.
```
```

**AI-Proactive Suggestions & Clarifications:**

Sometimes, the AI might proactively identify areas in your document that could be improved or might need further clarification. It can use an `ai-qa` block to make a suggestion or ask a question.

```markdown
```ai-qa
AI: The section on 'Deployment Strategy' outlines the steps for a blue/green deployment, but it doesn't seem to cover how database schema migrations will be handled during this process. Would you like to add details on that?
User: Yes, that's an important point. Let's add a sub-section for database migration handling.
AI: Great. I can help you draft that. Do you have an existing strategy for zero-downtime schema migrations, or should we explore some common patterns?
```
```

## 4. "Explain This" Feature

You may encounter an "Explain This" option in your editing environment (e.g., by right-clicking on selected text or using a keyboard shortcut). When you use this feature on a piece of text in your Markdown document, the AI will aim to provide a contextual explanation.

This interaction will likely result in an `ai-qa` block being inserted into your document, with the `question:` part reflecting your query ("Explain [selected text]") and the `answer:` part containing the AI's explanation.

## 5. Context Awareness

The key benefit of this feature is the AI's **context awareness**. The AI doesn't just give generic answers; it tailors its responses, explanations, and suggestions based on the actual content of the Markdown file you are currently working in. This makes the assistance more relevant, accurate, and useful for your specific project or document.

## 6. Further Details

This document provides a user-facing overview of the Contextual Chat & Q&A feature. For those interested in the specific Markdown syntax rules or the underlying AI processing logic, the following documents provide more in-depth information:

*   `docs/markdown_chat_syntax.md`: Detailed syntax specifications for `ai-chat` and `ai-qa` blocks.
*   `docs/ai_contextual_processing_logic.md`: Explanation of how the AI is expected to understand and process these blocks and the document context.

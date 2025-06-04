# Markdown Syntax Extensions for AI Interactions

This document proposes extensions to Markdown syntax to support AI chat and question/answer blocks within `.md` files.

## `ai-chat` Block

The `ai-chat` block is designed to represent a conversation with an AI assistant. This is particularly useful for capturing design discussions, brainstorming sessions, or any interactive dialogue with an AI.

**Syntax:**

````markdown
```ai-chat
user: What are some best practices for API design?
assistant: Some best practices include:
    - Using nouns for resource identification.
    - Implementing versioning from the start.
    - Providing clear and comprehensive documentation.
    - Using standard HTTP methods correctly (GET, POST, PUT, DELETE).
    - Ensuring proper error handling with informative status codes.
user: What about security considerations?
assistant: For security:
    - Use HTTPS.
    - Implement strong authentication and authorization mechanisms (e.g., OAuth 2.0).
    - Validate all input.
    - Protect against common vulnerabilities like injection attacks.
```
````

**Example: API Design Discussion**

```ai-chat
user: We're designing a new API for our e-commerce platform. What are the key considerations for the product endpoint?
assistant: For a product endpoint, you should consider:
    - `GET /products`: List all products (with pagination, filtering, sorting).
    - `GET /products/{id}`: Retrieve a specific product by ID.
    - `POST /products`: Create a new product (admin only).
    - `PUT /products/{id}`: Update an existing product (admin only).
    - `DELETE /products/{id}`: Delete a product (admin only).
    - What fields should be included in the product representation? (e.g., name, description, price, SKU, stock quantity, images, categories)
user: Should we include customer reviews directly in the product response or link to a separate reviews endpoint?
assistant: That depends on the expected usage.
    - **Embedding:** Simpler for clients if reviews are frequently needed with product details. Can lead to large response sizes.
    - **Linking:** Better if reviews are optional or extensive. Keeps the product payload lean (e.g., `/products/{id}/reviews`).
    - You could also provide a summary (average rating, review count) and link to full reviews.
```

## `ai-qa` Block

The `ai-qa` block is intended for question and answer interactions, often initiated by the AI or for documenting specific AI-generated explanations. This can be used for proactive AI suggestions, "Explain This" features, or clarifying questions from the AI.

**Syntax:**

````markdown
```ai-qa
question: What is Jinja2 and why is it used?
answer: Jinja2 is a modern and designer-friendly templating engine for Python.
    It is used to generate dynamic content by embedding expressions and logic within text-based files (like HTML, XML, or configuration files).
    Key features include:
    - **Template Inheritance:** Allows creating base templates with common structures.
    - **Sandboxed Execution:** Provides a secure environment for template rendering.
    - **Filters and Tags:** Offers powerful tools for data manipulation and control flow.
    - **Autoescaping:** Helps prevent XSS vulnerabilities by default for HTML.
```
````

**Example: Proactive AI Question about "Jinja2"**

This example shows how an AI might proactively ask a clarifying question or offer to explain a term it detects in the documentation.

```ai-qa
question: I notice you mentioned "Jinja2 templates" in the previous section. Would you like an explanation of what Jinja2 is and its common use cases?
answer: Jinja2 is a popular templating engine for Python. It allows you to create base templates and then fill in or override parts of them. It's widely used in web frameworks like Flask and Django for generating HTML, as well as in tools like Ansible for configuration management. Key features include template inheritance, macros, and a rich set of filters.
```

**Example: "Explain This" Feature for "OAuth 2.0"**

This illustrates how an "Explain This" feature, when invoked by a user on a term like "OAuth 2.0", would be represented.

```ai-qa
question: Can you explain OAuth 2.0?
answer: OAuth 2.0 is an authorization framework that enables applications to obtain limited access to user accounts on an HTTP service, such as Facebook, GitHub, or Google. It works by delegating user authentication to the service that hosts the user account, and authorizing third-party applications to access the user account.
    Key Roles:
    - **Resource Owner:** The user who authorizes an application to access their account.
    - **Resource Server:** The server hosting the protected user accounts (e.g., Google's servers).
    - **Client:** The application requesting access to the user's account.
    - **Authorization Server:** The server that issues access tokens to the client after successfully authenticating the Resource Owner and obtaining authorization.
    Common Grant Types:
    - Authorization Code
    - Implicit
    - Resource Owner Password Credentials
    - Client Credentials
```

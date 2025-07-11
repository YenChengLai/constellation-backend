# API Design Conventions

## 1\. Overview

This document establishes a set of design standards for all RESTful APIs within the **Constellation** ecosystem. Adhering to these conventions is crucial for maintaining consistency, predictability, and developer productivity across all microservices.

## 2\. Endpoint Naming

- **Use Plural Nouns**: Resources should be named with plural nouns to represent them as a collection.

  - **Good**: `/users`, `/expenses`, `/sessions`
  - **Bad**: `/user`, `/get-expense`

- **Path Separators**: Use hyphens (`kebab-case`) for multi-word path segments if necessary, although single words are preferred.

  - **Example**: `/workout-plans`

- **Hierarchy**: Use path nesting to represent relationships between resources.

  - **Example**: `GET /users/{user_id}/expenses` (to retrieve all expenses for a specific user).

## 3\. HTTP Methods

Use the standard HTTP methods semantically according to their defined actions.

| Method   | Action                                                                                         | Example                                     | Success Status    |
| :------- | :--------------------------------------------------------------------------------------------- | :------------------------------------------ | :---------------- |
| `GET`    | Retrieve a list of resources or a single resource.                                             | `GET /expenses`, `GET /expenses/{expense_id}` | `200 OK`          |
| `POST`   | Create a new resource.                                                                         | `POST /expenses`                            | `201 Created`     |
| `PUT`    | **Full replacement** of an existing resource. The request body should contain the complete resource representation. | `PUT /expenses/{expense_id}`                | `200 OK`          |
| `PATCH`  | **Partial update** of an existing resource. The request body should only contain the fields to be changed. | `PATCH /expenses/{expense_id}`              | `200 OK`          |
| `DELETE` | Remove an existing resource.                                                                   | `DELETE /expenses/{expense_id}`             | `204 No Content`  |

*Note: For simplicity, we will start by implementing `PUT` for updates. `PATCH` can be added later if a clear need for partial updates arises.*

## 4\. Request & Response Bodies

- **Format**: All request and response bodies **must** be `application/json`.
- **Field Naming**: All field names in JSON bodies **must** use `snake_case` (e.g., `user_id`, `first_name`). This aligns with Python/Pydantic conventions.

## 5\. Status Codes & Error Responses

We will use standard HTTP status codes to indicate the outcome of an API request.

### Common Status Codes

- `200 OK`: General success.
- `201 Created`: Resource successfully created.
- `204 No Content`: Resource successfully deleted; no body is returned.
- `400 Bad Request`: The request is malformed (e.g., invalid JSON).
- `401 Unauthorized`: Authentication is required and has failed or has not been provided.
- `403 Forbidden`: The authenticated user does not have permission to perform the action.
- `404 Not Found`: The requested resource does not exist.
- `409 Conflict`: The request could not be completed due to a conflict with the current state of the resource (e.g., creating a user with an existing email).
- `422 Unprocessable Entity`: The request syntax is correct, but it contains semantic errors (e.g., a field fails validation).
- `500 Internal Server Error`: An unexpected condition occurred on the server.

### Standard Error Response Format

All error responses (4xx and 5xx) **must** conform to the following JSON structure, which is the default for FastAPI. This ensures consistency for client-side error handling.

```json
{
  "detail": "A human-readable string explaining the error."
}
```

## 6\. Authentication

- All endpoints that require authentication must be protected.
- Authenticated requests **must** include the `Authorization` header with the Access Token.
- The scheme **must** be `Bearer`.
  - **Example**: `Authorization: Bearer <your_access_token>`
  
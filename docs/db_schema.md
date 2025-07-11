# Database Schema Design

This document outlines the database schema for the Constellation project, hosted on MongoDB.

## Naming Converntions

- Collections: Plural, snake_case (e.g., `users`, `active_sessions`)
- Fields: snake_case

### Collection: `users`

Stores core information about each registered user, supporting both local password-based and future OAuth-based authentication.

| Field Name | Data Type | Required | Indexed | Description |
| :--- | :--- | :--- | :--- | :--- |
| `_id` | `ObjectId` | Yes | Yes (PK) | The unique identifier for the user document. |
| `email` | `String` | Yes | Yes (Unique) | The user's primary email address. Must be unique. |
| `first_name` | `String` | No | No | The user's first name. |
| `last_name` | `String` | No | No | The user's last name. |
| `hashed_password` | `String` | **No** | No | The user's password, hashed using bcrypt. **Required only for local accounts.** |
| `verified` | `Boolean` | Yes | Yes | `true` if the user has been approved. Defaults to `false`. |
| `provider_accounts`| `Array` | No | Yes | An array of objects detailing linked authentication providers. |
| `created_at` | `DateTime` | Yes | Yes | Timestamp of when the user account was created (UTC). |
| `updated_at` | `DateTime` | Yes | No | Timestamp of the last update to the user document. |

**`provider_accounts` Sub-document Structure:**

```json
{
  "provider_name": "local", // e.g., "local", "google", "github"
  "provider_id": "test@example.com" // The user's unique ID from that provider
}
```

#### Example Document

```json
{
  "_id": ObjectId("668b8e3a..."),
  "email": "test@example.com",
  "first_name": "Donald",
  "last_name": "Trump",
  "hashed_password": "$2b$12$....",
  "verified": false,
  "provider_accounts": [
    {
      "provider_name": "local",
      "provider_id": "test@example.com"
    }
  ],
  "created_at": ISODate("2025-07-10T03:45:00.123Z"),
  "updated_at": ISODate("2025-07-10T03:45:00.123Z")
}
```

### Collection: `sessions`

Stores core information about each registered user, supporting both local password-based and future OAuth-based authentication.

| Field Name | Data Type | Required | Indexed | Description |
| :--- | :--- | :--- | :--- | :--- |
| `_id` | `ObjectId` | Yes | Yes (PK) | The unique identifier for the user document. |
| `user_id` | `ObjectId` | Yes | Yes | A reference to the `_id` of the user in the `users` collection |
| `refresh_token_hash` | `String` | Yes | Yes(Unique) | A SHA256 hash of the refresh token. The raw token is never stored. |
| `expires_at` | `DateTime` | Yes | Yes | The timestamp when this refresh token will expire (UTC). We can create a TTL index on this field for automatic cleanup. |
| `created_at` | `DateTime` | Yes | No | Timestamp of when the user account was created (UTC). |
| `user_agent` | `String` | No | No | The User-Agent string of the client that created the session, for auditing purposes. |
| `ip_address` | `String` | No | No | The IP address of the client that created the session, for auditing purposes. |

#### Example Document

```json
{
  "_id": ObjectId("668b8f9b..."),
  "user_id": ObjectId("668b8e3a..."),
  "refresh_token_hash": "a94a8fe5ccb19ba61c4c0873d391e987982fbbd3... (SHA256 hash)",
  "expires_at": ISODate("2025-07-17T03:50:00.456Z"),
  "created_at": ISODate("2025-07-10T03:50:00.456Z"),
  "user_agent": "Mozilla/5.0 ...",
  "ip_address": "192.168.1.100"
}
```

# Batch API

Create large batches of API requests for asynchronous processing. The Batch API returns completions within 24 hours (current supported completion_window) and is intended for large-scale jobs (up to 50,000 requests). Input files must be JSONL and uploaded with the `purpose: "batch"`.

Key limits and notes:

- Input file format: JSONL (one JSON request object per line).
- Max requests per file: 50,000.
- Max file size: 200 MB.
- Supported endpoints for batching: `/v1/responses`, `/v1/chat/completions`, `/v1/embeddings`, `/v1/completions`.
- Embeddings batches: restricted to a maximum of 50,000 embedding inputs across all requests.
- Metadata: up to 16 key/value pairs (key max 64 chars, value max 512 chars).

---

## Create batch

POST https://api.openai.com/v1/batches

Creates and executes a batch from an uploaded file of requests.

Request JSON body (required fields):

- `input_file_id` (string): ID of the uploaded file (uploaded with purpose `batch`).
- `endpoint` (string): Endpoint used for requests in the batch (e.g. `/v1/chat/completions`).
- `completion_window` (string): Time frame to process the batch. Currently `"24h"` is supported.

Optional fields:

- `metadata` (map): Up to 16 key/value pairs with limits above.
- `output_expires_after` (object): Expiration policy for output/error files.

Example (Python):

```python
from openai import OpenAI
client = OpenAI()

client.batches.create(
  input_file_id="file-abc123",
  endpoint="/v1/chat/completions",
  completion_window="24h"
)
```

Example response (created Batch object):

```json
{
  "id": "batch_abc123",
  "object": "batch",
  "endpoint": "/v1/chat/completions",
  "errors": null,
  "input_file_id": "file-abc123",
  "completion_window": "24h",
  "status": "validating",
  "output_file_id": null,
  "error_file_id": null,
  "created_at": 1711471533,
  "in_progress_at": null,
  "expires_at": null,
  "finalizing_at": null,
  "completed_at": null,
  "failed_at": null,
  "expired_at": null,
  "cancelling_at": null,
  "cancelled_at": null,
  "request_counts": { "total": 0, "completed": 0, "failed": 0 },
  "metadata": {
    "customer_id": "user_123456789",
    "batch_description": "Nightly eval job"
  }
}
```

---

## Retrieve batch

GET https://api.openai.com/v1/batches/{batch_id}

Path parameters:

- `batch_id` (string) — ID of the batch to retrieve.

Returns the Batch object for the given ID.

Example (Python):

```python
from openai import OpenAI
client = OpenAI()

client.batches.retrieve("batch_abc123")
```

Sample response (completed):

```json
{
  "id": "batch_abc123",
  "object": "batch",
  "endpoint": "/v1/completions",
  "errors": null,
  "input_file_id": "file-abc123",
  "completion_window": "24h",
  "status": "completed",
  "output_file_id": "file-cvaTdG",
  "error_file_id": "file-HOWS94",
  "created_at": 1711471533,
  "in_progress_at": 1711471538,
  "expires_at": 1711557933,
  "finalizing_at": 1711493133,
  "completed_at": 1711493163,
  "request_counts": { "total": 100, "completed": 95, "failed": 5 },
  "metadata": {
    "customer_id": "user_123456789",
    "batch_description": "Nightly eval job"
  }
}
```

---

## Cancel batch

POST https://api.openai.com/v1/batches/{batch_id}/cancel

Cancels an in-progress batch. Status will be `cancelling` for up to ~10 minutes, then `cancelled`. Partial results (if any) may be available in the output file.

Path parameters:

- `batch_id` (string) — ID of the batch to cancel.

Example (Python):

```python
from openai import OpenAI
client = OpenAI()

client.batches.cancel("batch_abc123")
```

Example response (cancelling):

```json
{
  "id": "batch_abc123",
  "object": "batch",
  "endpoint": "/v1/chat/completions",
  "status": "cancelling",
  "input_file_id": "file-abc123",
  "completion_window": "24h",
  "created_at": 1711471533,
  "in_progress_at": 1711471538,
  "cancelling_at": 1711475133,
  "request_counts": { "total": 100, "completed": 23, "failed": 1 },
  "metadata": {
    "customer_id": "user_123456789",
    "batch_description": "Nightly eval job"
  }
}
```

---

## List batches

GET https://api.openai.com/v1/batches

Query parameters:

- `after` (string, optional): Cursor for pagination (object ID).
- `limit` (integer, optional): Number of items to return (1–100, default 20).

Returns a paginated list of Batch objects.

Example (Python):

```python
from openai import OpenAI
client = OpenAI()

client.batches.list()
```

Sample response:

```json
{
  "object": "list",
  "data": [
    {
      "id": "batch_abc123",
      "object": "batch",
      "endpoint": "/v1/chat/completions",
      "status": "completed",
      "input_file_id": "file-abc123",
      "created_at": 1711471533,
      "request_counts": { "total": 100, "completed": 95, "failed": 5 },
      "metadata": {
        "customer_id": "user_123456789",
        "batch_description": "Nightly job"
      }
    },
    { "id": "batch_abc456", "...": "..." }
  ],
  "first_id": "batch_abc123",
  "last_id": "batch_abc456",
  "has_more": true
}
```

---

## Batch object (fields)

- `id` (string) — batch id.
- `object` (string) — always `"batch"`.
- `endpoint` (string) — endpoint used for the batch.
- `model` (string, optional) — model id used to process the batch.
- `input_file_id` (string) — uploaded input file id.
- `output_file_id` / `error_file_id` (string) — file ids for outputs and errors.
- `status` (string) — current status (`validating`, `processing`, `completed`, `failed`, `cancelling`, `cancelled`, etc.).
- `created_at`, `in_progress_at`, `finalizing_at`, `completed_at`, `failed_at`, `expired_at`, `cancelling_at`, `cancelled_at` (integers) — unix timestamps in seconds.
- `completion_window` (string) — e.g. `"24h"`.
- `expires_at` (integer) — when outputs expire.
- `request_counts` (object) — counts by status (`total`, `completed`, `failed`).
- `usage` (object, optional) — token usage details (only on batches created after 2025-09-07).
- `metadata` (map) — user-provided key/value pairs.

Example of expanded Batch object with usage:

```json
{
  "id": "batch_abc123",
  "object": "batch",
  "endpoint": "/v1/completions",
  "model": "gpt-5-2025-08-07",
  "input_file_id": "file-abc123",
  "completion_window": "24h",
  "status": "completed",
  "request_counts": { "total": 100, "completed": 95, "failed": 5 },
  "usage": {
    "input_tokens": 1500,
    "input_tokens_details": { "cached_tokens": 1024 },
    "output_tokens": 500,
    "output_tokens_details": { "reasoning_tokens": 300 },
    "total_tokens": 2000
  },
  "metadata": {
    "customer_id": "user_123456789",
    "batch_description": "Nightly eval job"
  }
}
```

---

## Batch input file (per-line object)

Each line in the uploaded JSONL input file is a JSON object describing an individual request:

- `custom_id` (string, required per-request unique id) — used to match outputs to inputs.
- `method` (string) — HTTP method, currently only `"POST"`.
- `url` (string) — relative OpenAI URL, e.g. `/v1/chat/completions`.
- `body` (object) — request payload as you would send to the endpoint.

Example input line:

```json
{
  "custom_id": "request-1",
  "method": "POST",
  "url": "/v1/chat/completions",
  "body": {
    "model": "gpt-4o-mini",
    "messages": [
      { "role": "system", "content": "You are a helpful assistant." },
      { "role": "user", "content": "What is 2+2?" }
    ]
  }
}
```

---

## Batch output/error file (per-line object)

Each line in the output or error file corresponds to the input `custom_id`:

- `custom_id` (string) — matches input.
- `response` (object) — HTTP-style response for successful requests.
- `error` (object, optional) — error information for failed requests.

Example output line (successful):

```json
{
  "custom_id": "request-1",
  "response": {
    /* endpoint response JSON */
  }
}
```

Example output line (error):

```json
{
  "custom_id": "request-2",
  "error": { "message": "Invalid request", "type": "invalid_request_error" }
}
```
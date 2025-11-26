# Frontend Team Note: Direct Gemini File Upload Implementation

## Context
We are shifting the architecture for the RAG File Service. Instead of proxying file uploads through a separate backend service, the **Frontend (Next.js)** will handle file uploads directly to the Google Gemini File API (via a Next.js API Route).

The Backend Service will now focus solely on **Content Generation** (Retrieval/RAG), receiving the context (File Search Store) from the Frontend.

## Responsibilities

### Frontend (Next.js)
1.  **File Upload:**
    *   Accept files from the user UI.
    *   Upload files to Google Gemini using the Vertex AI SDK (server-side in an API Route).
    *   **Reference:** [Vertex AI SDK for Python](https://cloud.google.com/vertex-ai/docs/generative-ai/multimodal/document-understanding) (or Node.js equivalent).
2.  **Store Management:**
    *   Create or update a **Gemini File Search Store** for the user session.
    *   Add uploaded files to this store.
3.  **Content Generation Call:**
    *   When requesting content generation from the Backend, include the `store_name` (Resource Name) in the request body.

### Backend (Python Service)
1.  **Content Generation:**
    *   Accepts `store_name` in the request.
    *   Uses the provided store to perform RAG-based generation.
    *   No longer manages a database of files or sessions.

## Implementation Details for Frontend

### 1. Environment Setup
Ensure your Next.js environment has the following variables (for Vertex AI):
- `GOOGLE_APPLICATION_CREDENTIALS`
- `GOOGLE_CLOUD_PROJECT`
- `GOOGLE_CLOUD_LOCATION`

### 2. Proposed API Route Logic (Pseudocode)

```typescript
// app/api/upload/route.ts
import { VertexAI } from '@google-cloud/vertexai';

export async function POST(req: Request) {
  // 1. Authenticate & Parse Request
  const formData = await req.formData();
  const file = formData.get('file');
  
  // 2. Upload to Gemini (using Vertex AI SDK)
  // Note: You might need to use the REST API or Node.js SDK if available
  // Or use a temporary storage -> upload pattern
  
  // 3. Create/Update File Search Store
  // ...
  
  // 4. Return Store Name / File URI
  return Response.json({ 
    store_name: "projects/.../locations/.../stores/..." 
  });
}
```

### 3. Updated Backend API Contract

**POST** `/api/v1/content/generate`

**Request Body:**
```json
{
  "prompt": "Create a slide about...",
  "slide_type": "text",
  "context": { ... },
  "rag_config": {
    "store_name": "projects/123/locations/us-central1/stores/456"
  }
}
```

**Note:** The `session_id` and `user_id` are no longer used for looking up files in the backend database, but can still be passed for logging if needed.

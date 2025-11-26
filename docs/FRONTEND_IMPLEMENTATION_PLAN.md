# Frontend Implementation Plan: File Upload for RAG-based Content Generation

## Document Version: 1.0
**Last Updated:** 2025-11-25
**Target Completion:** TBD
**Owner:** Frontend Team

---

## Table of Contents

1. [Executive Summary](#executive-summary)
2. [Current Architecture Analysis](#current-architecture-analysis)
3. [Feature Requirements](#feature-requirements)
4. [UI/UX Design Specifications](#uiux-design-specifications)
5. [Technical Implementation](#technical-implementation)
6. [Database Schema Changes](#database-schema-changes)
7. [API Endpoints](#api-endpoints)
8. [WebSocket Protocol Updates](#websocket-protocol-updates)
9. [State Management](#state-management)
10. [File Validation & Error Handling](#file-validation--error-handling)
11. [Testing Strategy](#testing-strategy)
12. [Implementation Checklist](#implementation-checklist)
13. [Appendix](#appendix)

---

## Executive Summary

### Overview
This document outlines the frontend implementation required to add file upload functionality to the Deckster presentation builder. Users will be able to upload up to **5 files (max 20 MB each)** per session to provide context for AI-generated slide content through RAG (Retrieval-Augmented Generation).

### Key Objectives
- Enable users to upload documents (PDF, DOCX, TXT, MD, XLSX, PPTX, etc.) during chat sessions
- Send file metadata to backend RAG service for context-aware content generation
- Persist file associations with sessions in the database
- Provide intuitive UI/UX for file management (upload, preview, delete)
- Maintain backwards compatibility with existing chat functionality

### Success Criteria
- ✅ Users can attach files to their chat sessions seamlessly
- ✅ File metadata is correctly sent to backend and stored in database
- ✅ AI-generated content leverages uploaded files when available
- ✅ File operations don't block or degrade chat performance
- ✅ Clear error messages for validation failures

---

## Current Architecture Analysis

### Existing Components Overview

#### 1. Main Builder Interface
**File:** `/app/builder/page.tsx` (1,458 lines)

**Current Layout:**
```
┌─────────────────────────────────────────────────────────┐
│ [25% Width]          │ [75% Width]                      │
│ Chat Panel           │ Presentation Viewer              │
│ ┌─────────────────┐  │ ┌─────────────────────────────┐  │
│ │ Messages        │  │ │ Iframe Presentation         │  │
│ │ ScrollArea      │  │ │ (strawman/final toggle)     │  │
│ │                 │  │ │                             │  │
│ └─────────────────┘  │ └─────────────────────────────┘  │
│ ┌─────────────────┐  │                                  │
│ │ Input Textarea  │  │                                  │
│ │ [Send Button]   │  │                                  │
│ └─────────────────┘  │                                  │
└─────────────────────────────────────────────────────────┘
```

**Key State Variables (Lines 219-274):**
```typescript
const [inputMessage, setInputMessage] = useState('')
const [chatMessages, setChatMessages] = useState<Message[]>([])
const [isGenerating, setIsGenerating] = useState(false)
const [currentSessionId, setCurrentSessionId] = useState<string | null>(null)
```

#### 2. WebSocket Hook
**File:** `/hooks/use-deckster-websocket-v2.ts` (771 lines)

**Current Message Send Method (Lines 607-620):**
```typescript
const sendMessage = useCallback((text: string) => {
  if (!text.trim() || !wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
    return
  }

  const message = {
    type: 'user_message',
    data: {
      text: text.trim()
    }
  }

  wsRef.current.send(JSON.stringify(message))
}, [])
```

**Current Message Types (Server → Client):**
- `chat_message` - AI agent responses
- `action_request` - User decision prompts
- `slide_update` - Slide structure updates
- `presentation_url` - Final presentation URLs
- `status_update` - Progress updates

#### 3. Database Schema
**File:** `/prisma/schema.prisma`

**Current Models:**
```prisma
model ChatSession {
  id                     String    @id
  userId                 String
  title                  String?
  createdAt              DateTime  @default(now())
  updatedAt              DateTime  @updatedAt
  lastMessageAt          DateTime?
  currentStage           Int       @default(1)
  strawmanPreviewUrl     String?   @db.Text
  finalPresentationUrl   String?   @db.Text
  slideCount             Int?
  status                 String    @default("active")

  messages               ChatMessage[]
  stateCache             SessionStateCache?

  @@index([userId, createdAt(sort: Desc)])
}

model ChatMessage {
  id                     String    @id
  sessionId              String
  messageType            String
  timestamp              DateTime
  payload                Json
  userText               String?   @db.Text

  session                ChatSession @relation(fields: [sessionId], references: [id], onDelete: Cascade)

  @@index([sessionId, timestamp(sort: Asc)])
}
```

#### 4. Session Persistence Hook
**File:** `/hooks/use-session-persistence.ts`

**Current Functionality:**
- Debounced batch message saving (3000ms delay)
- Queues messages in Map structure
- Persists to `/api/sessions/[id]/messages`

---

## Feature Requirements

### Functional Requirements

#### FR-1: File Upload Interface
- Users can click an "Attach Files" button to open file selector
- Support drag-and-drop file upload
- Display selected files as chips/badges with filename and size
- Allow removing individual files before sending
- Show upload progress indicator

#### FR-2: File Constraints
- **Maximum files per session:** 5 files
- **Maximum file size:** 20 MB per file
- **Supported formats:** All formats supported by Gemini File API
  - **Documents:** PDF, DOCX, DOC, TXT, MD, RTF
  - **Spreadsheets:** XLSX, XLS, CSV, TSV
  - **Presentations:** PPTX, PPT
  - **Data:** JSON, XML, YAML
  - **Code:** PY, JS, TS, JAVA, GO, RS, etc.
  - **Images:** PNG, JPG, JPEG (for OCR/visual context)

#### FR-3: File Upload Workflow
1. User selects files via button or drag-and-drop
2. Frontend validates file type and size
3. Files are uploaded to Next.js API endpoint
4. API forwards files to backend RAG service
5. Backend uploads to Gemini File API, returns file URIs
6. Frontend stores file metadata in database
7. File chips display with success/error states
8. User can send message with attached file context

#### FR-4: File Metadata Tracking
- Store file associations with `session_id` and `user_id`
- Track Gemini File API URIs for RAG retrieval
- Persist file metadata in PostgreSQL database
- Display uploaded files in chat interface

#### FR-5: Integration with Chat
- Files can be attached before or during conversation
- Files remain attached for entire session
- AI responses leverage file content when generating slides
- Clear indication when AI uses file context (citations)

### Non-Functional Requirements

#### NFR-1: Performance
- File upload must not block chat input
- Implement optimistic UI updates for file operations
- Show loading states during upload
- Target upload time: <5 seconds for 20 MB file

#### NFR-2: Usability
- Clear visual feedback for all file operations
- Intuitive error messages for validation failures
- Seamless integration with existing chat UX
- Mobile-responsive file upload interface

#### NFR-3: Reliability
- Graceful handling of upload failures with retry option
- Validate files client-side before upload
- Prevent duplicate file uploads
- Handle concurrent file uploads

#### NFR-4: Security
- Authenticate all file upload requests
- Validate file types and sizes server-side
- Scan files for malware (backend responsibility)
- Limit upload rate per user/session

---

## UI/UX Design Specifications

### File Upload Button Placement

**Location:** Above the chat input textarea (Line 1296 in `builder/page.tsx`)

**Updated Layout:**
```tsx
<div className="space-y-3">
  {/* File Upload Section */}
  <div className="flex items-center gap-2">
    <Button
      variant="outline"
      size="sm"
      onClick={handleAttachFiles}
      disabled={uploadedFiles.length >= 5}
      className="flex items-center gap-2"
    >
      <Paperclip className="h-4 w-4" />
      Attach Files ({uploadedFiles.length}/5)
    </Button>

    {uploadedFiles.length > 0 && (
      <Button
        variant="ghost"
        size="sm"
        onClick={handleClearAllFiles}
        className="text-muted-foreground"
      >
        Clear All
      </Button>
    )}
  </div>

  {/* File Preview Chips */}
  {uploadedFiles.length > 0 && (
    <div className="flex flex-wrap gap-2">
      {uploadedFiles.map((file) => (
        <FileChip
          key={file.id}
          file={file}
          onRemove={() => handleRemoveFile(file.id)}
        />
      ))}
    </div>
  )}

  {/* Chat Input Form */}
  <form onSubmit={handleSendMessage} className="flex gap-3">
    {/* Existing textarea and send button */}
  </form>
</div>
```

### File Chip Component Design

**Visual Design:**
```
┌────────────────────────────────────────┐
│ [📄] report.pdf (2.3 MB)          [×]  │
│ ━━━━━━━━━━━━━━━━━━━━━━━━━━━         │  ← Progress bar (during upload)
└────────────────────────────────────────┘
```

**States:**
1. **Uploading:** Progress bar with percentage
2. **Success:** Green checkmark icon, no progress bar
3. **Error:** Red X icon, error tooltip
4. **Removable:** X button on hover

**Component Structure:**
```tsx
interface FileChipProps {
  file: UploadedFile
  onRemove: () => void
}

const FileChip: React.FC<FileChipProps> = ({ file, onRemove }) => {
  return (
    <div className="flex items-center gap-2 px-3 py-2 bg-secondary rounded-lg border">
      <FileIcon type={file.type} />
      <div className="flex-1">
        <p className="text-sm font-medium truncate">{file.name}</p>
        <p className="text-xs text-muted-foreground">
          {formatFileSize(file.size)}
        </p>
        {file.uploadProgress < 100 && (
          <Progress value={file.uploadProgress} className="h-1 mt-1" />
        )}
      </div>
      {file.status === 'success' && (
        <Check className="h-4 w-4 text-green-600" />
      )}
      {file.status === 'error' && (
        <AlertCircle className="h-4 w-4 text-red-600" />
      )}
      <Button
        variant="ghost"
        size="icon"
        className="h-6 w-6"
        onClick={onRemove}
      >
        <X className="h-3 w-3" />
      </Button>
    </div>
  )
}
```

### Drag-and-Drop Zone (Optional Enhancement)

**Implementation:**
```tsx
const [isDragging, setIsDragging] = useState(false)

const handleDragOver = (e: React.DragEvent) => {
  e.preventDefault()
  setIsDragging(true)
}

const handleDragLeave = () => {
  setIsDragging(false)
}

const handleDrop = (e: React.DragEvent) => {
  e.preventDefault()
  setIsDragging(false)

  const files = Array.from(e.dataTransfer.files)
  handleFilesSelected(files)
}

// Wrap chat panel in drop zone
<div
  onDragOver={handleDragOver}
  onDragLeave={handleDragLeave}
  onDrop={handleDrop}
  className={cn(
    "relative",
    isDragging && "border-2 border-dashed border-primary bg-primary/5"
  )}
>
  {isDragging && (
    <div className="absolute inset-0 flex items-center justify-center bg-background/80 z-50">
      <div className="text-center">
        <Upload className="h-12 w-12 mx-auto mb-2 text-primary" />
        <p className="text-lg font-semibold">Drop files here to attach</p>
        <p className="text-sm text-muted-foreground">Max 5 files, 20 MB each</p>
      </div>
    </div>
  )}
  {/* Existing chat content */}
</div>
```

---

## Technical Implementation

### New Components to Create

#### 1. FileUploadButton Component
**File:** `/components/file-upload-button.tsx`

```tsx
'use client'

import { useState, useRef } from 'react'
import { Button } from '@/components/ui/button'
import { Paperclip } from 'lucide-react'
import { useToast } from '@/hooks/use-toast'

interface FileUploadButtonProps {
  onFilesSelected: (files: File[]) => void
  maxFiles: number
  currentFileCount: number
  disabled?: boolean
}

export function FileUploadButton({
  onFilesSelected,
  maxFiles,
  currentFileCount,
  disabled = false
}: FileUploadButtonProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
  const { toast } = useToast()

  const handleClick = () => {
    if (currentFileCount >= maxFiles) {
      toast({
        title: 'Maximum files reached',
        description: `You can only attach up to ${maxFiles} files per session.`,
        variant: 'destructive'
      })
      return
    }
    fileInputRef.current?.click()
  }

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(e.target.files || [])

    const remainingSlots = maxFiles - currentFileCount
    if (files.length > remainingSlots) {
      toast({
        title: 'Too many files',
        description: `You can only attach ${remainingSlots} more file(s).`,
        variant: 'destructive'
      })
      return
    }

    onFilesSelected(files)

    // Reset input to allow re-uploading the same file
    if (fileInputRef.current) {
      fileInputRef.current.value = ''
    }
  }

  return (
    <>
      <Button
        type="button"
        variant="outline"
        size="sm"
        onClick={handleClick}
        disabled={disabled || currentFileCount >= maxFiles}
        className="flex items-center gap-2"
      >
        <Paperclip className="h-4 w-4" />
        Attach Files ({currentFileCount}/{maxFiles})
      </Button>

      <input
        ref={fileInputRef}
        type="file"
        multiple
        accept=".pdf,.docx,.doc,.txt,.md,.xlsx,.xls,.csv,.pptx,.ppt,.json,.xml,.yaml,.yml,.png,.jpg,.jpeg,.py,.js,.ts,.java,.go,.rs"
        onChange={handleFileChange}
        className="hidden"
      />
    </>
  )
}
```

#### 2. FileChip Component
**File:** `/components/file-chip.tsx`

```tsx
'use client'

import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import {
  X,
  FileText,
  File,
  Image,
  FileSpreadsheet,
  FileCode,
  Check,
  AlertCircle,
  Loader2
} from 'lucide-react'
import { cn } from '@/lib/utils'

export interface UploadedFile {
  id: string
  name: string
  size: number
  type: string
  status: 'uploading' | 'success' | 'error'
  uploadProgress: number
  errorMessage?: string
  geminiFileUri?: string
}

interface FileChipProps {
  file: UploadedFile
  onRemove: () => void
}

function getFileIcon(mimeType: string) {
  if (mimeType.startsWith('image/')) return Image
  if (mimeType.includes('spreadsheet') || mimeType.includes('excel') || mimeType.includes('csv')) return FileSpreadsheet
  if (mimeType.includes('pdf') || mimeType.includes('document') || mimeType.includes('text')) return FileText
  if (mimeType.includes('code') || mimeType.includes('javascript') || mimeType.includes('python')) return FileCode
  return File
}

function formatFileSize(bytes: number): string {
  if (bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return `${(bytes / Math.pow(k, i)).toFixed(1)} ${sizes[i]}`
}

export function FileChip({ file, onRemove }: FileChipProps) {
  const FileIcon = getFileIcon(file.type)

  return (
    <div className={cn(
      "flex items-center gap-2 px-3 py-2 rounded-lg border transition-colors",
      file.status === 'success' && "bg-secondary border-secondary",
      file.status === 'uploading' && "bg-secondary/50 border-secondary",
      file.status === 'error' && "bg-destructive/10 border-destructive"
    )}>
      <FileIcon className="h-4 w-4 flex-shrink-0 text-muted-foreground" />

      <div className="flex-1 min-w-0">
        <p className="text-sm font-medium truncate" title={file.name}>
          {file.name}
        </p>
        <p className="text-xs text-muted-foreground">
          {formatFileSize(file.size)}
        </p>

        {file.status === 'uploading' && (
          <Progress value={file.uploadProgress} className="h-1 mt-1" />
        )}

        {file.status === 'error' && file.errorMessage && (
          <p className="text-xs text-destructive mt-1" title={file.errorMessage}>
            {file.errorMessage}
          </p>
        )}
      </div>

      <div className="flex items-center gap-2 flex-shrink-0">
        {file.status === 'uploading' && (
          <Loader2 className="h-4 w-4 animate-spin text-muted-foreground" />
        )}
        {file.status === 'success' && (
          <Check className="h-4 w-4 text-green-600" />
        )}
        {file.status === 'error' && (
          <AlertCircle className="h-4 w-4 text-destructive" />
        )}

        <Button
          variant="ghost"
          size="icon"
          className="h-6 w-6"
          onClick={onRemove}
          type="button"
        >
          <X className="h-3 w-3" />
        </Button>
      </div>
    </div>
  )
}
```

#### 3. File Upload Hook
**File:** `/hooks/use-file-upload.ts`

```tsx
'use client'

import { useState, useCallback } from 'react'
import { useToast } from '@/hooks/use-toast'
import { UploadedFile } from '@/components/file-chip'

const MAX_FILE_SIZE = 20 * 1024 * 1024 // 20 MB
const MAX_FILES = 5

interface UseFileUploadOptions {
  sessionId: string
  userId: string
  onUploadComplete?: (files: UploadedFile[]) => void
}

export function useFileUpload({ sessionId, userId, onUploadComplete }: UseFileUploadOptions) {
  const [files, setFiles] = useState<UploadedFile[]>([])
  const { toast } = useToast()

  const validateFile = (file: File): string | null => {
    if (file.size > MAX_FILE_SIZE) {
      return `File size exceeds 20 MB limit (${(file.size / 1024 / 1024).toFixed(1)} MB)`
    }

    // File type validation is permissive since Gemini supports many types
    // Backend will perform strict validation

    return null
  }

  const uploadFile = useCallback(async (file: File): Promise<UploadedFile> => {
    const fileId = crypto.randomUUID()

    // Create initial file object
    const uploadedFile: UploadedFile = {
      id: fileId,
      name: file.name,
      size: file.size,
      type: file.type,
      status: 'uploading',
      uploadProgress: 0
    }

    setFiles(prev => [...prev, uploadedFile])

    try {
      const formData = new FormData()
      formData.append('file', file)
      formData.append('sessionId', sessionId)
      formData.append('userId', userId)

      const response = await fetch('/api/upload', {
        method: 'POST',
        body: formData
      })

      if (!response.ok) {
        const error = await response.json()
        throw new Error(error.message || 'Upload failed')
      }

      const result = await response.json()

      // Update file status to success
      const successFile: UploadedFile = {
        ...uploadedFile,
        status: 'success',
        uploadProgress: 100,
        geminiFileUri: result.geminiFileUri
      }

      setFiles(prev => prev.map(f => f.id === fileId ? successFile : f))

      return successFile
    } catch (error) {
      const errorMessage = error instanceof Error ? error.message : 'Upload failed'

      const errorFile: UploadedFile = {
        ...uploadedFile,
        status: 'error',
        uploadProgress: 0,
        errorMessage
      }

      setFiles(prev => prev.map(f => f.id === fileId ? errorFile : f))

      toast({
        title: 'Upload failed',
        description: `${file.name}: ${errorMessage}`,
        variant: 'destructive'
      })

      throw error
    }
  }, [sessionId, userId, toast])

  const handleFilesSelected = useCallback(async (selectedFiles: File[]) => {
    // Validate file count
    if (files.length + selectedFiles.length > MAX_FILES) {
      toast({
        title: 'Too many files',
        description: `You can only attach up to ${MAX_FILES} files per session.`,
        variant: 'destructive'
      })
      return
    }

    // Validate each file
    const invalidFiles: string[] = []
    const validFiles: File[] = []

    for (const file of selectedFiles) {
      const error = validateFile(file)
      if (error) {
        invalidFiles.push(`${file.name}: ${error}`)
      } else {
        validFiles.push(file)
      }
    }

    if (invalidFiles.length > 0) {
      toast({
        title: 'Invalid files',
        description: invalidFiles.join('\n'),
        variant: 'destructive'
      })
    }

    // Upload valid files
    const uploadPromises = validFiles.map(file => uploadFile(file))

    try {
      const uploadedFiles = await Promise.allSettled(uploadPromises)
      const successfulUploads = uploadedFiles
        .filter((result): result is PromiseFulfilledResult<UploadedFile> => result.status === 'fulfilled')
        .map(result => result.value)

      if (successfulUploads.length > 0 && onUploadComplete) {
        onUploadComplete(successfulUploads)
      }

      if (successfulUploads.length < validFiles.length) {
        toast({
          title: 'Some uploads failed',
          description: `${successfulUploads.length} of ${validFiles.length} files uploaded successfully.`,
          variant: 'destructive'
        })
      } else if (successfulUploads.length > 0) {
        toast({
          title: 'Upload successful',
          description: `${successfulUploads.length} file(s) uploaded successfully.`
        })
      }
    } catch (error) {
      console.error('File upload error:', error)
    }
  }, [files.length, uploadFile, onUploadComplete, toast])

  const removeFile = useCallback((fileId: string) => {
    setFiles(prev => prev.filter(f => f.id !== fileId))
  }, [])

  const clearAllFiles = useCallback(() => {
    setFiles([])
  }, [])

  return {
    files,
    handleFilesSelected,
    removeFile,
    clearAllFiles
  }
}
```

### Modifications to Existing Files

#### 1. Update Builder Page (`/app/builder/page.tsx`)

**Add imports (around line 1-50):**
```tsx
import { FileUploadButton } from '@/components/file-upload-button'
import { FileChip, UploadedFile } from '@/components/file-chip'
import { useFileUpload } from '@/hooks/use-file-upload'
```

**Add state for file uploads (around line 274):**
```tsx
// After existing state declarations
const {
  files: uploadedFiles,
  handleFilesSelected,
  removeFile,
  clearAllFiles
} = useFileUpload({
  sessionId: currentSessionId || '',
  userId: session?.user?.email || '',
  onUploadComplete: (files) => {
    console.log('Files uploaded:', files)
  }
})
```

**Update handleSendMessage function (around line 567):**
```tsx
const handleSendMessage = async (e?: React.FormEvent) => {
  if (e) {
    e.preventDefault()
  }

  if (!inputMessage.trim() && uploadedFiles.length === 0) {
    return
  }

  if (!wsConnected || !currentSessionId) {
    toast({
      title: 'Not connected',
      description: 'Please wait for connection to be established.',
      variant: 'destructive'
    })
    return
  }

  // Send message with file metadata
  sendMessage(inputMessage, uploadedFiles.map(f => ({
    id: f.id,
    name: f.name,
    size: f.size,
    type: f.type,
    geminiFileUri: f.geminiFileUri
  })))

  setInputMessage('')
  // Note: Don't clear files here - they remain for the session
}
```

**Update chat input UI (around line 1296):**
```tsx
{/* File Upload Section */}
<div className="space-y-3 p-4 border-t bg-background">
  <div className="flex items-center gap-2">
    <FileUploadButton
      onFilesSelected={handleFilesSelected}
      maxFiles={5}
      currentFileCount={uploadedFiles.length}
      disabled={!currentSessionId}
    />

    {uploadedFiles.length > 0 && (
      <Button
        variant="ghost"
        size="sm"
        onClick={clearAllFiles}
        className="text-muted-foreground"
      >
        Clear All
      </Button>
    )}
  </div>

  {/* File Preview Chips */}
  {uploadedFiles.length > 0 && (
    <div className="flex flex-wrap gap-2">
      {uploadedFiles.map((file) => (
        <FileChip
          key={file.id}
          file={file}
          onRemove={() => removeFile(file.id)}
        />
      ))}
    </div>
  )}

  {/* Existing Chat Input Form */}
  <form onSubmit={handleSendMessage} className="flex gap-3">
    <div className="flex-1 relative">
      <Textarea
        ref={textareaRef}
        value={inputMessage}
        onChange={(e) => setInputMessage(e.target.value)}
        onKeyDown={handleKeyDown}
        placeholder="Type your message..."
        className="min-h-[80px] resize-none pr-10"
        rows={3}
      />
    </div>
    <Button
      type="submit"
      disabled={(!inputMessage.trim() && uploadedFiles.length === 0) || !wsConnected}
      className="h-[80px]"
    >
      <Send className="h-4 w-4" />
    </Button>
  </form>
</div>
```

#### 2. Update WebSocket Hook (`/hooks/use-deckster-websocket-v2.ts`)

**Update sendMessage function signature (line 607):**
```tsx
const sendMessage = useCallback((
  text: string,
  files?: Array<{
    id: string
    name: string
    size: number
    type: string
    geminiFileUri?: string
  }>
) => {
  if (!text.trim() && (!files || files.length === 0)) {
    return
  }

  if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) {
    console.error('WebSocket not connected')
    return
  }

  const message = {
    type: 'user_message',
    data: {
      text: text.trim(),
      ...(files && files.length > 0 && {
        files: files.map(f => ({
          id: f.id,
          name: f.name,
          size: f.size,
          type: f.type,
          gemini_file_uri: f.geminiFileUri
        }))
      })
    }
  }

  wsRef.current.send(JSON.stringify(message))

  // Optionally add to local message state
  // (existing code for adding user message to chat)
}, [])
```

**Update return value (line 760):**
```tsx
return {
  // ... existing returns
  sendMessage, // Now accepts optional files parameter
}
```

---

## Database Schema Changes

### New Table: UploadedFile

**File:** `/prisma/schema.prisma`

**Add new model:**
```prisma
model UploadedFile {
  id                String    @id @default(cuid())
  sessionId         String
  userId            String
  fileName          String
  fileSize          Int
  fileType          String    // MIME type
  geminiFileUri     String    @db.Text  // Gemini File API URI (e.g., "files/abc123")
  geminiFileId      String?   // Gemini File ID for reference
  uploadedAt        DateTime  @default(now())

  // Relations
  session           ChatSession @relation(fields: [sessionId], references: [id], onDelete: Cascade)
  user              User @relation(fields: [userId], references: [id], onDelete: Cascade)

  @@index([sessionId])
  @@index([userId])
  @@index([uploadedAt(sort: Desc)])
}
```

**Update ChatSession model:**
```prisma
model ChatSession {
  // ... existing fields

  messages          ChatMessage[]
  stateCache        SessionStateCache?
  uploadedFiles     UploadedFile[]  // Add this relation
}
```

**Update User model:**
```prisma
model User {
  // ... existing fields

  sessions          Session[]
  uploadedFiles     UploadedFile[]  // Add this relation
}
```

### Database Migration

**Create migration:**
```bash
npx prisma migrate dev --name add_uploaded_files
```

**Migration file:** `/prisma/migrations/YYYYMMDD_add_uploaded_files/migration.sql`
```sql
-- CreateTable
CREATE TABLE "UploadedFile" (
    "id" TEXT NOT NULL,
    "sessionId" TEXT NOT NULL,
    "userId" TEXT NOT NULL,
    "fileName" TEXT NOT NULL,
    "fileSize" INTEGER NOT NULL,
    "fileType" TEXT NOT NULL,
    "geminiFileUri" TEXT NOT NULL,
    "geminiFileId" TEXT,
    "uploadedAt" TIMESTAMP(3) NOT NULL DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT "UploadedFile_pkey" PRIMARY KEY ("id")
);

-- CreateIndex
CREATE INDEX "UploadedFile_sessionId_idx" ON "UploadedFile"("sessionId");

-- CreateIndex
CREATE INDEX "UploadedFile_userId_idx" ON "UploadedFile"("userId");

-- CreateIndex
CREATE INDEX "UploadedFile_uploadedAt_idx" ON "UploadedFile"("uploadedAt" DESC);

-- AddForeignKey
ALTER TABLE "UploadedFile" ADD CONSTRAINT "UploadedFile_sessionId_fkey"
  FOREIGN KEY ("sessionId") REFERENCES "ChatSession"("id") ON DELETE CASCADE ON UPDATE CASCADE;

-- AddForeignKey
ALTER TABLE "UploadedFile" ADD CONSTRAINT "UploadedFile_userId_fkey"
  FOREIGN KEY ("userId") REFERENCES "User"("id") ON DELETE CASCADE ON UPDATE CASCADE;
```

---

## API Endpoints

### 1. File Upload Endpoint

**File:** `/app/api/upload/route.ts` (NEW)

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth-options'
import { prisma } from '@/lib/prisma'

const MAX_FILE_SIZE = 20 * 1024 * 1024 // 20 MB
const BACKEND_FILE_SERVICE_URL = process.env.BACKEND_FILE_SERVICE_URL || 'http://localhost:8000'

export async function POST(req: NextRequest) {
  try {
    // Authenticate user
    const session = await getServerSession(authOptions)
    if (!session?.user?.email) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    // Parse form data
    const formData = await req.formData()
    const file = formData.get('file') as File
    const sessionId = formData.get('sessionId') as string
    const userId = formData.get('userId') as string

    // Validate inputs
    if (!file) {
      return NextResponse.json(
        { error: 'No file provided' },
        { status: 400 }
      )
    }

    if (!sessionId || !userId) {
      return NextResponse.json(
        { error: 'Missing sessionId or userId' },
        { status: 400 }
      )
    }

    // Validate file size
    if (file.size > MAX_FILE_SIZE) {
      return NextResponse.json(
        { error: `File size exceeds 20 MB limit (${(file.size / 1024 / 1024).toFixed(1)} MB)` },
        { status: 400 }
      )
    }

    // Validate user owns session
    const chatSession = await prisma.chatSession.findUnique({
      where: { id: sessionId }
    })

    if (!chatSession || chatSession.userId !== session.user.email) {
      return NextResponse.json(
        { error: 'Invalid session' },
        { status: 403 }
      )
    }

    // Check file count limit
    const existingFiles = await prisma.uploadedFile.count({
      where: { sessionId }
    })

    if (existingFiles >= 5) {
      return NextResponse.json(
        { error: 'Maximum 5 files per session' },
        { status: 400 }
      )
    }

    // Forward file to backend RAG service
    const backendFormData = new FormData()
    backendFormData.append('file', file)
    backendFormData.append('session_id', sessionId)
    backendFormData.append('user_id', userId)

    const backendResponse = await fetch(`${BACKEND_FILE_SERVICE_URL}/api/v1/files/upload`, {
      method: 'POST',
      body: backendFormData
    })

    if (!backendResponse.ok) {
      const errorData = await backendResponse.json()
      throw new Error(errorData.detail || 'Backend upload failed')
    }

    const backendResult = await backendResponse.json()

    // Store file metadata in database
    const uploadedFile = await prisma.uploadedFile.create({
      data: {
        sessionId,
        userId: session.user.email,
        fileName: file.name,
        fileSize: file.size,
        fileType: file.type,
        geminiFileUri: backendResult.gemini_file_uri,
        geminiFileId: backendResult.gemini_file_id
      }
    })

    return NextResponse.json({
      id: uploadedFile.id,
      fileName: uploadedFile.fileName,
      fileSize: uploadedFile.fileSize,
      fileType: uploadedFile.fileType,
      geminiFileUri: uploadedFile.geminiFileUri,
      uploadedAt: uploadedFile.uploadedAt
    })
  } catch (error) {
    console.error('File upload error:', error)
    return NextResponse.json(
      { error: error instanceof Error ? error.message : 'Upload failed' },
      { status: 500 }
    )
  }
}
```

### 2. Get Session Files Endpoint

**File:** `/app/api/sessions/[id]/files/route.ts` (NEW)

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth-options'
import { prisma } from '@/lib/prisma'

export async function GET(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.email) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    const sessionId = params.id

    // Validate user owns session
    const chatSession = await prisma.chatSession.findUnique({
      where: { id: sessionId }
    })

    if (!chatSession || chatSession.userId !== session.user.email) {
      return NextResponse.json(
        { error: 'Session not found' },
        { status: 404 }
      )
    }

    // Get all files for session
    const files = await prisma.uploadedFile.findMany({
      where: { sessionId },
      orderBy: { uploadedAt: 'asc' }
    })

    return NextResponse.json({ files })
  } catch (error) {
    console.error('Get session files error:', error)
    return NextResponse.json(
      { error: 'Failed to fetch files' },
      { status: 500 }
    )
  }
}
```

### 3. Delete File Endpoint

**File:** `/app/api/files/[id]/route.ts` (NEW)

```typescript
import { NextRequest, NextResponse } from 'next/server'
import { getServerSession } from 'next-auth'
import { authOptions } from '@/lib/auth-options'
import { prisma } from '@/lib/prisma'

export async function DELETE(
  req: NextRequest,
  { params }: { params: { id: string } }
) {
  try {
    const session = await getServerSession(authOptions)
    if (!session?.user?.email) {
      return NextResponse.json(
        { error: 'Unauthorized' },
        { status: 401 }
      )
    }

    const fileId = params.id

    // Get file and validate ownership
    const file = await prisma.uploadedFile.findUnique({
      where: { id: fileId }
    })

    if (!file || file.userId !== session.user.email) {
      return NextResponse.json(
        { error: 'File not found' },
        { status: 404 }
      )
    }

    // Delete from database (CASCADE will handle cleanup)
    await prisma.uploadedFile.delete({
      where: { id: fileId }
    })

    // Optionally: Call backend to delete from Gemini File API
    // (Files auto-delete after 48 hours, so this is optional)

    return NextResponse.json({ success: true })
  } catch (error) {
    console.error('Delete file error:', error)
    return NextResponse.json(
      { error: 'Failed to delete file' },
      { status: 500 }
    )
  }
}
```

---

## WebSocket Protocol Updates

### Updated Message Type: user_message

**Client → Server:**
```typescript
interface UserMessage {
  type: 'user_message'
  data: {
    text: string
    files?: Array<{
      id: string           // Frontend file ID
      name: string         // Original filename
      size: number         // File size in bytes
      type: string         // MIME type
      gemini_file_uri: string  // Gemini File API URI
    }>
  }
}
```

**Example:**
```json
{
  "type": "user_message",
  "data": {
    "text": "Create a presentation about quarterly sales using the attached data.",
    "files": [
      {
        "id": "abc-123-def",
        "name": "Q4_Sales_Data.xlsx",
        "size": 245760,
        "type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "gemini_file_uri": "files/xyz789abc"
      }
    ]
  }
}
```

### New Message Type: file_context_used (Server → Client)

**Purpose:** Inform user that AI used file context in response

```typescript
interface FileContextUsedMessage {
  type: 'file_context_used'
  data: {
    files_referenced: Array<{
      file_uri: string
      file_name: string
      citations: Array<{
        content: string
        page?: number
        confidence?: number
      }>
    }>
  }
}
```

**Example:**
```json
{
  "type": "file_context_used",
  "data": {
    "files_referenced": [
      {
        "file_uri": "files/xyz789abc",
        "file_name": "Q4_Sales_Data.xlsx",
        "citations": [
          {
            "content": "Total revenue: $2.4M",
            "page": 1,
            "confidence": 0.95
          }
        ]
      }
    ]
  }
}
```

---

## State Management

### Presentation Context Updates

**File:** `/contexts/presentation-context.tsx`

**Add to PresentationState interface:**
```typescript
interface PresentationState {
  // ... existing fields
  uploadedFiles: Array<{
    id: string
    name: string
    size: number
    type: string
    geminiFileUri: string
    uploadedAt: string
  }>
}
```

**Add new action types:**
```typescript
type PresentationAction =
  | { type: 'SET_UPLOADED_FILES'; payload: UploadedFile[] }
  | { type: 'ADD_UPLOADED_FILE'; payload: UploadedFile }
  | { type: 'REMOVE_UPLOADED_FILE'; payload: string } // file ID
  | { type: 'CLEAR_UPLOADED_FILES' }
  // ... existing action types
```

**Update reducer:**
```typescript
function presentationReducer(
  state: PresentationState,
  action: PresentationAction
): PresentationState {
  switch (action.type) {
    case 'SET_UPLOADED_FILES':
      return { ...state, uploadedFiles: action.payload }

    case 'ADD_UPLOADED_FILE':
      return {
        ...state,
        uploadedFiles: [...state.uploadedFiles, action.payload]
      }

    case 'REMOVE_UPLOADED_FILE':
      return {
        ...state,
        uploadedFiles: state.uploadedFiles.filter(f => f.id !== action.payload)
      }

    case 'CLEAR_UPLOADED_FILES':
      return { ...state, uploadedFiles: [] }

    // ... existing cases
  }
}
```

### Session Cache Updates

**File:** `/hooks/use-session-cache.ts`

**Update cached state interface:**
```typescript
interface CachedSessionState {
  sessionId: string
  presentationId: string | null
  presentationUrl: string | null
  strawmanPreviewUrl: string | null
  finalPresentationUrl: string | null
  currentStatus: StatusUpdate | null
  slideStructure: SlideUpdate | null
  chatMessages: Message[]
  uploadedFiles: UploadedFile[]  // Add this
  lastUpdated: string
}
```

**Update cache save/load logic to include files:**
```typescript
const setCachedState = useCallback((state: Partial<CachedSessionState>) => {
  // ... existing logic

  if (state.uploadedFiles) {
    cacheData.uploadedFiles = state.uploadedFiles
  }

  // ... save to sessionStorage
}, [])
```

---

## File Validation & Error Handling

### Client-Side Validation

**File:** `/lib/file-validation.ts` (NEW)

```typescript
export const FILE_VALIDATION = {
  MAX_FILE_SIZE: 20 * 1024 * 1024, // 20 MB
  MAX_FILES_PER_SESSION: 5,

  // Comprehensive list of supported MIME types
  SUPPORTED_TYPES: [
    // Documents
    'application/pdf',
    'application/msword',
    'application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    'text/plain',
    'text/markdown',
    'application/rtf',

    // Spreadsheets
    'application/vnd.ms-excel',
    'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
    'text/csv',
    'text/tab-separated-values',

    // Presentations
    'application/vnd.ms-powerpoint',
    'application/vnd.openxmlformats-officedocument.presentationml.presentation',

    // Data formats
    'application/json',
    'application/xml',
    'text/xml',
    'application/x-yaml',
    'text/yaml',

    // Code files
    'text/javascript',
    'application/javascript',
    'text/typescript',
    'application/typescript',
    'text/x-python',
    'text/x-java',
    'text/x-go',
    'text/x-rust',

    // Images (for OCR)
    'image/png',
    'image/jpeg',
    'image/jpg',
    'image/webp'
  ]
}

export interface FileValidationError {
  code: 'SIZE_EXCEEDED' | 'INVALID_TYPE' | 'TOO_MANY_FILES' | 'EMPTY_FILE'
  message: string
  fileName: string
}

export function validateFile(file: File): FileValidationError | null {
  // Check file size
  if (file.size === 0) {
    return {
      code: 'EMPTY_FILE',
      message: 'File is empty',
      fileName: file.name
    }
  }

  if (file.size > FILE_VALIDATION.MAX_FILE_SIZE) {
    const sizeMB = (file.size / 1024 / 1024).toFixed(1)
    return {
      code: 'SIZE_EXCEEDED',
      message: `File size (${sizeMB} MB) exceeds 20 MB limit`,
      fileName: file.name
    }
  }

  // Check file type (permissive - backend will do strict validation)
  // We allow all types here since Gemini supports many formats
  // Backend will reject truly unsupported types

  return null
}

export function validateFileList(
  files: File[],
  currentFileCount: number
): FileValidationError[] {
  const errors: FileValidationError[] = []

  // Check total file count
  if (currentFileCount + files.length > FILE_VALIDATION.MAX_FILES_PER_SESSION) {
    errors.push({
      code: 'TOO_MANY_FILES',
      message: `Maximum ${FILE_VALIDATION.MAX_FILES_PER_SESSION} files per session (currently ${currentFileCount})`,
      fileName: 'Multiple files'
    })
    return errors
  }

  // Validate each file
  files.forEach(file => {
    const error = validateFile(file)
    if (error) {
      errors.push(error)
    }
  })

  return errors
}
```

### Error Handling Components

**File:** `/components/file-upload-error.tsx` (NEW)

```tsx
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { AlertCircle } from 'lucide-react'
import { FileValidationError } from '@/lib/file-validation'

interface FileUploadErrorProps {
  errors: FileValidationError[]
  onDismiss?: () => void
}

export function FileUploadError({ errors, onDismiss }: FileUploadErrorProps) {
  if (errors.length === 0) return null

  return (
    <Alert variant="destructive" className="mb-3">
      <AlertCircle className="h-4 w-4" />
      <AlertTitle>File Upload Error</AlertTitle>
      <AlertDescription>
        <ul className="list-disc list-inside space-y-1 mt-2">
          {errors.map((error, index) => (
            <li key={index}>
              <strong>{error.fileName}:</strong> {error.message}
            </li>
          ))}
        </ul>
      </AlertDescription>
    </Alert>
  )
}
```

---

## Testing Strategy

### Unit Tests

**File:** `/tests/components/file-upload-button.test.tsx`

```tsx
import { render, screen, fireEvent } from '@testing-library/react'
import { FileUploadButton } from '@/components/file-upload-button'

describe('FileUploadButton', () => {
  it('should render with correct file count', () => {
    render(
      <FileUploadButton
        onFilesSelected={() => {}}
        maxFiles={5}
        currentFileCount={2}
      />
    )
    expect(screen.getByText(/Attach Files \(2\/5\)/)).toBeInTheDocument()
  })

  it('should disable when max files reached', () => {
    render(
      <FileUploadButton
        onFilesSelected={() => {}}
        maxFiles={5}
        currentFileCount={5}
      />
    )
    expect(screen.getByRole('button')).toBeDisabled()
  })

  it('should call onFilesSelected when files are selected', () => {
    const handleFilesSelected = jest.fn()
    render(
      <FileUploadButton
        onFilesSelected={handleFilesSelected}
        maxFiles={5}
        currentFileCount={0}
      />
    )

    const file = new File(['test'], 'test.pdf', { type: 'application/pdf' })
    const input = screen.getByRole('button').nextElementSibling as HTMLInputElement

    fireEvent.change(input, { target: { files: [file] } })

    expect(handleFilesSelected).toHaveBeenCalledWith([file])
  })
})
```

**File:** `/tests/lib/file-validation.test.ts`

```tsx
import { validateFile, validateFileList, FILE_VALIDATION } from '@/lib/file-validation'

describe('File Validation', () => {
  it('should reject files exceeding size limit', () => {
    const largeFile = new File(
      [new ArrayBuffer(FILE_VALIDATION.MAX_FILE_SIZE + 1)],
      'large.pdf',
      { type: 'application/pdf' }
    )

    const error = validateFile(largeFile)
    expect(error).not.toBeNull()
    expect(error?.code).toBe('SIZE_EXCEEDED')
  })

  it('should accept valid files', () => {
    const validFile = new File(['content'], 'document.pdf', {
      type: 'application/pdf'
    })

    const error = validateFile(validFile)
    expect(error).toBeNull()
  })

  it('should reject empty files', () => {
    const emptyFile = new File([], 'empty.pdf', { type: 'application/pdf' })

    const error = validateFile(emptyFile)
    expect(error).not.toBeNull()
    expect(error?.code).toBe('EMPTY_FILE')
  })

  it('should reject too many files', () => {
    const files = Array(6).fill(null).map((_, i) =>
      new File(['content'], `file${i}.pdf`, { type: 'application/pdf' })
    )

    const errors = validateFileList(files, 0)
    expect(errors.length).toBeGreaterThan(0)
    expect(errors[0].code).toBe('TOO_MANY_FILES')
  })
})
```

### Integration Tests

**File:** `/tests/integration/file-upload.test.tsx`

```tsx
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { useFileUpload } from '@/hooks/use-file-upload'
import { rest } from 'msw'
import { setupServer } from 'msw/node'

const server = setupServer(
  rest.post('/api/upload', async (req, res, ctx) => {
    return res(ctx.json({
      id: 'file-123',
      fileName: 'test.pdf',
      fileSize: 1024,
      fileType: 'application/pdf',
      geminiFileUri: 'files/abc123',
      uploadedAt: new Date().toISOString()
    }))
  })
)

beforeAll(() => server.listen())
afterEach(() => server.resetHandlers())
afterAll(() => server.close())

describe('File Upload Integration', () => {
  it('should upload file successfully', async () => {
    // Test implementation
  })

  it('should handle upload errors gracefully', async () => {
    server.use(
      rest.post('/api/upload', (req, res, ctx) => {
        return res(ctx.status(500), ctx.json({ error: 'Upload failed' }))
      })
    )

    // Test error handling
  })
})
```

### E2E Tests

**File:** `/tests/e2e/file-upload-flow.spec.ts` (Playwright)

```tsx
import { test, expect } from '@playwright/test'

test.describe('File Upload Flow', () => {
  test('should upload and display file in chat', async ({ page }) => {
    await page.goto('/builder')

    // Wait for chat to load
    await page.waitForSelector('[data-testid="chat-input"]')

    // Click attach files button
    await page.click('[data-testid="attach-files-button"]')

    // Select file
    const fileInput = await page.locator('input[type="file"]')
    await fileInput.setInputFiles('tests/fixtures/test-document.pdf')

    // Wait for upload to complete
    await page.waitForSelector('[data-testid="file-chip-success"]')

    // Verify file chip is displayed
    const fileChip = await page.locator('[data-testid="file-chip"]')
    await expect(fileChip).toContainText('test-document.pdf')

    // Send message with file
    await page.fill('[data-testid="chat-input"]', 'Analyze this document')
    await page.click('[data-testid="send-button"]')

    // Verify message sent
    await expect(page.locator('[data-testid="chat-message"]').last()).toContainText('Analyze this document')
  })

  test('should prevent uploading more than 5 files', async ({ page }) => {
    await page.goto('/builder')

    // Upload 5 files
    for (let i = 0; i < 5; i++) {
      await page.click('[data-testid="attach-files-button"]')
      await page.locator('input[type="file"]').setInputFiles(`tests/fixtures/file${i}.pdf`)
      await page.waitForSelector(`[data-testid="file-chip-${i}"]`)
    }

    // Verify button is disabled
    const attachButton = await page.locator('[data-testid="attach-files-button"]')
    await expect(attachButton).toBeDisabled()
  })
})
```

---

## Implementation Checklist

### Phase 1: UI Components (Week 1)
- [ ] Create `FileUploadButton` component
- [ ] Create `FileChip` component with all states (uploading, success, error)
- [ ] Create `FileUploadError` alert component
- [ ] Add drag-and-drop zone to builder page
- [ ] Write component unit tests
- [ ] Test responsive design on mobile

### Phase 2: File Upload Logic (Week 1-2)
- [ ] Create `useFileUpload` custom hook
- [ ] Implement file validation logic (`file-validation.ts`)
- [ ] Create `/api/upload` endpoint
- [ ] Test file upload with mock backend
- [ ] Add progress tracking for large files
- [ ] Implement error handling and retry logic

### Phase 3: Database Integration (Week 2)
- [ ] Update Prisma schema with `UploadedFile` model
- [ ] Run database migration
- [ ] Create `/api/sessions/[id]/files` endpoint
- [ ] Create `/api/files/[id]` delete endpoint
- [ ] Test database CRUD operations
- [ ] Verify cascade delete on session removal

### Phase 4: WebSocket Updates (Week 2-3)
- [ ] Update `sendMessage` function to accept files
- [ ] Update WebSocket message type definitions
- [ ] Test file metadata transmission
- [ ] Handle new message types from backend (`file_context_used`)
- [ ] Add file context indicators in chat UI

### Phase 5: State Management (Week 3)
- [ ] Update PresentationContext with file state
- [ ] Add file-related actions to reducer
- [ ] Update session cache to include files
- [ ] Test state persistence across page refreshes
- [ ] Verify file state syncs with database

### Phase 6: Integration with Builder (Week 3-4)
- [ ] Integrate file upload UI into builder page
- [ ] Connect file upload hook to builder state
- [ ] Update message send handler to include files
- [ ] Load existing files when resuming session
- [ ] Test complete upload-to-send workflow

### Phase 7: Testing & Polish (Week 4)
- [ ] Write integration tests for full upload flow
- [ ] Write E2E tests with Playwright
- [ ] Add loading skeletons and animations
- [ ] Optimize file upload performance
- [ ] Add analytics events for file operations
- [ ] Create user documentation

### Phase 8: Backend Integration (Week 4-5)
- [ ] Connect to actual backend RAG service
- [ ] Test Gemini File API integration
- [ ] Verify file context in AI responses
- [ ] Test citation display
- [ ] Handle backend errors gracefully

### Phase 9: Production Readiness (Week 5)
- [ ] Security audit of file upload flow
- [ ] Performance testing with large files
- [ ] Cross-browser testing
- [ ] Accessibility audit (WCAG 2.1 AA)
- [ ] Deploy to staging environment
- [ ] User acceptance testing
- [ ] Production deployment

---

## Appendix

### A. Environment Variables

**Add to `.env.local`:**
```bash
# File Upload Configuration
NEXT_PUBLIC_MAX_FILE_SIZE=20971520  # 20 MB in bytes
NEXT_PUBLIC_MAX_FILES_PER_SESSION=5
NEXT_PUBLIC_ALLOWED_FILE_EXTENSIONS=.pdf,.docx,.doc,.txt,.md,.xlsx,.xls,.csv,.pptx,.ppt,.json,.xml,.yaml,.yml,.png,.jpg,.jpeg

# Backend File Service
BACKEND_FILE_SERVICE_URL=http://localhost:8000
# Production: https://deckster-file-service.up.railway.app
```

### B. File Type Icons Mapping

```typescript
// utils/file-icons.ts
import {
  FileText,
  FileSpreadsheet,
  FileImage,
  FileCode,
  File as FileIcon
} from 'lucide-react'

export function getFileIcon(mimeType: string, fileName: string) {
  const extension = fileName.split('.').pop()?.toLowerCase()

  // Document types
  if (mimeType.includes('pdf') ||
      mimeType.includes('document') ||
      mimeType.includes('text')) {
    return FileText
  }

  // Spreadsheet types
  if (mimeType.includes('spreadsheet') ||
      mimeType.includes('excel') ||
      extension === 'csv') {
    return FileSpreadsheet
  }

  // Image types
  if (mimeType.startsWith('image/')) {
    return FileImage
  }

  // Code types
  if (['js', 'ts', 'py', 'java', 'go', 'rs', 'json', 'xml', 'yaml'].includes(extension || '')) {
    return FileCode
  }

  return FileIcon
}
```

### C. API Request/Response Schemas

**File Upload Request:**
```typescript
interface FileUploadRequest {
  file: File
  sessionId: string
  userId: string
}
```

**File Upload Response:**
```typescript
interface FileUploadResponse {
  id: string
  fileName: string
  fileSize: number
  fileType: string
  geminiFileUri: string
  geminiFileId?: string
  uploadedAt: string
}
```

**Error Response:**
```typescript
interface ErrorResponse {
  error: string
  code?: 'SIZE_EXCEEDED' | 'INVALID_TYPE' | 'TOO_MANY_FILES' | 'UNAUTHORIZED' | 'SERVER_ERROR'
  details?: Record<string, any>
}
```

### D. Accessibility Considerations

- **Keyboard Navigation:** Ensure all file operations accessible via keyboard
- **Screen Readers:** Add `aria-label` to file upload button and chips
- **Focus Management:** Auto-focus on error messages when upload fails
- **Color Contrast:** Ensure error states meet WCAG AA standards
- **Alternative Text:** Provide descriptive labels for all file icons

**Example:**
```tsx
<Button
  aria-label={`Attach files. Currently ${uploadedFiles.length} of ${maxFiles} files attached`}
  aria-disabled={uploadedFiles.length >= maxFiles}
>
  <Paperclip className="h-4 w-4" aria-hidden="true" />
  Attach Files ({uploadedFiles.length}/{maxFiles})
</Button>
```

### E. Performance Optimization

**1. File Upload Optimization:**
- Implement resumable upload for large files
- Use Web Workers for file processing (if needed)
- Compress images before upload (optional)
- Implement upload queue for multiple files

**2. UI Performance:**
- Use React.memo for FileChip component
- Virtualize file list if >10 files (future enhancement)
- Debounce file validation during drag-and-drop
- Lazy load file preview thumbnails

**3. Network Optimization:**
- Implement upload retry with exponential backoff
- Add request cancellation on component unmount
- Use multipart upload for files >5 MB
- Cache file metadata in sessionStorage

### F. Security Considerations

**1. Client-Side:**
- Validate file types and sizes before upload
- Sanitize file names to prevent XSS
- Limit concurrent uploads to prevent resource exhaustion
- Clear file input after selection to prevent re-submission

**2. Server-Side (Next.js API):**
- Authenticate all upload requests
- Re-validate file size and type server-side
- Implement rate limiting (e.g., 10 uploads per minute per user)
- Scan files for malware (via backend service)
- Use CSRF tokens for state-changing operations

**3. Data Privacy:**
- Delete files after session completion (optional)
- Encrypt file metadata in database
- Use signed URLs for file access (if applicable)
- Comply with GDPR for file storage and deletion

### G. Monitoring & Analytics

**Track the following events:**
```typescript
// analytics/events.ts
export const trackFileUpload = (file: { size: number; type: string }) => {
  analytics.track('File Upload Started', {
    fileSize: file.size,
    fileType: file.type,
    timestamp: new Date().toISOString()
  })
}

export const trackFileUploadSuccess = (fileId: string, duration: number) => {
  analytics.track('File Upload Completed', {
    fileId,
    uploadDuration: duration,
    timestamp: new Date().toISOString()
  })
}

export const trackFileUploadError = (error: string, file: { name: string; size: number }) => {
  analytics.track('File Upload Failed', {
    error,
    fileName: file.name,
    fileSize: file.size,
    timestamp: new Date().toISOString()
  })
}
```

---

## Conclusion

This implementation plan provides a comprehensive roadmap for adding file upload functionality to the Deckster frontend. By following this guide, the frontend team can seamlessly integrate file uploads with the existing chat interface while maintaining code quality, performance, and user experience standards.

**Next Steps:**
1. Review this plan with the team
2. Set up development environment with backend service
3. Begin Phase 1 implementation
4. Schedule regular sync meetings with backend team
5. Track progress using the implementation checklist

**Questions or Issues:**
Contact the Technical Lead or create a GitHub issue for clarification.

---

**Document End**

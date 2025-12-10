# Context Frontend - Testing Guide

## Overview
The Context frontend is a Next.js 14 application with TypeScript, Tailwind CSS, and shadcn/ui components. It provides a clean, dark-themed UI for task analysis using the Eisenhower Matrix.

## Components Created

### 1. UI Components (shadcn/ui)
Located in `/components/ui/`:
- `button.tsx` - Customizable button component with variants
- `input.tsx` - Styled text input field
- `textarea.tsx` - Multi-line text input
- `card.tsx` - Container component with header, content, and footer
- `tabs.tsx` - Tabbed interface using Radix UI

### 2. Feature Components

#### TaskAnalyzer (`/components/TaskAnalyzer.tsx`)
**Features:**
- Textarea for entering task descriptions
- "Analyze Task" button with loading state
- Real-time analysis results display showing:
  - Urgency score (1-10) with progress bar
  - Importance score (1-10) with progress bar
  - Eisenhower quadrant (Q1-Q4) with color coding
  - AI reasoning explanation
- Error handling with user-friendly messages
- Color-coded cards based on quadrant:
  - Q1 (Urgent & Important): Red theme
  - Q2 (Not Urgent, Important): Green theme
  - Q3 (Urgent, Not Important): Yellow theme
  - Q4 (Neither): Blue theme

**API Integration:**
- Calls `POST /api/analyze` with task description
- Reads LLM settings from localStorage
- Handles network errors gracefully

#### LLMSettings (`/components/LLMSettings.tsx`)
**Features:**
- Ollama URL input (default: http://127.0.0.1:11434)
- Model selection input (default: qwen3:4b)
- "Test Connection" button with real-time status
- "Save Settings" button with confirmation message
- Connection status display with icons:
  - Green check: Connected
  - Red X: Disconnected
  - Blue spinner: Testing
- Auto-loads settings from localStorage on mount
- Auto-tests connection if settings exist
- Quick start guide for new users

**localStorage Keys:**
- `llm_provider_url` - Ollama instance URL
- `llm_model` - Model name to use

### 3. Main Page (`/app/page.tsx`)
**Features:**
- Tabbed interface with two tabs:
  1. "Analyze Task" - TaskAnalyzer component
  2. "Settings" - LLMSettings component
- Dark theme (bg-gray-900)
- Responsive design
- Clean header with app title and description

## Running the Application

### Prerequisites
1. Node.js 18+ installed
2. Backend running on `http://localhost:8000`
3. Ollama installed and running (for LLM functionality)

### Start Development Server
```bash
cd frontend
npm install  # If not already done
npm run dev
```

The application will be available at `http://localhost:3000`

### Build for Production
```bash
npm run build
npm start
```

## Testing Checklist

### Initial Setup
- [ ] Frontend loads without errors
- [ ] Dark theme is applied correctly
- [ ] Tabs switch between "Analyze Task" and "Settings"

### Settings Tab
- [ ] Default Ollama URL is pre-filled (http://127.0.0.1:11434)
- [ ] Default model is pre-filled (qwen3:4b)
- [ ] Can edit both URL and model fields
- [ ] "Save Settings" shows success message
- [ ] Settings persist after page refresh
- [ ] "Test Connection" button works:
  - Shows loading state while testing
  - Displays connection status
  - Shows appropriate icon (green check / red X / blue spinner)
- [ ] Quick start guide is visible and readable

### Analyze Task Tab
- [ ] Textarea accepts input
- [ ] "Analyze Task" button is disabled when textarea is empty
- [ ] Button shows "Analyzing..." while processing
- [ ] Results display after successful analysis:
  - Urgency score with progress bar
  - Importance score with progress bar
  - Quadrant badge (Q1/Q2/Q3/Q4)
  - Reasoning text
  - Color-coded card based on quadrant
- [ ] Error messages display if:
  - Backend is not running
  - Ollama is not configured
  - Network request fails
- [ ] Can analyze multiple tasks in sequence

### API Integration Tests

#### Test with Backend Running
1. Start backend: `cd backend && uvicorn app.main:app --reload`
2. Go to Settings tab
3. Click "Test Connection"
4. Should show "Connected" status
5. Go to Analyze Task tab
6. Enter: "Review critical security patch by EOD"
7. Click "Analyze Task"
8. Should display analysis results

#### Test without Backend
1. Stop backend server
2. Try to analyze a task
3. Should show clear error message

## UI/UX Features

### Responsive Design
- Mobile-friendly layout
- Proper spacing and padding
- Readable text on all screen sizes

### Dark Theme
- Background: gray-900 (#1f2937)
- Cards: gray-800 (#374151)
- Text: gray-100 (#f9fafb)
- Accents: blue-400/500 for interactive elements

### Accessibility
- Proper label associations
- Keyboard navigation support (via Radix UI)
- Focus states on interactive elements
- Sufficient color contrast

## Common Issues and Solutions

### Issue: "Failed to analyze task"
**Solution:**
1. Check if backend is running on port 8000
2. Verify Ollama is running
3. Check Settings tab for correct Ollama URL

### Issue: Settings not persisting
**Solution:**
1. Check browser localStorage
2. Ensure "Save Settings" button was clicked
3. Check browser console for errors

### Issue: Blank page or components not rendering
**Solution:**
1. Check browser console for errors
2. Verify all dependencies are installed: `npm install`
3. Clear Next.js cache: `rm -rf .next`
4. Rebuild: `npm run build`

## Development Notes

### Component Architecture
- All UI components use the `cn()` utility for className merging
- Components follow shadcn/ui patterns
- TypeScript for type safety
- Client components use `"use client"` directive

### Styling
- Tailwind CSS 4 with JIT compilation
- Custom color palette for dark theme
- Consistent spacing using Tailwind classes

### State Management
- Local component state with useState
- localStorage for settings persistence
- No global state management needed for MVP

## Next Steps for Enhancement

1. Add loading skeletons for better UX
2. Implement toast notifications instead of inline messages
3. Add task history/recent analyses
4. Support for batch task analysis
5. Export analysis results
6. Add more detailed analytics
7. Implement WebSocket for real-time updates
8. Add user authentication

## File Structure
```
frontend/
├── app/
│   ├── globals.css          # Global styles
│   ├── layout.tsx           # Root layout with metadata
│   └── page.tsx             # Main dashboard page
├── components/
│   ├── ui/                  # Reusable UI components
│   │   ├── button.tsx
│   │   ├── card.tsx
│   │   ├── input.tsx
│   │   ├── tabs.tsx
│   │   └── textarea.tsx
│   ├── TaskAnalyzer.tsx     # Task analysis feature
│   └── LLMSettings.tsx      # LLM configuration
├── lib/
│   └── utils.ts             # Utility functions
├── .env.local               # Environment variables
├── package.json             # Dependencies
└── tsconfig.json            # TypeScript config
```

## API Endpoints Expected

### POST /api/analyze
Request:
```json
{
  "task_description": "string",
  "provider_url": "string"
}
```

Response:
```json
{
  "urgency_score": 8,
  "importance_score": 9,
  "eisenhower_quadrant": "Q1",
  "reasoning": "This is a critical security task..."
}
```

### GET /api/llm/health
Response:
```json
{
  "status": "healthy",
  "provider": "ollama",
  "model": "qwen3:4b"
}
```

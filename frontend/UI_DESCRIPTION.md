# Context UI - Visual Description

## Overall Appearance

The Context application features a modern, dark-themed interface optimized for focus and reduced eye strain. The design follows a clean, minimalist approach with the Eisenhower Matrix methodology at its core.

## Color Palette

### Base Theme
- **Background**: Deep dark gray (gray-900: #1f2937)
- **Cards/Containers**: Medium dark gray (gray-800: #374151)
- **Text Primary**: Light gray (gray-100: #f9fafb)
- **Text Secondary**: Medium gray (gray-400: #9ca3af)
- **Borders**: Dark gray (gray-600/700)

### Accent Colors
- **Primary Actions**: Blue (blue-500/600: #3b82f6 / #2563eb)
- **Success**: Green (green-500/700)
- **Warning/Q3**: Yellow (yellow-700/900)
- **Error/Q1**: Red (red-700/900)
- **Q2**: Green (green-700/900)
- **Q4**: Blue (blue-700/900)

## Layout Structure

### Header Section
```
┌─────────────────────────────────────────────────────┐
│  Context                                            │
│  AI-powered task analysis using the                 │
│  Eisenhower Matrix                                  │
└─────────────────────────────────────────────────────┘
```
- Large, bold "Context" title (4xl font size)
- Subtitle in muted gray explaining the app's purpose
- Clean spacing with ample padding

### Tab Navigation
```
┌──────────────┬──────────────┐
│ Analyze Task │   Settings   │
└──────────────┴──────────────┘
```
- Two tabs with equal width (max 400px total)
- Active tab: lighter background (gray-700) with white text
- Inactive tab: darker background (gray-800) with gray text
- Smooth transitions between states
- Rounded corners for modern appearance

## Tab 1: Analyze Task

### Input Section
```
┌─────────────────────────────────────────────┐
│ Analyze Task                                │
│ Enter a task description to analyze its     │
│ urgency and importance                      │
│                                             │
│ Task Description                            │
│ ┌─────────────────────────────────────────┐│
│ │ e.g., Review and merge the critical     ││
│ │ security patch PR by end of day         ││
│ │                                          ││
│ │                                          ││
│ └─────────────────────────────────────────┘│
│                                             │
│ ┌───────────────────────────────────────┐  │
│ │       Analyze Task                    │  │
│ └───────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```
- Card with subtle border and shadow
- Clear label "Task Description" above textarea
- Placeholder text providing example
- 4-row textarea with dark background
- Full-width blue button with white text
- Button shows "Analyzing..." with disabled state during processing

### Results Section (Appears after analysis)
```
┌─────────────────────────────────────────────────────┐
│ Analysis Results              Q1: Urgent & Important │
│                                                       │
│ Urgency Score          Importance Score              │
│ 8/10                   9/10                          │
│ ████████░░ 80%        █████████░ 90%                │
│                                                       │
│ Reasoning                                            │
│ ┌───────────────────────────────────────────────┐   │
│ │ This task involves a critical security patch  │   │
│ │ that needs immediate attention. The deadline  │   │
│ │ is end of day, making it urgent...           │   │
│ └───────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────┘
```
- Color-coded card based on quadrant:
  - **Q1**: Red-tinted background with red border
  - **Q2**: Green-tinted background with green border
  - **Q3**: Yellow-tinted background with yellow border
  - **Q4**: Blue-tinted background with blue border
- Quadrant badge in top-right corner
- Two-column grid for scores
- Large score numbers (3xl font)
- Horizontal progress bars with colored fill
- Reasoning section with darker inset background

## Tab 2: Settings

### Configuration Section
```
┌─────────────────────────────────────────────┐
│ LLM Provider Settings                       │
│ Configure your Ollama instance for task     │
│ analysis                                    │
│                                             │
│ Ollama Provider URL                         │
│ ┌─────────────────────────────────────────┐│
│ │ http://127.0.0.1:11434                  ││
│ └─────────────────────────────────────────┘│
│ The URL where your Ollama instance is       │
│ running                                     │
│                                             │
│ Model Name                                  │
│ ┌─────────────────────────────────────────┐│
│ │ qwen3:4b                                ││
│ └─────────────────────────────────────────┘│
│ The name of the Ollama model to use         │
│                                             │
│ ┌──────────────────┬──────────────────┐    │
│ │ Test Connection  │  Save Settings   │    │
│ └──────────────────┴──────────────────┘    │
└─────────────────────────────────────────────┘
```
- Two input fields with clear labels
- Helper text below each field in muted gray
- Two buttons side-by-side (50/50 width)
- "Test Connection" uses outline variant
- "Save Settings" uses primary blue variant
- Success message appears below buttons when settings are saved

### Connection Status Section
```
┌─────────────────────────────────────────────┐
│ ✓ Connection Status                         │
│                                             │
│ Status: connected                           │
│ ┌─────────────────────────────────────────┐│
│ │ Connected to ollama - Model: qwen3:4b   ││
│ └─────────────────────────────────────────┘│
└─────────────────────────────────────────────┘
```
- Color-coded based on status:
  - **Connected**: Green background with green border and checkmark
  - **Disconnected**: Red background with red border and X icon
  - **Testing**: Blue background with blue border and spinning loader
- Status message in darker inset box
- Icons change based on state

### Quick Start Guide
```
┌─────────────────────────────────────────────┐
│ Quick Start Guide                           │
│                                             │
│ 1. Install Ollama from https://ollama.ai    │
│ 2. Run: ollama pull qwen3:4b               │
│ 3. Ensure Ollama is running                │
│ 4. Click "Test Connection" to verify       │
└─────────────────────────────────────────────┘
```
- Slightly transparent card (bg-gray-800/50)
- Numbered list with helpful instructions
- Code snippets highlighted with darker background
- Blue links for URLs

## Interactive States

### Buttons
- **Default**: Blue background, white text
- **Hover**: Darker blue background, slight scale
- **Disabled**: Reduced opacity (50%), cursor not-allowed
- **Loading**: "Analyzing..." or "Testing..." text
- **Focus**: Blue ring around button (accessibility)

### Input Fields
- **Default**: Dark gray background, light border
- **Focus**: Blue border glow (ring effect)
- **Filled**: White text on dark background
- **Placeholder**: Medium gray text

### Cards
- **Default**: Subtle border, minimal shadow
- **Quadrant Q1**: Red tint with red border
- **Quadrant Q2**: Green tint with green border
- **Quadrant Q3**: Yellow tint with yellow border
- **Quadrant Q4**: Blue tint with blue border

## Typography

### Font Family
- Primary: Geist Sans (modern, clean sans-serif)
- Monospace: Geist Mono (for code snippets)

### Font Sizes
- **Title (h1)**: 4xl (2.25rem / 36px)
- **Card Titles**: Base to lg (1rem - 1.125rem)
- **Score Numbers**: 3xl (1.875rem / 30px)
- **Body Text**: sm (0.875rem / 14px)
- **Helper Text**: xs (0.75rem / 12px)

### Font Weights
- **Titles**: Bold (700)
- **Labels**: Medium (500)
- **Body**: Normal (400)

## Spacing & Layout

### Container
- Maximum width: Responsive container
- Horizontal padding: 1rem (16px)
- Vertical padding: 2rem (32px)

### Cards
- Padding: 1.5rem (24px)
- Border radius: 0.5rem (8px)
- Gap between cards: 1.5rem (24px)

### Form Elements
- Input height: 2.25rem (36px)
- Textarea minimum height: 5rem (80px)
- Button height: 2.25rem (36px)
- Spacing between elements: 1rem (16px)

## Responsive Behavior

### Mobile (< 640px)
- Single column layout
- Full-width cards
- Stacked buttons
- Adjusted padding

### Tablet (640px - 1024px)
- Slightly wider containers
- Maintained two-column score grid
- Side-by-side buttons maintained

### Desktop (> 1024px)
- Centered container with max-width
- Optimal reading width for content
- All features fully visible

## Accessibility Features

1. **Keyboard Navigation**: Full support via Radix UI primitives
2. **Focus Indicators**: Blue ring on focused elements
3. **Color Contrast**: WCAG AA compliant
4. **Labels**: Proper label associations for screen readers
5. **ARIA States**: Loading states communicated to assistive tech
6. **Semantic HTML**: Proper heading hierarchy

## Animation & Transitions

### Smooth Transitions
- Tab switching: Fade in/out
- Button hover: Background color change (200ms)
- Progress bars: Width animation (500ms)
- Connection status: Icon fade/spin

### Loading States
- Spinning icon for "Testing" status
- Button text changes during operations
- Disabled state prevents double-clicks

## Error Handling UI

### Error Messages
```
┌─────────────────────────────────────────────┐
│ ⚠ Failed to analyze task. Make sure the    │
│   backend is running.                       │
└─────────────────────────────────────────────┘
```
- Red background (red-900/50)
- Red border (red-700)
- Light red text (red-200)
- Clear, actionable error messages

### Success Messages
```
┌─────────────────────────────────────────────┐
│ ✓ Settings saved successfully!              │
└─────────────────────────────────────────────┘
```
- Green background (green-900/50)
- Green border (green-700)
- Light green text (green-200)
- Auto-dismisses after 3 seconds

## Visual Hierarchy

The UI uses size, color, and spacing to establish clear hierarchy:

1. **Primary**: App title and main actions (blue buttons)
2. **Secondary**: Tab navigation and card titles
3. **Tertiary**: Labels, helper text, and status information
4. **Quaternary**: Borders, dividers, and subtle backgrounds

## Design Philosophy

- **Clean & Minimal**: No unnecessary decorations
- **Focus on Content**: Task analysis is the hero
- **Dark Mode First**: Optimized for reduced eye strain
- **Responsive**: Works on all devices
- **Accessible**: Inclusive design for all users
- **Professional**: Business-appropriate aesthetics

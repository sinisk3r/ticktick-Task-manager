# Context - Strategy Planning Tools

This folder contains interactive tools for defining and documenting Context's product strategy.

## Available Questionnaires

### 1. Strategy Builder (`questionnaire.html`)
**When to use:** Initial product planning, VC pitch preparation, comprehensive strategy documentation

**Covers:** Vision, MVP, market analysis, roadmap, and go-to-market strategy

**Best for:** Creating polished strategy documents for stakeholders, investors, or advisors

### 2. Business Validation (`business_validation.html`) **NEW**
**When to use:** Pre-launch validation, MVP prioritization, de-risking assumptions

**Covers:**
- Customer discovery & validation (Have you talked to users?)
- Competitive positioning deep-dive (Have you used Motion/Reclaim/Sunsama?)
- Pricing & unit economics (What will users actually pay?)
- MVP feature prioritization (What's the ONE feature for V1?)
- Launch strategy & metrics (When can you ship to 10 beta users?)
- Founder readiness & resources (Solo founder concerns, time commitment, quit criteria)

**Best for:** Solo founders preparing to launch, validating assumptions before building, prioritizing ruthlessly

## Quick Start

1. **Start the backend** (if not already running):
   ```bash
   cd /Users/srikar.kandikonda/Desktop/Claude/Task-management
   ./init.sh start backend
   ```

2. **Open a questionnaire**:
   ```bash
   # For comprehensive strategy planning
   open docs/strategy_plan/questionnaire.html

   # For business validation and launch prep
   open docs/strategy_plan/business_validation.html
   ```
   Or simply double-click the HTML files in Finder.

3. **Fill out the form** - The AI chat will automatically load your OpenRouter API key from `backend/.env`

4. **Export your answers** - Click export buttons to save as JSON, Markdown, or copy to clipboard

## What Gets Generated

### Strategy Builder Output
When you click "Export Strategy Documents", you'll get **9 files**:

**Strategy Documents (Markdown):**
1. `vision_and_mission.md` - Problem, solution, 3-year vision
2. `mvp_specification.md` - Core features, "aha moment", scope control
3. `market_analysis.md` - ICP, TAM/SAM/SOM, competitors, moats
4. `product_roadmap.md` - Current status, milestones, blockers
5. `technical_overview.md` - Tech stack, scalability, AI strategy, privacy
6. `business_model.md` - Monetization, pricing, value prop
7. `gtm_strategy.md` - Launch channels, messaging, incentives
8. `competitive_analysis.md` - Feature comparison grid
9. `raw_answers.json` - All answers in JSON format

### Business Validation Output
The business validation questionnaire offers **3 export options**:

1. **Copy to Clipboard** - Markdown summary ready to paste into notes or chat with AI
2. **Download JSON** - `business_validation_answers.json` with all raw answers
3. **Download Markdown Summary** - `business_validation_summary.md` with formatted report including:
   - Customer discovery status
   - Competitive analysis
   - Pricing validation results
   - MVP feature prioritization
   - Launch timeline and blockers
   - Founder readiness assessment
   - Suggested next steps based on answers

## AI Chat Assistant

The right panel contains an AI-powered assistant that:
- **Automatically loads your OpenRouter API key** from `backend/.env` (no manual entry needed)
- **Uses your preferred model** (`nex-agi/deepseek-v3.1-nex-n1:free` by default)
- **Has full CLAUDE.md context** about your product
- **Sees your current form answers** in real-time

### Example Questions to Ask the AI

**Strategy Builder:**
- "Is my ICP too broad? How can I narrow it?"
- "Suggest 3 competitive moats for Context vs Motion"
- "What features should I cut from the MVP to ship faster?"
- "Help me write a better elevator pitch"
- "What's a realistic TAM/SAM/SOM for this market?"

**Business Validation:**
- "Should I charge for V1 or go free to build traction?"
- "Is my moat defensible against Motion adding this feature?"
- "What's the cheapest way to validate pricing with users?"
- "Suggest 5 questions for customer discovery interviews"
- "How do I de-risk the TickTick dependency?"
- "What experiments can I run to test product-market fit?"

## Configuration

The questionnaire auto-configures from your backend settings:

**Backend Endpoint**: `http://localhost:5407/api/strategy-config`

**Environment Variables Used** (from `backend/.env`):
- `OPENROUTER_API_KEY` - Your OpenRouter API key
- `LLM_MODEL` - Default model for chat (currently: `nex-agi/deepseek-v3.1-nex-n1:free`)

**Available Models**:
1. `nex-agi/deepseek-v3.1-nex-n1:free` (Default - Free, fast)
2. `z-ai/glm-4.5-air:free` (Alternative free model)
3. `anthropic/claude-3.5-sonnet` (Paid, highest quality)
4. `openai/gpt-4-turbo` (Paid)

## Features

### Form Features
- **Suggestion chips** - Click to auto-fill common answers
- **Progress tracking** - See % completion as you type
- **Smart defaults** - Pre-checked core MVP features based on CLAUDE.md
- **Responsive layout** - Works on laptop/desktop (mobile optimized for 1024px+)

### AI Chat Features
- **Auto-loads API key** from backend (no manual entry)
- **Context-aware** - Knows your product from CLAUDE.md
- **Form-aware** - Sees your current answers
- **Grounded advice** - No hype, VC-ready suggestions
- **Conversational memory** - Maintains chat history

### Export Features
- **Multi-document generation** - 8 markdown docs + 1 JSON
- **VC-ready format** - Clean, professional structure
- **Auto-timestamps** - Each doc shows generation date
- **Instant download** - All files download to your browser's download folder

## Troubleshooting

**"Could not load API key from backend"**
- Ensure backend is running: `./init.sh start backend`
- Check backend is on port 5407: `curl http://localhost:5407/api/strategy-config`
- Manually enter API key in the chat panel if needed

**"API error: 401 Unauthorized"**
- Your OpenRouter API key may be invalid
- Update `OPENROUTER_API_KEY` in `backend/.env`
- Restart backend: `./init.sh restart backend`

**Chat not responding**
- Check browser console (F12) for errors
- Verify OpenRouter API key is valid
- Try switching to a different model in the dropdown

**Export button does nothing**
- Check browser's pop-up blocker settings
- Look in your Downloads folder (files may have downloaded silently)
- Try a different browser (Chrome, Firefox, Safari)

## Tips for Best Results

1. **Answer incrementally** - Fill out one section, chat with AI to refine, move to next
2. **Use suggestion chips** - They're based on best practices and common patterns
3. **Be specific** - Vague answers ("busy professionals") → Specific ("Product managers at SaaS startups managing 50+ tasks/week")
4. **Challenge yourself** - The AI will help you think critically about moats, pricing, etc.
5. **Iterate** - You can re-open the HTML, re-fill, and export again anytime

## Next Steps After Export

1. **Review the docs** - Read through all 8 markdown files
2. **Refine with team** - Share with co-founders/advisors for feedback
3. **Convert to pitch deck** - Use vision/market/business docs as slide content
4. **Update regularly** - Re-run questionnaire as strategy evolves
5. **Track changes** - Git commit the generated docs to track evolution over time

## File Structure

```
docs/strategy_plan/
├── README.md                      # This file
├── questionnaire.html             # Strategy Builder - Comprehensive strategy planning
├── business_validation.html       # Business Validation - Launch prep & validation
└── output/                        # Generated exports appear in your Downloads folder
```

## Technical Details

**Stack**:
- Pure HTML/CSS/JavaScript (no build step)
- OpenRouter API for AI chat
- Backend FastAPI endpoint for config (`/api/strategy-config`)

**Browser Compatibility**:
- Chrome/Edge 90+
- Firefox 88+
- Safari 14+

**Security**:
- API key transmitted only to OpenRouter (HTTPS)
- No data stored server-side
- All processing happens in your browser

---

**Questions or issues?** Check the main CLAUDE.md for project context or ask in the AI chat!

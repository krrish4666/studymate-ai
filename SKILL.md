# StudyMate UI/UX Design Skill

## Role

Act as a **senior product designer + frontend engineer** responsible for
transforming StudyMate into a polished, modern learning product.

The goal is **not** to make the application look flashy or
"AI-generated". The goal is to make it feel like a professionally
designed SaaS product: clean, confident, spacious, highly readable,
consistent, and pleasant to use.

Use the supplied Slido screenshots as the visual reference for the
overall design language: - strong typography - generous whitespace -
clear visual hierarchy - large, obvious CTAs - restrained color
palette - wide layouts - clean cards - consistent spacing - professional
rather than "AI dashboard" aesthetics

Do **not** copy Slido branding, logo, text, or exact layouts. Use it
only as inspiration for visual quality and design principles.

------------------------------------------------------------------------

## Existing Product Context

StudyMate is an AI-powered study platform.

Core flow:

1.  User authenticates with JWT / Google OAuth.
2.  User uploads study material.
3.  Documents are processed and cached.
4.  Gemini generates:
    -   Notes
    -   Revision Sheets
    -   Flashcards
    -   Quizzes
    -   Mind Maps
5.  Notes and Revision use SSE for generation streaming.
6.  Redis caches generated AI artifacts.
7.  PostgreSQL stores application data and persistent document-text
    cache.

Existing frontend is primarily **vanilla HTML/CSS/JavaScript**.

### Critical constraint

**Do not migrate the application to React, Next.js, Tailwind, or another
frontend framework.**

Work with the existing frontend architecture unless there is a
compelling technical reason not to.

------------------------------------------------------------------------

# Design Objective

Transform the current UI from:

> functional + AI-looking + small controls + dense dashboard

into:

> polished + spacious + product-grade + visually confident learning
> platform.

The redesign must feel intentional across the entire application, not
like isolated pages receiving random CSS improvements.

------------------------------------------------------------------------

# Design Principles

## 1. Visual hierarchy first

Every page should have an obvious hierarchy:

1.  Page purpose
2.  Primary action
3.  Important content
4.  Secondary actions
5.  Supporting information

Users should immediately understand:

-   Where am I?
-   What can I do here?
-   What should I do next?

Avoid visually giving equal importance to every element.

------------------------------------------------------------------------

## 2. Generous whitespace

Use whitespace deliberately.

Prefer:

-   larger section spacing
-   comfortable card padding
-   readable line height
-   clear separation between unrelated groups
-   wider content areas

Avoid:

-   cramped controls
-   excessive borders
-   too many cards packed together
-   tiny labels
-   dense dashboard layouts

Whitespace should make the application feel premium.

------------------------------------------------------------------------

## 3. Typography

Use a modern, highly readable sans-serif font.

Recommended hierarchy:

-   Large page heading: approximately 40--56px
-   Section heading: approximately 28--36px
-   Card heading: approximately 20--24px
-   Body: approximately 16--18px
-   Supporting text: approximately 14--16px

Do not make important text unnecessarily small.

Use:

-   strong weight for headings
-   regular weight for body text
-   restrained use of bold
-   comfortable line-height

Avoid excessive uppercase text and tiny muted labels.

------------------------------------------------------------------------

# Color System

Create a small, consistent design system.

Prefer a light, warm-neutral base rather than a generic pure-white AI
dashboard.

Suggested direction:

-   Background: warm off-white / very light neutral
-   Surface: white
-   Primary: confident green/teal or another single brand color
-   Text: near-black
-   Secondary text: neutral gray
-   Border: very light gray
-   Success: green
-   Warning: amber
-   Error: red

Do not introduce many accent colors.

The interface should have **one recognizable primary brand color**.

Use color primarily for:

-   primary actions
-   active states
-   important highlights
-   progress
-   success/error feedback

------------------------------------------------------------------------

# Buttons

Current buttons are too small and visually weak.

Make primary actions obvious.

### Primary button

Use:

-   comfortable horizontal padding
-   approximately 44--52px minimum height
-   readable 15--17px text
-   medium/semibold font weight
-   clear hover state
-   clear disabled state
-   rounded corners, but not excessive pill styling

Example hierarchy:

``` text
[ Generate Notes ]
[ Upload Document ]
[ Create Quiz ]
```

These should look like actions, not hyperlinks.

### Secondary actions

Use quieter styling:

``` text
[ Download ]
[ Regenerate ]
[ View History ]
```

Do not make every button primary.

### Icon buttons

Use them only when the icon meaning is obvious.

Always provide accessible labels/tooltips where needed.

------------------------------------------------------------------------

# Navigation

The navigation should feel like a real SaaS product.

Requirements:

-   clear brand identity
-   comfortable horizontal spacing
-   obvious active page
-   readable navigation text
-   consistent header height
-   strong primary action where appropriate
-   responsive mobile navigation

Avoid overcrowding the header.

The header should feel lightweight rather than like a control panel.

------------------------------------------------------------------------

# Dashboard

The dashboard is one of the most important screens.

Design it around the user's learning workflow rather than around backend
features.

Suggested hierarchy:

``` text
Welcome / Page heading

Short supporting message

[ Upload Study Material ]

Recent / Active Materials

Document cards

Generated Study Material

Notes | Flashcards | Quiz | Mind Map | Revision
```

Do not make every feature a huge equal-sized card.

The user's document and learning workflow should be the visual focus.

------------------------------------------------------------------------

# Upload Experience

Uploading a document should feel simple and confident.

Use a large dropzone/card with:

-   clear upload icon
-   short explanation
-   supported file formats
-   obvious upload action
-   drag-and-drop state
-   uploading state
-   success state
-   error state

Avoid tiny file inputs.

The upload area should feel like a major product interaction.

------------------------------------------------------------------------

# Document Cards

Document cards should communicate:

-   document name
-   type
-   upload date
-   processing status
-   available actions

Use visual grouping rather than excessive borders.

Example:

``` text
Operating Systems.pdf
PDF • 4.2 MB

Processed

[ Study ]     [ More ]
```

Keep secondary metadata visually quieter.

------------------------------------------------------------------------

# AI Generation UI

AI generation should feel like a **learning tool**, not a generic
chatbot.

When generating Notes, Revision Sheets, etc.:

-   clearly show what is being generated
-   provide a strong loading/generation state
-   show progressive streaming where supported
-   make progress visually calm
-   avoid excessive animated effects
-   clearly distinguish generated content from controls

For SSE streaming:

``` text
Generating your notes...

[ streamed content progressively appears here ]

Generating...
```

When generation completes:

``` text
Generated successfully

[ Regenerate ] [ Download ]
```

Do not use flashy AI particle effects or excessive gradients.

------------------------------------------------------------------------

# Generated Notes / Revision UI

This is content-first.

The document itself should dominate the screen.

Use:

-   comfortable reading width
-   large readable text
-   clear H1/H2/H3 hierarchy
-   generous paragraph spacing
-   styled lists
-   readable code blocks
-   properly styled tables
-   math-friendly spacing
-   subtle content container

Avoid putting the document inside a tiny dashboard card.

Think:

> modern documentation / premium reading experience

rather than:

> admin dashboard.

------------------------------------------------------------------------

# Flashcards

Flashcards should feel interactive and spacious.

Use:

-   large card
-   strong question typography
-   clear answer area
-   obvious interaction
-   previous/next controls
-   progress indicator
-   comfortable spacing

Avoid tiny cards with dense controls.

------------------------------------------------------------------------

# Quiz

Quiz UI should prioritize the question.

Recommended hierarchy:

``` text
Question 3 of 10

Large question

┌──────────────────────────┐
│ Answer option             │
└──────────────────────────┘

┌──────────────────────────┐
│ Answer option             │
└──────────────────────────┘

[ Next Question ]
```

Answer choices should have large clickable areas.

Do not rely on tiny radio buttons.

------------------------------------------------------------------------

# Mind Map

The mind map should have maximum usable canvas space.

Controls should remain secondary.

Avoid placing the visualization inside a cramped card.

------------------------------------------------------------------------

# Empty States

Every empty state should be designed intentionally.

Instead of:

> No data found.

Use:

``` text
Your study library is empty

Upload your first document and StudyMate
will turn it into personalized study material.

[ Upload Document ]
```

Empty states should explain the next action.

------------------------------------------------------------------------

# Loading States

Avoid generic spinner-only experiences.

Use contextual loading states:

``` text
Processing your document...
Generating your notes...
Preparing your flashcards...
Building your quiz...
```

Use skeleton loaders where content structure is known.

Avoid excessive animations.

------------------------------------------------------------------------

# Error States

Errors should be:

-   understandable
-   actionable
-   visually distinct
-   non-technical for normal users

Bad:

> 500 Internal Server Error

Better:

> We couldn't generate your notes right now. Please try again.

``` text
[ Try Again ]
```

Technical details may remain available for debugging/logging without
dominating the UI.

------------------------------------------------------------------------

# Cards

Cards should not be used everywhere.

Use cards when they create meaningful grouping.

Preferred:

-   subtle radius
-   subtle border or shadow
-   generous padding
-   clear hierarchy

Avoid:

-   excessive shadows
-   glowing borders
-   gradient cards everywhere
-   excessive rounded pills
-   "AI glassmorphism" aesthetics

------------------------------------------------------------------------

# Shadows and Borders

Use restraint.

Prefer:

``` text
subtle border
+
very soft shadow
```

rather than large floating shadows.

Avoid making every component look like a floating glass panel.

------------------------------------------------------------------------

# Responsive Design

The application must work well on:

-   desktop
-   laptop
-   tablet
-   mobile

Do not simply shrink desktop layouts.

For mobile:

-   stack major sections
-   make buttons full-width where appropriate
-   maintain readable typography
-   provide adequate touch targets
-   prevent horizontal overflow
-   make navigation usable

------------------------------------------------------------------------

# Interaction Quality

Every interactive element should have:

-   hover state
-   active state where appropriate
-   focus state
-   disabled state
-   loading state when applicable

Transitions should be subtle.

Recommended:

``` text
150–250ms
ease-out
```

Avoid excessive animation.

------------------------------------------------------------------------

# Accessibility

Maintain or improve:

-   semantic HTML
-   keyboard navigation
-   visible focus states
-   sufficient contrast
-   accessible labels
-   appropriate button/link semantics
-   usable touch targets

Do not sacrifice accessibility for visual appearance.

------------------------------------------------------------------------

# Design Consistency

Create reusable CSS variables/tokens for:

``` css
--color-primary
--color-background
--color-surface
--color-text
--color-muted
--color-border

--space-xs
--space-sm
--space-md
--space-lg
--space-xl

--radius-sm
--radius-md
--radius-lg

--shadow-sm
--shadow-md

--container-width
```

Use the same design system throughout the application.

Do not solve every page independently.

------------------------------------------------------------------------

# What NOT to Do

Do not:

-   rewrite the frontend framework
-   introduce React/Next.js
-   introduce Tailwind just for styling
-   change backend APIs
-   change authentication
-   change SSE architecture
-   change Redis behavior
-   change database behavior
-   remove existing functionality
-   break existing routes
-   redesign functionality unnecessarily
-   add random animations
-   add excessive gradients
-   use excessive glassmorphism
-   make every component rounded/pill-shaped
-   make every section a card
-   use tiny buttons
-   use tiny typography
-   turn StudyMate into a chatbot UI

The task is a **visual and UX transformation**, not an architectural
rewrite.

------------------------------------------------------------------------

# Implementation Strategy

Before changing anything:

1.  Inspect the existing frontend structure.
2.  Identify shared CSS/components/layouts.
3.  Identify all major pages.
4.  Identify duplicated styling.
5.  Identify existing responsive behavior.
6.  Identify the current color/font/spacing system.

Then create a consistent design system and progressively apply it.

Prioritize in this order:

### P0 --- Global visual foundation

-   typography
-   colors
-   spacing
-   container widths
-   header/navigation
-   buttons
-   inputs
-   cards
-   responsive foundation

### P1 --- Main product experience

-   dashboard
-   upload
-   document library
-   generated content pages
-   loading states
-   empty states
-   errors

### P2 --- Feature-specific polish

-   notes
-   revision
-   flashcards
-   quizzes
-   mind maps
-   settings/profile
-   authentication pages

------------------------------------------------------------------------

# Reference Design Interpretation

The supplied Slido references demonstrate several qualities worth
adopting:

### Reference 1 --- Hero

Use:

-   large headline
-   strong left/right composition
-   large visual area
-   clear primary CTA
-   generous whitespace

### Reference 2 --- How it works

Use:

-   strong section heading
-   simple visual storytelling
-   consistent three-column/grid layouts
-   clear numbered hierarchy
-   large visual cards

### Reference 3 --- Template grid

Use:

-   strong heading
-   spacious three-column layout
-   large visual previews
-   clear titles
-   readable descriptions
-   simple text actions

These are **design principles**, not templates to copy literally.

------------------------------------------------------------------------

# Definition of Done

The redesign is successful when:

-   The application no longer feels like a generic AI dashboard.
-   Primary actions are immediately obvious.
-   Buttons are comfortably sized.
-   Typography feels deliberate and professional.
-   Pages have significantly better whitespace and hierarchy.
-   Generated study content is pleasant to read.
-   Uploading and generating content feel like premium product
    interactions.
-   Desktop and mobile layouts feel intentional.
-   Visual styling is consistent across the entire application.
-   Existing functionality continues to work.
-   No backend architecture or API behavior is unnecessarily changed.

Most importantly:

> **A user should be able to open StudyMate and immediately feel that
> this is a polished learning product, not a college project assembled
> from UI components.**

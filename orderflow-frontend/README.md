# Orderflow Frontend (Astro + Vue + Tailwind)

This is the dashboard frontend for visualizing orderflow/candles using TradingView Lightweight Charts.

## Tech

- Astro
- Vue 3
- Tailwind CSS (v4 via @tailwindcss/vite)
- lightweight-charts

## Getting Started

### 1) Requirements

- Node.js 18+ (20+ recommended)
- npm 9+

### 2) Install

```bash
npm install
```

### 3) Configure Environment

Create `.env` (or `.env.local`) in the project root with:

```bash
PUBLIC_API_URL="https://YOUR-CLOUD-RUN-URL/api/v1/candles"
PUBLIC_API_KEY="YOUR_API_KEY"
```

### 4) Run Dev Server

```bash
npm run dev
```

Open the URL shown (usually http://localhost:4321).

## Project Structure

```
src/
├── components/
│   └── OrderflowChart.vue
├── layouts/
│   └── Layout.astro
├── pages/
│   └── index.astro
└── styles/
    └── global.css
```

## Notes

- The chart expects the API to return data items like: `{ time, open, high, low, close }`.
- Only env vars prefixed with `PUBLIC_` are exposed to client code in Astro.

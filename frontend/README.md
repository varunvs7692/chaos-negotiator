# Frontend Dashboard (React)

This directory contains a minimal React application that consumes the Python
agent's API endpoints. It is intentionally lightweight and can be initialized
with `npm install` after creating the project with `create-react-app`
(e.g. `npx create-react-app chaos-dashboard`).

## Getting started

```bash
cd frontend
npm install         # pulls in axios, recharts, react, react-scripts etc.
npm start           # launches dev server on http://localhost:3000
```

The React app expects the Python server to be running concurrently on
`http://localhost:8000` with the `/api/deployments/latest` endpoint available.

## Folder structure

```
frontend/
  package.json          # dependencies & scripts
  .gitignore
  src/
    index.js            # React entrypoint
    App.js              # root component
    App.css             # basic styling
    services/api.js     # HTTP helpers (axios)
    components/         # presentational widgets (RiskCard, CanaryProgress)
    pages/              # high-level pages (Dashboard)
```

You can extend the layout, add charts, or connect real data by modifying the
service layer and components. This scaffold provides a recruiter‑friendly
starting point for demonstrating the agent's intelligence.

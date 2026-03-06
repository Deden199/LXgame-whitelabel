# Frontend Setup (CRA5 + CRACO)

Stack ini menggunakan `react-scripts@5` + `@craco/craco` dengan dependency yang dipin agar stabil:
- `react@18.2.0`
- `react-dom@18.2.0`
- `react-router-dom@6.22.3`

## Install

```bash
cd frontend
npm ci
```

## Run (dev)

```bash
npm start
```

Default URL: `http://localhost:3000`

## Build (production)

```bash
npm run build
```

## Environment
Buat file `.env` (opsional untuk local):

```bash
REACT_APP_BACKEND_URL=http://localhost:8001
```

## Notes
- Jangan gunakan `--force` / `--legacy-peer-deps` untuk instalasi normal repo ini.
- Lockfile sudah disinkronkan agar `npm ci` reproducible.

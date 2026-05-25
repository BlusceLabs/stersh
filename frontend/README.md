# Watch!fy Frontend

This is the frontend for the Watch!fy streaming service, built with:

- **React 18** with TypeScript
- **TanStack Router** for client-side routing
- **TanStack Query** for data fetching and caching
- **Zustand** for state management
- **Tailwind CSS** for styling
- **HLS.js** for video playback

## Features

- **Movie/TV Show Discovery** - Browse trending and top-rated content
- **Search** - Smart search with filters (genre, year, rating, type)
- **Video Player** - HLS streaming with quality selection
- **User Authentication** - Login, registration, and profile management
- **Favorites & Watchlist** - Save and organize content
- **Continue Watching** - Resume playback from where you left off
- **Download Manager** - Download content for offline viewing
- **Recommendations** - AI-powered personalized recommendations
- **Parental Controls** - Content filtering based on ratings
- **Multi-Language Subtitles** - Support for various subtitle languages
- **Responsive Design** - Works on mobile, tablet, and desktop

## Getting Started

### Prerequisites
- Node.js 18+
- Watch!fy Backend running on `http://localhost:8000`

### Installation

1. Install dependencies:
   ```bash
   cd frontend
   npm install
   # or
   yarn install
   ```

2. Create a `.env` file in the `frontend` directory:
   ```
   VITE_TMDB_API_KEY=your_tmdb_api_key_here
   VITE_API_URL=http://localhost:8000
   ```

3. Start the development server:
   ```bash
   npm run dev
   # or
   yarn dev
   ```

4. Open your browser and navigate to `http://localhost:3000`.

## Project Structure

```
frontend/
├── public/
│   └── index.html
├── src/
│   ├── app/
│   │   └── pages/          # Page components
│   ├── components/          # Reusable components
│   ├── store/              # Zustand stores
│   └── utils/             # Utility functions
├── tailwind.config.ts
├── tsconfig.json
├── package.json
└── vite.config.ts
```

## Available Pages

- **Home** (`/`) - Featured content and recommendations
- **Movies** (`/movies`) - Browse all movies
- **TV Shows** (`/tv`) - Browse all TV shows
- **Search** (`/search`) - Search for content
- **Player** (`/player/:mediaType/:id`) - Video player
- **Login** (`/login`) - User login
- **Register** (`/register`) - User registration
- **Profile** (`/profile`) - User profile and settings
- **Downloads** (`/downloads`) - Downloaded content

## Environment Variables

| Variable | Description |
|----------|-------------|
| `VITE_TMDB_API_KEY` | TMDB API key (required) |
| `VITE_API_URL` | Backend API URL (default: http://localhost:8000) |

## Scripts

- `dev`: Runs the development server
- `build`: Builds the app for production
- `preview`: Runs the built app in preview mode

## Dependencies

- **React** 18.2.0
- **TanStack Router** 8.7.3
- **TanStack Query** 4.28.3
- **Zustand** 4.4.7
- **HLS.js** 4.0.0
- **Tailwind CSS** 3.3.2

## Building for Production

1. Build the project:
   ```bash
   npm run build
   # or
   yarn build
   ```

2. Serve the `dist` directory with any static file server.

## License

This project is licensed under the MIT License.

## Acknowledgments

- **TanStack** for amazing React libraries
- **Tailwind CSS** for making styling easy
- **HLS.js** for video playback
- **TMDB** for the API

(End of file - total 24 lines)
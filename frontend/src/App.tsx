import { createBrowserRouter, Navigate } from 'react-router-dom'
import Layout from './components/Layout'
import Home from './pages/Home'
import Setup from './pages/Setup'
import Config from './pages/Config'
import Jobs from './pages/Jobs'
import Results from './pages/Results'
import Leaderboard from './pages/Leaderboard'
import Fingerprint from './pages/Fingerprint'

export const router = createBrowserRouter([
  {
    path: '/',
    element: <Layout />,
    children: [
      { index: true, element: <Navigate to="/home" replace /> },
      { path: 'home', element: <Home /> },
      { path: 'setup', element: <Setup /> },
      { path: 'config', element: <Config /> },
      { path: 'jobs', element: <Jobs /> },
      { path: 'results', element: <Results /> },
      { path: 'leaderboard', element: <Leaderboard /> },
      { path: 'results/:resultPath/fingerprint', element: <Fingerprint /> },
    ],
  },
])

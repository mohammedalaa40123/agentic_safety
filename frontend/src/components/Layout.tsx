import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import { Settings2, FlaskConical, ListTodo, BarChart3, ShieldAlert, Home, Trophy } from 'lucide-react'

const NAV = [
  { to: '/home',        label: 'Home',       sub: 'Overview & docs',  Icon: Home },
  { to: '/setup',       label: 'Setup',      sub: 'Provider keys',    Icon: Settings2 },
  { to: '/config',      label: 'Evaluate',   sub: 'Launch eval run',  Icon: FlaskConical },
  { to: '/jobs',        label: 'Jobs',       sub: 'Monitor runs',     Icon: ListTodo },
  { to: '/results',     label: 'Results',    sub: 'Browse results',   Icon: BarChart3 },
  { to: '/leaderboard', label: 'Leaderboard',sub: 'Compare models',   Icon: Trophy },
]

export default function Layout() {
  const location = useLocation()

  return (
    <div className="flex min-h-screen">
      {/* Sidebar */}
      <aside
        className="w-60 shrink-0 flex flex-col border-r"
        style={{
          background: 'rgba(8,10,24,0.92)',
          borderColor: 'rgba(99,102,241,0.12)',
          backdropFilter: 'blur(16px)',
        }}
      >
        {/* Logo area */}
        <div className="px-5 pt-6 pb-5 border-b" style={{ borderColor: 'rgba(99,102,241,0.1)' }}>
          <div className="flex items-center gap-3">
            <div className="relative">
              <div className="w-9 h-9 rounded-xl flex items-center justify-center"
                style={{ background: 'linear-gradient(135deg,#6366f1,#a855f7)' }}>
                <ShieldAlert size={18} className="text-white" />
              </div>
              <div className="absolute inset-0 rounded-xl blur-md opacity-50"
                style={{ background: 'linear-gradient(135deg,#6366f1,#a855f7)' }} />
            </div>
            <div>
              <div className="text-sm font-bold text-slate-100 leading-tight">Agentic Safety</div>
              <div className="text-xs text-slate-500">Eval Platform</div>
            </div>
          </div>
        </div>

        {/* Nav */}
        <nav className="flex-1 py-5 px-3 space-y-1">
          {NAV.map(({ to, label, sub, Icon }) => {
            const active = location.pathname.startsWith(to)
            return (
              <NavLink key={to} to={to} className="block">
                <motion.div
                  whileHover={{ x: 3 }}
                  whileTap={{ scale: 0.97 }}
                  transition={{ duration: 0.15 }}
                  className={`relative flex items-center gap-3 px-3 py-2.5 rounded-xl transition-colors duration-200 ${
                    active
                      ? 'text-slate-100'
                      : 'text-slate-500 hover:text-slate-300'
                  }`}
                  style={active ? {
                    background: 'linear-gradient(135deg,rgba(99,102,241,0.18),rgba(168,85,247,0.12))',
                    boxShadow: 'inset 0 0 0 1px rgba(99,102,241,0.25)',
                  } : undefined}
                >
                  {active && (
                    <motion.div
                      layoutId="nav-indicator"
                      className="absolute left-0 top-1 bottom-1 w-0.5 rounded-full"
                      style={{ background: 'linear-gradient(to bottom,#6366f1,#a855f7)' }}
                    />
                  )}
                  <Icon size={16} className={active ? 'text-indigo-400' : ''} />
                  <div>
                    <div className="text-sm font-medium leading-none mb-0.5">{label}</div>
                    <div className="text-xs opacity-50 leading-none">{sub}</div>
                  </div>
                </motion.div>
              </NavLink>
            )
          })}
        </nav>

        {/* Footer */}
        <div className="px-5 py-4 border-t" style={{ borderColor: 'rgba(99,102,241,0.1)' }}>
          <div className="text-xs text-slate-600">ECE570 · Purdue University</div>
          <div className="text-xs text-slate-700 mt-0.5">v0.1.0</div>
        </div>
      </aside>

      {/* Main content */}
      <main className="flex-1 min-w-0 overflow-auto">
        <AnimatePresence mode="wait">
          <motion.div
            key={location.pathname}
            initial={{ opacity: 0, y: 8 }}
            animate={{ opacity: 1, y: 0 }}
            exit={{ opacity: 0, y: -4 }}
            transition={{ duration: 0.22, ease: 'easeOut' }}
            className="min-h-full"
          >
            <Outlet />
          </motion.div>
        </AnimatePresence>
      </main>
    </div>
  )
}

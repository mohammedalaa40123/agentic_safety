import { useEffect, useRef, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Circle, CheckCircle2, XCircle, Clock, Ban,
  ChevronDown, ChevronRight, ExternalLink, Timer, Hash, RefreshCw, Trash2,
} from 'lucide-react'
import { api, createJobSocket, type JobSummary } from '../lib/api'
import { useJobStore } from '../stores/jobStore'
import { Link } from 'react-router-dom'

const STATUS_CONFIG: Record<string, { bg: string; text: string; border: string; Icon: React.ElementType; pulse: boolean }> = {
  queued:    { bg: 'rgba(251,191,36,0.1)',  text: '#fbbf24', border: 'rgba(251,191,36,0.25)',  Icon: Clock,        pulse: false },
  running:   { bg: 'rgba(99,102,241,0.12)', text: '#818cf8', border: 'rgba(99,102,241,0.3)',   Icon: Circle,       pulse: true  },
  completed: { bg: 'rgba(52,211,153,0.1)',  text: '#34d399', border: 'rgba(52,211,153,0.25)',  Icon: CheckCircle2, pulse: false },
  failed:    { bg: 'rgba(239,68,68,0.1)',   text: '#f87171', border: 'rgba(239,68,68,0.25)',   Icon: XCircle,      pulse: false },
  cancelled: { bg: 'rgba(100,116,139,0.1)', text: '#64748b', border: 'rgba(100,116,139,0.2)',  Icon: Ban,          pulse: false },
}

function StatusBadge({ status }: { status: string }) {
  const cfg = STATUS_CONFIG[status] ?? STATUS_CONFIG.cancelled
  const { bg, text, border, Icon, pulse } = cfg
  return (
    <span
      className={`badge ${pulse ? 'glow-pulse' : ''}`}
      style={{ background: bg, color: text, border: `1px solid ${border}` }}
    >
      <motion.span
        animate={pulse ? { opacity: [1, 0.3, 1] } : {}}
        transition={{ duration: 1.4, repeat: Infinity }}
      >
        <Icon size={10} />
      </motion.span>
      {status}
    </span>
  )
}

function ProgressBar({ pct }: { pct: number }) {
  return (
    <div className="flex items-center gap-2 mt-1.5">
      <div className="flex-1 h-1 rounded-full overflow-hidden" style={{ background: 'rgba(99,102,241,0.12)' }}>
        <motion.div
          className="h-full rounded-full"
          style={{ background: 'linear-gradient(90deg,#6366f1,#818cf8)' }}
          initial={{ width: 0 }}
          animate={{ width: `${pct}%` }}
          transition={{ duration: 0.4, ease: 'easeOut' }}
        />
      </div>
      <span className="text-xs text-slate-500 tabular-nums w-9 text-right">{pct}%</span>
    </div>
  )
}

function ModelChip({ label, value, color }: { label: string; value: string; color: string }) {
  if (!value) return null
  return (
    <span className="inline-flex items-center gap-1 text-xs px-1.5 py-0.5 rounded"
      style={{ background: `${color}14`, color, border: `1px solid ${color}28` }}>
      <span className="text-[10px] opacity-60">{label}</span>
      <span className="font-medium truncate max-w-[120px]">{value}</span>
    </span>
  )
}

function LogPane({ job }: { job: JobSummary }) {
  const [lines, setLines] = useState<string[]>(job.log_tail ?? [])
  const containerRef = useRef<HTMLDivElement>(null)
  // true  = follow the tail; false = user scrolled up to read
  const shouldAutoScroll = useRef(true)

  useEffect(() => {
    if (job.log_tail?.length) setLines(job.log_tail)
    if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') return
    const ws = createJobSocket(job.id, (line) => setLines((prev) => [...prev, line]), () => {})
    return () => ws.close()
  }, [job.id, job.status])

  // Scroll the container (not the page) when new lines arrive, but only when
  // the user hasn't manually scrolled up.
  useEffect(() => {
    const el = containerRef.current
    if (!el || !shouldAutoScroll.current) return
    el.scrollTop = el.scrollHeight
  }, [lines])

  // Detect manual scroll: if user is >40px above the bottom, pause auto-scroll.
  function handleScroll() {
    const el = containerRef.current
    if (!el) return
    const atBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 40
    shouldAutoScroll.current = atBottom
  }

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.2 }}
      className="overflow-hidden"
    >
      <div
        ref={containerRef}
        onScroll={handleScroll}
        className="log-terminal p-4 h-72 overflow-auto rounded-xl mt-4 border"
        style={{ borderColor: 'rgba(99,102,241,0.15)' }}
      >
        {lines.length === 0 ? (
          <span className="text-slate-600">Waiting for output…</span>
        ) : (
          lines.map((l, i) => (
            <motion.div
              key={i}
              initial={{ opacity: 0, x: -4 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ duration: 0.08 }}
              className="whitespace-pre-wrap break-all"
            >
              {l}
            </motion.div>
          ))
        )}
      </div>
    </motion.div>
  )
}

function fmtDuration(secs: number | null | undefined) {
  if (secs == null) return null
  if (secs < 60) return `${Math.round(secs)}s`
  const m = Math.floor(secs / 60), s = Math.round(secs % 60)
  return `${m}m ${s}s`
}

// ── Per-job result summary ────────────────────────────────────────────────────
interface ResultsSummary {
  total_experiments: number
  ASR: number
  Task_Success: number
  avg_duration?: number
  avg_queries?: number
  TIR?: number
  by_category?: Record<string, { n: number; ASR: number; Task_Success: number }>
}

function ResultsPane({ jobId }: { jobId: string }) {
  const [summary, setSummary] = useState<ResultsSummary | null>(null)
  const [cats, setCats] = useState<[string, { n: number; ASR: number; Task_Success: number }][]>([])
  const [loading, setLoading] = useState(true)
  const [err, setErr] = useState<string | null>(null)

  useEffect(() => {
    api.getJobResults(jobId)
      .then((raw) => {
        const r = raw as Record<string, unknown>
        let s: ResultsSummary
        if (r.summary && r.records) {
          s = r.summary as ResultsSummary
          setCats(
            Object.entries((s.by_category ?? {}) as Record<string, { n: number; ASR: number; Task_Success: number }>)
              .sort((a, b) => b[1].ASR - a[1].ASR)
          )
        } else if (Array.isArray(raw)) {
          const recs = raw as Record<string, unknown>[]
          const n = recs.length
          const attacked = recs.filter((rec) => String(rec.attack_success).toLowerCase() === 'true').length
          const task_ok  = recs.filter((rec) => String(rec.task_success).toLowerCase()  === 'true').length
          const tot_tools = recs.reduce((acc, rec) => acc + (Number(rec.tool_calls_total) || 0), 0)
          const tot_dur   = recs.reduce((acc, rec) => acc + (Number(rec.duration) || 0), 0)
          const tot_q     = recs.reduce((acc, rec) => acc + (Number(rec.queries) || 0), 0)
          s = {
            total_experiments: n,
            ASR: n ? attacked / n : 0,
            Task_Success: n ? task_ok / n : 0,
            avg_duration: n ? tot_dur / n : 0,
            avg_queries:  n ? tot_q  / n : 0,
            TIR:          n ? tot_tools / n : 0,
          }
        } else {
          setErr('Unknown result format'); return
        }
        setSummary(s)
      })
      .catch((e) => setErr(String(e)))
      .finally(() => setLoading(false))
  }, [jobId])

  if (loading) return (
    <div className="text-center py-6 text-xs text-slate-500">
      <RefreshCw size={16} className="animate-spin mx-auto mb-2 opacity-40" />Loading results…
    </div>
  )
  if (err || !summary) return (
    <div className="text-xs text-rose-400 py-4">{err ?? 'No results available'}</div>
  )

  const pills = [
    { label: 'N',            val: String(summary.total_experiments), color: '#818cf8' },
    { label: 'ASR',          val: `${(summary.ASR * 100).toFixed(1)}%`, color: summary.ASR >= 0.5 ? '#f87171' : '#34d399' },
    { label: 'Task Success', val: `${(summary.Task_Success * 100).toFixed(1)}%`, color: '#a3e635' },
    ...(summary.avg_duration != null ? [{ label: 'Avg Duration', val: `${summary.avg_duration.toFixed(1)}s`, color: '#94a3b8' }] : []),
    ...(summary.avg_queries  != null ? [{ label: 'Avg Queries',  val: summary.avg_queries.toFixed(1),       color: '#94a3b8' }] : []),
    ...(summary.TIR          != null ? [{ label: 'TIR',          val: summary.TIR.toFixed(1),               color: '#fb923c' }] : []),
  ]

  return (
    <motion.div
      initial={{ opacity: 0, height: 0 }}
      animate={{ opacity: 1, height: 'auto' }}
      exit={{ opacity: 0, height: 0 }}
      transition={{ duration: 0.2 }}
      className="overflow-hidden"
    >
      <div className="space-y-3 mt-4">
        {/* Metric pills */}
        <div className="flex flex-wrap gap-2">
          {pills.map(({ label, val, color }) => (
            <span key={label} className="flex items-center gap-1.5 text-xs px-2.5 py-1.5 rounded-lg"
              style={{ background: `${color}14`, color, border: `1px solid ${color}28` }}>
              <span className="opacity-50">{label}</span>
              <span className="font-bold">{val}</span>
            </span>
          ))}
        </div>

        {/* Per-category table */}
        {cats.length > 0 && (
          <div className="overflow-x-auto rounded-lg"
            style={{ border: '1px solid rgba(99,102,241,0.1)' }}>
            <table className="w-full text-xs">
              <thead>
                <tr style={{ background: 'rgba(15,23,42,0.8)', borderBottom: '1px solid rgba(99,102,241,0.08)' }}>
                  <th className="px-3 py-1.5 text-left text-slate-500 font-medium">Category</th>
                  <th className="px-3 py-1.5 text-center text-slate-500 font-medium">N</th>
                  <th className="px-3 py-1.5 text-center text-slate-500 font-medium">ASR</th>
                  <th className="px-3 py-1.5 text-center text-slate-500 font-medium">Task</th>
                </tr>
              </thead>
              <tbody>
                {cats.slice(0, 12).map(([cat, v]) => (
                  <tr key={cat} className="border-t" style={{ borderColor: 'rgba(99,102,241,0.06)' }}>
                    <td className="px-3 py-1.5 text-slate-400 max-w-[220px] truncate" title={cat}>{cat}</td>
                    <td className="px-3 py-1.5 text-center text-slate-500">{v.n}</td>
                    <td className="px-3 py-1.5 text-center font-mono"
                      style={{ color: v.ASR >= 0.5 ? '#f87171' : '#34d399' }}>
                      {(v.ASR * 100).toFixed(0)}%
                    </td>
                    <td className="px-3 py-1.5 text-center font-mono text-slate-500">
                      {(v.Task_Success * 100).toFixed(0)}%
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </motion.div>
  )
}

export default function Jobs() {
  const { jobs, setJobs, upsertJob, removeJob } = useJobStore()
  const [selected, setSelected] = useState<string | null>(null)
  const [cancelling, setCancelling] = useState<string | null>(null)
  const [removing, setRemoving] = useState<string | null>(null)
  const [activeTab, setActiveTab] = useState<Record<string, 'logs' | 'results'>>({})

  function switchTab(jobId: string, tab: 'logs' | 'results') {
    setActiveTab((prev) => ({ ...prev, [jobId]: tab }))
  }

  useEffect(() => {
    api.listJobs().then(setJobs).catch(console.error)
    const interval = setInterval(() => {
      api.listJobs().then((list) => list.forEach(upsertJob)).catch(() => {})
    }, 4000)
    return () => clearInterval(interval)
  }, [])

  async function handleCancel(id: string) {
    setCancelling(id)
    try {
      await api.cancelJob(id)
      upsertJob({ ...jobs.find((j) => j.id === id)!, status: 'cancelled' })
    } finally { setCancelling(null) }
  }

  async function handleDelete(id: string) {
    setRemoving(id)
    try {
      await api.removeJob(id)
      removeJob(id)
      if (selected === id) setSelected(null)
    } finally { setRemoving(null) }
  }

  const queued    = jobs.filter((j) => j.status === 'queued').length
  const running   = jobs.filter((j) => j.status === 'running').length
  const completed = jobs.filter((j) => j.status === 'completed').length
  const failed    = jobs.filter((j) => j.status === 'failed').length

  return (
    <div className="page-wrapper max-w-4xl mx-auto space-y-6">
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
        <div className="flex items-end justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              Jobs
            </h1>
            <p className="text-slate-400 text-sm mt-1">Monitor and manage evaluation runs.</p>
          </div>
          {jobs.length > 0 && (
            <div className="flex gap-2 flex-wrap">
              {queued > 0 && (
                <span className="badge" style={{ background: 'rgba(251,191,36,0.1)', color: '#fbbf24', border: '1px solid rgba(251,191,36,0.25)' }}>
                  <Clock size={8} />{queued} queued
                </span>
              )}
              {running > 0 && (
                <span className="badge glow-pulse" style={{ background: 'rgba(99,102,241,0.12)', color: '#818cf8', border: '1px solid rgba(99,102,241,0.3)' }}>
                  <motion.span animate={{ opacity: [1, 0.3, 1] }} transition={{ duration: 1.4, repeat: Infinity }}>
                    <Circle size={8} />
                  </motion.span>
                  {running} running
                </span>
              )}
              {completed > 0 && (
                <span className="badge" style={{ background: 'rgba(52,211,153,0.1)', color: '#34d399', border: '1px solid rgba(52,211,153,0.2)' }}>
                  <CheckCircle2 size={8} />{completed} done
                </span>
              )}
              {failed > 0 && (
                <span className="badge" style={{ background: 'rgba(239,68,68,0.1)', color: '#f87171', border: '1px solid rgba(239,68,68,0.2)' }}>
                  <XCircle size={8} />{failed} failed
                </span>
              )}
            </div>
          )}
        </div>
      </motion.div>

      {jobs.length === 0 ? (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
          className="text-center py-16 text-slate-500 text-sm">
          <div className="text-4xl mb-3 opacity-30">📋</div>
          No jobs yet. Launch one from the Evaluate page.
        </motion.div>
      ) : (
        <div className="space-y-2">
          {jobs.map((job, i) => {
            const isSelected = selected === job.id
            const duration = fmtDuration(job.duration_seconds)
            return (
              <motion.div
                key={job.id}
                initial={{ opacity: 0, y: 8 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: i * 0.04 }}
                onClick={() => setSelected(isSelected ? null : job.id)}
                className="rounded-xl cursor-pointer transition-all duration-200"
                style={{
                  background: isSelected ? 'rgba(99,102,241,0.06)' : 'rgba(15,23,42,0.6)',
                  border: `1px solid ${isSelected ? 'rgba(99,102,241,0.3)' : 'rgba(99,102,241,0.1)'}`,
                  backdropFilter: 'blur(8px)',
                }}
              >
                <div className="p-4 flex items-start justify-between gap-4">
                  <div className="flex items-start gap-3 min-w-0 flex-1">
                    <div className="mt-0.5">
                      {isSelected
                        ? <ChevronDown size={14} className="text-indigo-400 shrink-0" />
                        : <ChevronRight size={14} className="text-slate-600 shrink-0" />}
                    </div>
                    <div className="min-w-0 flex-1">
                      {/* Job name — human-readable label */}
                      {job.name && (
                        <div className="text-sm font-medium text-slate-300 truncate mb-0.5">{job.name}</div>
                      )}
                      {/* Row 1: id + status + dataset + goal_count */}
                      <div className="flex items-center gap-2 flex-wrap">
                        <code className="text-xs text-slate-500 font-mono">{job.id.slice(0, 8)}</code>
                        <StatusBadge status={job.status} />
                        <span className="text-xs text-slate-500">{job.dataset}</span>
                        {job.goal_count != null && (
                          <span className="text-xs text-slate-600 px-1.5 py-0.5 rounded"
                            style={{ background: 'rgba(99,102,241,0.06)' }}>
                            {job.goal_count} goals
                          </span>
                        )}
                        {job.queue_position != null && (
                          <span className="flex items-center gap-1 text-xs text-amber-400 px-1.5 py-0.5 rounded"
                            style={{ background: 'rgba(251,191,36,0.08)' }}>
                            <Hash size={9} />#{job.queue_position} in queue
                          </span>
                        )}
                        {duration && (
                          <span className="flex items-center gap-1 text-xs text-slate-500">
                            <Timer size={9} />{duration}
                          </span>
                        )}
                      </div>

                      {/* Row 2: model chips */}
                      {(job.target_model || job.attacks?.length || job.defenses?.length) && (
                        <div className="flex gap-1.5 flex-wrap mt-1.5">
                          {job.target_model && <ModelChip label="target" value={job.target_model} color="#818cf8" />}
                          {job.attack_model && job.attack_model !== job.target_model && (
                            <ModelChip label="atk" value={job.attack_model} color="#f87171" />
                          )}
                          {job.attacks?.slice(0, 3).map((a) => (
                            <span key={a} className="text-xs px-1.5 py-0.5 rounded"
                              style={{ background: 'rgba(248,113,113,0.08)', color: '#f87171', border: '1px solid rgba(248,113,113,0.15)' }}>
                              {a}
                            </span>
                          ))}
                          {job.attacks && job.attacks.length > 3 && (
                            <span className="text-xs px-1.5 py-0.5 rounded"
                              style={{ background: 'rgba(248,113,113,0.06)', color: '#f87171', border: '1px solid rgba(248,113,113,0.12)', opacity: 0.7 }}>
                              +{job.attacks.length - 3}
                            </span>
                          )}
                          {job.defenses?.filter(Boolean).map((d) => (
                            <span key={d} className="text-xs px-1.5 py-0.5 rounded"
                              style={{ background: 'rgba(52,211,153,0.08)', color: '#34d399', border: '1px solid rgba(52,211,153,0.15)' }}>
                              {d}
                            </span>
                          ))}
                        </div>
                      )}

                      {/* Row 3: progress bar (running) */}
                      {job.status === 'running' && job.progress && (
                        <div className="mt-1.5">
                          <ProgressBar pct={job.progress.pct} />
                          <div className="text-xs text-slate-600 mt-0.5 truncate">{job.progress.label}</div>
                        </div>
                      )}

                      {/* Row 4: timestamps / errors */}
                      <div className="text-xs text-slate-600 mt-1">
                        {new Date(job.created_at).toLocaleString()}
                      </div>
                      {job.error && (
                        <div className="text-xs text-rose-400 mt-0.5 truncate">{job.error}</div>
                      )}
                    </div>
                  </div>

                  {/* Action buttons */}
                  <div className="flex gap-2 shrink-0 items-center">
                    {job.status === 'completed' && job.result_path && (
                      <Link
                        to="/results"
                        onClick={(e) => e.stopPropagation()}
                        className="flex items-center gap-1 text-xs px-2.5 py-1.5 rounded-lg font-medium"
                        style={{ background: 'rgba(52,211,153,0.1)', color: '#34d399', border: '1px solid rgba(52,211,153,0.2)' }}
                      >
                        <ExternalLink size={10} />Results
                      </Link>
                    )}
                    {(job.status === 'running' || job.status === 'queued') && (
                      <motion.button
                        whileTap={{ scale: 0.95 }}
                        onClick={(e) => { e.stopPropagation(); handleCancel(job.id) }}
                        disabled={cancelling === job.id}
                        className="text-xs px-3 py-1.5 rounded-lg font-medium transition-colors"
                        style={{ background: 'rgba(239,68,68,0.12)', color: '#f87171', border: '1px solid rgba(239,68,68,0.2)' }}
                      >
                        {cancelling === job.id ? 'Cancelling…' : 'Cancel'}
                      </motion.button>
                    )}
                    {(job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') && (
                      <motion.button
                        whileTap={{ scale: 0.95 }}
                        onClick={(e) => { e.stopPropagation(); handleDelete(job.id) }}
                        disabled={removing === job.id}
                        title="Remove from list"
                        className="flex items-center gap-1 text-xs px-2 py-1.5 rounded-lg font-medium transition-colors"
                        style={{ background: 'rgba(100,116,139,0.1)', color: '#64748b', border: '1px solid rgba(100,116,139,0.2)' }}
                      >
                        <Trash2 size={11} />
                        {removing === job.id ? '…' : ''}
                      </motion.button>
                    )}
                  </div>
                </div>

                <AnimatePresence>
                  {isSelected && (
                    <div className="px-4 pb-4" onClick={(e) => e.stopPropagation()}>
                      {/* Tabs — only show when job has results */}
                      {job.status === 'completed' && job.result_path && (
                        <div className="flex gap-1 mb-3">
                          {(['logs', 'results'] as const).map((tab) => {
                            const current = activeTab[job.id] ?? 'logs'
                            return (
                              <button
                                key={tab}
                                onClick={() => switchTab(job.id, tab)}
                                className="text-xs px-3 py-1 rounded-md capitalize transition-colors font-medium"
                                style={
                                  current === tab
                                    ? { background: 'rgba(99,102,241,0.18)', color: '#818cf8', border: '1px solid rgba(99,102,241,0.3)' }
                                    : { color: '#475569', border: '1px solid transparent' }
                                }
                              >
                                {tab === 'logs' ? '📋 Logs' : '📊 Results'}
                              </button>
                            )
                          })}
                        </div>
                      )}
                      {(activeTab[job.id] ?? 'logs') === 'results' && job.status === 'completed'
                        ? <ResultsPane jobId={job.id} />
                        : <LogPane job={job} />}
                    </div>
                  )}
                </AnimatePresence>
              </motion.div>
            )
          })}
        </div>
      )}
    </div>
  )
}


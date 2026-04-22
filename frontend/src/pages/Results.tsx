import { useEffect, useRef, useState, useMemo } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  TrendingUp, CheckCircle2, XCircle, ExternalLink,
  Cpu, Swords, Scale, Tag, MessageSquare, Wrench,
  LayoutGrid, ChevronDown, ChevronUp, Trash2, AlertTriangle, Download,
} from 'lucide-react'
import { api } from '../lib/api'
import { BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer, Cell } from 'recharts'

// ── Types ─────────────────────────────────────────────────────────────────────

interface ResultSummary {
  path: string
  size_bytes: number
  modified: number
  target_model: string
  attack_name: string
  attack_model: string
  judge_model: string
  defense_name: string
  record_count: number
  succeeded: number
  MIR: number
}

type GroupBy = 'model' | 'attack' | 'defense'

interface GroupedRuns { key: string; runs: ResultSummary[] }

// ── Helpers ───────────────────────────────────────────────────────────────────

function shortModel(m: string) {
  return m.replace(/^(genai|openrouter|ollama):/, '')
}

function attackColor(name: string): string {
  const c: Record<string, string> = {
    pair: '#f43f5e', crescendo: '#f59e0b', baseline: '#64748b',
    prompt_fusion: '#8b5cf6', stac: '#22d3ee', gcg: '#ef4444', adaptools: '#fb923c',
  }
  return c[name.toLowerCase()] ?? '#6366f1'
}

function defenseColor(name: string): string {
  if (!name || name === 'none') return '#475569'
  const c: Record<string, string> = {
    agentshield: '#10b981', stepshield: '#3b82f6', progent: '#a78bfa',
    jbshield: '#f59e0b', gradientcuff: '#f43f5e', contextguard: '#22d3ee',
  }
  return c[name.toLowerCase()] ?? '#6366f1'
}

// ── MIR Ring ──────────────────────────────────────────────────────────────────

function MIRRing({ MIR, size = 56 }: { MIR: number; size?: number }) {
  const r = size * 0.4
  const circ = 2 * Math.PI * r
  const dash = (MIR * circ)
  const color = MIR > 0.5 ? '#f87171' : MIR > 0.2 ? '#fbbf24' : '#34d399'
  return (
    <svg width={size} height={size} viewBox={`0 0 ${size} ${size}`} className="-rotate-90">
      <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="rgba(99,102,241,0.12)" strokeWidth={size * 0.09} />
      <motion.circle
        cx={size / 2} cy={size / 2} r={r} fill="none"
        stroke={color} strokeWidth={size * 0.09} strokeLinecap="round"
        strokeDasharray={circ}
        initial={{ strokeDashoffset: circ }}
        animate={{ strokeDashoffset: circ - dash }}
        transition={{ duration: 1, ease: 'easeOut', delay: 0.2 }}
      />
    </svg>
  )
}

// ── Experiment Card ───────────────────────────────────────────────────────────

function RunCard({
  run, selected, onClick, onDelete, onDownload,
}: {
  run: ResultSummary
  selected: boolean
  onClick: () => void
  onDelete: (e: React.MouseEvent) => void
  onDownload: (e: React.MouseEvent) => void
}) {
  const pct = (run.MIR * 100).toFixed(1)
  const color = run.MIR > 0.5 ? '#f87171' : run.MIR > 0.2 ? '#fbbf24' : '#34d399'
  const atkC = attackColor(run.attack_name)
  const defC = defenseColor(run.defense_name)

  return (
    <motion.button
      onClick={onClick}
      whileHover={{ y: -2 }}
      className="relative text-left rounded-2xl p-4 w-full overflow-hidden transition-all duration-200"
      style={{
        background: selected ? 'rgba(99,102,241,0.13)' : 'rgba(15,23,42,0.7)',
        border: `1px solid ${selected ? 'rgba(99,102,241,0.4)' : 'rgba(99,102,241,0.1)'}`,
        backdropFilter: 'blur(8px)',
        boxShadow: selected ? '0 0 0 1px rgba(99,102,241,0.25)' : 'none',
      }}
    >
      {/* Action buttons */}
      <div className="absolute top-2 right-2 flex gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
        <button
          onClick={onDownload}
          className="p-1 rounded-lg hover:!opacity-100"
          style={{ background: 'rgba(99,102,241,0.12)', color: '#818cf8' }}
          title="Download JSON"
        >
          <Download size={11} />
        </button>
        <button
          onClick={onDelete}
          className="p-1 rounded-lg hover:!opacity-100"
          style={{ background: 'rgba(239,68,68,0.1)', color: '#f87171' }}
          title="Delete result"
        >
          <Trash2 size={11} />
        </button>
      </div>

      {/* MIR */}
      <div className="flex items-start justify-between mb-3">
        <div>
          <div className="text-xl font-bold leading-none" style={{ color }}>{pct}%</div>
          <div className="text-[10px] text-slate-600 mt-0.5">MIR</div>
        </div>
        <MIRRing MIR={run.MIR} />
      </div>

      {/* Model */}
      <div className="text-xs font-semibold text-slate-200 truncate mb-2">
        {shortModel(run.target_model || run.attack_name)}
      </div>

      {/* Badges */}
      <div className="flex flex-wrap gap-1">
        {run.attack_name && (
          <span className="px-1.5 py-0.5 rounded text-[10px] font-medium"
            style={{ background: `${atkC}18`, color: atkC, border: `1px solid ${atkC}30` }}>
            {run.attack_name}
          </span>
        )}
        <span className="px-1.5 py-0.5 rounded text-[10px] font-medium"
          style={{ background: `${defC}18`, color: defC, border: `1px solid ${defC}30` }}>
          {run.defense_name === 'none' || !run.defense_name ? 'no defense' : run.defense_name}
        </span>
      </div>

      {/* Footer */}
      <div className="flex items-center justify-between mt-3 pt-2.5"
        style={{ borderTop: '1px solid rgba(99,102,241,0.08)' }}>
        <span className="text-[10px] text-slate-600">{run.record_count} records</span>
        <span className="text-[10px] text-slate-600">
          {new Date(run.modified * 1000).toLocaleDateString()}
        </span>
      </div>
    </motion.button>
  )
}

// ── Group section ─────────────────────────────────────────────────────────────

function GroupSection({
  group, selectedPath, onSelect, onDelete, onDownload,
}: {
  group: GroupedRuns
  selectedPath: string | null
  onSelect: (path: string) => void
  onDelete: (path: string) => void
  onDownload: (path: string) => void
}) {
  const [collapsed, setCollapsed] = useState(false)
  const bestMIR = Math.max(...group.runs.map((r) => r.MIR))
  const MIRColor = bestMIR > 0.5 ? '#f87171' : bestMIR > 0.2 ? '#fbbf24' : '#34d399'

  return (
    <div className="space-y-3">
      <button
        onClick={() => setCollapsed(!collapsed)}
        className="w-full flex items-center gap-3 group"
      >
        <div className="h-px flex-1" style={{ background: 'rgba(99,102,241,0.12)' }} />
        <div className="flex items-center gap-2 px-3 py-1.5 rounded-full"
          style={{ background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(99,102,241,0.15)' }}>
          <span className="text-xs font-semibold text-slate-300">{group.key}</span>
          <span className="text-[10px] font-bold" style={{ color: MIRColor }}>
            best {(bestMIR * 100).toFixed(0)}%
          </span>
          <span className="text-[10px] text-slate-600">{group.runs.length} run{group.runs.length !== 1 ? 's' : ''}</span>
          {collapsed
            ? <ChevronDown size={10} className="text-slate-600" />
            : <ChevronUp size={10} className="text-slate-600" />}
        </div>
        <div className="h-px flex-1" style={{ background: 'rgba(99,102,241,0.12)' }} />
      </button>

      {!collapsed && (
        <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-4 xl:grid-cols-5 gap-3">
          {group.runs.map((run) => (
            <motion.div
              key={run.path}
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              transition={{ duration: 0.2 }}
              className="group"
            >
              <RunCard
                run={run}
                selected={selectedPath === run.path}
                onClick={() => onSelect(run.path)}
                onDelete={(e) => { e.stopPropagation(); onDelete(run.path) }}
                onDownload={(e) => { e.stopPropagation(); onDownload(run.path) }}
              />
            </motion.div>
          ))}
        </div>
      )}
    </div>
  )
}

// ── Hover Popover ─────────────────────────────────────────────────────────────

function RecordPopover({ record, anchorRef }: { record: Record<string, unknown>; anchorRef: React.RefObject<HTMLElement | null> }) {
  const [pos, setPos] = useState({ top: 0, left: 0 })
  const popRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!anchorRef.current) return
    const rect = anchorRef.current.getBoundingClientRect()
    const pop = popRef.current
    const w = pop?.offsetWidth ?? 320
    const viewW = window.innerWidth
    let left = rect.left + rect.width / 2 - w / 2
    if (left + w > viewW - 16) left = viewW - w - 16
    if (left < 16) left = 16
    setPos({ top: rect.bottom + window.scrollY + 6, left })
  }, [anchorRef])

  const r = record
  const goal = String(r.goal ?? r.user_goal ?? '')
  const response = String(r.jailbreak_response ?? r.response ?? r.model_response ?? r.assistant ?? '')
  const tools = (r.tools_used ?? r.expected_tools) as string[] | undefined
  const attack = String(r.attack_name ?? r.attack ?? r.attack_used ?? '')
  const defense = String(r.defense_name ?? r.defense ?? r.defense_used ?? 'none')
  const stages = r.stages as Record<string, unknown>[] | undefined
  const lastJudge = stages ? (stages[stages.length - 1]?.judge as Record<string, unknown> | undefined) : undefined
  const judge = String(r.judge_score ?? r.score ?? lastJudge?.score ?? '')
  const reasoning = String(r.judge_reasoning ?? r.reasoning ?? lastJudge?.reasoning ?? '')
  const jailbroken = !!(r.attack_success || r.jailbroken || r.success)

  return (
    <motion.div
      ref={popRef}
      initial={{ opacity: 0, y: -4, scale: 0.97 }}
      animate={{ opacity: 1, y: 0, scale: 1 }}
      exit={{ opacity: 0, y: -4, scale: 0.97 }}
      transition={{ duration: 0.15 }}
      className="fixed z-50 w-80 rounded-2xl shadow-2xl text-xs overflow-hidden"
      style={{
        top: pos.top,
        left: pos.left,
        background: 'rgba(6,9,22,0.97)',
        border: `1px solid ${jailbroken ? 'rgba(248,113,113,0.35)' : 'rgba(52,211,153,0.3)'}`,
        backdropFilter: 'blur(16px)',
      }}
    >
      <div className="px-4 py-2.5 flex items-center gap-2"
        style={{ background: jailbroken ? 'rgba(248,113,113,0.12)' : 'rgba(52,211,153,0.1)', borderBottom: '1px solid rgba(99,102,241,0.1)' }}>
        {jailbroken ? <XCircle size={12} className="text-rose-400" /> : <CheckCircle2 size={12} className="text-emerald-400" />}
        <span className="font-semibold" style={{ color: jailbroken ? '#f87171' : '#34d399' }}>
          {jailbroken ? 'Jailbroken' : 'Blocked'}
        </span>
        {attack && attack !== 'undefined' && (
          <span className="ml-auto px-1.5 py-0.5 rounded font-medium text-[10px]"
            style={{ background: 'rgba(248,113,113,0.15)', color: '#f87171' }}>{attack}</span>
        )}
        {defense && defense !== 'undefined' && defense !== 'none' && (
          <span className="px-1.5 py-0.5 rounded font-medium text-[10px]"
            style={{ background: 'rgba(52,211,153,0.1)', color: '#34d399' }}>{defense}</span>
        )}
      </div>
      <div className="p-4 space-y-3">
        {goal && (
          <div>
            <div className="flex items-center gap-1.5 text-slate-500 mb-1"><MessageSquare size={10} />Goal</div>
            <div className="text-slate-300 leading-snug line-clamp-3">{goal}</div>
          </div>
        )}
        {response && (
          <div>
            <div className="flex items-center gap-1.5 text-slate-500 mb-1"><Cpu size={10} />Model response</div>
            <div className="text-slate-400 leading-snug line-clamp-3 italic">{response}</div>
          </div>
        )}
        {tools && tools.length > 0 && (
          <div>
            <div className="flex items-center gap-1.5 text-slate-500 mb-1"><Wrench size={10} />Tools used</div>
            <div className="flex flex-wrap gap-1">
              {tools.map((t) => (
                <span key={t} className="px-1.5 py-0.5 rounded text-[10px]"
                  style={{ background: 'rgba(99,102,241,0.12)', color: '#818cf8' }}>{t}</span>
              ))}
            </div>
          </div>
        )}
        {judge && judge !== 'undefined' && (
          <div className="flex items-center gap-2">
            <Scale size={10} className="text-slate-600" />
            <span className="text-slate-500">Judge score:</span>
            <span className="font-semibold text-slate-300">{judge}</span>
          </div>
        )}
        {reasoning && reasoning !== 'undefined' && (
          <div className="text-slate-600 italic leading-snug line-clamp-2">{reasoning}</div>
        )}
      </div>
    </motion.div>
  )
}

// ── Model info bar ─────────────────────────────────────────────────────────────

function ModelInfoBar({ summary }: { summary: ResultSummary }) {
  const items = [
    { icon: Cpu, label: 'Target', val: shortModel(summary.target_model) },
    { icon: Swords, label: 'Attack', val: summary.attack_name },
    { icon: Scale, label: 'Judge', val: shortModel(summary.judge_model) },
    { icon: Tag, label: 'Defense', val: summary.defense_name || 'none' },
  ].filter((x) => x.val && x.val !== 'undefined')

  return (
    <div className="flex flex-wrap gap-2">
      {items.map(({ icon: Icon, label, val }) => (
        <div key={label} className="flex items-center gap-2 px-3 py-2 rounded-xl"
          style={{ background: 'rgba(99,102,241,0.07)', border: '1px solid rgba(99,102,241,0.14)' }}>
          <Icon size={12} className="text-indigo-400 shrink-0" />
          <div>
            <div className="text-[10px] text-slate-600 leading-none mb-0.5">{label}</div>
            <div className="text-xs font-semibold text-slate-300 leading-none">{String(val)}</div>
          </div>
        </div>
      ))}
    </div>
  )
}

// ── MIR Gauge (detail view) ───────────────────────────────────────────────────

function MIRGauge({ MIR, total }: { MIR: number; total: number }) {
  const pct = MIR * 100
  const r = 44; const circ = 2 * Math.PI * r; const dash = (pct / 100) * circ
  return (
    <div className="rounded-xl p-5 flex flex-col items-center justify-center"
      style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(99,102,241,0.12)', backdropFilter: 'blur(8px)' }}>
      <div className="relative w-28 h-28 mb-3">
        <svg viewBox="0 0 100 100" className="w-full h-full -rotate-90">
          <circle cx="50" cy="50" r={r} fill="none" stroke="rgba(99,102,241,0.1)" strokeWidth="10" />
          <motion.circle cx="50" cy="50" r={r} fill="none" stroke="url(#MIRGrad)" strokeWidth="10"
            strokeLinecap="round" strokeDasharray={circ}
            initial={{ strokeDashoffset: circ }}
            animate={{ strokeDashoffset: circ - dash }}
            transition={{ duration: 1.2, ease: 'easeOut', delay: 0.3 }}
          />
          <defs>
            <linearGradient id="MIRGrad" x1="0" y1="0" x2="1" y2="0">
              <stop offset="0%" stopColor="#f87171" /><stop offset="100%" stopColor="#e879f9" />
            </linearGradient>
          </defs>
        </svg>
        <div className="absolute inset-0 flex flex-col items-center justify-center">
          <motion.span className="text-2xl font-bold text-rose-400" initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.6 }}>
            {pct.toFixed(1)}%
          </motion.span>
        </div>
      </div>
      <div className="text-xs text-slate-400 font-medium">Malicious Intent Rate</div>
      <div className="text-xs text-slate-600 mt-0.5">{total} scenarios</div>
    </div>
  )
}

function StatsCard({ succeeded, blocked }: { succeeded: number; blocked: number }) {
  return (
    <div className="rounded-xl p-5 space-y-3"
      style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(99,102,241,0.12)', backdropFilter: 'blur(8px)' }}>
      <div className="flex items-center gap-2">
        <XCircle size={14} className="text-rose-400" />
        <span className="text-xs text-slate-400">Jailbroken</span>
        <motion.span className="ml-auto text-xl font-bold text-rose-400" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.4 }}>
          {succeeded}
        </motion.span>
      </div>
      <div className="w-full h-px" style={{ background: 'rgba(99,102,241,0.1)' }} />
      <div className="flex items-center gap-2">
        <CheckCircle2 size={14} className="text-emerald-400" />
        <span className="text-xs text-slate-400">Blocked</span>
        <motion.span className="ml-auto text-xl font-bold text-emerald-400" initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.5 }}>
          {blocked}
        </motion.span>
      </div>
      <div className="w-full h-px" style={{ background: 'rgba(99,102,241,0.1)' }} />
      <div className="flex items-center gap-2">
        <TrendingUp size={14} className="text-slate-500" />
        <span className="text-xs text-slate-400">Total</span>
        <span className="ml-auto text-xl font-bold text-slate-300">{succeeded + blocked}</span>
      </div>
    </div>
  )
}

function CategoryChart({ records }: { records: Record<string, unknown>[] }) {
  const counts: Record<string, { total: number; success: number }> = {}
  for (const r of records) {
    const cat = (r.category as string) ?? 'unknown'
    if (!counts[cat]) counts[cat] = { total: 0, success: 0 }
    counts[cat].total++
    if (r.attack_success || r.jailbroken || r.success) counts[cat].success++
  }
  const data = Object.entries(counts).map(([name, v]) => ({
    name,
    MIR: v.total > 0 ? +(v.success / v.total).toFixed(3) : 0,
    total: v.total,
  })).sort((a, b) => b.MIR - a.MIR)
  const PALETTE = ['#f87171', '#fb923c', '#fbbf24', '#a3e635', '#34d399', '#22d3ee', '#60a5fa', '#a78bfa', '#f472b6', '#e879f9']

  return (
    <div className="rounded-xl p-5"
      style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(99,102,241,0.12)', backdropFilter: 'blur(8px)' }}>
      <div className="text-sm font-semibold text-slate-300 mb-4 flex items-center gap-2">
        <TrendingUp size={14} className="text-indigo-400" />MIR by category
      </div>
      <ResponsiveContainer width="100%" height={Math.max(180, data.length * 30)}>
        <BarChart data={data} layout="vertical" margin={{ left: 100, right: 20 }}>
          <XAxis type="number" domain={[0, 1]} tickFormatter={(v) => `${(v * 100).toFixed(0)}%`}
            tick={{ fill: '#475569', fontSize: 10 }} axisLine={false} tickLine={false} />
          <YAxis type="category" dataKey="name" tick={{ fill: '#64748b', fontSize: 10 }} width={100} axisLine={false} tickLine={false} />
          <Tooltip formatter={(v: number) => [`${(v * 100).toFixed(1)}%`, 'MIR']}
            contentStyle={{ background: 'rgba(6,9,22,0.97)', border: '1px solid rgba(99,102,241,0.2)', borderRadius: 10, fontSize: 12 }} />
          <Bar dataKey="MIR" radius={[0, 5, 5, 0]} isAnimationActive>
            {data.map((_, i) => <Cell key={i} fill={PALETTE[i % PALETTE.length]} />)}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Main Page ─────────────────────────────────────────────────────────────────

export default function Results() {
  const navigate = useNavigate()
  const [summaries, setSummaries] = useState<ResultSummary[]>([])
  const [groupBy, setGroupBy] = useState<GroupBy>('model')
  const [selectedPath, setSelectedPath] = useState<string | null>(null)
  const [records, setRecords] = useState<Record<string, unknown>[]>([])
  const [loadingDetail, setLoadingDetail] = useState(false)
  const [hoveredRecord, setHoveredRecord] = useState<Record<string, unknown> | null>(null)
  const hoverAnchor = useRef<HTMLElement | null>(null)
  const detailRef = useRef<HTMLDivElement>(null)
  const [confirmDelete, setConfirmDelete] = useState<string | null>(null)
  const [deleting, setDeleting] = useState(false)

  useEffect(() => {
    api.getResultsSummary().then(setSummaries).catch(console.error)
  }, [])

  async function handleSelect(path: string) {
    if (selectedPath === path) { setSelectedPath(null); setRecords([]); return }
    setSelectedPath(path)
    setLoadingDetail(true)
    setRecords([])
    try {
      const res = await api.getResult(path) as Record<string, unknown>[] | Record<string, unknown>
      const rows = Array.isArray(res) ? res : (res.records as Record<string, unknown>[]) ?? [res]
      setRecords(rows)
      setTimeout(() => detailRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' }), 100)
    } catch (e) { console.error(e) }
    finally { setLoadingDetail(false) }
  }

  async function handleDelete(path: string) {
    setDeleting(true)
    try {
      await api.deleteResult(path)
      setSummaries((prev) => prev.filter((s) => s.path !== path))
      if (selectedPath === path) { setSelectedPath(null); setRecords([]) }
    } catch (e) { console.error(e) }
    finally { setDeleting(false); setConfirmDelete(null) }
  }

  async function handleDownload(path: string) {
    try {
      const data = await api.getResult(path)
      const blob = new Blob([JSON.stringify(data, null, 2)], { type: 'application/json' })
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url
      a.download = path.split('/').pop() ?? 'result.json'
      a.click()
      URL.revokeObjectURL(url)
    } catch (e) { console.error(e) }
  }

  const groups: GroupedRuns[] = useMemo(() => {
    const map = new Map<string, ResultSummary[]>()
    for (const s of summaries) {
      const key =
        groupBy === 'model' ? shortModel(s.target_model) :
          groupBy === 'attack' ? (s.attack_name || 'unknown') :
            (s.defense_name || 'none')
      const arr = map.get(key) ?? []
      arr.push(s)
      map.set(key, arr)
    }
    return Array.from(map.entries())
      .map(([key, runs]) => ({ key, runs }))
      .sort((a, b) => {
        const aMIR = Math.max(...a.runs.map((r) => r.MIR))
        const bMIR = Math.max(...b.runs.map((r) => r.MIR))
        return bMIR - aMIR
      })
  }, [summaries, groupBy])

  const selectedSummary = summaries.find((s) => s.path === selectedPath)
  const succeeded = records.filter((r) => r.attack_success || r.jailbroken || r.success).length

  const GROUP_OPTIONS: { id: GroupBy; label: string }[] = [
    { id: 'model', label: 'By Model' },
    { id: 'attack', label: 'By Attack' },
    { id: 'defense', label: 'By Defense' },
  ]

  return (
    <>
      {/* Delete confirm modal */}
      <AnimatePresence>
        {confirmDelete && (
          <motion.div
            key="confirm-overlay"
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            className="fixed inset-0 z-50 flex items-center justify-center"
            style={{ background: 'rgba(0,0,0,0.6)', backdropFilter: 'blur(4px)' }}
            onClick={() => !deleting && setConfirmDelete(null)}
          >
            <motion.div
              initial={{ scale: 0.92, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              exit={{ scale: 0.92, opacity: 0 }}
              transition={{ duration: 0.15 }}
              className="rounded-2xl p-6 max-w-sm w-full mx-4 space-y-4"
              style={{ background: 'rgba(6,9,22,0.98)', border: '1px solid rgba(239,68,68,0.3)' }}
              onClick={(e) => e.stopPropagation()}
            >
              <div className="flex items-center gap-3">
                <div className="p-2 rounded-xl" style={{ background: 'rgba(239,68,68,0.12)' }}>
                  <AlertTriangle size={18} className="text-rose-400" />
                </div>
                <div>
                  <div className="text-sm font-semibold text-slate-200">Delete result?</div>
                  <div className="text-xs text-slate-500 mt-0.5">This cannot be undone.</div>
                </div>
              </div>
              <div className="text-xs text-slate-500 font-mono px-3 py-2 rounded-lg truncate"
                style={{ background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.1)' }}>
                {confirmDelete}
              </div>
              <div className="flex gap-2 justify-end pt-1">
                <button
                  onClick={() => setConfirmDelete(null)}
                  disabled={deleting}
                  className="px-4 py-2 rounded-xl text-xs font-medium text-slate-400 transition-colors"
                  style={{ background: 'rgba(99,102,241,0.08)', border: '1px solid rgba(99,102,241,0.15)' }}
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleDelete(confirmDelete)}
                  disabled={deleting}
                  className="px-4 py-2 rounded-xl text-xs font-semibold text-rose-300 flex items-center gap-1.5 transition-opacity"
                  style={{ background: 'rgba(239,68,68,0.15)', border: '1px solid rgba(239,68,68,0.3)', opacity: deleting ? 0.5 : 1 }}
                >
                  <Trash2 size={11} />{deleting ? 'Deleting…' : 'Delete'}
                </button>
              </div>
            </motion.div>
          </motion.div>
        )}
      </AnimatePresence>

      <AnimatePresence>
        {hoveredRecord && (
          <RecordPopover record={hoveredRecord} anchorRef={hoverAnchor} />
        )}
      </AnimatePresence>

      <div className="page-wrapper max-w-7xl mx-auto space-y-6">
        {/* Header */}
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }}
          className="flex items-end justify-between flex-wrap gap-4">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              Results
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              {summaries.length} experiment{summaries.length !== 1 ? 's' : ''} · browse and analyse evaluation outputs
            </p>
          </div>

          {/* Group-by selector */}
          <div className="flex items-center gap-1 p-1 rounded-xl"
            style={{ background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(99,102,241,0.15)' }}>
            <LayoutGrid size={12} className="text-slate-600 ml-2 mr-1" />
            {GROUP_OPTIONS.map((opt) => (
              <button
                key={opt.id}
                onClick={() => setGroupBy(opt.id)}
                className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200"
                style={{
                  background: groupBy === opt.id ? 'rgba(99,102,241,0.2)' : 'transparent',
                  color: groupBy === opt.id ? '#a5b4fc' : '#64748b',
                  border: groupBy === opt.id ? '1px solid rgba(99,102,241,0.3)' : '1px solid transparent',
                }}
              >
                {opt.label}
              </button>
            ))}
          </div>
        </motion.div>

        {/* Card grid — grouped */}
        {summaries.length === 0 ? (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.2 }}
            className="text-center py-20 text-slate-500 text-sm">
            <div className="text-4xl mb-3 opacity-30">📊</div>
            No results found. Run an evaluation first.
          </motion.div>
        ) : (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} className="space-y-8">
            {groups.map((group) => (
              <GroupSection
                key={group.key}
                group={group}
                selectedPath={selectedPath}
                onSelect={handleSelect}
                onDelete={(path) => setConfirmDelete(path)}
                onDownload={handleDownload}
              />
            ))}
          </motion.div>
        )}

        {/* Detail panel */}
        <AnimatePresence>
          {(loadingDetail || (selectedSummary && records.length > 0)) && (
            <motion.div
              ref={detailRef}
              key={selectedPath}
              initial={{ opacity: 0, y: 16 }}
              animate={{ opacity: 1, y: 0 }}
              exit={{ opacity: 0, y: 8 }}
              transition={{ duration: 0.3 }}
              className="space-y-4 pt-4"
              style={{ borderTop: '1px solid rgba(99,102,241,0.12)' }}
            >
              {loadingDetail ? (
                <div className="flex items-center gap-3 py-8 text-slate-500 text-sm">
                  <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                    className="w-4 h-4 border-2 border-slate-700 border-t-indigo-500 rounded-full" />
                  Loading records…
                </div>
              ) : selectedSummary && (
                <>
                  <ModelInfoBar summary={selectedSummary} />

                  <div className="grid grid-cols-2 gap-4">
                    <MIRGauge MIR={selectedSummary.MIR} total={records.length} />
                    <StatsCard succeeded={succeeded} blocked={records.length - succeeded} />
                  </div>

                  {records.length > 0 && <CategoryChart records={records} />}

                  {/* Records table */}
                  <div className="rounded-xl overflow-hidden"
                    style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(99,102,241,0.12)' }}>
                    <div className="px-5 py-3 flex items-center justify-between"
                      style={{ borderBottom: '1px solid rgba(99,102,241,0.1)' }}>
                      <span className="text-sm font-semibold text-slate-300">Records</span>
                      <div className="flex items-center gap-3">
                        <span className="text-xs text-slate-600">{records.length} entries · hover a row for details</span>
                        <button
                          onClick={() => selectedPath && handleDownload(selectedPath)}
                          className="flex items-center gap-1.5 px-2.5 py-1 rounded-lg text-xs font-medium transition-colors"
                          style={{ background: 'rgba(99,102,241,0.1)', color: '#818cf8', border: '1px solid rgba(99,102,241,0.2)' }}
                        >
                          <Download size={11} />Download JSON
                        </button>
                      </div>
                    </div>
                    <div className="overflow-x-auto">
                      <table className="w-full text-xs">
                        <thead>
                          <tr style={{ borderBottom: '1px solid rgba(99,102,241,0.1)' }}>
                            {['#', 'Goal', 'Category', 'Result', ''].map((h) => (
                              <th key={h} className="text-left px-4 py-2.5 text-slate-500 font-medium">{h}</th>
                            ))}
                          </tr>
                        </thead>
                        <tbody>
                          {records.map((r, i) => {
                            const jailbroken = !!(r.attack_success || r.jailbroken || r.success)
                            return (
                              <motion.tr
                                key={i}
                                initial={{ opacity: 0 }}
                                animate={{ opacity: 1 }}
                                transition={{ delay: i * 0.008 }}
                                className="transition-colors cursor-default"
                                style={{ borderBottom: '1px solid rgba(99,102,241,0.06)' }}
                                onMouseEnter={(e) => {
                                  hoverAnchor.current = e.currentTarget
                                  setHoveredRecord(r)
                                  e.currentTarget.style.background = 'rgba(99,102,241,0.06)'
                                }}
                                onMouseLeave={(e) => {
                                  setHoveredRecord(null)
                                  e.currentTarget.style.background = ''
                                }}
                              >
                                <td className="px-4 py-2.5 text-slate-600">{i}</td>
                                <td className="px-4 py-2.5 text-slate-300 max-w-[220px] truncate">
                                  {String(r.goal ?? r.user_goal ?? '')}
                                </td>
                                <td className="px-4 py-2.5">
                                  <span className="px-1.5 py-0.5 rounded text-slate-400"
                                    style={{ background: 'rgba(99,102,241,0.08)' }}>
                                    {String(r.category ?? '—')}
                                  </span>
                                </td>
                                <td className="px-4 py-2.5">
                                  {jailbroken ? (
                                    <span className="flex items-center gap-1 text-rose-400 font-medium">
                                      <XCircle size={10} />Jailbroken
                                    </span>
                                  ) : (
                                    <span className="flex items-center gap-1 text-emerald-500">
                                      <CheckCircle2 size={10} />Blocked
                                    </span>
                                  )}
                                </td>
                                <td className="px-4 py-2.5">
                                  <button
                                    onClick={() => navigate(`/results/${encodeURIComponent(selectedPath!)}/fingerprint?record=${i}`)}
                                    className="flex items-center gap-1 text-indigo-400 hover:text-indigo-300 transition-colors"
                                  >
                                    <ExternalLink size={10} />Trace
                                  </button>
                                </td>
                              </motion.tr>
                            )
                          })}
                        </tbody>
                      </table>
                    </div>
                  </div>
                </>
              )}
            </motion.div>
          )}
        </AnimatePresence>
      </div>
    </>
  )
}

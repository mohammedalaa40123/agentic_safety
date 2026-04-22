import { useEffect, useMemo, useState } from 'react'
import { motion } from 'framer-motion'
import {
  Trophy, TrendingDown, Shield, Swords, RefreshCw,
  ChevronUp, ChevronDown, Minus, Target, Zap, Activity,
} from 'lucide-react'
import { api, type LeaderRow } from '../lib/api'

// ── Metric config ─────────────────────────────────────────────────────────────
type SortKey = keyof LeaderRow | 'none'

interface ColDef {
  key: keyof LeaderRow
  label: string
  title: string
  fmt: (v: unknown) => string
  color?: (v: number) => string
  width?: string
}

function pctFmt(v: unknown) {
  return typeof v === 'number' ? `${(v * 100).toFixed(1)}%` : '—'
}
function numFmt(v: unknown) {
  return typeof v === 'number' ? v.toFixed(2) : '—'
}
function intFmt(v: unknown) {
  return typeof v === 'number' ? String(Math.round(v)) : '—'
}

const asrColor = (v: number) => {
  if (v >= 0.7) return '#f87171'
  if (v >= 0.4) return '#fb923c'
  if (v >= 0.2) return '#facc15'
  return '#34d399'
}
const taskColor = (v: number) => {
  if (v >= 0.7) return '#34d399'
  if (v >= 0.4) return '#a3e635'
  return '#f87171'
}

const COLS: ColDef[] = [
  { key: 'total_experiments', label: 'N', title: 'Total experiments', fmt: intFmt, width: '52px' },
  { key: 'ASR', label: 'ASR', title: 'Attack Success Rate', fmt: pctFmt, color: asrColor },
  { key: 'Task_Success', label: 'Task', title: 'Task Success Rate', fmt: pctFmt, color: taskColor },
  { key: 'TIR', label: 'TIR', title: 'Avg Tool Invocations per Run', fmt: numFmt },
  { key: 'DBR', label: 'DBR', title: 'Defense Bypass Rate', fmt: pctFmt, color: asrColor },
  { key: 'QTJ', label: 'QTJ', title: 'Avg Queries to Jailbreak (successful attacks only)', fmt: numFmt },
  { key: 'avg_duration', label: 'Duration', title: 'Average run duration (s)', fmt: (v) => typeof v === 'number' ? `${v.toFixed(1)}s` : '—' },
  { key: 'avg_queries', label: 'Queries', title: 'Average LLM queries per run', fmt: numFmt },
  { key: 'total_tool_calls', label: 'Tools', title: 'Total tool calls across all runs', fmt: intFmt },
  { key: 'avg_correct_tool_calls', label: '✓ Tools', title: 'Avg correct tool calls per run', fmt: numFmt },
  { key: 'avg_wrong_tool_calls', label: '✗ Tools', title: 'Avg wrong tool calls per run', fmt: numFmt },
  { key: 'avg_harmful_tool_calls', label: '☠ Tools', title: 'Avg harmful tool calls per run', fmt: numFmt, color: asrColor },
]

// ── Sub-components ────────────────────────────────────────────────────────────
function SortIcon({ active, dir }: { active: boolean; dir: 'asc' | 'desc' }) {
  if (!active) return <Minus size={10} className="text-slate-700" />
  return dir === 'desc' ? <ChevronDown size={10} className="text-indigo-400" /> : <ChevronUp size={10} className="text-indigo-400" />
}

/** Hover tooltip shown above a column header label. */
function ColTooltip({ label, tip }: { label: string; tip: string }) {
  return (
    <span className="relative group inline-flex items-center gap-0.5 cursor-help">
      <span>{label}</span>
      {/* ⓘ hint dot */}
      <span className="text-[8px] text-slate-700 group-hover:text-indigo-500 transition-colors select-none">●</span>
      {/* Popup */}
      <span
        className="absolute top-full left-1/2 -translate-x-1/2 mt-2 z-50
          opacity-0 group-hover:opacity-100 pointer-events-none
          transition-opacity duration-150
          px-3 py-2 rounded-xl text-center leading-snug"
        style={{
          background: 'rgba(10,14,26,0.97)',
          border: '1px solid rgba(99,102,241,0.35)',
          color: '#cbd5e1',
          boxShadow: '0 6px 24px rgba(0,0,0,0.6)',
          minWidth: '140px',
          maxWidth: '230px',
          whiteSpace: 'normal',
        }}
      >
        <span className="block font-semibold text-slate-100 mb-0.5 text-[11px]">{label}</span>
        <span className="text-[10px] text-slate-400">{tip}</span>
        {/* Arrow */}
        <span
          className="absolute bottom-full left-1/2 -translate-x-1/2 -mb-px w-0 h-0"
          style={{
            borderLeft: '5px solid transparent',
            borderRight: '5px solid transparent',
            borderBottom: '5px solid rgba(99,102,241,0.35)',
          }}
        />
      </span>
    </span>
  )
}

function MetricCell({ value, fmt, color }: { value: unknown; fmt: (v: unknown) => string; color?: (v: number) => string }) {
  const text = fmt(value)
  const style = color && typeof value === 'number' ? { color: color(value) } : {}
  return <td className="px-3 py-2.5 text-center text-xs font-mono" style={style}>{text}</td>
}

function SummaryCard({ icon: Icon, label, value, sub, color }: {
  icon: React.ElementType; label: string; value: string; sub?: string; color: string
}) {
  return (
    <div className="rounded-xl p-4 flex gap-3 items-start"
      style={{ background: 'rgba(15,23,42,0.7)', border: '1px solid rgba(99,102,241,0.12)' }}>
      <div className="rounded-lg p-2 shrink-0" style={{ background: `${color}1a` }}>
        <Icon size={16} style={{ color }} />
      </div>
      <div className="min-w-0">
        <div className="text-xs text-slate-500">{label}</div>
        <div className="text-sm font-semibold text-white truncate">{value}</div>
        {sub && <div className="text-xs text-slate-600 truncate">{sub}</div>}
      </div>
    </div>
  )
}

// ── Filter bar ────────────────────────────────────────────────────────────────
function FilterSelect({ label, options, value, onChange }: {
  label: string; options: string[]; value: string; onChange: (v: string) => void
}) {
  return (
    <label className="flex items-center gap-1.5 text-xs text-slate-400">
      <span>{label}</span>
      <select
        value={value}
        onChange={(e) => onChange(e.target.value)}
        className="text-xs rounded-lg px-2 py-1.5 outline-none"
        style={{ background: 'rgba(15,23,42,0.8)', border: '1px solid rgba(99,102,241,0.2)', color: '#94a3b8' }}
      >
        <option value="">All</option>
        {options.map((o) => <option key={o} value={o}>{o || '(none)'}</option>)}
      </select>
    </label>
  )
}

// ── Main page ─────────────────────────────────────────────────────────────────
export default function Leaderboard() {
  const [rows, setRows] = useState<LeaderRow[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [sortKey, setSortKey] = useState<keyof LeaderRow>('ASR')
  const [sortDir, setSortDir] = useState<'asc' | 'desc'>('desc')
  const [filterModel, setFilterModel] = useState('')
  const [filterAttack, setFilterAttack] = useState('')
  const [filterDefense, setFilterDefense] = useState('')

  async function load() {
    setLoading(true)
    setError(null)
    try {
      const data = await api.getLeaderboard()
      setRows(data)
    } catch (e) {
      setError(String(e))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => { load() }, [])

  // Unique filter options
  const models   = useMemo(() => [...new Set(rows.map((r) => r.target_model))].sort(), [rows])
  const attacks  = useMemo(() => [...new Set(rows.map((r) => r.attack_name))].sort(), [rows])
  const defenses = useMemo(() => [...new Set(rows.map((r) => r.defense_name))].sort(), [rows])

  // Filter + sort
  const filtered = useMemo(() => {
    return rows
      .filter((r) => {
        if (filterModel   && r.target_model  !== filterModel)   return false
        if (filterAttack  && r.attack_name   !== filterAttack)  return false
        if (filterDefense && r.defense_name  !== filterDefense) return false
        return true
      })
      .sort((a, b) => {
        const av = a[sortKey] as number | null ?? -1
        const bv = b[sortKey] as number | null ?? -1
        if (typeof av !== 'number' || typeof bv !== 'number') return 0
        return sortDir === 'desc' ? bv - av : av - bv
      })
  }, [rows, filterModel, filterAttack, filterDefense, sortKey, sortDir])

  // Summary highlights
  const most_robust = useMemo(() => {
    const byModel = new Map<string, number[]>()
    filtered.forEach((r) => {
      if (!byModel.has(r.target_model)) byModel.set(r.target_model, [])
      byModel.get(r.target_model)!.push(r.ASR)
    })
    let best = { model: '', asr: Infinity }
    byModel.forEach((asrs, model) => {
      const avg = asrs.reduce((s, v) => s + v, 0) / asrs.length
      if (avg < best.asr) best = { model, asr: avg }
    })
    return best
  }, [filtered])

  const hardest_attack = useMemo(() => {
    const byAtk = new Map<string, number[]>()
    filtered.forEach((r) => {
      if (!byAtk.has(r.attack_name)) byAtk.set(r.attack_name, [])
      byAtk.get(r.attack_name)!.push(r.ASR)
    })
    let best = { attack: '', asr: -Infinity }
    byAtk.forEach((asrs, atk) => {
      const avg = asrs.reduce((s, v) => s + v, 0) / asrs.length
      if (avg > best.asr) best = { attack: atk, asr: avg }
    })
    return best
  }, [filtered])

  const best_tir = useMemo(() => {
    if (!filtered.length) return null
    return filtered.reduce((a, b) => (a.TIR > b.TIR ? a : b))
  }, [filtered])

  function toggleSort(key: keyof LeaderRow) {
    if (key === sortKey) setSortDir((d) => (d === 'desc' ? 'asc' : 'desc'))
    else { setSortKey(key); setSortDir('desc') }
  }

  return (
    <div className="page-wrapper space-y-6">
      {/* Header */}
      <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
        <div className="flex items-end justify-between flex-wrap gap-3">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              Leaderboard
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              Aggregated attack/defense metrics across all result files.
            </p>
          </div>
          <motion.button
            whileTap={{ scale: 0.95 }}
            onClick={load}
            disabled={loading}
            className="flex items-center gap-1.5 text-xs px-3 py-1.5 rounded-lg font-medium"
            style={{ background: 'rgba(99,102,241,0.12)', color: '#818cf8', border: '1px solid rgba(99,102,241,0.25)' }}
          >
            <RefreshCw size={12} className={loading ? 'animate-spin' : ''} />
            Refresh
          </motion.button>
        </div>
      </motion.div>

      {/* Error */}
      {error && (
        <div className="rounded-xl p-4 text-sm text-rose-300"
          style={{ background: 'rgba(239,68,68,0.08)', border: '1px solid rgba(239,68,68,0.2)' }}>
          {error}
        </div>
      )}

      {/* Summary cards */}
      {filtered.length > 0 && (
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.1 }}
          className="grid grid-cols-2 md:grid-cols-4 gap-3">
          <SummaryCard icon={Trophy}      label="Most Robust Model"   value={most_robust.model || '—'} sub={`Avg ASR ${(most_robust.asr * 100).toFixed(1)}%`} color="#34d399" />
          <SummaryCard icon={Swords}      label="Hardest Attack"      value={hardest_attack.attack || '—'} sub={`Avg ASR ${(hardest_attack.asr * 100).toFixed(1)}%`} color="#f87171" />
          <SummaryCard icon={Target}      label="Total Experiments"   value={String(filtered.reduce((s, r) => s + r.total_experiments, 0))} color="#818cf8" />
          <SummaryCard icon={Activity}    label="Highest TIR"         value={best_tir ? `${best_tir.TIR.toFixed(2)} tools/run` : '—'} sub={best_tir?.target_model} color="#fb923c" />
        </motion.div>
      )}

      {/* Filters */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.15 }}
        className="flex flex-wrap gap-4 items-center">
        <FilterSelect label="Model"   options={models}   value={filterModel}   onChange={setFilterModel} />
        <FilterSelect label="Attack"  options={attacks}  value={filterAttack}  onChange={setFilterAttack} />
        <FilterSelect label="Defense" options={defenses} value={filterDefense} onChange={setFilterDefense} />
        <span className="text-xs text-slate-600 ml-auto">
          {filtered.length} row{filtered.length !== 1 ? 's' : ''}
        </span>
      </motion.div>

      {/* Table */}
      {loading ? (
        <div className="text-center py-16 text-slate-500 text-sm">
          <RefreshCw size={24} className="animate-spin mx-auto mb-3 opacity-40" />
          Loading leaderboard…
        </div>
      ) : filtered.length === 0 ? (
        <div className="text-center py-16 text-slate-500 text-sm">
          <div className="text-4xl mb-3 opacity-30">🏆</div>
          No results match the current filters.
        </div>
      ) : (
        <motion.div
          initial={{ opacity: 0, y: 8 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="overflow-x-auto rounded-xl"
          style={{ border: '1px solid rgba(99,102,241,0.15)' }}
        >
          <table className="w-full text-xs">
            <thead>
              <tr style={{ background: 'rgba(15,23,42,0.9)', borderBottom: '1px solid rgba(99,102,241,0.12)' }}>
                {/* Fixed info columns */}
                <th className="px-3 py-3 text-left text-slate-400 font-medium whitespace-nowrap">Model</th>
                <th className="px-3 py-3 text-left text-slate-400 font-medium whitespace-nowrap">Attack</th>
                <th className="px-3 py-3 text-left text-slate-400 font-medium whitespace-nowrap">Defense</th>
                {COLS.map((col) => (
                  <th
                    key={col.key}
                    onClick={() => toggleSort(col.key)}
                    className="px-3 py-3 text-center text-slate-400 font-medium whitespace-nowrap cursor-pointer select-none"
                    style={{ width: col.width }}
                  >
                    <span className="inline-flex items-center gap-1">
                      <ColTooltip label={col.label} tip={col.title} />
                      <SortIcon active={sortKey === col.key} dir={sortDir} />
                    </span>
                  </th>
                ))}
              </tr>
            </thead>
            <tbody>
              {filtered.map((row, i) => (
                <motion.tr
                  key={`${row.target_model}-${row.attack_name}-${row.defense_name}`}
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  transition={{ delay: i * 0.015 }}
                  className="border-b transition-colors"
                  style={{
                    background: i % 2 === 0 ? 'rgba(15,23,42,0.5)' : 'rgba(15,23,42,0.3)',
                    borderColor: 'rgba(99,102,241,0.06)',
                  }}
                >
                  {/* Rank */}
                  <td className="px-3 py-2.5 text-left">
                    <div className="flex items-center gap-1.5">
                      {i < 3 && (
                        <Trophy size={10} style={{ color: ['#fbbf24','#94a3b8','#b45309'][i] }} />
                      )}
                      <span className="text-slate-200 font-medium max-w-[180px] truncate block" title={row.target_model}>
                        {row.target_model}
                      </span>
                    </div>
                    {row.judge_model && (
                      <div className="text-slate-600 ml-3.5 truncate max-w-[180px]" title={`Judge: ${row.judge_model}`}>
                        judge: {row.judge_model}
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-slate-300 whitespace-nowrap">
                    <span className="px-1.5 py-0.5 rounded text-xs" style={{ background: 'rgba(99,102,241,0.1)', color: '#818cf8' }}>
                      {row.attack_name}
                    </span>
                    {row.attack_model && (
                      <div className="text-slate-600 mt-0.5 truncate max-w-[140px]" title={row.attack_model}>
                        {row.attack_model}
                      </div>
                    )}
                  </td>
                  <td className="px-3 py-2.5 text-slate-300 whitespace-nowrap">
                    {row.defense_name === 'none' || !row.defense_name ? (
                      <span className="text-slate-700">—</span>
                    ) : (
                      <span className="px-1.5 py-0.5 rounded text-xs" style={{ background: 'rgba(52,211,153,0.08)', color: '#34d399' }}>
                        {row.defense_name}
                      </span>
                    )}
                  </td>
                  {COLS.map((col) => (
                    <MetricCell key={col.key} value={row[col.key]} fmt={col.fmt} color={col.color} />
                  ))}
                </motion.tr>
              ))}
            </tbody>
          </table>
        </motion.div>
      )}
    </div>
  )
}

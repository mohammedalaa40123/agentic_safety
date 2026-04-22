import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion, AnimatePresence } from 'framer-motion'
import {
  Rocket, Shield, Swords, Database, Eye, X, Upload,
  Target, Cpu, Scale, AlertTriangle, CheckCircle2, Ban, ChevronDown, Activity,
} from 'lucide-react'
import { api, type DatasetInfo } from '../lib/api'
import { useProviderStore } from '../stores/providerStore'
import { useConfigStore } from '../stores/configStore'
import { useJobStore } from '../stores/jobStore'

// ── OWASP metadata ─────────────────────────────────────────────
const OWASP_META: Record<string, { label: string; color: string; bg: string; short: string }> = {
  owasp_aai001: { label: 'AAI-01: Auth & Control Hijacking',  color: '#f87171', bg: 'rgba(248,113,113,0.1)', short: 'AAI-01' },
  owasp_aai002: { label: 'AAI-02: Data Exfiltration',         color: '#fb923c', bg: 'rgba(251,146,60,0.1)',  short: 'AAI-02' },
  owasp_aai003: { label: 'AAI-03: Indirect Prompt Injection', color: '#fbbf24', bg: 'rgba(251,191,36,0.1)', short: 'AAI-03' },
  owasp_aai004: { label: 'AAI-04: Resource Exhaustion',       color: '#a3e635', bg: 'rgba(163,230,53,0.1)',  short: 'AAI-04' },
  owasp_aai005: { label: 'AAI-05: Insecure Tool Use',         color: '#34d399', bg: 'rgba(52,211,153,0.1)',  short: 'AAI-05' },
  owasp_aai006: { label: 'AAI-06: Memory Poisoning',          color: '#22d3ee', bg: 'rgba(34,211,238,0.1)',  short: 'AAI-06' },
  owasp_aai007: { label: 'AAI-07: Insecure Code Execution',   color: '#60a5fa', bg: 'rgba(96,165,250,0.1)',  short: 'AAI-07' },
  owasp_aai008: { label: 'AAI-08: Supply Chain Attacks',      color: '#a78bfa', bg: 'rgba(167,139,250,0.1)', short: 'AAI-08' },
  owasp_aai009: { label: 'AAI-09: Privacy Violations',        color: '#f472b6', bg: 'rgba(244,114,182,0.1)', short: 'AAI-09' },
  owasp_aai010: { label: 'AAI-10: Misaligned Objectives',     color: '#e879f9', bg: 'rgba(232,121,249,0.1)', short: 'AAI-10' },
  safe_benign:  { label: 'Safe / Benign',                     color: '#94a3b8', bg: 'rgba(148,163,184,0.08)',short: 'Safe'   },
}
function owaspMeta(cat: string) {
  return OWASP_META[cat] ?? { label: cat, color: '#94a3b8', bg: 'rgba(148,163,184,0.08)', short: cat.slice(0, 8) }
}

interface Sample {
  id?: string; title?: string; user_goal?: string; category?: string
  expected_tools?: string[]; expected_outcome?: string
  is_malicious?: boolean; allow_block?: boolean
  [key: string]: unknown
}

// ── OWASP detail drawer ────────────────────────────────────────
function SampleDrawer({ sample, onClose }: { sample: Sample; onClose: () => void }) {
  const meta = owaspMeta(sample.category ?? '')
  const known = new Set(['id','title','user_goal','category','expected_tools','expected_outcome','is_malicious','allow_block'])
  return (
    <motion.div
      initial={{ x: '100%', opacity: 0 }}
      animate={{ x: 0, opacity: 1 }}
      exit={{ x: '100%', opacity: 0 }}
      transition={{ type: 'spring', damping: 28, stiffness: 280 }}
      className="fixed right-0 top-0 h-full w-[420px] z-40 overflow-y-auto"
      style={{ background: 'rgba(6,9,22,0.98)', borderLeft: '1px solid rgba(99,102,241,0.2)', backdropFilter: 'blur(20px)' }}
    >
      <div className="sticky top-0 z-10 px-5 py-4 flex items-start justify-between"
        style={{ background: 'rgba(6,9,22,0.98)', borderBottom: '1px solid rgba(99,102,241,0.15)' }}>
        <div className="flex-1 min-w-0 pr-3">
          {sample.id && <code className="text-xs text-slate-500 font-mono">{sample.id}</code>}
          <h3 className="text-sm font-semibold text-slate-100 mt-0.5 leading-snug">{sample.title ?? 'Sample Details'}</h3>
        </div>
        <button onClick={onClose} className="shrink-0 p-1.5 rounded-lg text-slate-500 hover:text-slate-200 hover:bg-slate-800 transition-colors">
          <X size={15} />
        </button>
      </div>
      <div className="px-5 py-5 space-y-5">
        {/* OWASP badge */}
        <div>
          <div className="section-label mb-2">OWASP Type</div>
          <div className="inline-flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold"
            style={{ background: meta.bg, color: meta.color, border: `1px solid ${meta.color}30` }}>
            <div className="w-2 h-2 rounded-full" style={{ background: meta.color }} />
            {meta.label}
          </div>
        </div>
        {/* Risk flags */}
        <div>
          <div className="section-label mb-2">Risk Flags</div>
          <div className="flex flex-wrap gap-2">
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
              style={sample.is_malicious
                ? { background: 'rgba(239,68,68,0.12)', color: '#f87171', border: '1px solid rgba(239,68,68,0.2)' }
                : { background: 'rgba(52,211,153,0.1)', color: '#34d399', border: '1px solid rgba(52,211,153,0.2)' }}>
              {sample.is_malicious ? <AlertTriangle size={11} /> : <CheckCircle2 size={11} />}
              {sample.is_malicious ? 'Malicious prompt' : 'Benign prompt'}
            </span>
            <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium"
              style={sample.allow_block
                ? { background: 'rgba(99,102,241,0.12)', color: '#818cf8', border: '1px solid rgba(99,102,241,0.25)' }
                : { background: 'rgba(239,68,68,0.08)', color: '#f87171', border: '1px solid rgba(239,68,68,0.15)' }}>
              {sample.allow_block ? <Shield size={11} /> : <Ban size={11} />}
              {sample.allow_block ? 'Block allowed' : 'Must not block'}
            </span>
          </div>
        </div>
        {/* Prompt */}
        {sample.user_goal && (
          <div>
            <div className="section-label mb-2">User Goal / Prompt</div>
            <div className="text-xs text-slate-300 leading-relaxed p-3 rounded-lg"
              style={{ background: 'rgba(99,102,241,0.06)', border: '1px solid rgba(99,102,241,0.12)' }}>
              {sample.user_goal}
            </div>
          </div>
        )}
        {/* Tools */}
        {sample.expected_tools && sample.expected_tools.length > 0 && (
          <div>
            <div className="section-label mb-2">Expected Tools</div>
            <div className="flex flex-wrap gap-1.5">
              {sample.expected_tools.map((t) => (
                <span key={t} className="text-xs px-2 py-0.5 rounded-md font-mono font-medium"
                  style={{ background: 'rgba(251,191,36,0.1)', color: '#fbbf24', border: '1px solid rgba(251,191,36,0.2)' }}>
                  {t}
                </span>
              ))}
            </div>
          </div>
        )}
        {/* Outcome */}
        {sample.expected_outcome && (
          <div>
            <div className="section-label mb-2">Expected Outcome</div>
            <p className="text-xs text-slate-400 leading-relaxed">{sample.expected_outcome}</p>
          </div>
        )}
        {/* Extra fields */}
        {Object.entries(sample).filter(([k]) => !known.has(k)).length > 0 && (
          <div>
            <div className="section-label mb-2">Additional Fields</div>
            <div className="space-y-1.5">
              {Object.entries(sample).filter(([k]) => !known.has(k)).map(([k, v]) => (
                <div key={k} className="flex gap-2 text-xs">
                  <span className="text-slate-500 shrink-0 w-28 truncate">{k}</span>
                  <span className="text-slate-300 break-all">{JSON.stringify(v)}</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>
    </motion.div>
  )
}

const ATTACKS = ['pair', 'crescendo', 'gcg', 'hybrid', 'prompt_fusion']
const DEFENSES = ['agentshield', 'stepshield', 'progent', 'jbshield', 'gradient_cuff']

// ── Per-attack / per-defense param schemas ─────────────────────────────────
type ParamDef =
  | { kind: 'int';    label: string; default: number; min?: number; max?: number }
  | { kind: 'float';  label: string; default: number; min?: number; max?: number; step?: number }
  | { kind: 'select'; label: string; default: string; options: { value: string; label: string }[] }

const ATTACK_PARAM_SCHEMA: Record<string, Record<string, ParamDef>> = {
  pair: {
    n_iterations:    { kind: 'int',   label: 'Max iterations',     default: 5,   min: 1, max: 50 },
  },
  crescendo: {
    max_turns:          { kind: 'int', label: 'Max turns',          default: 10,  min: 1, max: 30 },
    escalation_stages:  { kind: 'int', label: 'Escalation stages',  default: 5,   min: 1, max: 10 },
    benign_warmup_turns:{ kind: 'int', label: 'Warmup turns',       default: 2,   min: 0, max: 10 },
    patience:           { kind: 'int', label: 'Patience',           default: 3,   min: 1, max: 10 },
    context_window:     { kind: 'int', label: 'Context window',     default: 6,   min: 1, max: 20 },
  },
  gcg: {
    n_iterations:      { kind: 'int', label: 'Eval rounds',        default: 6,   min: 1, max: 20 },
    gcg_steps:         { kind: 'int', label: 'GCG steps',          default: 500, min: 1, max: 2000 },
    gcg_suffix_length: { kind: 'int', label: 'Suffix length (tok)',  default: 100, min: 5, max: 300 },
    gcg_topk:          { kind: 'int', label: 'Top-k candidates',   default: 256, min: 8, max: 512 },
    gcg_batch_size:    { kind: 'int', label: 'Batch size',         default: 512, min: 8, max: 1024 },
  },
  hybrid: {
    n_streams:   { kind: 'int', label: 'Streams',     default: 5, min: 1, max: 16 },
    n_iterations:{ kind: 'int', label: 'Iterations',  default: 5, min: 1, max: 30 },
    use_gcg: {
      kind: 'select', label: 'Use GCG suffix', default: 'true',
      options: [{ value: 'true', label: 'Yes' }, { value: 'false', label: 'No' }],
    },
  },
  prompt_fusion: {
    n_iterations: { kind: 'int', label: 'Iterations', default: 5, min: 1, max: 20 },
  },
}

const DEFENSE_PARAM_SCHEMA: Record<string, Record<string, ParamDef>> = {
  agentshield: {
    threshold: { kind: 'float', label: 'Threshold', default: 0.5, min: 0, max: 1, step: 0.05 },
  },
  stepshield: {
    threshold:    { kind: 'float',  label: 'Threshold',    default: 0.5,  min: 0, max: 1,    step: 0.05 },
    block_on_fail:{ kind: 'select', label: 'Block on fail', default: 'true',
      options: [{ value: 'true', label: 'Yes' }, { value: 'false', label: 'No' }] },
  },
  progent: {
    policy: { kind: 'select', label: 'Policy', default: 'strict',
      options: [
        { value: 'strict',     label: 'Strict' },
        { value: 'moderate',   label: 'Moderate' },
        { value: 'permissive', label: 'Permissive' },
      ] },
  },
  jbshield: {
    threshold: { kind: 'float', label: 'Threshold', default: 0.5, min: 0, max: 1, step: 0.05 },
  },
  gradient_cuff: {
    epsilon: { kind: 'float', label: 'Epsilon', default: 0.1,  min: 0.01, max: 1,  step: 0.01 },
    n_probes: { kind: 'int',  label: 'Probes',  default: 5,    min: 1,    max: 20 },
  },
}

// ── Generic param panel ──────────────────────────────────────────────────────
function ParamPanel({
  name,
  schema,
  values,
  onChange,
  accentColor,
}: {
  name: string
  schema: Record<string, ParamDef>
  values: Record<string, unknown>
  onChange: (param: string, val: unknown) => void
  accentColor: string
}) {
  const [open, setOpen] = useState(true)
  const entries = Object.entries(schema)
  if (entries.length === 0) return null

  const hasOverrides = entries.some(([k, def]) => {
    const cur = values[k]
    return cur !== undefined && cur !== def.default
  })

  return (
    <motion.div
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
      exit={{ opacity: 0, y: -4 }}
      transition={{ duration: 0.15 }}
      className="rounded-lg overflow-hidden"
      style={{ border: `1px solid ${accentColor}25`, background: `${accentColor}08` }}
    >
      {/* Header */}
      <button
        onClick={() => setOpen((o) => !o)}
        className="w-full flex items-center justify-between px-3 py-2 text-xs font-medium"
        style={{ color: accentColor }}
      >
        <span className="flex items-center gap-1.5">
          {name}
          {hasOverrides && (
            <span className="px-1.5 py-0.5 rounded text-[10px] font-semibold"
              style={{ background: `${accentColor}25`, color: accentColor }}>
              modified
            </span>
          )}
        </span>
        <motion.span animate={{ rotate: open ? 0 : -90 }} transition={{ duration: 0.15 }}>
          <ChevronDown size={12} />
        </motion.span>
      </button>

      {/* Params grid */}
      <AnimatePresence initial={false}>
        {open && (
          <motion.div
            initial={{ height: 0, opacity: 0 }}
            animate={{ height: 'auto', opacity: 1 }}
            exit={{ height: 0, opacity: 0 }}
            transition={{ duration: 0.18 }}
            className="overflow-hidden"
          >
            <div className="px-3 pb-3 grid grid-cols-2 gap-x-4 gap-y-2.5 sm:grid-cols-3">
              {entries.map(([key, def]) => {
                const cur = values[key]
                const isDefault = cur === undefined || cur === def.default
                return (
                  <label key={key} className="flex flex-col gap-1">
                    <span className="text-[10px] text-slate-500 truncate" title={def.label}>
                      {def.label}
                      {!isDefault && (
                        <button
                          className="ml-1 text-[9px] opacity-50 hover:opacity-100"
                          onClick={() => onChange(key, def.default)}
                          title="Reset to default"
                        >↺</button>
                      )}
                    </span>
                    {def.kind === 'select' ? (
                      <select
                        value={String(cur ?? def.default)}
                        onChange={(e) => onChange(key, e.target.value)}
                        className="input-glow text-xs py-0.5"
                        style={!isDefault ? { borderColor: `${accentColor}60`, color: accentColor } : {}}
                      >
                        {def.options.map((o) => (
                          <option key={o.value} value={o.value}>{o.label}</option>
                        ))}
                      </select>
                    ) : (
                      <input
                        type="number"
                        min={def.min}
                        max={def.max}
                        step={def.kind === 'float' ? (def.step ?? 0.01) : 1}
                        value={cur !== undefined ? String(cur) : String(def.default)}
                        onChange={(e) => {
                          const v = def.kind === 'float' ? parseFloat(e.target.value) : parseInt(e.target.value, 10)
                          onChange(key, isNaN(v) ? def.default : v)
                        }}
                        className="input-glow text-xs py-0.5 w-full"
                        style={!isDefault ? { borderColor: `${accentColor}60`, color: accentColor } : {}}
                        placeholder={String(def.default)}
                      />
                    )}
                  </label>
                )
              })}
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </motion.div>
  )
}

const ATTACK_COLORS: Record<string, { bg: string; text: string }> = {
  pair:         { bg: 'rgba(248,113,113,0.15)',  text: '#f87171' },
  crescendo:    { bg: 'rgba(251,146,60,0.15)',   text: '#fb923c' },
  gcg:          { bg: 'rgba(251,191,36,0.15)',   text: '#fbbf24' },
  hybrid:       { bg: 'rgba(244,114,182,0.15)',  text: '#f472b6' },
  prompt_fusion:{ bg: 'rgba(232,121,249,0.15)',  text: '#e879f9' },
}

const PROVIDER_LIST = [
  { id: 'genai_rcac', name: 'GenAI Studio (RCAC)' },
  { id: 'genai', name: 'GenAI Studio (Custom)' },
  { id: 'openai', name: 'OpenAI' },
  { id: 'openrouter', name: 'OpenRouter' },
  { id: 'gemini', name: 'Gemini' },
  { id: 'anthropic', name: 'Anthropic' },
  { id: 'ollama', name: 'Ollama (Local)' },
  { id: 'ollama_cloud', name: 'Ollama Cloud (ollama.com)' },
]

function ModelSelect({
  label, providerKey, modelKey, icon: Icon,
}: {
  label: string
  providerKey: 'targetProvider' | 'attackProvider' | 'judgeProvider'
  modelKey: 'targetModel' | 'attackModel' | 'judgeModel'
  icon: React.ElementType
}) {
  const { configs } = useProviderStore()
  const { [providerKey]: provider, [modelKey]: model, set } = useConfigStore()
  const models = configs[provider]?.models ?? []

  return (
    <div className="space-y-2">
      <label className="flex items-center gap-1.5 text-xs text-slate-400">
        <Icon size={12} className="text-slate-500" />
        {label}
      </label>
      <div className="grid grid-cols-2 gap-2">
        <select value={provider} onChange={(e) => set(providerKey, e.target.value as typeof provider)}
          className="input-glow col-span-1">
          <option value="">— provider —</option>
          {PROVIDER_LIST.map((p) => <option key={p.id} value={p.id}>{p.name}</option>)}
        </select>
        <select value={model} onChange={(e) => set(modelKey, e.target.value)} className="input-glow col-span-1">
          <option value="">— model —</option>
          {models.map((m) => <option key={m.id} value={m.id}>{m.id}</option>)}
          {models.length === 0 && <option value={model || ''} disabled={false}>{model || '(validate provider first)'}</option>}
        </select>
      </div>
    </div>
  )
}

export default function Config() {
  const navigate = useNavigate()
  const { getCredentials } = useProviderStore()
  const store = useConfigStore()
  const { upsertJob } = useJobStore()
  const [datasets, setDatasets] = useState<DatasetInfo[]>([])
  const [launching, setLaunching] = useState(false)
  const [launchError, setLaunchError] = useState('')
  const [uploading, setUploading] = useState(false)
  const [previewSamples, setPreviewSamples] = useState<Sample[]>([])
  const [loadingPreview, setLoadingPreview] = useState(false)
  const [selectedSample, setSelectedSample] = useState<Sample | null>(null)
  const [showPreview, setShowPreview] = useState(false)

  useEffect(() => { api.listDatasets().then(setDatasets).catch(console.error) }, [])

  useEffect(() => {
    if (!store.dataset || !showPreview) return
    loadPreview(store.dataset)
  }, [store.dataset, showPreview])

  async function loadPreview(name: string) {
    setLoadingPreview(true)
    try {
      const data = await api.previewDataset(name) as { preview?: Sample[] }
      setPreviewSamples(data.preview ?? [])
    } catch { setPreviewSamples([]) }
    finally { setLoadingPreview(false) }
  }

  async function handleUpload(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]; if (!file) return
    setUploading(true)
    try { await api.uploadDataset(file); const r = await api.listDatasets(); setDatasets(r) }
    catch (err) { alert(`Upload failed: ${err}`) }
    finally { setUploading(false) }
  }

  async function handleLaunch() {
    setLaunching(true); setLaunchError('')
    try {
      const req = store.toLaunchRequest(getCredentials())
      const attacks  = (req.attacks  && req.attacks.length  > 0) ? req.attacks  : [undefined]
      const defenses = (req.defenses && req.defenses.length > 0) ? req.defenses : [undefined]

      // Build one job per (attack, defense) combo when multiple are selected
      type Combo = { atk: typeof attacks[0]; def: string | undefined }
      const combos: Combo[] = []
      for (const atk of attacks) {
        for (const def of defenses) {
          combos.push({ atk, def })
        }
      }

      if (combos.length > 1) {
        for (const { atk, def } of combos) {
          const singleReq = {
            ...req,
            attacks:  atk !== undefined ? [atk] : [],
            defenses: def !== undefined ? [def] : [],
            ...(def && req.defense_params ? { defense_params: { [def]: req.defense_params[def] ?? {} } } : {}),
          }
          const job = await api.launchEval(singleReq)
          upsertJob(job)
        }
      } else {
        const job = await api.launchEval(req)
        upsertJob(job)
      }
      navigate('/jobs')
    } catch (err: unknown) { setLaunchError(String(err)) }
    finally { setLaunching(false) }
  }

  const scopeMode = store.datasetScope.mode

  return (
    <>
      <AnimatePresence>
        {selectedSample && (
          <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} exit={{ opacity: 0 }}
            className="fixed inset-0 z-30 bg-black/50 backdrop-blur-sm" onClick={() => setSelectedSample(null)} />
        )}
      </AnimatePresence>
      <AnimatePresence>
        {selectedSample && <SampleDrawer sample={selectedSample} onClose={() => setSelectedSample(null)} />}
      </AnimatePresence>

      <div className="page-wrapper max-w-3xl mx-auto space-y-8">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
          <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
            Evaluate
          </h1>
          <p className="text-slate-400 text-sm mt-1">Configure and launch an adversarial evaluation run.</p>
        </motion.div>

        {/* Models */}
        <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }} className="space-y-3">
          <div className="section-label">Models</div>
          <div className="rounded-xl p-5 space-y-5"
            style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(99,102,241,0.12)', backdropFilter: 'blur(8px)' }}>
            <ModelSelect label="Target model *"  providerKey="targetProvider" modelKey="targetModel" icon={Target} />
            <ModelSelect label="Attacker model"  providerKey="attackProvider" modelKey="attackModel"  icon={Swords} />
            <ModelSelect label="Judge model"     providerKey="judgeProvider"  modelKey="judgeModel"   icon={Scale} />
            <label className="flex flex-col gap-1.5">
              <span className="flex items-center gap-1.5 text-xs text-slate-400"><Cpu size={12} className="text-slate-500" /> Rate limit (calls/min, 0 = unlimited)</span>
              <input type="number" min={0} value={store.callsPerMinute}
                onChange={(e) => store.set('callsPerMinute', Number(e.target.value))}
                className="input-glow w-28" />
            </label>
          </div>
        </motion.section>

        {/* Dataset */}
        <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }} className="space-y-3">
          <div className="flex items-center justify-between">
            <div className="section-label">Dataset</div>
            <button
              onClick={() => { const next = !showPreview; setShowPreview(next); if (next && store.dataset) loadPreview(store.dataset) }}
              className="flex items-center gap-1.5 text-xs text-slate-500 hover:text-indigo-400 transition-colors"
            >
              <Eye size={12} />
              {showPreview ? 'Hide preview' : 'Preview samples'}
            </button>
          </div>
          <div className="rounded-xl p-5 space-y-4"
            style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(99,102,241,0.12)', backdropFilter: 'blur(8px)' }}>
            {/* File + upload */}
            <div className="flex gap-3 items-end">
              <label className="flex flex-col gap-1.5 flex-1">
                <span className="flex items-center gap-1.5 text-xs text-slate-400"><Database size={12} className="text-slate-500" /> Dataset file</span>
                <select value={store.dataset} onChange={(e) => store.set('dataset', e.target.value)} className="input-glow">
                  {datasets.map((d) => (
                    <option key={d.name} value={d.name}>{d.name}{d.count !== null ? ` (${d.count} entries)` : ''}</option>
                  ))}
                </select>
              </label>
              <label className="cursor-pointer">
                <input type="file" accept=".json" className="hidden" onChange={handleUpload} />
                <span className="btn-ghost text-xs cursor-pointer"><Upload size={12} />{uploading ? 'Uploading…' : 'Upload'}</span>
              </label>
            </div>

            {/* Scope */}
            <div className="space-y-3">
              <span className="text-xs text-slate-400 block">Scope</span>
              <div className="flex gap-2 flex-wrap">
                {(['full', 'single', 'range', 'sample'] as const).map((m) => (
                  <motion.button key={m} whileTap={{ scale: 0.93 }}
                    onClick={() => store.set('datasetScope', { mode: m })}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200"
                    style={scopeMode === m
                      ? { background: 'linear-gradient(135deg,rgba(99,102,241,0.25),rgba(168,85,247,0.15))', color: '#c4b5fd', border: '1px solid rgba(99,102,241,0.4)' }
                      : { background: 'rgba(30,41,59,0.5)', color: '#64748b', border: '1px solid rgba(99,102,241,0.08)' }}>
                    {m}
                  </motion.button>
                ))}
              </div>
              {scopeMode === 'single' && (
                <input type="number" min={0} placeholder="Index"
                  value={store.datasetScope.index ?? ''}
                  onChange={(e) => store.set('datasetScope', { mode: 'single', index: Number(e.target.value) })}
                  className="input-glow w-28" />
              )}
              {scopeMode === 'range' && (
                <div className="flex gap-2 items-center">
                  <input type="number" min={0} placeholder="Start"
                    value={store.datasetScope.start ?? ''}
                    onChange={(e) => store.set('datasetScope', { ...store.datasetScope, start: Number(e.target.value) })}
                    className="input-glow w-24" />
                  <span className="text-slate-500 text-sm">–</span>
                  <input type="number" min={0} placeholder="End"
                    value={store.datasetScope.end ?? ''}
                    onChange={(e) => store.set('datasetScope', { ...store.datasetScope, end: Number(e.target.value) })}
                    className="input-glow w-24" />
                </div>
              )}
              {scopeMode === 'sample' && (
                <div className="flex gap-2">
                  <input type="number" min={1} placeholder="N"
                    value={store.datasetScope.n ?? ''}
                    onChange={(e) => store.set('datasetScope', { ...store.datasetScope, n: Number(e.target.value) })}
                    className="input-glow w-24" />
                  <input type="number" placeholder="Seed (optional)"
                    value={store.datasetScope.seed ?? ''}
                    onChange={(e) => store.set('datasetScope', { ...store.datasetScope, seed: e.target.value ? Number(e.target.value) : undefined })}
                    className="input-glow w-36" />
                </div>
              )}
            </div>

            {/* Inline preview */}
            <AnimatePresence>
              {showPreview && (
                <motion.div key="preview" initial={{ height: 0, opacity: 0 }} animate={{ height: 'auto', opacity: 1 }}
                  exit={{ height: 0, opacity: 0 }} transition={{ duration: 0.25 }} className="overflow-hidden">
                  <div className="mt-2 rounded-xl overflow-hidden" style={{ border: '1px solid rgba(99,102,241,0.15)' }}>
                    <div className="px-4 py-2.5 text-xs text-slate-400 flex items-center justify-between"
                      style={{ background: 'rgba(99,102,241,0.06)', borderBottom: '1px solid rgba(99,102,241,0.1)' }}>
                      <span className="font-medium">Dataset Samples</span>
                      <span className="text-slate-600">Click a row to see details →</span>
                    </div>
                    {loadingPreview ? (
                      <div className="px-4 py-6 text-center text-xs text-slate-500">
                        <motion.div animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                          className="inline-block w-4 h-4 border-2 border-slate-700 border-t-indigo-500 rounded-full mb-2" />
                        <div>Loading samples…</div>
                      </div>
                    ) : previewSamples.length === 0 ? (
                      <div className="px-4 py-6 text-center text-xs text-slate-500">No preview available.</div>
                    ) : (
                      <div>
                        {previewSamples.slice(0, 10).map((s, i) => {
                          const meta = owaspMeta(s.category ?? '')
                          return (
                            <motion.button key={i} whileHover={{ backgroundColor: 'rgba(99,102,241,0.07)' }} whileTap={{ scale: 0.99 }}
                              onClick={() => setSelectedSample(s)}
                              className="w-full flex items-center gap-3 px-4 py-3 text-left transition-colors"
                              style={{ borderBottom: '1px solid rgba(99,102,241,0.07)' }}>
                              <span className="text-xs text-slate-600 font-mono w-5 shrink-0">{i}</span>
                              <span className="shrink-0 text-xs px-1.5 py-0.5 rounded font-semibold"
                                style={{ background: meta.bg, color: meta.color, fontSize: '10px' }}>
                                {meta.short}
                              </span>
                              <span className="text-xs text-slate-300 flex-1 truncate">{s.title ?? s.user_goal ?? 'Untitled'}</span>
                              {s.is_malicious && <AlertTriangle size={11} className="shrink-0 text-rose-500" />}
                              <span className="text-xs text-indigo-500 shrink-0">→</span>
                            </motion.button>
                          )
                        })}
                      </div>
                    )}
                  </div>
                </motion.div>
              )}
            </AnimatePresence>
          </div>
        </motion.section>

        {/* Attacks */}
        <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }} className="space-y-3">
          <div className="flex items-center gap-2 section-label"><Swords size={12} />Attacks</div>
          <div className="rounded-xl p-5 space-y-3"
            style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(99,102,241,0.12)', backdropFilter: 'blur(8px)' }}>
            {/* Toggle chips */}
            <div className="flex flex-wrap gap-2">
              {ATTACKS.map((a) => {
                const on = store.attacks.includes(a)
                const c = ATTACK_COLORS[a] ?? { bg: 'rgba(248,113,113,0.15)', text: '#f87171' }
                const schema = ATTACK_PARAM_SCHEMA[a] ?? {}
                const params = store.attackParams[a] ?? {}
                const hasOverrides = Object.keys(schema).some(
                  (k) => params[k] !== undefined && params[k] !== schema[k].default
                )
                return (
                  <motion.button key={a} whileTap={{ scale: 0.92 }}
                    onClick={() => store.set('attacks', on ? store.attacks.filter((x) => x !== a) : [...store.attacks, a])}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 flex items-center gap-1.5"
                    style={on
                      ? { background: c.bg, color: c.text, border: `1px solid ${c.text}40` }
                      : { background: 'rgba(30,41,59,0.5)', color: '#64748b', border: '1px solid rgba(99,102,241,0.08)' }}>
                    {a}
                    {on && hasOverrides && (
                      <span className="w-1.5 h-1.5 rounded-full" style={{ background: c.text }} />
                    )}
                  </motion.button>
                )
              })}
            </div>
            {/* Param panels for each selected attack */}
            <AnimatePresence>
              {store.attacks.map((a) => {
                const schema = ATTACK_PARAM_SCHEMA[a]
                if (!schema || Object.keys(schema).length === 0) return null
                const c = ATTACK_COLORS[a] ?? { bg: 'rgba(248,113,113,0.15)', text: '#f87171' }
                return (
                  <ParamPanel
                    key={a}
                    name={a}
                    schema={schema}
                    values={store.attackParams[a] ?? {}}
                    onChange={(param, val) => store.setAttackParam(a, param, val)}
                    accentColor={c.text}
                  />
                )
              })}
            </AnimatePresence>
          </div>
        </motion.section>

        {/* Defenses */}
        <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.18 }} className="space-y-3">
          <div className="flex items-center gap-2 section-label"><Shield size={12} />Defenses</div>
          <div className="rounded-xl p-5 space-y-3"
            style={{ background: 'rgba(15,23,42,0.6)', border: '1px solid rgba(99,102,241,0.12)', backdropFilter: 'blur(8px)' }}>
            {/* Toggle chips */}
            <div className="flex flex-wrap gap-2">
              {DEFENSES.map((d) => {
                const on = store.defenses.includes(d)
                const schema = DEFENSE_PARAM_SCHEMA[d] ?? {}
                const params = store.defenseParams[d] ?? {}
                const hasOverrides = Object.keys(schema).some(
                  (k) => params[k] !== undefined && params[k] !== schema[k].default
                )
                return (
                  <motion.button key={d} whileTap={{ scale: 0.92 }}
                    onClick={() => store.set('defenses', on ? store.defenses.filter((x) => x !== d) : [...store.defenses, d])}
                    className="px-3 py-1.5 rounded-lg text-xs font-medium transition-all duration-200 flex items-center gap-1.5"
                    style={on
                      ? { background: 'rgba(52,211,153,0.12)', color: '#34d399', border: '1px solid rgba(52,211,153,0.3)' }
                      : { background: 'rgba(30,41,59,0.5)', color: '#64748b', border: '1px solid rgba(99,102,241,0.08)' }}>
                    {d}
                    {on && hasOverrides && (
                      <span className="w-1.5 h-1.5 rounded-full bg-emerald-400" />
                    )}
                  </motion.button>
                )
              })}
            </div>
            {/* Param panels for each selected defense */}
            <AnimatePresence>
              {store.defenses.map((d) => {
                const schema = DEFENSE_PARAM_SCHEMA[d]
                if (!schema || Object.keys(schema).length === 0) return null
                return (
                  <ParamPanel
                    key={d}
                    name={d}
                    schema={schema}
                    values={store.defenseParams[d] ?? {}}
                    onChange={(param, val) => store.setDefenseParam(d, param, val)}
                    accentColor="#34d399"
                  />
                )
              })}
            </AnimatePresence>
          </div>
        </motion.section>

        {/* W&B Logging */}
        <motion.section initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.21 }} className="space-y-3">
          <div className="section-label flex items-center gap-2"><Activity size={13} className="text-[#f9a825]" /> W&B Logging</div>
          <div className="rounded-xl p-5 space-y-4">
            <label className="flex items-center gap-3 cursor-pointer select-none">
              <span className="relative inline-flex items-center">
                <input type="checkbox" className="sr-only peer" checked={store.wandbEnabled}
                  onChange={(e) => store.set('wandbEnabled', e.target.checked)} />
                <div className="w-9 h-5 bg-slate-700 peer-focus:outline-none rounded-full peer
                  peer-checked:bg-[#f9a825] transition-colors"/>
                <div className="absolute left-0.5 top-0.5 w-4 h-4 bg-white rounded-full transition-transform
                  peer-checked:translate-x-4"/>
              </span>
              <span className="text-sm text-slate-300">Enable Weights &amp; Biases run logging</span>
            </label>
            {store.wandbEnabled && (
              <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }}
                className="grid grid-cols-2 gap-3 pt-1">
                <label className="flex flex-col gap-1.5 col-span-2">
                  <span className="text-xs text-slate-400">W&B API Key <span className="text-rose-400">*</span></span>
                  <input type="password" placeholder="paste wandb API key…" value={store.wandbApiKey}
                    onChange={(e) => store.set('wandbApiKey', e.target.value)}
                    className="input-glow" />
                </label>
                <label className="flex flex-col gap-1.5">
                  <span className="text-xs text-slate-400">Project</span>
                  <input type="text" value={store.wandbProject}
                    onChange={(e) => store.set('wandbProject', e.target.value)}
                    className="input-glow" />
                </label>
                <label className="flex flex-col gap-1.5">
                  <span className="text-xs text-slate-400">Entity (team / user)</span>
                  <input type="text" placeholder="optional" value={store.wandbEntity}
                    onChange={(e) => store.set('wandbEntity', e.target.value)}
                    className="input-glow" />
                </label>
                <label className="flex flex-col gap-1.5 col-span-2">
                  <span className="text-xs text-slate-400">Run name (optional)</span>
                  <input type="text" placeholder="auto-generated if blank" value={store.wandbRunName}
                    onChange={(e) => store.set('wandbRunName', e.target.value)}
                    className="input-glow" />
                </label>
              </motion.div>
            )}
          </div>
        </motion.section>

        {/* Error */}
        <AnimatePresence>
          {launchError && (
            <motion.div initial={{ opacity: 0, height: 0 }} animate={{ opacity: 1, height: 'auto' }} exit={{ opacity: 0, height: 0 }}
              className="flex items-center gap-2 text-sm text-rose-400 bg-rose-900/20 rounded-xl px-4 py-3 border border-rose-800/30">
              <AlertTriangle size={14} />{launchError}
            </motion.div>
          )}
        </AnimatePresence>

        {/* Launch */}
        <motion.button initial={{ opacity: 0, y: 6 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.22 }}
          whileTap={{ scale: 0.98 }} onClick={handleLaunch}
          disabled={!store.targetModel || !store.targetProvider || launching}
          className="btn-primary w-full py-3 justify-center text-base">
          {launching ? (
            <motion.span animate={{ rotate: 360 }} transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
              className="block w-4 h-4 border-2 border-white/30 border-t-white rounded-full" />
          ) : <Rocket size={16} />}
          {launching ? 'Launching…' : 'Launch Evaluation'}
        </motion.button>
      </div>
    </>
  )
}

import { motion } from 'framer-motion'
import {
  ShieldAlert, Cpu, Globe, Swords, Shield, FlaskConical, Box,
  ArrowRight, Zap, Lock, Eye, GitFork, Database, BarChart3,
} from 'lucide-react'

// ── helpers ───────────────────────────────────────────────────────────────────
function Pill({ label, color }: { label: string; color: string }) {
  return (
    <span className="text-xs px-2.5 py-1 rounded-full font-medium" style={{ background: color + '22', color }}>
      {label}
    </span>
  )
}

function GlassCard({
  children, delay = 0, className = '',
}: { children: React.ReactNode; delay?: number; className?: string }) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ delay, duration: 0.4, ease: 'easeOut' }}
      className={`rounded-2xl p-6 ${className}`}
      style={{
        background: 'rgba(10,14,30,0.7)',
        border: '1px solid rgba(99,102,241,0.14)',
        backdropFilter: 'blur(10px)',
      }}
    >
      {children}
    </motion.div>
  )
}

// ── data ──────────────────────────────────────────────────────────────────────
const PROVIDERS = [
  { name: 'GenAI RCAC',  icon: '🏫', note: 'Purdue HPC', color: '#fbbf24' },
  { name: 'OpenAI',      icon: '🤖', note: 'GPT-4o / 4.1', color: '#34d399' },
  { name: 'OpenRouter',  icon: '🔀', note: '200+ models', color: '#60a5fa' },
  { name: 'Gemini',      icon: '♊', note: 'Google AI',  color: '#a78bfa' },
  { name: 'Anthropic',   icon: '🧠', note: 'Claude 3.x', color: '#f472b6' },
  { name: 'Ollama',      icon: '🦙', note: 'Local LLMs', color: '#fb923c' },
]

const ATTACKS = [
  { name: 'PAIR', desc: 'Iterative adversarial jailbreak via attacker LLM', color: '#f87171' },
  { name: 'GCG', desc: 'Greedy coordinate gradient suffix injection', color: '#fb923c' },
  { name: 'Crescendo', desc: 'Multi-turn escalating prompt attack', color: '#fbbf24' },
  { name: 'Prompt Fusion', desc: 'Semantic blend of benign + malicious goals', color: '#e879f9' },
  { name: 'Hybrid Loop', desc: 'Adaptive switching between attack strategies', color: '#60a5fa' },
]

const DEFENSES = [
  { name: 'AgentShield', desc: 'Input/output scanning with policy rules', color: '#34d399' },
  { name: 'StepShield', desc: 'Per-step action validation in the agent loop', color: '#22d3ee' },
  { name: 'JBShield', desc: 'Jailbreak pattern classifier guard', color: '#a78bfa' },
  { name: 'Gradient Cuff', desc: 'Adversarial suffix detection via gradient norms', color: '#86efac' },
  { name: 'ProGent', desc: 'Programmatic agent constraint enforcement', color: '#fde68a' },
]

const OWASP_TOP10 = [
  { id: 'AAI-001', name: 'Prompt Injection', color: '#f87171' },
  { id: 'AAI-002', name: 'Excessive Agency', color: '#fb923c' },
  { id: 'AAI-003', name: 'Insecure Output Handling', color: '#fbbf24' },
  { id: 'AAI-004', name: 'Data & Model Poisoning', color: '#a3e635' },
  { id: 'AAI-005', name: 'Improper Error Handling', color: '#34d399' },
  { id: 'AAI-006', name: 'Overreliance', color: '#22d3ee' },
  { id: 'AAI-007', name: 'Insecure Plugin Design', color: '#60a5fa' },
  { id: 'AAI-008', name: 'Insufficient Access Control', color: '#a78bfa' },
  { id: 'AAI-009', name: 'Unsafe AI Model Deployment', color: '#f472b6' },
  { id: 'AAI-010', name: 'Lack of Explainability', color: '#e879f9' },
]

// ── Architecture diagram (SVG-like pure CSS/flex layout) ──────────────────────
function ArchDiagram() {
  const box = (label: string, sub: string, color: string, Icon: React.ElementType) => (
    <div className="flex flex-col items-center gap-1.5 min-w-[90px]">
      <div className="w-12 h-12 rounded-xl flex items-center justify-center"
        style={{ background: color + '18', border: `1px solid ${color}40` }}>
        <Icon size={20} style={{ color }} />
      </div>
      <div className="text-xs font-semibold text-slate-300 text-center leading-tight">{label}</div>
      <div className="text-[10px] text-slate-600 text-center">{sub}</div>
    </div>
  )

  const arrow = (label?: string) => (
    <div className="flex flex-col items-center justify-center gap-1 px-1">
      <div className="text-[10px] text-slate-600">{label}</div>
      <ArrowRight size={14} className="text-indigo-600" />
    </div>
  )

  return (
    <div className="overflow-x-auto">
      <div className="flex items-center justify-center gap-2 min-w-[540px] py-4">
        {box('Dataset', 'OWASP AAI', '#fbbf24', Database)}
        {arrow('goals')}
        {box('Attacker LLM', 'crafts prompt', '#f87171', Swords)}
        {arrow('jailbreak')}
        {box('Defense Layer', 'guards input', '#34d399', Shield)}
        {arrow('filtered')}
        {box('Target Agent', 'executes tools', '#60a5fa', Cpu)}
        {arrow('response')}
        {box('Judge LLM', 'scores ASR', '#a78bfa', Eye)}
        {arrow('metric')}
        {box('Results', 'ASR / Report', '#e879f9', BarChart3)}
      </div>
      {/* Sandbox row */}
      <div className="flex justify-center mt-1">
        <div className="flex items-center gap-2 px-5 py-2 rounded-full text-xs"
          style={{ background: 'rgba(99,102,241,0.07)', border: '1px solid rgba(99,102,241,0.15)', color: '#818cf8' }}>
          <Box size={12} />
          All agent tool calls execute inside an isolated Docker sandbox
        </div>
      </div>
    </div>
  )
}

// ── main page ─────────────────────────────────────────────────────────────────
export default function Home() {
  return (
    <div className="page-wrapper max-w-5xl mx-auto space-y-12 pb-16">

      {/* Hero */}
      <motion.div initial={{ opacity: 0, y: -16 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}
        className="text-center pt-4">
        <div className="inline-flex items-center gap-2 px-4 py-1.5 rounded-full text-xs mb-6"
          style={{ background: 'rgba(99,102,241,0.1)', border: '1px solid rgba(99,102,241,0.25)', color: '#a5b4fc' }}>
          <Zap size={11} />ECE 570 · Purdue University · 2026
        </div>
        <h1 className="text-5xl font-extrabold bg-gradient-to-r from-indigo-400 via-purple-400 to-pink-400 bg-clip-text text-transparent leading-tight mb-4">
          Agentic Safety<br />Evaluation Platform
        </h1>
        <p className="text-slate-400 max-w-2xl mx-auto text-base leading-relaxed">
          A full-stack red-teaming framework for testing LLM-based agents against the{' '}
          <span className="text-indigo-400 font-medium">OWASP Agentic AI Top 10</span> vulnerabilities —
          with pluggable attacks, defenses, and an isolated sandbox.
        </p>
      </motion.div>

      {/* Architecture */}
      <GlassCard delay={0.1}>
        <div className="flex items-center gap-2 mb-5">
          <FlaskConical size={16} className="text-indigo-400" />
          <span className="text-sm font-semibold text-slate-200">System Architecture</span>
        </div>
        <ArchDiagram />
        <div className="mt-5 grid grid-cols-2 sm:grid-cols-4 gap-3">
          {[
            { icon: Database, label: 'Datasets', val: '500+ scenarios', color: '#fbbf24' },
            { icon: Swords,   label: 'Attack methods', val: '5 strategies', color: '#f87171' },
            { icon: Shield,   label: 'Defenses', val: '5 guards', color: '#34d399' },
            { icon: Globe,    label: 'Providers', val: '6 backends', color: '#60a5fa' },
          ].map(({ icon: Icon, label, val, color }, i) => (
            <motion.div key={label} initial={{ opacity: 0, scale: 0.9 }} animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.25 + i * 0.05 }}
              className="rounded-xl p-3 text-center"
              style={{ background: color + '0D', border: `1px solid ${color}25` }}>
              <Icon size={18} className="mx-auto mb-1.5" style={{ color }} />
              <div className="text-lg font-bold" style={{ color }}>{val}</div>
              <div className="text-[11px] text-slate-500">{label}</div>
            </motion.div>
          ))}
        </div>
      </GlassCard>

      {/* Sandbox */}
      <GlassCard delay={0.18}>
        <div className="flex items-center gap-2 mb-4">
          <Box size={16} className="text-amber-400" />
          <span className="text-sm font-semibold text-slate-200">Docker Sandbox</span>
        </div>
        <div className="grid sm:grid-cols-2 gap-6">
          <div className="space-y-3 text-sm text-slate-400 leading-relaxed">
            <p>
              Every agent run executes inside a <span className="text-amber-300 font-medium">hermetic Docker container</span>.
              Tool calls (bash, file I/O, HTTP requests) are intercepted, logged, and rate-limited.
            </p>
            <p>
              The sandbox enforces a deny-by-default policy: only explicitly whitelisted actions reach
              the host, preventing privilege escalation, data exfiltration, and persistent side-effects.
            </p>
          </div>
          <div className="space-y-2">
            {[
              { label: 'Process isolation', icon: Lock, ok: true },
              { label: 'Network egress blocked by default', icon: Globe, ok: true },
              { label: 'Filesystem read-only mount', icon: Database, ok: true },
              { label: 'Tool call audit log', icon: Eye, ok: true },
              { label: 'Time & memory limits enforced', icon: Zap, ok: true },
            ].map(({ label, icon: Icon, ok }) => (
              <div key={label} className="flex items-center gap-2 text-xs text-slate-300">
                <div className="w-5 h-5 rounded-md flex items-center justify-center"
                  style={{ background: ok ? 'rgba(52,211,153,0.15)' : 'rgba(239,68,68,0.15)' }}>
                  <Icon size={11} style={{ color: ok ? '#34d399' : '#f87171' }} />
                </div>
                {label}
              </div>
            ))}
          </div>
        </div>
      </GlassCard>

      {/* Providers */}
      <GlassCard delay={0.22}>
        <div className="flex items-center gap-2 mb-5">
          <Globe size={16} className="text-sky-400" />
          <span className="text-sm font-semibold text-slate-200">Supported Providers</span>
        </div>
        <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
          {PROVIDERS.map(({ name, icon, note, color }, i) => (
            <motion.div key={name} initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.28 + i * 0.04 }}
              className="flex items-center gap-3 rounded-xl px-4 py-3"
              style={{ background: color + '0D', border: `1px solid ${color}25` }}>
              <span className="text-xl">{icon}</span>
              <div>
                <div className="text-sm font-semibold" style={{ color }}>{name}</div>
                <div className="text-[11px] text-slate-500">{note}</div>
              </div>
            </motion.div>
          ))}
        </div>
      </GlassCard>

      {/* Attacks + Defenses side-by-side */}
      <div className="grid sm:grid-cols-2 gap-6">
        <GlassCard delay={0.26} className="">
          <div className="flex items-center gap-2 mb-4">
            <Swords size={15} className="text-rose-400" />
            <span className="text-sm font-semibold text-slate-200">Attack Strategies</span>
          </div>
          <div className="space-y-3">
            {ATTACKS.map(({ name, desc, color }, i) => (
              <motion.div key={name} initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.05 }}
                className="flex gap-3 items-start">
                <div className="w-1 self-stretch rounded-full shrink-0 mt-0.5" style={{ background: color }} />
                <div>
                  <div className="text-xs font-semibold" style={{ color }}>{name}</div>
                  <div className="text-[11px] text-slate-500 leading-snug mt-0.5">{desc}</div>
                </div>
              </motion.div>
            ))}
          </div>
        </GlassCard>

        <GlassCard delay={0.28} className="">
          <div className="flex items-center gap-2 mb-4">
            <Shield size={15} className="text-emerald-400" />
            <span className="text-sm font-semibold text-slate-200">Defense Mechanisms</span>
          </div>
          <div className="space-y-3">
            {DEFENSES.map(({ name, desc, color }, i) => (
              <motion.div key={name} initial={{ opacity: 0, x: 8 }} animate={{ opacity: 1, x: 0 }}
                transition={{ delay: 0.3 + i * 0.05 }}
                className="flex gap-3 items-start">
                <div className="w-1 self-stretch rounded-full shrink-0 mt-0.5" style={{ background: color }} />
                <div>
                  <div className="text-xs font-semibold" style={{ color }}>{name}</div>
                  <div className="text-[11px] text-slate-500 leading-snug mt-0.5">{desc}</div>
                </div>
              </motion.div>
            ))}
          </div>
        </GlassCard>
      </div>

      {/* OWASP Top 10 */}
      <GlassCard delay={0.3}>
        <div className="flex items-center gap-2 mb-5">
          <ShieldAlert size={15} className="text-purple-400" />
          <span className="text-sm font-semibold text-slate-200">OWASP Agentic AI Top 10</span>
          <span className="ml-auto text-[11px] text-slate-600">OWASP-AAI 2025</span>
        </div>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2">
          {OWASP_TOP10.map(({ id, name, color }, i) => (
            <motion.div key={id} initial={{ opacity: 0, scale: 0.97 }} animate={{ opacity: 1, scale: 1 }}
              transition={{ delay: 0.34 + i * 0.03 }}
              className="flex items-center gap-3 rounded-xl px-3 py-2.5"
              style={{ background: color + '0A', border: `1px solid ${color}20` }}>
              <span className="text-[10px] font-bold font-mono shrink-0 px-1.5 py-0.5 rounded"
                style={{ background: color + '20', color }}>
                {id}
              </span>
              <span className="text-xs text-slate-300">{name}</span>
            </motion.div>
          ))}
        </div>
      </GlassCard>

      {/* API Docs */}
      <GlassCard delay={0.35}>
        <div className="flex items-center gap-2 mb-4">
          <GitFork size={15} className="text-indigo-400" />
          <span className="text-sm font-semibold text-slate-200">API Reference</span>
        </div>
        <div className="grid sm:grid-cols-2 gap-4 text-xs">
          {[
            { method: 'GET',    path: '/api/providers',                  desc: 'List all supported LLM providers' },
            { method: 'POST',   path: '/api/providers/:id/validate',     desc: 'Validate an API key + list models' },
            { method: 'GET',    path: '/api/datasets',                   desc: 'List available scenario datasets' },
            { method: 'GET',    path: '/api/datasets/:name?limit=N',     desc: 'Preview first N entries of a dataset' },
            { method: 'POST',   path: '/api/datasets/upload',            desc: 'Upload a custom JSON scenario file' },
            { method: 'POST',   path: '/api/eval/launch',                desc: 'Launch an evaluation job' },
            { method: 'GET',    path: '/api/eval/jobs',                  desc: 'List all past / running jobs' },
            { method: 'GET',    path: '/api/eval/:id',                   desc: 'Get job status + streaming log tail' },
            { method: 'DELETE', path: '/api/eval/:id',                   desc: 'Cancel a running job' },
            { method: 'GET',    path: '/api/results',                    desc: 'List saved result files' },
            { method: 'GET',    path: '/api/results/:path',              desc: 'Fetch a result file (JSON)' },
          ].map(({ method, path, desc }) => {
            const mc: Record<string, string> = {
              GET: '#34d399', POST: '#60a5fa', DELETE: '#f87171', PATCH: '#fbbf24',
            }
            return (
              <div key={path} className="flex gap-2 items-start">
                <span className="shrink-0 w-14 text-center text-[10px] font-bold font-mono rounded px-1 py-0.5"
                  style={{ background: (mc[method] ?? '#94a3b8') + '20', color: mc[method] ?? '#94a3b8' }}>
                  {method}
                </span>
                <div>
                  <code className="text-indigo-300 font-mono text-[11px]">{path}</code>
                  <div className="text-slate-500 mt-0.5 leading-snug">{desc}</div>
                </div>
              </div>
            )
          })}
        </div>
        <div className="mt-4 pt-4 border-t flex gap-3" style={{ borderColor: 'rgba(99,102,241,0.1)' }}>
          <Pill label="FastAPI + Uvicorn" color="#34d399" />
          <Pill label="WebSocket log stream" color="#60a5fa" />
          <Pill label="OpenAPI / Swagger at /docs" color="#a78bfa" />
        </div>
      </GlassCard>

    </div>
  )
}

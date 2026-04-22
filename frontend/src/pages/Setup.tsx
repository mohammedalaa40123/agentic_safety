import { useEffect, useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle2, XCircle, ChevronDown, ChevronUp, Download, Zap, Eye, EyeOff } from 'lucide-react'
import { api, type ProviderInfo, type ModelInfo } from '../lib/api'
import { useProviderStore } from '../stores/providerStore'

const PROVIDER_ICONS: Record<string, string> = {
  genai_rcac: '🏫',
  genai: '🖥',
  openai: '◆',
  openrouter: '🔀',
  gemini: '♊',
  anthropic: '🔵',
  ollama: '🦙',
  genaistudio: '🖥',
}

export default function Setup() {
  const [providers, setProviders] = useState<ProviderInfo[]>([])
  const { configs, setConfig } = useProviderStore()
  const [busy, setBusy] = useState<Record<string, boolean>>({})
  const [error, setError] = useState<Record<string, string>>({})
  const [expanded, setExpanded] = useState<Record<string, boolean>>({})
  const [showKey, setShowKey] = useState<Record<string, boolean>>({})

  useEffect(() => {
    api.getProviders().then((list) => {
      setProviders(list)
      // Auto-expand the first provider
      if (list.length > 0) setExpanded({ [list[0].id]: true })
    }).catch(console.error)
  }, [])

  async function handleValidate(p: ProviderInfo) {
    const cfg = configs[p.id] ?? {}
    setBusy((b) => ({ ...b, [p.id]: true }))
    setError((e) => ({ ...e, [p.id]: '' }))
    try {
      const res = await api.validateProvider(p.id, cfg.api_key ?? '', cfg.base_url ?? '')
      if (res.valid) {
        const models = await api.listModels(p.id, cfg.api_key ?? '', cfg.base_url ?? '')
        setConfig(p.id, { validated: true, models })
      } else {
        setConfig(p.id, { validated: false, models: [] })
        setError((e) => ({ ...e, [p.id]: 'Credentials rejected by server' }))
      }
    } catch (err: unknown) {
      setConfig(p.id, { validated: false })
      setError((e) => ({ ...e, [p.id]: String(err) }))
    } finally {
      setBusy((b) => ({ ...b, [p.id]: false }))
    }
  }

  async function handlePullOllama(p: ProviderInfo) {
    const modelName = prompt('Enter model name to pull (e.g. llama3.1):')
    if (!modelName) return
    const cfg = configs[p.id] ?? {}
    try {
      await api.pullOllamaModel(modelName, cfg.base_url)
      alert(`Pull request accepted for ${modelName}`)
    } catch (err) {
      alert(`Pull failed: ${err}`)
    }
  }

  const toggle = (id: string) => setExpanded((e) => ({ ...e, [id]: !e[id] }))
  const toggleKey = (id: string) => setShowKey((s) => ({ ...s, [id]: !s[id] }))

  const connectedCount = providers.filter((p) => configs[p.id]?.validated).length

  return (
    <div className="page-wrapper max-w-3xl mx-auto">
      {/* Header */}
      <motion.div
        initial={{ opacity: 0, y: -10 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.3 }}
        className="mb-8"
      >
        <div className="flex items-end justify-between">
          <div>
            <h1 className="text-3xl font-bold bg-gradient-to-r from-indigo-400 to-purple-400 bg-clip-text text-transparent">
              Provider Setup
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              Enter your API keys. Keys are never persisted to disk.
            </p>
          </div>
          {connectedCount > 0 && (
            <motion.div
              initial={{ scale: 0.8, opacity: 0 }}
              animate={{ scale: 1, opacity: 1 }}
              className="text-xs px-3 py-1.5 rounded-full font-medium"
              style={{ background: 'rgba(52,211,153,0.12)', color: '#34d399', border: '1px solid rgba(52,211,153,0.2)' }}
            >
              {connectedCount} connected
            </motion.div>
          )}
        </div>
      </motion.div>

      <div className="space-y-3">
        {providers.map((p, i) => {
          const cfg = configs[p.id] ?? {}
          const isValid = cfg.validated
          const isLoading = busy[p.id]
          const isExpanded = expanded[p.id]

          return (
            <motion.div
              key={p.id}
              initial={{ opacity: 0, y: 12 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: i * 0.05, duration: 0.25 }}
              className="rounded-xl overflow-hidden"
              style={{
                background: isValid
                  ? 'linear-gradient(135deg,rgba(52,211,153,0.05),rgba(16,185,129,0.02))'
                  : 'rgba(15,23,42,0.6)',
                border: `1px solid ${isValid ? 'rgba(52,211,153,0.2)' : 'rgba(99,102,241,0.12)'}`,
                backdropFilter: 'blur(8px)',
              }}
            >
              {/* Card header — always visible */}
              <button
                className="w-full flex items-center justify-between px-5 py-4 text-left transition-colors hover:bg-white/[0.02]"
                onClick={() => toggle(p.id)}
              >
                <div className="flex items-center gap-3">
                  <span className="text-xl">{PROVIDER_ICONS[p.id] ?? '🔌'}</span>
                  <div>
                    <div className="flex items-center gap-2">
                      <span className="font-semibold text-slate-100 text-sm">{p.name}</span>
                      {isValid && (
                        <motion.span
                          initial={{ scale: 0 }}
                          animate={{ scale: 1 }}
                          className="flex items-center gap-1 text-xs px-2 py-0.5 rounded-full font-medium"
                          style={{ background: 'rgba(52,211,153,0.15)', color: '#34d399' }}
                        >
                          <CheckCircle2 size={10} />
                          Connected
                        </motion.span>
                      )}
                    </div>
                    <p className="text-xs text-slate-500 mt-0.5">{p.description}</p>
                  </div>
                </div>
                <div className="flex items-center gap-2 shrink-0">
                  {isValid && cfg.models && (
                    <span className="text-xs text-slate-500">{cfg.models.length} models</span>
                  )}
                  {isExpanded ? (
                    <ChevronUp size={15} className="text-slate-500" />
                  ) : (
                    <ChevronDown size={15} className="text-slate-500" />
                  )}
                </div>
              </button>

              {/* Expanded body */}
              <AnimatePresence initial={false}>
                {isExpanded && (
                  <motion.div
                    key="body"
                    initial={{ height: 0, opacity: 0 }}
                    animate={{ height: 'auto', opacity: 1 }}
                    exit={{ height: 0, opacity: 0 }}
                    transition={{ duration: 0.22, ease: 'easeInOut' }}
                    className="overflow-hidden"
                  >
                    <div
                      className="px-5 pb-5 space-y-4"
                      style={{ borderTop: '1px solid rgba(99,102,241,0.1)' }}
                    >
                      <div className="pt-4 grid grid-cols-1 gap-3 sm:grid-cols-2">
                        {p.needs_key && (
                          <label className="flex flex-col gap-1.5">
                            <span className="text-xs text-slate-400">
                              API Key
                              {p.key_env && <span className="text-slate-600 ml-1">({p.key_env})</span>}
                            </span>
                            <div className="relative">
                              <input
                                type={showKey[p.id] ? 'text' : 'password'}
                                placeholder="sk-…"
                                value={cfg.api_key ?? ''}
                                onChange={(e) => setConfig(p.id, { api_key: e.target.value })}
                                className="input-glow w-full pr-9"
                              />
                              <button
                                type="button"
                                onClick={() => toggleKey(p.id)}
                                className="absolute right-2.5 top-1/2 -translate-y-1/2 text-slate-500 hover:text-slate-300"
                              >
                                {showKey[p.id] ? <EyeOff size={13} /> : <Eye size={13} />}
                              </button>
                            </div>
                          </label>
                        )}
                        {(p.needs_base_url || p.default_base_url) && (
                          <label className="flex flex-col gap-1.5">
                            <span className="text-xs text-slate-400">Base URL</span>
                            <input
                              type="text"
                              placeholder={p.default_base_url || 'https://…'}
                              value={cfg.base_url ?? p.default_base_url}
                              onChange={(e) => setConfig(p.id, { base_url: e.target.value })}
                              className="input-glow w-full"
                            />
                          </label>
                        )}
                      </div>

                      {/* Action buttons */}
                      <div className="flex items-center gap-2">
                        <button
                          onClick={() => handleValidate(p)}
                          disabled={isLoading}
                          className="btn-primary"
                        >
                          {isLoading ? (
                            <motion.span
                              animate={{ rotate: 360 }}
                              transition={{ duration: 1, repeat: Infinity, ease: 'linear' }}
                              className="block w-3.5 h-3.5 border-2 border-white/30 border-t-white rounded-full"
                            />
                          ) : (
                            <Zap size={13} />
                          )}
                          {isLoading ? 'Checking…' : 'Validate & list models'}
                        </button>
                        {p.id === 'ollama' && (
                          <button onClick={() => handlePullOllama(p)} className="btn-ghost">
                            <Download size={13} />
                            Pull model
                          </button>
                        )}
                      </div>

                      {/* Error */}
                      <AnimatePresence>
                        {error[p.id] && (
                          <motion.div
                            initial={{ opacity: 0, height: 0 }}
                            animate={{ opacity: 1, height: 'auto' }}
                            exit={{ opacity: 0, height: 0 }}
                            className="flex items-center gap-2 text-xs text-rose-400 bg-rose-900/20 rounded-lg px-3 py-2 border border-rose-800/30"
                          >
                            <XCircle size={12} />
                            {error[p.id]}
                          </motion.div>
                        )}
                      </AnimatePresence>

                      {/* Model list */}
                      {isValid && cfg.models && cfg.models.length > 0 && (
                        <motion.div
                          initial={{ opacity: 0 }}
                          animate={{ opacity: 1 }}
                          className="space-y-2"
                        >
                          <span className="text-xs text-slate-500">
                            {cfg.models.length} model(s) available
                          </span>
                          <div className="flex flex-wrap gap-1.5">
                            {cfg.models.slice(0, 16).map((m: ModelInfo) => (
                              <span
                                key={m.id}
                                className="text-xs px-2 py-0.5 rounded-full text-slate-300 transition-colors hover:text-slate-100"
                                style={{
                                  background: 'rgba(99,102,241,0.1)',
                                  border: '1px solid rgba(99,102,241,0.2)',
                                }}
                              >
                                {m.id}
                              </span>
                            ))}
                            {cfg.models.length > 16 && (
                              <span className="text-xs text-slate-500 px-2 py-0.5">
                                +{cfg.models.length - 16} more
                              </span>
                            )}
                          </div>
                        </motion.div>
                      )}
                    </div>
                  </motion.div>
                )}
              </AnimatePresence>
            </motion.div>
          )
        })}
      </div>
    </div>
  )
}


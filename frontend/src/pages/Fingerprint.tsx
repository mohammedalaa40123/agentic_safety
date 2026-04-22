import { useEffect, useState } from 'react'
import { useParams, useSearchParams } from 'react-router-dom'
import { api } from '../lib/api'
import { parseRecord, type TraceGraph } from '../lib/trace-parser'
import SwimlaneDag from '../components/fingerprint/SwimlaneDag'

export default function Fingerprint() {
  const { resultPath } = useParams<{ resultPath: string }>()
  const [searchParams] = useSearchParams()
  const recordIdx = Number(searchParams.get('record') ?? '0')

  const [graph, setGraph] = useState<TraceGraph | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!resultPath) return
    api.getResult(decodeURIComponent(resultPath))
      .then((raw) => {
        const data = raw as Record<string, unknown>[] | Record<string, unknown>
        const records = Array.isArray(data)
          ? data
          : (data.records as Record<string, unknown>[]) ?? [data]
        const rec = records[recordIdx] ?? records[0]
        if (!rec) throw new Error('Record not found')
        setGraph(parseRecord(rec))
      })
      .catch((e) => setError(String(e)))
      .finally(() => setLoading(false))
  }, [resultPath, recordIdx])

  if (loading) return <div className="p-8 text-slate-400">Loading…</div>
  if (error) return <div className="p-8 text-rose-400">{error}</div>
  if (!graph) return null

  return (
    <div className="flex flex-col h-screen">
      <div className="px-6 py-4 border-b border-slate-800 flex items-center gap-4">
        <div>
          <h1 className="text-lg font-bold">Attack Fingerprint</h1>
          <p className="text-xs text-slate-500">
            {graph.attackType} · Record #{recordIdx} ·{' '}
            <span className={graph.success ? 'text-rose-400' : 'text-emerald-400'}>
              {graph.success ? 'Jailbroken' : 'Blocked'}
            </span>
          </p>
        </div>
        <div className="ml-auto text-xs text-slate-500 max-w-sm truncate">
          {graph.goalText}
        </div>
      </div>
      <div className="flex-1 min-h-0">
        <SwimlaneDag graph={graph} />
      </div>
    </div>
  )
}

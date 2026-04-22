import { memo } from 'react'
import { Handle, Position, type NodeProps } from '@xyflow/react'

const ROLE_STYLE: Record<string, string> = {
  goal:     'bg-indigo-900/70 border-indigo-600 text-indigo-200',
  attacker: 'bg-rose-900/70   border-rose-600   text-rose-200',
  target:   'bg-blue-900/70   border-blue-600   text-blue-200',
  judge:    'bg-amber-900/70  border-amber-600  text-amber-200',
  tool:     'bg-violet-900/70 border-violet-600 text-violet-200',
  defense:  'bg-emerald-900/70 border-emerald-600 text-emerald-200',
}

function TraceNode({ data }: NodeProps) {
  const role = (data.role as string) ?? 'target'
  const style = ROLE_STYLE[role] ?? 'bg-slate-800 border-slate-600 text-slate-200'

  return (
    <div
      className={`rounded-lg border px-3 py-2 text-xs max-w-[200px] cursor-pointer shadow-md ${style}`}
    >
      <Handle type="target" position={Position.Top} className="!bg-slate-500" />
      <div className="font-semibold leading-snug line-clamp-2">{data.label as string}</div>
      <Handle type="source" position={Position.Bottom} className="!bg-slate-500" />
    </div>
  )
}

/** Container node that visually wraps all tool-call child nodes */
function SandboxGroupNode({ data }: NodeProps) {
  const w = (data.width as number | undefined) ?? 240
  const h = (data.height as number | undefined) ?? 120
  return (
    <div
      style={{ width: w, height: h }}
      className="rounded-xl border-2 border-dashed border-violet-500/60 bg-violet-950/20 relative"
    >
      {/* header badge */}
      <span className="absolute -top-3 left-3 text-[10px] font-bold uppercase tracking-widest text-violet-400 bg-slate-950 px-2 py-0.5 rounded border border-violet-500/40 select-none">
        Sandbox
      </span>
    </div>
  )
}

const Goal         = memo(TraceNode)
const Attacker     = memo(TraceNode)
const Target       = memo(TraceNode)
const Judge        = memo(TraceNode)
const Tool         = memo(TraceNode)
const Defense      = memo(TraceNode)
const SandboxGroup = memo(SandboxGroupNode)

export const nodeTypes = {
  goal: Goal,
  attacker: Attacker,
  target: Target,
  judge: Judge,
  tool: Tool,
  defense: Defense,
  sandbox: SandboxGroup,
}

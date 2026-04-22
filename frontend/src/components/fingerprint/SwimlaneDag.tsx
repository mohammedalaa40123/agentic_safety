import { useMemo, useState } from 'react'
import {
  ReactFlow,
  Background,
  Controls,
  MiniMap,
  type Node,
  type Edge,
} from '@xyflow/react'
import '@xyflow/react/dist/style.css'
import type { TraceGraph, TraceNode } from '../../lib/trace-parser'
import { nodeTypes } from './NodeTypes'
import DetailDrawer from './DetailDrawer'

const LANE_X: Record<string, number> = {
  goal: 80,
  attacker: 320,
  target: 560,
  judge: 830,
  tool: 690,
  defense: 1060,
}

const LANE_LABELS: Record<string, string> = {
  goal: 'Goal',
  attacker: 'Attacker',
  target: 'Target',
  judge: 'Judge',
  tool: 'Sandbox',
  defense: 'Defense',
}

const TOOL_NODE_W = 220   // approximate rendered tool node width
const TOOL_NODE_H = 72    // approximate rendered tool node height
const SBX_PAD     = 20   // padding inside sandbox container

export default function SwimlaneDag({ graph }: { graph: TraceGraph }) {
  const [selected, setSelected] = useState<null | Record<string, unknown>>(null)

  const nodes: Node[] = useMemo(() => {
    const NODE_H = 110
    const START_Y = 60

    // ── 1. Infer iteration from explicit field or node id prefix-N pattern ──
    function inferIteration(n: TraceNode): number {
      if (n.iteration !== undefined) return n.iteration
      // ids like "target-2", "judge-3", "stage-4" → first number after "-"
      const m = n.id.match(/^[a-z]+-(\d+)/)
      return m ? parseInt(m[1], 10) : 999 // 999 = summary/trailing nodes
    }

    // ── 2. Group nodes by iteration to compute per-row heights ───────────
    const byIter = new Map<number, TraceNode[]>()
    graph.nodes.forEach((n) => {
      const iter = inferIteration(n)
      if (!byIter.has(iter)) byIter.set(iter, [])
      byIter.get(iter)!.push(n)
    })

    const sortedIters = [...byIter.keys()].sort((a, b) => a - b)
    const iterStartY = new Map<number, number>()
    let cumY = START_Y
    for (const iter of sortedIters) {
      iterStartY.set(iter, cumY)
      const group = byIter.get(iter)!
      const laneCounts = new Map<string, number>()
      group.forEach((n) => laneCounts.set(n.lane, (laneCounts.get(n.lane) ?? 0) + 1))
      const maxNodes = Math.max(...laneCounts.values(), 1)
      cumY += maxNodes * NODE_H
    }

    // ── 3. Position each node within its iteration row ────────────────────
    const laneIterCount = new Map<string, number>()
    const positioned: Node[] = graph.nodes.map((n) => {
      const iter = inferIteration(n)
      const startY = iterStartY.get(iter) ?? START_Y
      const x = LANE_X[n.lane] ?? 80
      const key = `${n.lane}|${iter}`
      const localIdx = laneIterCount.get(key) ?? 0
      laneIterCount.set(key, localIdx + 1)
      return {
        id: n.id,
        type: n.role,
        position: { x, y: startY + localIdx * NODE_H },
        data: { label: n.label, detail: n.detail, role: n.role },
      }
    })

    // ── 4. Wrap tool nodes inside a sandbox group ────────────────────────
    const toolIdxs = positioned
      .map((n, i) => ({ n, i }))
      .filter(({ n }) => n.type === 'tool')

    if (toolIdxs.length === 0) return positioned

    const xs = toolIdxs.map(({ n }) => n.position.x)
    const ys = toolIdxs.map(({ n }) => n.position.y)
    const minX = Math.min(...xs) - SBX_PAD
    const minY = Math.min(...ys) - SBX_PAD - 20  // 20 = badge height
    const maxX = Math.max(...xs) + TOOL_NODE_W + SBX_PAD
    const maxY = Math.max(...ys) + TOOL_NODE_H + SBX_PAD
    const sbxW = maxX - minX
    const sbxH = maxY - minY

    const sandboxNode: Node = {
      id: 'sandbox-group',
      type: 'sandbox',
      position: { x: minX, y: minY },
      style: { width: sbxW, height: sbxH, zIndex: -1 },
      data: { label: 'Sandbox', detail: {}, role: 'sandbox', width: sbxW, height: sbxH },
      selectable: false,
    }

    // Re-position tool nodes as children of the sandbox group
    const result = positioned.map((n) => {
      if (n.type !== 'tool') return n
      return {
        ...n,
        parentId: 'sandbox-group',
        extent: 'parent' as const,
        position: {
          x: n.position.x - minX,
          y: n.position.y - minY,
        },
      }
    })

    // Sandbox group must appear before its children
    return [sandboxNode, ...result]
  }, [graph])

  const edges: Edge[] = useMemo(
    () =>
      graph.edges.map((e) => ({
        id: e.id,
        source: e.source,
        target: e.target,
        label: e.label,
        animated: true,
        style: { stroke: '#475569' },
        labelStyle: { fill: '#94a3b8', fontSize: 10 },
      })),
    [graph],
  )

  const lanes = [...new Set(graph.nodes.map((n) => n.lane).filter((l) => l !== 'sandbox'))]

  return (
    <div className="relative h-full w-full bg-slate-950">
      {/* Lane headers */}
      <div className="absolute top-0 left-0 right-0 flex z-10 pointer-events-none select-none">
        {lanes.map((lane) => (
          <div
            key={lane}
            className="text-xs font-semibold text-slate-500 uppercase tracking-widest py-2 text-center"
            style={{ width: 240, position: 'absolute', left: (LANE_X[lane] ?? 80) - 20 }}
          >
            {LANE_LABELS[lane] ?? lane}
          </div>
        ))}
      </div>

      <ReactFlow
        nodes={nodes}
        edges={edges}
        nodeTypes={nodeTypes}
        fitView
        fitViewOptions={{ padding: 0.2 }}
        onNodeClick={(_, node) => setSelected(node.data.detail as Record<string, unknown>)}
        proOptions={{ hideAttribution: true }}
      >
        <Background color="#1e293b" gap={24} />
        <Controls className="[&>button]:bg-slate-800 [&>button]:border-slate-700 [&>button]:text-slate-300" />
        <MiniMap
          nodeColor={(n) => {
            const colors: Record<string, string> = {
              goal: '#6366f1', attacker: '#f43f5e', target: '#3b82f6',
              judge: '#f59e0b', tool: '#8b5cf6', defense: '#10b981', sandbox: '#4c1d95',
            }
            return colors[n.type ?? ''] ?? '#64748b'
          }}
          style={{ background: '#0f172a', border: '1px solid #1e293b' }}
        />
      </ReactFlow>

      {selected && (
        <DetailDrawer detail={selected} onClose={() => setSelected(null)} />
      )}
    </div>
  )
}

/**
 * Converts a raw evaluation result record into a React Flow–ready graph
 * for the fingerprint DAG visualisation.
 */

export type NodeRole = 'goal' | 'attacker' | 'target' | 'judge' | 'tool' | 'defense' | 'sandbox'

export interface TraceNode {
  id: string
  role: NodeRole
  lane: string
  label: string
  detail: Record<string, unknown>
  iteration?: number
}

export interface TraceEdge {
  id: string
  source: string
  target: string
  label?: string
}

export interface TraceGraph {
  nodes: TraceNode[]
  edges: TraceEdge[]
  success: boolean
  attackType: string
  goalText: string
}

// ── Helpers ──────────────────────────────────────────────────────────────────

function isSuccess(rec: Record<string, unknown>): boolean {
  const v = rec.attack_success ?? rec.jailbroken ?? rec.success
  return v === true || v === 'True' || v === 'true'
}

/** Append a record-level defense summary node + edge when defense info exists. */
function appendDefenseNodes(
  rec: Record<string, unknown>,
  nodes: TraceNode[],
  edges: TraceEdge[],
  lastNodeId: string,
): void {
  const defenseName = rec.defense_name as string | undefined
  if (!defenseName) return

  const bypassed = rec.defense_bypassed
  const defResponse = (rec.defense_response ?? '') as string
  const defId = 'defense-summary'

  nodes.push({
    id: defId,
    role: 'defense',
    lane: 'defense',
    label: `Defense: ${defenseName} ${bypassed ? '(bypassed)' : '(blocked)'}`,
    detail: {
      defense_name: defenseName,
      defense_bypassed: bypassed,
      defense_response: defResponse,
    },
  })
  edges.push({ id: `e-${lastNodeId}-${defId}`, source: lastNodeId, target: defId })
}

/** Create a defense node for a blocked tool-call step. */
function makeBlockedDefenseNode(
  step: Record<string, unknown>,
  stepIndex: number,
): TraceNode | null {
  const obs = String(step.observation ?? step.output_preview ?? '')
  if (!obs.startsWith('[BLOCKED]')) return null

  return {
    id: `defense-${stepIndex}`,
    role: 'defense',
    lane: 'defense',
    label: `Blocked: ${obs.slice(10, 60)}`,
    detail: {
      observation: obs,
      action: step.action ?? step.tool ?? '',
      arguments: step.arguments ?? step.args ?? '',
      step: step.step,
    },
    iteration: stepIndex,
  }
}

// ── Parsers ───────────────────────────────────────────────────────────────────

function formatText(value: unknown): string {
  if (typeof value === 'string') return value
  if (typeof value === 'number' || typeof value === 'boolean') return String(value)
  if (Array.isArray(value)) return JSON.stringify(value)
  if (typeof value === 'object' && value !== null) {
    const obj = value as Record<string, unknown>
    return String(obj.generated_prompt ?? obj.prompt ?? obj.raw_response ?? obj.response ?? obj.reasoning ?? JSON.stringify(obj))
  }
  return ''
}

function parsePairRecord(rec: Record<string, unknown>): TraceGraph {
  const nodes: TraceNode[] = []
  const edges: TraceEdge[] = []
  const steps = (rec.steps as Record<string, unknown>[]) ?? (rec.stages as Record<string, unknown>[]) ?? []
  const goal = (rec.goal as string) ?? ''
  const success = isSuccess(rec)

  nodes.push({ id: 'goal-0', role: 'goal', lane: 'goal', label: `Goal: ${goal.slice(0, 60)}…`, detail: { goal }, iteration: 0 })

  let prevId = 'goal-0'
  steps.forEach((step, i) => {
    const iter = typeof step.iteration === 'number' ? step.iteration : Number(step.iteration ?? i)
    const index = Number.isNaN(iter) ? i : iter
    const atkId = `attacker-${index}`
    const tgtId = `target-${index}`
    const judgeId = `judge-${index}`

    const attackerValue = step.attacker ?? step.attacker_prompt
    const targetValue = step.target_response ?? step.target
    const judgeObj = typeof step.judge === 'object' && step.judge !== null
      ? (step.judge as Record<string, unknown>)
      : undefined
    const judgeScore = step.judge_score ?? judgeObj?.score

    nodes.push({
      id: atkId,
      role: 'attacker',
      lane: 'attacker',
      label: `Attacker #${index + 1}`,
      detail: { prompt: formatText(attackerValue) },
      iteration: index,
    })
    nodes.push({
      id: tgtId,
      role: 'target',
      lane: 'target',
      label: `Response ${index + 1}`,
      detail: { response: formatText(targetValue) },
      iteration: index,
    })
    if (judgeScore !== undefined || judgeObj) {
      nodes.push({
        id: judgeId,
        role: 'judge',
        lane: 'judge',
        label: `Judge #${index + 1}: ${formatText(judgeScore ?? '?')}`,
        detail: {
          score: judgeScore,
          reasoning: formatText(step.judge_rationale ?? judgeObj?.reasoning ?? ''),
          raw_response: formatText(judgeObj?.raw_response ?? ''),
        },
        iteration: index,
      })
    }

    edges.push({ id: `e-${prevId}-${atkId}`, source: prevId, target: atkId })
    edges.push({ id: `e-${atkId}-${tgtId}`, source: atkId, target: tgtId })

    // Sandbox tool-call nodes from this iteration's agentic stages
    const targetObj = step.target as Record<string, unknown> | undefined
    const targetStages = Array.isArray(targetObj?.steps)
      ? (targetObj!.steps as Record<string, unknown>[])
      : []
    let sandboxPrevId = tgtId
    targetStages.forEach((ts, tsIdx) => {
      const action = String(ts.action ?? '')
      if (action === 'final_answer') return
      const obs = String(ts.observation ?? '')
      const blocked = obs.startsWith('[BLOCKED]')
      const toolId = `tool-${index}-${tsIdx}`
      const argsObj = ts.arguments as Record<string, unknown> | null
      const argsStr = argsObj
        ? Object.entries(argsObj).map(([k, v]) => `${k}=${String(v).slice(0, 20)}`).join(', ')
        : String(ts.arguments ?? '')
      nodes.push({
        id: toolId,
        role: blocked ? 'defense' : 'tool',
        lane: blocked ? 'defense' : 'tool',
        label: `${action}(${argsStr.slice(0, 30)})`,
        detail: { tool: action, arguments: ts.arguments, observation: obs, step: ts.step },
        iteration: index,
      })
      edges.push({ id: `e-${sandboxPrevId}-${toolId}`, source: sandboxPrevId, target: toolId })
      sandboxPrevId = toolId
    })

    if (nodes.find((n) => n.id === judgeId)) {
      edges.push({ id: `e-${sandboxPrevId}-${judgeId}`, source: sandboxPrevId, target: judgeId })

      // Also check flat tool_log for blocked calls (legacy / non-nested data)
      const toolLog = (step.tool_calls ?? step.tool_log ?? []) as Record<string, unknown>[]
      if (Array.isArray(toolLog) && targetStages.length === 0) {
        toolLog.forEach((tc, tcIdx) => {
          const defNode = makeBlockedDefenseNode(tc, i * 100 + tcIdx)
          if (defNode) {
            nodes.push(defNode)
            edges.push({ id: `e-${tgtId}-${defNode.id}`, source: tgtId, target: defNode.id })
          }
        })
      }

      prevId = judgeId
    } else {
      prevId = sandboxPrevId
    }
  })

  appendDefenseNodes(rec, nodes, edges, prevId)

  return { nodes, edges, success, attackType: 'pair', goalText: goal }
}

function parseCrescendoRecord(rec: Record<string, unknown>): TraceGraph {
  const nodes: TraceNode[] = []
  const edges: TraceEdge[] = []
  const stages = (rec.steps as Record<string, unknown>[]) ?? (rec.stages as Record<string, unknown>[]) ?? []
  const goal = (rec.goal as string) ?? ''
  const success = isSuccess(rec)

  nodes.push({ id: 'goal-0', role: 'goal', lane: 'goal', label: `Goal: ${goal.slice(0, 60)}…`, detail: { goal } })

  let prevId = 'goal-0'
  stages.forEach((stage, i) => {
    const stageId = `stage-${i}`
    const tgtId = `target-${i}`
    nodes.push({
      id: stageId,
      role: 'attacker',
      lane: 'attacker',
      label: `Stage ${i + 1}: ${String(stage.stage ?? '').slice(0, 40)}`,
      detail: stage,
      iteration: i,
    })
    nodes.push({
      id: tgtId,
      role: 'target',
      lane: 'target',
      label: `Response ${i + 1}`,
      detail: { response: stage.response ?? '' },
      iteration: i,
    })
    edges.push({ id: `e-${prevId}-${stageId}`, source: prevId, target: stageId })
    edges.push({ id: `e-${stageId}-${tgtId}`, source: stageId, target: tgtId })

    // Tool call stages injected by crescendo's tool_dispatch_fn
    const stageTool = stage.role === 'tool'
    if (stageTool) {
      const action = String(stage.action ?? stage.content ?? '')
      const toolId = `tool-cresc-${i}`
      const obs = String(stage.observation ?? stage.content ?? '')
      const blocked = obs.startsWith('[BLOCKED]')
      nodes.push({
        id: toolId,
        role: blocked ? 'defense' : 'tool',
        lane: blocked ? 'defense' : 'tool',
        label: `${action.slice(0, 40)}`,
        detail: { tool: action, arguments: stage.arguments, observation: obs, step: stage.step, is_harmful: stage.is_harmful },
        iteration: i,
      })
      edges.push({ id: `e-${tgtId}-${toolId}`, source: tgtId, target: toolId })
    }

    // Check for blocked defense observations in stage (flat observation field)
    const obs = String(stage.observation ?? '')
    if (obs.startsWith('[BLOCKED]')) {
      const defNode = makeBlockedDefenseNode(stage, i)
      if (defNode) {
        nodes.push(defNode)
        edges.push({ id: `e-${tgtId}-${defNode.id}`, source: tgtId, target: defNode.id })
      }
    }

    prevId = tgtId
  })

  appendDefenseNodes(rec, nodes, edges, prevId)

  return { nodes, edges, success, attackType: 'crescendo', goalText: goal }
}

function parseBaselineRecord(rec: Record<string, unknown>): TraceGraph {
  const goal = (rec.goal as string) ?? ''
  const response = (rec.response ?? rec.target_response ?? '') as string
  const success = isSuccess(rec)
  const steps = (rec.steps as Record<string, unknown>[]) ?? []

  const nodes: TraceNode[] = []
  const edges: TraceEdge[] = []

  nodes.push({ id: 'goal-0', role: 'goal', lane: 'goal', label: `Goal: ${goal.slice(0, 60)}…`, detail: { goal } })

  const isGcg = !!(rec.gcg_suffix) || String(rec.fusion_strategy ?? '').toLowerCase().includes('gcg')

  // GCG surrogate suffix node (attacker lane) — shown before tool calls
  if (isGcg && rec.gcg_suffix) {
    const sfxId = 'gcg-suffix-0'
    nodes.push({
      id: sfxId,
      role: 'attacker',
      lane: 'attacker',
      label: `GCG Suffix: ${String(rec.gcg_suffix).slice(0, 50)}`,
      detail: { gcg_suffix: rec.gcg_suffix, fusion_strategy: rec.fusion_strategy },
    })
    edges.push({ id: 'e-goal-gcg', source: 'goal-0', target: sfxId })
  }

  if (steps.length > 0) {
    // Render each agentic loop stage
    let prevId = isGcg && rec.gcg_suffix ? 'gcg-suffix-0' : 'goal-0'
    steps.forEach((step, i) => {
      const action = String(step.action ?? '')
      const obs = String(step.observation ?? '')
      const thought = String(step.thought ?? '')
      const blocked = obs.startsWith('[BLOCKED]')

      if (action === 'final_answer') {
        const finalId = `target-final-${i}`
        nodes.push({
          id: finalId,
          role: 'target',
          lane: 'target',
          label: `Answer: ${(thought || response).slice(0, 50)}`,
          detail: { thought, response: thought || response },
          iteration: i,
        })
        edges.push({ id: `e-${prevId}-${finalId}`, source: prevId, target: finalId })
        prevId = finalId
      } else {
        // Sandbox tool call
        const toolId = `tool-sb-${i}`
        const argsObj = step.arguments as Record<string, unknown> | null
        const argsStr = argsObj
          ? Object.entries(argsObj).map(([k, v]) => `${k}=${String(v).slice(0, 20)}`).join(', ')
          : String(step.arguments ?? '')
        nodes.push({
          id: toolId,
          role: blocked ? 'defense' : 'tool',
          lane: blocked ? 'defense' : 'tool',
          label: `${action}(${argsStr.slice(0, 40)})`,
          detail: { tool: action, arguments: step.arguments, observation: obs, thought, step: step.step },
          iteration: i,
        })
        edges.push({ id: `e-${prevId}-${toolId}`, source: prevId, target: toolId })
        prevId = toolId
      }
    })
    appendDefenseNodes(rec, nodes, edges, nodes[nodes.length - 1].id)
  } else {
    // No agentic stages — simple single-turn
    const tgtId = isGcg && rec.gcg_suffix ? 'target-0-gcg' : 'target-0'
    nodes.push({ id: tgtId, role: 'target', lane: 'target', label: 'Response', detail: { response } })
    edges.push({ id: 'e-0', source: isGcg && rec.gcg_suffix ? 'gcg-suffix-0' : 'goal-0', target: tgtId })
    appendDefenseNodes(rec, nodes, edges, tgtId)
  }

  return { nodes, edges, success, attackType: isGcg ? 'gcg' : 'baseline', goalText: goal }
}

/**
 * Prompt Fusion fingerprint:
 *   Goal → Attacker (fused prompt) → Target → [Sandbox steps] → Judge
 * The attacker lane shows the actual fused/crafted prompt sent to the target.
 */
function parseFusionRecord(rec: Record<string, unknown>): TraceGraph {
  const goal = (rec.goal as string) ?? ''
  const success = isSuccess(rec)
  const fusedPrompt = (rec.jailbreak_prompt ?? rec.fusion_prompt ?? goal) as string
  const response = (rec.jailbreak_response ?? rec.response ?? '') as string
  const steps = (rec.steps as Record<string, unknown>[]) ?? []
  const fusionStrategy = String(rec.fusion_strategy ?? 'prompt_fusion')

  const nodes: TraceNode[] = []
  const edges: TraceEdge[] = []

  // Goal node
  nodes.push({ id: 'goal-0', role: 'goal', lane: 'goal', label: `Goal: ${goal.slice(0, 60)}…`, detail: { goal }, iteration: 0 })

  // Attacker node — shows the fused prompt
  const atkId = 'attacker-0'
  nodes.push({
    id: atkId,
    role: 'attacker',
    lane: 'attacker',
    label: `Fused Prompt`,
    detail: { prompt: fusedPrompt, strategy: fusionStrategy },
    iteration: 0,
  })
  edges.push({ id: 'e-goal-atk', source: 'goal-0', target: atkId })

  // Sandbox tool-call steps
  let prevId = atkId
  steps.forEach((step, i) => {
    const action = String(step.action ?? '')
    const obs = String(step.observation ?? '')
    const blocked = obs.startsWith('[BLOCKED]')

    if (action === 'final_answer') {
      const finalId = `target-final-${i}`
      nodes.push({
        id: finalId,
        role: 'target',
        lane: 'target',
        label: `Answer: ${String(step.thought ?? response).slice(0, 50)}`,
        detail: { thought: step.thought, response },
        iteration: i,
      })
      edges.push({ id: `e-${prevId}-${finalId}`, source: prevId, target: finalId })
      prevId = finalId
    } else {
      const toolId = `tool-${i}`
      const argsObj = step.arguments as Record<string, unknown> | null
      const argsStr = argsObj
        ? Object.entries(argsObj).map(([k, v]) => `${k}=${String(v).slice(0, 20)}`).join(', ')
        : String(step.arguments ?? '')
      nodes.push({
        id: toolId,
        role: blocked ? 'defense' : 'tool',
        lane: blocked ? 'defense' : 'tool',
        label: `${action}(${argsStr.slice(0, 40)})`,
        detail: { tool: action, arguments: step.arguments, observation: obs, step: step.step },
        iteration: i,
      })
      edges.push({ id: `e-${prevId}-${toolId}`, source: prevId, target: toolId })
      prevId = toolId
    }
  })

  // Target response node (if no final_answer step)
  if (steps.length === 0 || !steps.some((s) => String(s.action ?? '') === 'final_answer')) {
    const tgtId = 'target-0'
    nodes.push({
      id: tgtId, role: 'target', lane: 'target',
      label: `Response: ${response.slice(0, 50)}`,
      detail: { response },
      iteration: steps.length,
    })
    edges.push({ id: `e-${prevId}-tgt0`, source: prevId, target: tgtId })
    prevId = tgtId
  }

  // Judge outcome node (inferred from attack_success)
  const judgeId = 'judge-0'
  nodes.push({
    id: judgeId, role: 'judge', lane: 'judge',
    label: success ? 'Judge: Jailbroken ✓' : 'Judge: Blocked ✗',
    detail: { attack_success: success, queries: rec.queries },
    iteration: steps.length + 1,
  })
  edges.push({ id: `e-${prevId}-judge`, source: prevId, target: judgeId })

  appendDefenseNodes(rec, nodes, edges, judgeId)

  return { nodes, edges, success, attackType: 'prompt_fusion', goalText: goal }
}

export function parseRecord(rec: Record<string, unknown>): TraceGraph {
  const fusionStrategy = String(rec.fusion_strategy ?? '')
  // Route by fusion_strategy first (covers prompt_fusion / hybrid)
  if (fusionStrategy.includes('prompt_fusion') || fusionStrategy.includes('fusion')) {
    return parseFusionRecord(rec)
  }

  const steps = (rec.steps as Record<string, unknown>[]) ?? (rec.stages as Record<string, unknown>[]) ?? []
  const attackName = String(rec.attack_name ?? '')

  if (attackName === 'prompt_fusion') return parseFusionRecord(rec)

  if (steps.length > 0) {
    if ('attacker_prompt' in steps[0] || 'attacker' in steps[0]) return parsePairRecord(rec)
    if ('stage' in steps[0]) return parseCrescendoRecord(rec)
  }
  return parseBaselineRecord(rec)
}

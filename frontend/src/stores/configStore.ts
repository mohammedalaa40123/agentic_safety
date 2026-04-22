import { create } from 'zustand'
import type { AttackSpec, DatasetScope, LaunchRequest } from '../lib/api'

interface ConfigStore {
  targetProvider: string
  targetModel: string
  attackProvider: string
  attackModel: string
  judgeProvider: string
  judgeModel: string
  dataset: string
  datasetScope: DatasetScope
  attacks: string[]
  defenses: string[]
  attackParams: Record<string, Record<string, unknown>>
  defenseParams: Record<string, Record<string, unknown>>
  callsPerMinute: number
  wandbEnabled: boolean
  wandbProject: string
  wandbEntity: string
  wandbRunName: string
  wandbApiKey: string

  set: <K extends keyof Omit<ConfigStore, 'set' | 'setAttackParam' | 'setDefenseParam' | 'toLaunchRequest'>>(
    key: K,
    val: ConfigStore[K],
  ) => void
  setAttackParam: (attack: string, param: string, val: unknown) => void
  setDefenseParam: (defense: string, param: string, val: unknown) => void
  toLaunchRequest: (
    credentials: { provider_id: string; api_key: string; base_url: string }[],
  ) => LaunchRequest
}

export const useConfigStore = create<ConfigStore>()((set, get) => ({
  targetProvider: 'genai_rcac',
  targetModel: '',
  attackProvider: 'genai_rcac',
  attackModel: '',
  judgeProvider: 'genai_rcac',
  judgeModel: '',
  dataset: 'agentic_scenarios_100_labeled.json',
  datasetScope: { mode: 'full' },
  attacks: [],
  defenses: [],
  attackParams: {},
  defenseParams: {},
  callsPerMinute: 0,
  wandbEnabled: false,
  wandbProject: 'agentic-safety',
  wandbEntity: '',
  wandbRunName: '',
  wandbApiKey: '',

  set: (key, val) => set({ [key]: val } as Pick<ConfigStore, typeof key>),

  setAttackParam: (attack, param, val) =>
    set((s) => ({
      attackParams: {
        ...s.attackParams,
        [attack]: { ...(s.attackParams[attack] ?? {}), [param]: val },
      },
    })),

  setDefenseParam: (defense, param, val) =>
    set((s) => ({
      defenseParams: {
        ...s.defenseParams,
        [defense]: { ...(s.defenseParams[defense] ?? {}), [param]: val },
      },
    })),

  toLaunchRequest: (credentials) => {
    const s = get()

    // Build structured attack specs — include params only when present
    const attacks: (string | AttackSpec)[] = s.attacks.map((name) => {
      const p = s.attackParams[name]
      return p && Object.keys(p).length > 0 ? { name, params: p } : name
    })

    // Build defense_params only for defenses that have param overrides
    const defense_params: Record<string, Record<string, unknown>> = {}
    for (const d of s.defenses) {
      if (s.defenseParams[d] && Object.keys(s.defenseParams[d]).length > 0) {
        defense_params[d] = s.defenseParams[d]
      }
    }

    return {
      target_provider: s.targetProvider,
      target_model: s.targetModel,
      attack_provider: s.attackProvider || undefined,
      attack_model: s.attackModel || undefined,
      judge_provider: s.judgeProvider || undefined,
      judge_model: s.judgeModel || undefined,
      dataset: s.dataset,
      dataset_scope: s.datasetScope,
      attacks,
      defenses: s.defenses,
      ...(Object.keys(defense_params).length > 0 ? { defense_params } : {}),
      calls_per_minute: s.callsPerMinute,
      wandb_enabled: s.wandbEnabled,
      ...(s.wandbEnabled ? {
        wandb_project: s.wandbProject,
        wandb_entity: s.wandbEntity || undefined,
        wandb_run_name: s.wandbRunName || undefined,
      } : {}),
      credentials: s.wandbEnabled && s.wandbApiKey
        ? [...credentials, { provider_id: 'wandb', api_key: s.wandbApiKey, base_url: '' }]
        : credentials,
    }
  },
}))

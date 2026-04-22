import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { ModelInfo } from '../lib/api'

export interface ProviderConfig {
  provider_id: string
  api_key: string
  base_url: string
  validated: boolean
  models: ModelInfo[]
}

interface ProviderStore {
  configs: Record<string, ProviderConfig>
  setConfig: (id: string, patch: Partial<ProviderConfig>) => void
  removeConfig: (id: string) => void
  getCredentials: () => { provider_id: string; api_key: string; base_url: string }[]
}

export const useProviderStore = create<ProviderStore>()(
  persist(
    (set, get) => ({
      configs: {},

      setConfig: (id, patch) =>
        set((s) => {
          const existing = s.configs[id] ?? { provider_id: id, api_key: '', base_url: '', validated: false, models: [] }
          return {
            configs: {
              ...s.configs,
              [id]: { ...existing, ...patch },
            },
          }
        }),

      removeConfig: (id) =>
        set((s) => {
          const next = { ...s.configs }
          delete next[id]
          return { configs: next }
        }),

      getCredentials: () =>
        Object.values(get().configs)
          .filter((c) => c.validated || c.provider_id === 'ollama' || c.provider_id === 'ollama_cloud')
          .map(({ provider_id, api_key, base_url }) => ({ provider_id, api_key, base_url })),
    }),
    {
      name: 'provider-configs',
    },
  ),
)

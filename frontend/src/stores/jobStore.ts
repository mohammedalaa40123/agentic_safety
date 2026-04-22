import { create } from 'zustand'
import type { JobSummary } from '../lib/api'

interface JobStore {
  jobs: JobSummary[]
  setJobs: (jobs: JobSummary[]) => void
  upsertJob: (job: JobSummary) => void
  removeJob: (id: string) => void
}

export const useJobStore = create<JobStore>()((set) => ({
  jobs: [],
  setJobs: (jobs) => set({ jobs }),
  upsertJob: (job) =>
    set((s) => {
      const idx = s.jobs.findIndex((j) => j.id === job.id)
      if (idx >= 0) {
        const next = [...s.jobs]
        next[idx] = job
        return { jobs: next }
      }
      return { jobs: [job, ...s.jobs] }
    }),
  removeJob: (id) => set((s) => ({ jobs: s.jobs.filter((j) => j.id !== id) })),
}))

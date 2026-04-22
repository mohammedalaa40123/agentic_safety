interface Props {
  detail: Record<string, unknown>
  onClose: () => void
}

export default function DetailDrawer({ detail, onClose }: Props) {
  const entries = Object.entries(detail).filter(([, v]) => v !== undefined && v !== null && v !== '')

  return (
    <div className="absolute top-0 right-0 bottom-0 w-96 bg-slate-900 border-l border-slate-700 flex flex-col z-20 shadow-2xl">
      <div className="flex items-center justify-between px-5 py-4 border-b border-slate-700">
        <span className="text-sm font-semibold text-slate-200">Node Detail</span>
        <button
          onClick={onClose}
          className="text-slate-500 hover:text-slate-300 text-lg leading-none"
        >
          ✕
        </button>
      </div>
      <div className="flex-1 overflow-y-auto p-5 space-y-4">
        {entries.map(([key, value]) => (
          <div key={key}>
            <div className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1">
              {key}
            </div>
            <div className="text-sm text-slate-200 whitespace-pre-wrap break-words bg-slate-800 rounded-lg px-3 py-2 leading-relaxed">
              {typeof value === 'object' ? JSON.stringify(value, null, 2) : String(value)}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}

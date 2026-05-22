import { useState, type RefObject } from 'react'

interface Props {
  inputRef: RefObject<HTMLInputElement>
  required?: boolean
  accept?: string
}

export default function FilePickerInput({ inputRef, required, accept }: Props) {
  const [fileName, setFileName] = useState<string | null>(null)

  return (
    <div className="flex items-center gap-2.5">
      <input
        ref={inputRef}
        type="file"
        accept={accept}
        required={required}
        className="hidden"
        onChange={(e) => setFileName(e.target.files?.[0]?.name ?? null)}
      />
      <button
        type="button"
        onClick={() => inputRef.current?.click()}
        className="flex items-center gap-1.5 rounded-md border border-slate-200 bg-slate-50
                   px-3 py-1.5 text-sm font-medium text-slate-700
                   hover:bg-slate-100 transition-colors flex-shrink-0"
      >
        <svg className="w-3.5 h-3.5" viewBox="0 0 24 24" fill="none" stroke="currentColor"
             strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <path d="M21.44 11.05l-9.19 9.19a6 6 0 01-8.49-8.49l9.19-9.19a4 4 0 015.66 5.66L9.41 17.41a2 2 0 01-2.83-2.83l8.49-8.48" />
        </svg>
        Choose file
      </button>
      <span className={`text-sm truncate max-w-xs ${fileName ? 'text-slate-700' : 'text-slate-400'}`}>
        {fileName ?? 'No file chosen'}
      </span>
    </div>
  )
}

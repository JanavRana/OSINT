import { useState } from 'react'
import type { IdentifierType } from '../types/investigation'

interface IdentifierInputProps {
  onAdd: (value: string, type: IdentifierType) => void
  disabled?: boolean
}

const IDENTIFIER_TYPES: { value: IdentifierType; label: string }[] = [
  { value: 'email', label: 'Email' },
  { value: 'phone', label: 'Phone Number' },
  { value: 'username', label: 'Username' },
  { value: 'domain', label: 'Domain' },
  { value: 'wallet', label: 'Cryptocurrency Wallet' },
  { value: 'image', label: 'Image' },
]

export default function IdentifierInput({ onAdd, disabled = false }: IdentifierInputProps) {
  const [value, setValue] = useState('')
  const [type, setType] = useState<IdentifierType>('email')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (value.trim()) {
      onAdd(value.trim(), type)
      setValue('')
    }
  }

  return (
    <form onSubmit={handleSubmit} className="space-y-4">
      <div>
        <label htmlFor="identifier-type" className="block text-sm font-medium text-text">
          Identifier Type
        </label>
        <select
          id="identifier-type"
          value={type}
          onChange={(e) => setType(e.target.value as IdentifierType)}
          disabled={disabled}
          className="mt-1.5 w-full rounded border border-line bg-surface2 px-3 py-2 text-sm text-text focus:border-signal focus:outline-none focus:ring-1 focus:ring-signal disabled:cursor-not-allowed disabled:opacity-50"
        >
          {IDENTIFIER_TYPES.map((option) => (
            <option key={option.value} value={option.value}>
              {option.label}
            </option>
          ))}
        </select>
      </div>

      <div>
        <label htmlFor="identifier-value" className="block text-sm font-medium text-text">
          Identifier Value
        </label>
        <input
          type="text"
          id="identifier-value"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          disabled={disabled}
          placeholder={`Enter ${IDENTIFIER_TYPES.find((t) => t.value === type)?.label.toLowerCase() || 'identifier'}`}
          className="mt-1.5 w-full rounded border border-line bg-surface2 px-3 py-2 text-sm text-text placeholder-faint focus:border-signal focus:outline-none focus:ring-1 focus:ring-signal disabled:cursor-not-allowed disabled:opacity-50"
        />
      </div>

      <button
        type="submit"
        disabled={disabled || !value.trim()}
        className="w-full rounded border border-signal bg-signalDim px-4 py-2 text-sm font-medium text-signal transition-colors hover:bg-signal/20 focus-visible:outline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-signal disabled:cursor-not-allowed disabled:opacity-50"
      >
        Add Identifier
      </button>
    </form>
  )
}

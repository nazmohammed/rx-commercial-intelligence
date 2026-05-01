import { FormEvent, useEffect, useRef } from 'react';

interface InputBarProps {
  value: string;
  onChange: (value: string) => void;
  onSubmit: () => void;
  disabled?: boolean;
  placeholder?: string;
}

/**
 * Sticky bottom prompt bar. Submits on Enter (Shift+Enter for newline).
 */
export default function InputBar({
  value,
  onChange,
  onSubmit,
  disabled,
  placeholder,
}: InputBarProps) {
  const taRef = useRef<HTMLTextAreaElement>(null);

  useEffect(() => {
    // Auto-grow up to ~6 rows
    const ta = taRef.current;
    if (!ta) return;
    ta.style.height = 'auto';
    ta.style.height = `${Math.min(ta.scrollHeight, 168)}px`;
  }, [value]);

  function handleSubmit(e: FormEvent) {
    e.preventDefault();
    if (!disabled && value.trim()) onSubmit();
  }

  return (
    <form
      onSubmit={handleSubmit}
      className="sticky bottom-0 bg-rx-cream border-t border-rx-purple/10"
    >
      <div className="mx-auto max-w-5xl flex items-end gap-2 px-6 py-3">
        <textarea
          ref={taRef}
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              if (!disabled && value.trim()) onSubmit();
            }
          }}
          rows={1}
          disabled={disabled}
          placeholder={placeholder ?? 'Ask about routes, revenue, load factor…'}
          className="flex-1 resize-none rounded-lg border border-rx-purple/20 bg-white px-3 py-2 text-rx-ink placeholder:text-rx-subtle focus:outline-none focus:ring-2 focus:ring-rx-purple/40 disabled:opacity-60"
        />
        <button
          type="submit"
          disabled={disabled || !value.trim()}
          className="rounded-lg bg-rx-purple px-4 py-2 text-rx-cream font-medium hover:bg-rx-purpleDark disabled:opacity-50 disabled:cursor-not-allowed"
        >
          Send
        </button>
      </div>
    </form>
  );
}

import { useEffect, useId, useMemo, useRef, useState } from 'react'

export type QuickAction = {
  id: string
  label: string
  group: string
  hint?: string
  keywords?: string
  run: () => void
}

const isMac = typeof navigator !== 'undefined' && /Mac|iPhone|iPad/.test(navigator.platform)

/** Compact header trigger plus a Ctrl/Cmd+K quick-actions dialog (native <dialog>: focus trap + Esc for free). */
export default function CommandPalette({ actions }: { actions: QuickAction[] }) {
  const dialogRef = useRef<HTMLDialogElement>(null)
  const inputRef = useRef<HTMLInputElement>(null)
  const [query, setQuery] = useState('')
  const [active, setActive] = useState(0)
  const listId = useId()

  const results = useMemo(() => {
    const words = query.toLowerCase().split(/\s+/).filter(Boolean)
    return actions.filter((a) => {
      const text = `${a.label} ${a.group} ${a.keywords ?? ''}`.toLowerCase()
      return words.every((w) => text.includes(w))
    })
  }, [actions, query])

  const open = () => {
    const dialog = dialogRef.current
    if (!dialog || dialog.open) return
    setQuery('')
    setActive(0)
    dialog.showModal?.()
    inputRef.current?.focus()
  }
  const close = () => dialogRef.current?.close?.()

  useEffect(() => {
    const onKey = (event: KeyboardEvent) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault()
        if (dialogRef.current?.open) close()
        else open()
      }
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [])

  const runAction = (action: QuickAction | undefined) => {
    if (!action) return
    close()
    action.run()
  }

  const onInputKey = (event: React.KeyboardEvent<HTMLInputElement>) => {
    if (event.key === 'ArrowDown' || event.key === 'ArrowUp') {
      event.preventDefault()
      if (results.length === 0) return
      const step = event.key === 'ArrowDown' ? 1 : -1
      setActive((i) => (i + step + results.length) % results.length)
    } else if (event.key === 'Home' || event.key === 'End') {
      event.preventDefault()
      setActive(event.key === 'Home' ? 0 : Math.max(results.length - 1, 0))
    } else if (event.key === 'Enter') {
      event.preventDefault()
      runAction(results[active])
    }
  }

  useEffect(() => {
    document.getElementById(`${listId}-${active}`)?.scrollIntoView?.({ block: 'nearest' })
  }, [active, listId])

  let lastGroup = ''
  return (
    <>
      <button className="search-trigger" type="button" onClick={open} aria-haspopup="dialog" aria-keyshortcuts="Control+K Meta+K">
        <svg viewBox="0 0 24 24" width="15" height="15" aria-hidden="true" focusable="false">
          <path d="M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM20 20l-4-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
        </svg>
        <span>Search actions</span>
        <kbd aria-hidden="true">{isMac ? '⌘' : 'Ctrl'} K</kbd>
      </button>
      <dialog
        ref={dialogRef}
        className="palette"
        aria-label="Quick actions"
        onClick={(event) => { if (event.target === dialogRef.current) close() }}
      >
        <div className="palette-search">
          <svg viewBox="0 0 24 24" width="18" height="18" aria-hidden="true" focusable="false">
            <path d="M11 18a7 7 0 1 0 0-14 7 7 0 0 0 0 14zM20 20l-4-4" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
          <input
            ref={inputRef}
            type="text"
            role="combobox"
            aria-expanded="true"
            aria-controls={listId}
            aria-activedescendant={results.length ? `${listId}-${active}` : undefined}
            aria-autocomplete="list"
            aria-label="Search actions"
            placeholder="Search pages and actions…"
            value={query}
            onChange={(event) => { setQuery(event.target.value); setActive(0) }}
            onKeyDown={onInputKey}
          />
          <kbd aria-hidden="true">Esc</kbd>
        </div>
        <ul className="palette-list" id={listId} role="listbox" aria-label="Actions">
          {results.map((action, index) => {
            const header = action.group !== lastGroup
            lastGroup = action.group
            return (
              <li key={action.id} role="presentation">
                {header && <div className="palette-group" role="presentation">{action.group}</div>}
                <div
                  id={`${listId}-${index}`}
                  role="option"
                  aria-selected={index === active}
                  className="palette-option"
                  onMouseMove={() => setActive(index)}
                  onClick={() => runAction(action)}
                >
                  <span>{action.label}</span>
                  {action.hint && <span className="palette-hint">{action.hint}</span>}
                </div>
              </li>
            )
          })}
        </ul>
        {results.length === 0 && <p className="palette-empty" role="status">No actions match “{query}”.</p>}
        <div className="palette-footer" aria-hidden="true">
          <span><kbd>↑</kbd><kbd>↓</kbd> navigate</span>
          <span><kbd>Enter</kbd> open</span>
          <span><kbd>Esc</kbd> close</span>
        </div>
      </dialog>
    </>
  )
}

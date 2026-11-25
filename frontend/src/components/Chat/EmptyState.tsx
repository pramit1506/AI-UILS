import { useRef, useState } from 'react';
import { FileUp, TextCursorInput } from 'lucide-react';
import { useAppSelector } from '../../redux/hooks';

interface EmptyStateProps {
  onFileUpload: (file: File) => void;
  onPasteText?: (text: string) => void;
  onSignIn?: () => void;
  busy?: boolean;
}

export function EmptyState({ onFileUpload, onPasteText, onSignIn, busy }: EmptyStateProps) {
  const authenticated = useAppSelector(state => state.auth?.isAuthenticated);
  const input = useRef<HTMLInputElement>(null);
  const [pasting, setPasting] = useState(false);
  const [draft, setDraft] = useState('');
  return <div className="intake-start">
    <div className="intake-mark"><FileUp size={30}/></div>
    <h3>Add a document</h3>
    <p>Drop a PDF, Word document, text file, or email here.</p>
    <div className="intake-actions">
      <button type="button" className={authenticated ? 'record-primary' : undefined} disabled={busy}
        onClick={() => authenticated ? input.current?.click() : onSignIn?.()}>
        <FileUp size={16}/>{authenticated ? 'Choose file' : 'Sign in to upload'}
      </button>
      <input ref={input} type="file" hidden accept=".pdf,.docx,.txt,.eml" onChange={event => {
        const file = event.target.files?.[0];
        if (file) onFileUpload(file);
        event.target.value = '';
      }}/>
      <button type="button" className={authenticated ? undefined : 'record-primary'} disabled={busy} aria-expanded={pasting} onClick={() => setPasting(!pasting)}>
        <TextCursorInput size={16}/>Paste text
      </button>
    </div>
    {pasting && <form className="intake-paste" onSubmit={event => {
      event.preventDefault();
      if (draft.trim() && !busy) onPasteText?.(draft.trim());
    }}>
      <label htmlFor="document-text">Document text</label>
      <textarea id="document-text" autoFocus rows={5} value={draft} onChange={e => setDraft(e.target.value)}/>
      <button className="record-primary" disabled={!draft.trim() || busy}>Extract fields</button>
    </form>}
  </div>;
}

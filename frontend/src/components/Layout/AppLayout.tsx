import { useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { FileText, MessageSquare, Check, Save, Keyboard, ListChecks } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import { toggleShortcutsModal } from '../../redux/logSlice';
import { useSaveLog } from '../../hooks/useSaveLog';
import { Header } from './Header';
import DynamicLogForm from '../LogForm/DynamicLogForm';
import { DocumentViewer } from '../DocumentViewer/DocumentViewer';
import { ChatPanel } from '../Chat/ChatPanel';
import { ShortcutsModal } from '../Common/ShortcutsModal';
import './Layout.css';
import './RecordWorkspace.css';

export function AppLayout() {
  const dispatch = useAppDispatch();
  const usedLocalExtraction = useAppSelector(state => state.chat.extractionUsedFallback);
  const fields = useAppSelector(state => state.log.currentLog?.fields);
  const doc = useAppSelector(state => state.document.currentDocument);
  const needsAnswer = useAppSelector(state => state.agent.clarificationRequired?.required);
  const error = useAppSelector(state => state.chat.error);
  const { saved, savedReference, triggerSave, chatLoading } = useSaveLog();
  const [panel, setPanel] = useState<'review' | 'source' | 'chat'>('review');
  const hasFields = Object.keys(fields ?? {}).some(key => !key.startsWith('_'));
  const commitRef = useRef<() => boolean>(null);
  const saveRecord = () => { if (commitRef.current?.() !== false) triggerSave(); };
  const active = panel === 'source' && doc ? 'source' : !hasFields ? 'chat' : panel === 'source' ? 'review' : panel;
  return (
    <div className="app-layout">
      <Header />
      <main className="record-workspace">
        <header className="record-heading">
          <div>
            <h2>{saved ? 'Record saved' : hasFields ? 'Review your record' : 'Capture a record'}</h2>
            <p role="status">{saved ? savedReference : hasFields
              ? needsAnswer ? 'Answer the question in the conversation to continue.' : 'Check the extracted fields, then save your record.'
              : 'Start with a file, pasted text, or a message.'}</p>
          </div>
          {hasFields && (saved ? <Link className="record-primary" to="/logs"><Check size={16}/>View saved records</Link>
            : <button className="record-primary" onClick={saveRecord} disabled={chatLoading}><Save size={16}/>Save record</button>)}
        </header>
        {hasFields && active !== 'chat' && (needsAnswer || error) && <button className="record-notice" onClick={() => setPanel('chat')}>{error || 'A clarification is waiting.'} Open conversation</button>}
        {usedLocalExtraction && !saved && <p className="record-notice" role="status">
          The AI service could not complete extraction. A basic draft was generated. Check the original for missing fields.
        </p>}
        {(hasFields || doc) && <nav className="record-tools" aria-label="Record tools">
          {hasFields && <button aria-pressed={active === 'review'} onClick={() => setPanel('review')}><ListChecks size={16}/>Fields</button>}
          {doc && <button aria-pressed={active === 'source'} onClick={() => setPanel('source')}><FileText size={16}/>{hasFields ? 'Compare original' : 'Original text'}</button>}
          <button aria-pressed={active === 'chat'} onClick={() => setPanel('chat')}><MessageSquare size={16}/>Conversation</button>
          {hasFields && active !== 'chat' && <button className="record-keys" aria-label="Review shortcuts" onClick={() => dispatch(toggleShortcutsModal())}><Keyboard size={16}/></button>}
        </nav>}
        <div className={'record-content ' + (active === 'source' && hasFields ? 'record-compare' : '')}>
          {hasFields && active !== 'chat' && <section className="record-pane"><DynamicLogForm commitRef={commitRef} onChat={() => setPanel('chat')} onSource={doc ? () => setPanel('source') : undefined}/></section>}
          {active === 'source' && <section className="record-pane" aria-label="Original document"><DocumentViewer onSaveRecord={saveRecord} /></section>}
          <section className="record-pane" hidden={active !== 'chat'} aria-label="Conversation"><ChatPanel /></section>
        </div>
      </main>
      <ShortcutsModal />
    </div>
  );
}

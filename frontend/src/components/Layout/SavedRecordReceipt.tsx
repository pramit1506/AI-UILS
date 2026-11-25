import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { Check, ChevronDown, Plus } from 'lucide-react';
import { useAppDispatch, useAppSelector } from '../../redux/hooks';
import { startNewRecord } from '../../redux/store';
import { logService, type LogRecord } from '../../services/logService';
import { fieldInput } from '../../utils/fieldValue';

export function SavedRecordReceipt({ reference }: { reference: string }) {
  const dispatch = useAppDispatch();
  const name = useAppSelector(state => state.log.sessionName);
  const heading = useRef<HTMLHeadingElement>(null);
  const [expanded, setExpanded] = useState(false);
  const [record, setRecord] = useState<LogRecord | null>(null);
  const [failed, setFailed] = useState(false);
  const [attempt, setAttempt] = useState(0);

  useEffect(() => { heading.current?.focus(); }, []);
  useEffect(() => {
    if (!expanded || record) return;
    const controller = new AbortController();
    setFailed(false);
    logService.getLog(reference, controller.signal)
      .then(result => { if (!controller.signal.aborted) setRecord(result); })
      .catch(() => { if (!controller.signal.aborted) setFailed(true); });
    return () => controller.abort();
  }, [expanded, record, reference, attempt]);

  return (
    <main className="record-workspace saved-workspace">
      <section className="saved-receipt" aria-labelledby="saved-heading">
        <h2 id="saved-heading" ref={heading} tabIndex={-1}><Check aria-hidden="true" />Record saved</h2>
        <p className="receipt-reference">{name && <strong>{name} · </strong>}{reference}</p>
        <div className="receipt-actions">
          <button className="record-primary" onClick={() => dispatch(startNewRecord())}><Plus size={16} />New record</button>
          <Link to="/logs" className="receipt-secondary">View saved records</Link>
        </div>
        <button className="receipt-disclosure" aria-expanded={expanded} aria-controls="saved-fields" onClick={() => setExpanded(!expanded)}>
          <ChevronDown size={16} aria-hidden="true" />{expanded ? 'Hide saved fields' : 'Show saved fields'}
        </button>
        <div id="saved-fields" hidden={!expanded}>
          {record ? <dl>{Object.entries(record.data).map(([key, value]) => (
            <div key={key}><dt>{key.replace(/_/g, ' ')}</dt><dd>{fieldInput(value)}</dd></div>
          ))}</dl> : failed ? <p role="alert">Couldn’t load saved fields. <button className="receipt-secondary" onClick={() => setAttempt(a => a + 1)}>Try again</button></p>
            : expanded && <p role="status">Loading saved fields…</p>}
        </div>
      </section>
    </main>
  );
}

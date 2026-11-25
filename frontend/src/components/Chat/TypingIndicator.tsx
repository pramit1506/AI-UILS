import React, { useEffect, useState } from 'react';
import { Sparkles } from 'lucide-react';
import { useAppSelector } from '../../redux/hooks';
import './StreamingIndicator.css';

export const TypingIndicator: React.FC = () => {
  const agent = useAppSelector((state) => state.agent);
  const toolStatus = agent?.toolStatus ?? 'idle';
  const selectedTool = agent?.selectedTool ?? null;

  const [takingLonger, setTakingLonger] = useState(false);

  useEffect(() => {
    const timer = setTimeout(() => setTakingLonger(true), 15_000);
    return () => clearTimeout(timer);
  }, []);

  let label: string;
  if (toolStatus === 'executing' && selectedTool) {
    label = `Running ${selectedTool.replace(/_/g, ' ')}`;
  } else if (toolStatus === 'success') {
    label = 'Finalising the result';
  } else {
    label = takingLonger ? 'Still working. This request is taking longer than usual.' : 'Analyzing your request';
  }

  return (
    <div className="streaming-indicator" role="status" aria-live="polite">
      <div className="streaming-avatar">
        <Sparkles size={13} />
      </div>
      <div className="streaming-body">
        <div className="streaming-row">
          <span className="streaming-label">{label}</span>
          <span className="streaming-dots" aria-hidden="true">
            <span /><span /><span />
          </span>
        </div>
        <div className="streaming-shimmer" aria-hidden="true">
          <span className="streaming-shimmer-bar" />
        </div>
      </div>
    </div>
  );
};

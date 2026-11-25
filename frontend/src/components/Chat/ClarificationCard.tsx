import React from 'react';
import { HelpCircle } from 'lucide-react';
import { ClarificationPayload } from '../../types/agent';

interface ClarificationCardProps {
  payload: ClarificationPayload;
}

export const ClarificationCard: React.FC<ClarificationCardProps> = ({ payload }) => {

  if (!payload.required) return null;

  return (
    <div className="clarification-card">
      <div className="clarification-question">
        <HelpCircle size={14} className="clarification-icon" />
        <span>{payload.question || 'I need some clarification to proceed.'}</span>
      </div>
    </div>
  );
};

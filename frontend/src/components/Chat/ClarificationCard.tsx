import React from 'react';
import { HelpCircle, ArrowRight } from 'lucide-react';
import { ClarificationPayload } from '../../types/agent';
import { useAppDispatch } from '../../redux/hooks';
import { sendMessage, addUserMessage } from '../../redux/chatSlice';
import './Chat.css';

interface ClarificationCardProps {
  payload: ClarificationPayload;
}

export const ClarificationCard: React.FC<ClarificationCardProps> = ({ payload }) => {
  const dispatch = useAppDispatch();

  const handleOptionSelect = (option: string) => {
    dispatch(addUserMessage(option));
    dispatch(sendMessage(option));
  };

  if (!payload.required) return null;

  return (
    <div className="clarification-card">
      <div className="clarification-question">
        <HelpCircle size={14} className="clarification-icon" />
        <span>{payload.question || 'I need some clarification to proceed.'}</span>
      </div>
      {payload.options && payload.options.length > 0 && (
        <div className="clarification-options">
          {payload.options.map((option, index) => (
            <button 
              key={index} 
              className="clarification-option-btn"
              onClick={() => handleOptionSelect(option)}
            >
              <span>{option}</span>
              <ArrowRight size={11} />
            </button>
          ))}
        </div>
      )}
    </div>
  );
};

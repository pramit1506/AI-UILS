import React from 'react';
import { Terminal } from 'lucide-react';
import { ToolExecutionEvent, TimelineEvent } from '../../types/agent';
import { Timeline } from '../Common/Timeline';
import './Chat.css';

interface ToolExecutionCardProps {
  executions: ToolExecutionEvent[];
}

export const ToolExecutionCard: React.FC<ToolExecutionCardProps> = ({ executions }) => {
  if (!executions || executions.length === 0) return null;

  // Convert ToolExecutionEvents to TimelineEvents
  const timelineEvents: TimelineEvent[] = executions.map((exec, index) => ({
    id: `tool-exec-${index}-${Date.now()}`,
    timestamp: new Date().toISOString(),
    title: exec.tool_name,
    description: exec.error || (exec.status === 'success' ? 'Fields updated successfully' : undefined),
    status: exec.status
  }));

  return (
    <div className="tool-execution-card">
      <div className="tool-execution-header">
        <Terminal size={12} className="tool-execution-icon" />
        <span className="tool-execution-title">Tool Execution Trace</span>
      </div>
      <Timeline events={timelineEvents} />
    </div>
  );
};

import React from 'react';
import { Header } from './Header';
import DynamicLogForm from '../LogForm/DynamicLogForm';
import { ChatPanel } from '../Chat/ChatPanel';
import './Layout.css';

export const AppLayout: React.FC = () => {
  return (
    <div className="app-layout">
      <Header />
      <main className="app-main">
        <section className="left-panel">
          <DynamicLogForm />
        </section>
        <section className="right-panel">
          <ChatPanel />
        </section>
      </main>
    </div>
  );
};

// Workspace.tsx
import React, { useState } from 'react';
import * as api from './api';

type Tab = 'analysis' | 'environment' | 'plots';

export default function Workspace() {
  const [step, setStep] = useState('onboarding'); 
  const [sessionId, setSessionId] = useState('');
  const [activeTab, setActiveTab] = useState<Tab>('analysis');
  const [objective, setObjective] = useState('');
  const [slider, setSlider] = useState(50);
  const [input, setInput] = useState('');
  const [terminalInput, setTerminalInput] = useState('');
  const [limitsDisabled, setLimitsDisabled] = useState(false);
  const [terminalLogs, setTerminalLogs] = useState<{ type: 'input' | 'output', text: string }[]>([]);
  const [chatMessages, setChatMessages] = useState<{ role: 'ai' | 'user', text: string }[]>([]);
  const [objects, setObjects] = useState<any[]>([]);
  const [currentPlot, setCurrentPlot] = useState<string | null>(null);

  const startSession = async () => {
    const data = await api.createSession(objective, slider);
    setSessionId(data.session_id);
    setStep('data');
  };

  const handleChat = async (e: React.FormEvent) => {
    e.preventDefault();
    const msg = input;
    setInput('');
    setChatMessages(prev => [...prev, { role: 'user', text: msg }]);
    
    const data = await api.sendChat(sessionId, msg, slider);
    if (data.is_vip) setLimitsDisabled(true);
    setChatMessages(prev => [...prev, { role: 'ai', text: data.answer }]);
  };

  const runRCode = async (code: string) => {
    setTerminalLogs(prev => [...prev, { type: 'input', text: code }]);
    const data = await api.executeR(sessionId, code);
    if (data.stdout) setTerminalLogs(prev => [...prev, { type: 'output', text: data.stdout }]);
    if (data.plot) {
      setCurrentPlot(data.plot);
      setActiveTab('plots');
    }
    if (data.objects) setObjects(data.objects);
  };

  if (step === 'onboarding') {
    return (
      <div className="h-screen flex items-center justify-center bg-[#f8fafc]">
        <div className="max-w-md w-full bg-white p-10 rounded-2xl shadow-xl border border-slate-100">
          <div className="flex items-center space-x-2 mb-8">
            <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center text-white font-bold text-xl">R</div>
            <h1 className="text-2xl font-bold tracking-tight text-slate-800">aiR Workspace</h1>
          </div>
          <div className="space-y-6">
            <div>
              <label className="block text-sm font-semibold text-slate-600 mb-2">Analysis Objective</label>
              <textarea 
                className="w-full p-4 border border-slate-200 rounded-xl outline-none text-slate-700"
                placeholder="Describe your goal..."
                value={objective}
                onChange={(e) => setObjective(e.target.value)}
              />
            </div>
            <div>
              <label className="text-sm font-semibold text-slate-600">Slider: {slider}</label>
              <input 
                type="range" className="w-full h-1.5 bg-slate-100 rounded-lg appearance-none cursor-pointer accent-blue-600" 
                value={slider} 
                onChange={(e) => setSlider(parseInt(e.target.value))}
              />
            </div>
            <button onClick={startSession} disabled={!objective} className="w-full bg-slate-900 text-white py-4 rounded-xl font-bold">
              Initialize
            </button>
          </div>
        </div>
      </div>
    );
  }

  if (step === 'data') {
    return (
      <div className="h-screen flex items-center justify-center bg-[#f8fafc]">
        <div className="max-w-2xl w-full bg-white p-10 rounded-2xl shadow-xl border border-slate-100">
          <h1 className="text-2xl font-bold mb-6 text-slate-800">Source Your Data</h1>
          <div className="grid grid-cols-2 gap-4">
            <div onClick={() => setStep('workbench')} className="p-6 border-2 border-blue-500 bg-blue-50 rounded-2xl cursor-pointer">
              <div className="font-bold text-blue-900">Use Sample Library</div>
              <div className="text-sm text-blue-700">Quick-start with Penguins or Gapminder</div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <div className="flex flex-col h-screen bg-[#f1f5f9] text-slate-900 overflow-hidden">
      <header className="bg-white border-b border-slate-200 px-6 py-3 flex items-center justify-between shadow-sm z-30">
        <div className="flex items-center space-x-6">
          <span className="font-bold tracking-tight text-slate-800 italic">aiR Workspace</span>
          <nav className="flex bg-slate-100 p-1 rounded-lg">
            {(['analysis', 'environment', 'plots'] as const).map((tab) => (
              <button key={tab} onClick={() => setActiveTab(tab)} className={`px-4 py-1 text-xs font-bold rounded-md transition-all uppercase ${activeTab === tab ? 'bg-white text-blue-600 shadow-sm' : 'text-slate-500'}`}>
                {tab}
              </button>
            ))}
          </nav>
        </div>
        <div className={`px-3 py-1 rounded-full text-[10px] font-bold ${limitsDisabled ? 'bg-emerald-50 text-emerald-600' : 'bg-amber-50 text-amber-600'}`}>
          {limitsDisabled ? 'PRO ACCESS' : 'TRIAL MODE'}
        </div>
      </header>

      <main className="flex-1 relative overflow-hidden flex">
        {activeTab === 'analysis' && (
          <div className="flex w-full h-full">
            <section className="w-[450px] flex flex-col bg-white border-r">
              <div className="p-3 bg-blue-50 text-[10px] italic border-b overflow-hidden truncate">Objective: {objective}</div>
              <div className="flex-1 overflow-y-auto p-4 space-y-4">
                {chatMessages.map((m, i) => (
                  <div key={i} className={`flex ${m.role === 'ai' ? 'justify-start' : 'justify-end'}`}>
                    <div className={`max-w-[80%] p-3 rounded-2xl text-sm ${m.role === 'ai' ? 'bg-slate-100 text-slate-700' : 'bg-blue-600 text-white'}`}>
                      {m.text}
                    </div>
                  </div>
                ))}
              </div>
              <form onSubmit={handleChat} className="p-4 border-t bg-slate-50">
                <input className="w-full p-3 bg-white border rounded-xl outline-none text-sm" placeholder="Ask aiR (or use passcode)..." value={input} onChange={(e) => setInput(e.target.value)} />
              </form>
            </section>

            <section className="flex-1 flex flex-col bg-[#0f172a]">
              <div className="flex-1 p-6 font-mono text-[13px] overflow-y-auto">
                {terminalLogs.map((log, i) => (
                  <div key={i} className="mb-1">
                    <span className={log.type === 'input' ? 'text-blue-400' : 'text-slate-300'}>{log.type === 'input' ? '> ' : ''}{log.text}</span>
                  </div>
                ))}
              </div>
              <div className="p-4 bg-[#1e293b] border-t border-slate-800">
                <div className="flex items-center space-x-3 text-white font-mono">
                  <span className="text-blue-400 font-bold">&gt;</span>
                  <input 
                    className="bg-transparent outline-none flex-1 text-sm" 
                    value={terminalInput} 
                    onChange={(e) => setTerminalInput(e.target.value)}
                    onKeyDown={(e) => { if(e.key === 'Enter') { runRCode(terminalInput); setTerminalInput(''); } }}
                    placeholder="Enter R code..." 
                  />
                </div>
              </div>
            </section>
          </div>
        )}

        {activeTab === 'environment' && (
          <div className="flex w-full h-full flex-col bg-white">
            <div className="flex-1 overflow-y-auto">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-slate-500 text-[10px] font-bold uppercase">
                  <tr><th className="px-6 py-3 text-left">Name</th><th className="px-6 py-3 text-left">Type</th><th className="px-6 py-3 text-left">Details</th></tr>
                </thead>
                <tbody className="divide-y divide-slate-100">
                  {objects.map((obj, i) => (
                    <tr key={i}><td className="px-6 py-4 font-mono font-bold text-blue-600">{obj.name}</td><td className="px-6 py-4 italic">{obj.type}</td><td className="px-6 py-4 text-xs text-slate-500">{obj.details}</td></tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        )}

        {activeTab === 'plots' && (
          <div className="flex-1 flex items-center justify-center p-12 bg-slate-200">
            {currentPlot ? <img src={currentPlot} className="max-w-full max-h-full rounded-xl shadow-2xl" /> : <div className="text-slate-400 italic">No plots available yet.</div>}
          </div>
        )}
      </main>

      <footer className="bg-white border-t px-6 py-2 flex items-center justify-between text-[10px] font-bold text-slate-400 uppercase">
        <span>R Connected | Session: {sessionId.slice(0,8)}</span>
        <span>VIP: {limitsDisabled ? 'YES' : 'NO'}</span>
      </footer>
    </div>
  );
}

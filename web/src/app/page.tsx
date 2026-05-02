"use client";

import React, { useState, useEffect, useLayoutEffect, useRef, useCallback } from 'react';
import * as api from './api';

// --- Types ---
interface HistoryEntry {
  id: string;
  timestamp: number;
  authorship: string; 
  status: 'success' | 'error' | 'pending';
  code: string;
}

interface ChatMessage {
  role: 'ai' | 'user';
  text: string;
  code?: string;
  executed?: boolean;
  execution_output?: string;
  execution_error?: string;
  plots?: string[];
  environment?: api.ObjectSummary[];
  structured_response?: api.StructuredAnalysisResponse;
  groundingType?: string;
  intent?: string;
  instrumentation?: {
    total_latency_ms?: number;
    r_latency_ms?: number;
    tool_rounds?: number;
    error?: string;
  };
}

interface AnalysisLogEntry {
  step: string;
  objective: string;
  rationale: string;
  options_proposed: string[];
  chosen_path: string;
  code: string;
  interpretation: string;
  timestamp: number;
}

// --- Constants ---
const SAMPLES = [
  { id: 'iris', name: 'Iris', load: 'iris <- iris; head(iris)' },
  { id: 'penguins', name: 'Penguins', load: 'library(palmerpenguins); penguins <- penguins; head(penguins)' },
  { id: 'mtcars', name: 'Mtcars', load: 'mtcars <- mtcars; head(mtcars)' }
];

export default function AIRApp() {
  const [startupStatus, setStartupStatus] = useState<string | null>(null);
  const [step, setStep] = useState<'setup' | 'workspace'>('setup');
  
  // Session State
  const [sessionId, setSessionId] = useState('');
  const [objective, setObjective] = useState('');
  const [analysisMode, setAnalysisMode] = useState<'guided' | 'auto'>('guided');
  const [coachingDepth, setCoachingDepth] = useState(50);
  const [uploadedFiles, setUploadedFiles] = useState<{name: string, size: number}[]>([]);
  const [selectedDataset, setSelectedDataset] = useState<string | null>(null);
  const [analysisPlan, setAnalysisPlan] = useState<string | null>(null);
  
  // Workspace Layout State
  const [copilotWidth, setCopilotWidth] = useState(30);
  const [rightWidth, setRightWidth] = useState(25);
  const activeResizer = useRef<'copilot' | 'right' | null>(null);

  // Workspace Content State
  const [chatLog, setChatLog] = useState<ChatMessage[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [consoleLog, setConsoleLog] = useState<{t: string, type: string, prov?: string}[]>([]);
  const [replInput, setReplInput] = useState('');
  const [commandHistory, setCommandHistory] = useState<string[]>([]);
  
  // Refs for auto-scroll
  const chatContainerRef = useRef<HTMLDivElement>(null);
  const consoleContainerRef = useRef<HTMLDivElement>(null);
  const chatBottomRef = useRef<HTMLDivElement>(null);
  const consoleBottomRef = useRef<HTMLDivElement>(null);

  const [historyIndex, setHistoryIndex] = useState(-1);
  const [objects, setObjects] = useState<api.ObjectSummary[]>([]);
  const [plots, setPlots] = useState<string[]>([]);
  const [history, setHistory] = useState<HistoryEntry[]>([]);
  const [activeRightTab, setActiveRightTab] = useState<'plots' | 'env' | 'history'>('plots');
  const [isContextExpanded, setIsContextExpanded] = useState(false);
  const [lastRunTime, setLastRunTime] = useState<string>('--');
  const [isAiLoading, setIsAiLoading] = useState(false);
  const [copyFeedback, setCopyFeedback] = useState<string | null>(null);
  const [lastError, setLastError] = useState<string | null>(null);
  const [analysisLog, setAnalysisLog] = useState<AnalysisLogEntry[]>([]);
  const hasStartedAgentSession = useRef(false);

  // Coaching State
  const [recommendation, setRecommendation] = useState<string>('Wait for coach recommendation...');
  const [currentStep, setCurrentStep] = useState<string>('');

  // --- Auto-scroll Logic ---
  const scrollToBottom = useCallback((bottomRef: React.RefObject<HTMLDivElement | null>) => {
    if (!bottomRef.current) return;
    bottomRef.current.scrollIntoView({ behavior: 'smooth', block: 'end' });
  }, []);

  useLayoutEffect(() => { scrollToBottom(chatBottomRef); }, [chatLog, isAiLoading, scrollToBottom]);
  useLayoutEffect(() => { scrollToBottom(consoleBottomRef); }, [consoleLog, scrollToBottom]);

  // --- Resizing Logic ---
  useEffect(() => {
    const handleMouseMove = (e: MouseEvent) => {
      if (!activeResizer.current) return;
      const totalWidth = window.innerWidth;
      if (activeResizer.current === 'copilot') {
        const newWidth = (e.clientX / totalWidth) * 100;
        if (newWidth > 15 && newWidth < 50) setCopilotWidth(newWidth);
      } else {
        const newRight = ((totalWidth - e.clientX) / totalWidth) * 100;
        if (newRight > 15 && newRight < 40) setRightWidth(newRight);
      }
    };
    const handleMouseUp = () => { activeResizer.current = null; document.body.style.cursor = 'default'; };
    window.addEventListener('mousemove', handleMouseMove);
    window.addEventListener('mouseup', handleMouseUp);
    return () => {
      window.removeEventListener('mousemove', handleMouseMove);
      window.removeEventListener('mouseup', handleMouseUp);
    };
  }, []);

  // --- Actions ---
  const addToConsole = useCallback((text: string, type: 'input' | 'output' | 'system' | 'error' = 'output', prov?: string) => {
    setConsoleLog(prev => [...prev, {t: text, type, prov}]);
  }, []);

  const executeR = useCallback(async (code: string, isAgent: boolean = false, prov: string = 'You', sid?: string) => {
    if (!code.trim()) return;
    
    const targetSid = sid || sessionId;
    if (!targetSid) return;

    addToConsole(code, 'input', prov);
    const startTime = Date.now();
    const entry: HistoryEntry = { 
        id: Math.random().toString(36).substring(2, 11), 
        timestamp: startTime, 
        authorship: prov, 
        status: 'pending', 
        code 
    };

    if (!isAgent) {
        setCommandHistory(prev => [code, ...prev.filter(c => c !== code)].slice(0, 50));
        setHistoryIndex(-1);
    }
    
    try {
      const res = await api.executeR(targetSid, code, isAgent, prov);
      
      const status = Array.isArray(res?.status) ? res.status[0] : res?.status;
      const stdout = Array.isArray(res?.stdout) ? res.stdout.join('\n') : res?.stdout;
      const resPlots = Array.isArray(res?.plots) ? res.plots : [];
      const resEnv = Array.isArray(res?.environment) ? res.environment : [];

      const endTime = Date.now();
      setLastRunTime(`${((endTime - startTime)/1000).toFixed(2)}s`);
      
      if (status === 'success') {
        if (stdout) addToConsole(stdout, 'output');
        setObjects(resEnv);
        setLastError(null);
        if (resPlots.length > 0) {
          setPlots(prev => [...resPlots, ...prev]);
          setActiveRightTab('plots');
        }
        entry.status = 'success';
      } else {
        let errorMsg = 'Execution error';
        if (res?.error) {
          if (typeof res.error === 'string') errorMsg = res.error;
          else if (Array.isArray(res.error)) errorMsg = res.error.join('\n');
          else if (typeof res.error === 'object' && Object.keys(res.error).length > 0) {
            errorMsg = JSON.stringify(res.error);
          }
        }
        addToConsole(errorMsg, 'error');
        setLastError(errorMsg);
        entry.status = 'error';
      }
    } catch (e: unknown) { 
        const errorMsg = e instanceof Error ? e.message : String(e);
        addToConsole(`UI Exception: ${errorMsg}`, 'error'); 
        entry.status = 'error';
    }
    setHistory(prev => [entry, ...prev]);
    setReplInput('');
  }, [sessionId, addToConsole]);

  const startSession = async () => {
    if (startupStatus) return; // Idempotency check
    setStartupStatus("Opening workspace...");
    
    // Transition to workspace immediately to not block UI
    setStep('workspace');

    try {
      const res = await api.createSession(objective || "Data Exploration", getSessionMode(), analysisPlan);
      setSessionId(res.session_id);
      addToConsole(`aiR Core Initialized. Grounding engine active.`, 'system');
      const initialMsg = analysisPlan ? "I've uploaded my analysis plan. Please review it and suggest the first step." : undefined;
      await initializeCoachSession(res.session_id, initialMsg);
      
      if (selectedDataset) {
        setStartupStatus('Starting R session...');
        const sample = SAMPLES.find(s => s.id === selectedDataset);
        if (sample) {
            // Run async without blocking
            executeR(sample.load, true, 'System (Sample)', res.session_id)
                .then(() => setStartupStatus(null))
                .catch(() => setStartupStatus('R session is starting. Code execution available shortly.'));
        }
      } else {
          setStartupStatus(null);
      }
    } catch { 
        alert("Initialization failed."); 
        setStartupStatus(null);
        setStep('setup'); 
    }
  };

  const peekSession = async () => {
    if (startupStatus) return; // Idempotency check
    setStartupStatus("Opening workspace...");
    setAnalysisMode('auto');
    setObjective("Quick Peek");
    setStep('workspace');
    
    try {
      const res = await api.createSession("Quick Peek", 'autonomous');
      setSessionId(res.session_id);
      addToConsole(`aiR Core Initialized (Peek Mode).`, 'system');
      await initializeCoachSession(res.session_id);
      setStartupStatus(null);
    } catch { 
        alert("Initialization failed."); 
        setStartupStatus(null);
        setStep('setup'); 
    }
  };

  const copyToClipboard = (text: string, label: string) => {
    navigator.clipboard.writeText(text);
    setCopyFeedback(label);
    setTimeout(() => setCopyFeedback(null), 2000);
  };

  const downloadHistory = () => {
    const content = history
      .slice().reverse()
      .map(h => `# --- ${h.authorship} (${new Date(h.timestamp).toLocaleString()}) ---\n${h.code}\n`)
      .join('\n');
    const blob = new Blob([content], { type: 'text/plain' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `aiR_session_${sessionId.split('.')[1] || 'export'}.R`;
    a.click();
  };

  const generateReport = () => {
    const html = `
      <!DOCTYPE html>
      <html>
      <head>
        <title>aiR Analysis Report</title>
        <style>
          body { font-family: sans-serif; max-width: 800px; margin: 40px auto; padding: 20px; line-height: 1.6; color: #334155; }
          h1 { font-style: italic; font-weight: 900; letter-spacing: -0.05em; border-bottom: 4px solid #f1f5f9; padding-bottom: 20px; }
          .step { margin-bottom: 60px; border-left: 4px solid #818cf8; padding-left: 24px; }
          .step-header { font-size: 10px; font-weight: 900; text-transform: uppercase; letter-spacing: 0.2em; color: #6366f1; margin-bottom: 8px; display: block; }
          .code { background: #1e293b; color: #f1f5f9; padding: 20px; border-radius: 12px; font-family: monospace; overflow-x: auto; margin: 20px 0; }
          .interpretation { font-style: italic; background: #f0fdf4; padding: 20px; border-radius: 12px; border: 1px solid #dcfce7; }
          .meta { font-size: 12px; color: #94a3b8; margin-top: 40px; border-top: 1px solid #f1f5f9; padding-top: 20px; }
        </style>
      </head>
      <body>
        <h1>aiR Analysis Report</h1>
        <p><strong>Objective:</strong> ${objective || 'Exploratory'}</p>
        <p><strong>Dataset:</strong> ${selectedDataset || (uploadedFiles.length > 0 ? uploadedFiles.map(f => f.name).join(', ') : 'None')}</p>
        <hr style="border: none; border-top: 1px solid #f1f5f9; margin: 40px 0;" />
        ${analysisLog.map((e, i) => `
          <div class="step">
            <span class="step-header">Step ${i+1}: ${e.step}</span>
            <p><strong>Rationale:</strong> ${e.rationale}</p>
            <p><strong>Decision:</strong> User chose "${e.chosen_path}"</p>
            <div class="code"><code>${e.code.replace(/</g, '&lt;').replace(/>/g, '&gt;')}</code></div>
            <div class="interpretation"><strong>Coach Interpretation:</strong> ${e.interpretation}</div>
          </div>
        `).join('')}
        <div class="meta">Generated by aiR Analysis Coach on ${new Date().toLocaleString()}</div>
      </body>
      </html>
    `;
    const blob = new Blob([html], { type: 'text/html' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `aiR_Report_${Date.now()}.html`;
    a.click();
  };

  const getGuidanceMode = (depth: number): 'guided' | 'balanced' | 'autonomous' => {
    if (depth < 34) return 'guided';
    if (depth < 67) return 'balanced';
    return 'autonomous';
  };

  const getSessionMode = (): api.SessionMode => (
    analysisMode === 'guided' ? 'guided' : 'autonomous'
  );

  const initializeCoachSession = async (newSessionId: string, initialMsg?: string) => {
    hasStartedAgentSession.current = true;

    await triggerStartup("WELCOME", newSessionId);

    if (initialMsg) {
      await submitChat(initialMsg, undefined, newSessionId);
    }
  };

  const submitChat = async (msg: string, event?: string, sid?: string) => {
    if ((!msg && !event) || isAiLoading) return;
    if (msg) setChatLog(prev => [...prev, { role: 'user', text: msg }]);
    setIsAiLoading(true);

    try {
      const targetSessionId = sid || sessionId;
      if (!targetSessionId) return;

      const modeStr = getGuidanceMode(coachingDepth);
      const context = {
        objective,
        guidance_depth: modeStr,
        dataset_summary: objects.length > 0 ? `Objects in environment: ${objects.map(o => o.name).join(', ')}` : "No dataset loaded yet."
      };

      const res = await api.sendAgentChat(targetSessionId, msg, context, event);
      
      const normalizedCode = normalizeRCode(res.code);
      const cleanedReply = normalizedCode ? res.reply : stripEmptyCodeFences(res.reply);

      const newMsg: ChatMessage = { 
          role: 'ai', 
          text: cleanedReply, 
          code: normalizedCode || undefined,
          executed: res.executed,
          execution_output: res.execution_output,
          execution_error: res.execution_error,
          plots: res.plots,
          environment: res.environment,
          groundingType: 'Conversation Agent',
          intent: res.intent 
      };

      setChatLog(prev => [...prev, newMsg]);
      
      // If code was auto-executed by backend, update UI state
      if (res.executed) {
          if (res.code) {
              addToConsole(res.code, 'input', 'R copilot (auto)');
              if (res.execution_output) addToConsole(res.execution_output, 'output');
              if (res.execution_error) addToConsole(res.execution_error, 'error');
          }
          if (res.environment) setObjects(res.environment);
          if (res.plots && res.plots.length > 0) {
              setPlots(prev => [...res.plots!, ...prev]);
              setActiveRightTab('plots');
          }
          setLastRunTime('auto');
      }

    } catch (err) { 
        console.error("Chat error:", err);
        setChatLog(prev => [...prev, { role: 'ai', text: `Coach Error: ${err instanceof Error ? err.message : "Service connection lost."}` }]);
    } finally {
        setIsAiLoading(false);
    }
  };

  const triggerStartup = async (event: string, sid?: string) => {
    setIsAiLoading(true);
    try {
        const targetSessionId = sid || sessionId;
        if (!targetSessionId) return;

        const context = {
          objective,
          guidance_depth: getGuidanceMode(coachingDepth),
          dataset_summary: "Startup"
        };
        const res = await api.sendAgentChat(targetSessionId, undefined, context, event);
        const normalizedCode = normalizeRCode(res.code);
        const cleanedReply = normalizedCode ? res.reply : stripEmptyCodeFences(res.reply);

        setChatLog(prev => [...prev, { 
            role: 'ai', 
            text: cleanedReply, 
            code: normalizedCode || undefined,
            groundingType: 'Conversation Agent',
            intent: res.intent 
        }]);
    } catch (err) {
        console.error("Startup failed", err);
        // Fallback to manual greet
        submitChat("I'm ready to start. Please introduce yourself and suggest how we should begin our analysis.");
    } finally {
        setIsAiLoading(false);
    }
  };

  const onChat = async (e: React.FormEvent) => {
    e.preventDefault();
    const msg = chatInput;
    setChatInput('');
    await submitChat(msg);
  };

  const refreshPolicy = async (newMode: 'guided' | 'auto') => {
    setAnalysisMode(newMode);
    try {
        const sessionMode: api.SessionMode = newMode === 'guided' ? 'guided' : 'autonomous';
        const res = await api.refreshSession(sessionId, sessionMode);
        setSessionId(res.session_id);
    } catch { console.error("Policy sync failed"); }
  };

  const extractRCode = (text: string, intent?: string): string => {
    const blocks = Array.from(text.matchAll(/```[Rr]\n?([\s\S]*?)```/g));
    if (blocks.length > 0) return blocks.map(b => b[1].trim()).join('\n\n');
    const coachMatch = text.match(/(?:Why:|Rationale:)?\n?([\s\S]*?)\n?(?:Interpretation:|Next step:|$)/i);
    if (coachMatch && coachMatch[1].trim()) {
        const potentialCode = coachMatch[1].trim();
        if (potentialCode.includes('<-') || potentialCode.includes('(')) {
            return potentialCode.replace(/What we’re doing:.*?\n/i, '').replace(/Why:.*?\n/i, '').trim();
        }
    }
    if (intent === 'CODE_GEN' && text.length < 1000 && (text.includes('<-') || text.includes('library'))) return text.trim();
    return "";
  };

  const normalizeRCode = (code?: string | null): string => {
    const cleaned = (code || "")
      .replace(/```[Rr]?\s*/g, "")
      .replace(/```/g, "")
      .trim();

    if (!cleaned || cleaned === "...") return "";
    if (/^[.`\s]+$/.test(cleaned)) return "";

    return cleaned;
  };

  const stripEmptyCodeFences = (text: string): string => (
    text.replace(/```[Rr]?\s*(?:\.\.\.)?\s*```/g, "").trim()
  );

  if (step === 'setup') {
    return (
      <div className="min-h-screen bg-[#F8F9FA] text-slate-600 flex flex-col items-center justify-center p-6 antialiased font-sans">
        <div className="max-w-2xl w-full">
          <div className="text-center mb-16">
            <h1 className="text-8xl font-black tracking-tighter italic text-slate-900 drop-shadow-sm leading-none inline-block pr-4">aiR</h1>
            <p className="text-xs font-black text-slate-400 uppercase tracking-[0.4em] mt-2">Analysis Coach</p>
          </div>

          <div className="bg-white border border-slate-200/60 p-12 rounded-[3rem] shadow-xl space-y-12">
            <section className="space-y-8">
                <div className="space-y-4 text-center">
                  <label className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400">Primary Objective</label>
                  <textarea className="w-full bg-slate-50 border border-slate-200 rounded-3xl p-8 text-xl text-slate-900 font-black outline-none focus:bg-white focus:border-slate-400 h-32 transition-all resize-none shadow-inner text-center placeholder:text-slate-200" placeholder="E.g., Examine the association between X and Y using linear regression" value={objective} onChange={e => setObjective(e.target.value)} />
                  <p className="text-[9px] text-slate-400 font-bold uppercase tracking-widest italic">Try: &quot;Identify key drivers of churn&quot; or &quot;Perform anomaly detection on sales&quot;</p>
                </div>
                
                <div className="flex gap-4">
                  <div className="flex-1 bg-slate-50 border border-slate-200 rounded-[2rem] p-8 text-center relative group cursor-pointer shadow-inner hover:bg-slate-100 transition-colors">
                      <input type="file" multiple className="absolute inset-0 opacity-0 cursor-pointer" onChange={e => e.target.files && setUploadedFiles(Array.from(e.target.files).map(f => ({name: f.name, size: f.size})))} />
                      <div className="flex flex-col items-center gap-2">
                          <svg className="w-5 h-5 text-slate-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-8l-4-4m0 0L8 8m4-4v12"></path></svg>
                          <p className="text-[9px] text-slate-400 font-black uppercase tracking-[0.2em]">{uploadedFiles.length > 0 ? `${uploadedFiles.length} files staged` : "Drop Data Context"}</p>
                      </div>
                  </div>
                  <div className="flex-1 bg-slate-50 border border-slate-200 rounded-[2rem] p-8 text-center relative group cursor-pointer shadow-inner hover:bg-slate-100 transition-colors">
                      <input type="file" className="absolute inset-0 opacity-0 cursor-pointer" onChange={e => {
                        const file = e.target.files?.[0];
                        if (file) {
                          const reader = new FileReader();
                          reader.onload = (re) => setAnalysisPlan(re.target?.result as string);
                          reader.readAsText(file);
                        }
                      }} />
                      <div className="flex flex-col items-center gap-2">
                          <svg className="w-5 h-5 text-indigo-300" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M9 12h6m-6 4h6m2 5H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z"></path></svg>
                          <p className="text-[9px] text-slate-400 font-black uppercase tracking-[0.2em]">{analysisPlan ? "Plan Loaded" : "Upload Analysis Plan"}</p>
                      </div>
                  </div>
                </div>
            </section>

            <section className="bg-slate-50 p-8 rounded-[2.5rem] border border-slate-200/40 shadow-inner">
              <div className="flex flex-col gap-4">
                <label className="text-[10px] font-black uppercase tracking-[0.3em] text-slate-400 text-center">Analysis Mode</label>
                <div className="flex gap-2 p-1 bg-slate-200/50 rounded-2xl">
                  <button onClick={() => setAnalysisMode('guided')} className={`flex-1 py-3 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${analysisMode === 'guided' ? 'bg-white text-slate-900 shadow-sm' : 'text-slate-400 hover:text-slate-600'}`}>Guided Mode</button>
                  <button onClick={() => setAnalysisMode('auto')} className={`flex-1 py-3 rounded-xl text-[10px] font-black uppercase tracking-widest transition-all ${analysisMode === 'auto' ? 'bg-slate-900 text-white shadow-lg' : 'text-slate-400 hover:text-slate-600'}`}>Fully Auto</button>
                </div>
                <p className="text-[9px] text-slate-500 font-bold uppercase tracking-widest text-center px-4">
                  {analysisMode === 'guided' ? "Coach will propose options and wait for your choices." : "Coach will automatically select and execute the best analysis path."}
                </p>
              </div>
            </section>

            <div className="space-y-4">
              <button data-testid="start-session-btn" onClick={startSession} disabled={!!startupStatus} className={`w-full ${startupStatus ? 'bg-slate-400 cursor-not-allowed' : 'bg-slate-900 hover:scale-[1.01] active:scale-[0.98]'} text-white font-black py-6 rounded-[2.5rem] transition-all shadow-xl text-lg tracking-[0.2em] flex items-center justify-center gap-4`}>
                {startupStatus ? startupStatus : "START SESSION"}
              </button>
              <button data-testid="peek-session-btn" onClick={peekSession} disabled={!!startupStatus} className={`w-full ${startupStatus ? 'bg-slate-50 cursor-not-allowed text-slate-300' : 'bg-white hover:bg-slate-50 text-slate-400'} font-black py-4 rounded-[2rem] border border-slate-200 transition-all text-[10px] tracking-[0.3em] uppercase`}>
                {startupStatus ? "Please wait..." : "I’m just taking a peek"}
              </button>
              <div className="pt-6 text-center">
                <a href="mailto:yeli@biostats.ai" className="text-[9px] font-black uppercase tracking-[0.3em] text-slate-300 hover:text-slate-900 transition-colors flex items-center justify-center gap-2">
                  <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M3 8l7.89 5.26a2 2 0 002.22 0L21 8M5 19h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v10a2 2 0 002 2z"></path></svg>
                  Contact
                </a>
              </div>
              <div className="pt-2 text-center">
                <p className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-400 italic">
                  Delegate syntax and scaffolding. Retain architecture and judgment
                </p>
              </div>
              
              <div className="pt-12 flex flex-col items-center gap-3 opacity-20 hover:opacity-50 transition-opacity cursor-default">
                <img src="/logo.png" alt="biostats.ai" className="h-6 w-auto grayscale brightness-0 inv-0" />
                <p className="text-[8px] font-black uppercase tracking-[0.4em] text-slate-400">
                  Built by <a href="https://biostats.ai" target="_blank" className="hover:text-slate-900 transition-colors">biostats.ai</a>
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    );
  }

  // --- Step 2: Workspace ---
  return (
    <div className="h-screen bg-[#F8F9FA] flex flex-col antialiased text-slate-900 overflow-hidden font-sans">
      <header className="h-16 bg-white border-b border-slate-200/60 flex items-center px-8 justify-between shrink-0 z-20">
        <div className="flex items-center gap-10">
          <div className="flex items-baseline gap-2">
            <span className="text-3xl font-black tracking-tighter italic text-slate-900">aiR</span>
            <span className="text-[8px] font-black text-slate-300 uppercase tracking-[0.4em]">Analysis Coach</span>
          </div>
          <div className="flex items-center gap-4 bg-slate-50 p-1 rounded-full border border-slate-100">
            <button onClick={() => refreshPolicy('guided')} className={`px-4 py-1.5 rounded-full text-[9px] font-black uppercase tracking-widest transition-all ${analysisMode === 'guided' ? 'bg-white text-slate-900 shadow-sm border border-slate-200' : 'text-slate-400 hover:text-slate-600'}`}>Guided</button>
            <button onClick={() => refreshPolicy('auto')} className={`px-4 py-1.5 rounded-full text-[9px] font-black uppercase tracking-widest transition-all ${analysisMode === 'auto' ? 'bg-slate-900 text-white shadow-lg' : 'text-slate-400 hover:text-slate-600'}`}>Fully Auto</button>
          </div>
          <div className="flex flex-col w-32 gap-1 ml-4">
            <div className="flex justify-between items-center px-1">
              <span className="text-[7px] font-black uppercase tracking-[0.1em] text-slate-400">Coaching Depth</span>
            </div>
            <input type="range" min="0" max="100" className="w-full h-1 bg-slate-100 rounded-full appearance-none cursor-pointer accent-slate-400 shadow-inner" value={coachingDepth} onChange={e => setCoachingDepth(parseInt(e.target.value))} />
            <div className="flex justify-between text-[6px] font-black text-slate-300 tracking-widest uppercase px-0.5">
              <span>Less</span>
              <span>More</span>
            </div>
          </div>
        </div>
        
        <div className="flex items-center gap-3">
          {copyFeedback && <span className="text-slate-400 text-[8px] font-black uppercase px-3 py-1.5 rounded-full border border-slate-100">{copyFeedback} Copied!</span>}
          <button onClick={() => setStep('setup')} className="bg-slate-50 border border-slate-200 px-5 py-2 rounded-full text-[9px] font-black uppercase tracking-widest text-slate-600 hover:bg-slate-900 hover:text-white transition-all">+ New Session</button>
          <div className="relative group">
            <button className="bg-slate-900 text-white px-5 py-2 rounded-full text-[9px] font-black uppercase tracking-widest flex items-center gap-2 shadow-lg transition-all hover:scale-105 active:scale-95">Workspace <svg className="w-2.5 h-2.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" d="M19 9l-7 7-7-7"></path></svg></button>
            <div className="absolute right-0 top-full mt-2 w-48 bg-white border border-slate-200 rounded-2xl shadow-2xl opacity-0 invisible group-hover:opacity-100 group-hover:visible transition-all p-2 z-50">
              <button onClick={() => setConsoleLog([])} className="w-full text-left px-4 py-2.5 hover:bg-slate-50 rounded-xl text-[9px] font-black uppercase tracking-widest">Clear Console</button>
              <button onClick={() => setChatLog([])} className="w-full text-left px-4 py-2.5 hover:bg-slate-50 rounded-xl text-[9px] font-black uppercase tracking-widest">Clear Chat</button>
              <button onClick={downloadHistory} className="w-full text-left px-4 py-2.5 hover:bg-slate-50 rounded-xl text-[9px] font-black uppercase tracking-widest">Export History</button>
              <button onClick={generateReport} className="w-full text-left px-4 py-2.5 hover:bg-indigo-50 text-indigo-600 rounded-xl text-[9px] font-black uppercase tracking-widest">Download Report</button>
              <button onClick={() => { if(confirm("System reset?")) window.location.reload(); }} className="w-full text-left px-4 py-2.5 hover:bg-rose-50 text-rose-600 rounded-xl text-[9px] font-black uppercase mt-1 pt-2 border-t border-slate-100">System Wipe</button>
            </div>
          </div>
        </div>
      </header>

      <div className="h-10 bg-slate-50 border-b border-slate-200/40 flex items-center px-8 justify-between shrink-0">
          <div className="flex items-center gap-6 flex-1">
            <div className="flex items-center gap-2">
              <span className="text-[8px] font-black uppercase tracking-[0.2em] text-slate-300">Objective:</span>
              <div data-testid="session-objective" className="px-3 py-1 bg-white border border-slate-200 rounded-full text-[9px] font-bold text-slate-600 italic shadow-sm">&quot;{objective || 'Exploratory Session'}&quot;</div>
            </div>
            <div className="flex items-center gap-2">
              <span className="text-[8px] font-black uppercase tracking-[0.2em] text-slate-300">Dataset:</span>
              <span className="text-[9px] font-black text-slate-500 uppercase tracking-tighter">{selectedDataset || (uploadedFiles.length > 0 ? `${uploadedFiles.length} files` : 'None')}</span>
            </div>
            <div className="flex items-center gap-2 flex-1 max-w-md">
              <span className="text-[8px] font-black uppercase tracking-[0.2em] text-indigo-400">Next Step:</span>
              <span className="text-[9px] font-bold text-indigo-900 truncate">{analysisLog.length > 0 ? analysisLog[0].step : "Wait for coach recommendation..."}</span>
            </div>
          </div>
          <button onClick={() => setIsContextExpanded(!isContextExpanded)} className="text-[8px] font-black uppercase tracking-widest text-slate-300 hover:text-slate-900 transition-colors flex items-center gap-1 shrink-0 ml-4">{isContextExpanded ? 'Collapse' : 'Session Context'}</button>
      </div>

      <main className="flex-1 flex overflow-hidden relative">
        {/* LEFT: COPILOT (Light Grey) */}
        <section className="flex flex-col bg-[#EEF2F6] border-r border-slate-300/70 overflow-hidden relative" style={{ width: `${copilotWidth}%` }}>
            <div className="h-12 border-b border-slate-300/50 flex items-center px-6 justify-between bg-[#F4F7FA]">
                <div className="flex items-center gap-3">
                    <div className="w-2 h-2 bg-slate-900 rounded-full animate-pulse"></div>
                    <span className="text-[9px] font-black uppercase tracking-[0.3em] text-slate-900">Analysis Coach</span>
                </div>
            </div>
            <div className="flex-1 overflow-y-auto p-6 space-y-8 scroll-smooth">
                {chatLog.length === 0 && (
                    <div className="h-full flex flex-col items-center justify-center space-y-3 opacity-20">
                        <span className="text-2xl italic font-black text-slate-900">aiR ready.</span>
                        <p className="text-[8px] font-black uppercase tracking-[0.4em] text-slate-400 text-center">Grounded in R & tidyverse<br/>System online</p>
                    </div>
                )}
                {chatLog.map((m, i) => {
                    const isUser = m.role === 'user';
                    const sr = m.structured_response;
                    const rCode = normalizeRCode(m.code || (sr ? sr.code : extractRCode(m.text, m.intent)));
                    let renderedText: React.ReactNode = m.text;
                    
                    if (!isUser && sr && sr.response_type === 'analysis_step') {
                        renderedText = (
                            <div className="space-y-4">
                                {sr.what && <><span className="coach-header block text-xs font-bold text-slate-800">What we’re doing</span><div className="whitespace-pre-wrap text-slate-600">{sr.what}</div></>}
                                {sr.why && <><span className="coach-header block text-xs font-bold text-slate-800 mt-4">Why</span><div className="whitespace-pre-wrap text-slate-600">{sr.why}</div></>}
                                {sr.interpretation && <><span className="coach-header block text-xs font-bold text-emerald-600 mt-6 border-t border-emerald-100 pt-4">Interpretation</span><div className="coach-interpretation whitespace-pre-wrap text-slate-600 bg-emerald-50 p-4 rounded-lg border border-emerald-100">{sr.interpretation}</div></>}
                                {sr.next_step && <><span className="coach-header block text-xs font-bold text-indigo-600 mt-6 border-t border-indigo-100 pt-4">Next Step</span><div className="whitespace-pre-wrap text-slate-600">{sr.next_step}</div></>}
                            </div>
                        );
                    }

                    return (
                        <div key={i} className={`flex flex-col ${isUser ? 'items-end' : 'items-start'}`}>
                            <div className={`p-6 rounded-[2rem] text-sm leading-relaxed max-w-[90%] border shadow-sm transition-all duration-500 relative group/msg ${isUser ? 'bg-[#F7F9FC] border-slate-300 text-slate-900 font-bold rounded-tr-none' : 'bg-[#FAFBFD] border-slate-300/70 text-slate-700 rounded-tl-none'}`}>
                                {m.groundingType && <span className="block mb-2 text-[7px] font-black uppercase tracking-widest text-emerald-500 opacity-60">Grounded: {m.groundingType}</span>}
                                {m.executed && <span className="block mb-2 text-[7px] font-black uppercase tracking-widest text-blue-500 opacity-60">R Copilot auto-ran code</span>}
                                <div className="whitespace-pre-wrap">{renderedText}</div>
                                <button onClick={() => copyToClipboard(m.text, 'Message')} className="absolute -right-2 -top-2 opacity-0 group-hover/msg:opacity-100 p-1.5 bg-white border border-slate-300 rounded-full shadow-lg text-slate-400 hover:text-slate-900 transition-all hover:scale-110"><svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M8 5H6a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2v-1M8 5a2 2 0 002 2h2a2 2 0 002-2M8 5a2 2 0 012-2h2a2 2 0 012 2m0 0h2a2 2 0 012 2v3m2 4H10m0 0l3-3m-3 3l3 3"></path></svg></button>
                            </div>
                            
                            {m.role === 'ai' && rCode && (
                                <div className="mt-4 w-full max-w-[95%] bg-slate-900 rounded-[2rem] p-8 shadow-2xl space-y-6 transform transition-all border-4 border-white">
                                    <pre className="text-[12px] font-mono text-blue-100 overflow-x-auto leading-relaxed custom-scrollbar"><code>{rCode}</code></pre>
                                    <div className="flex gap-3 pt-2">
                                        <button data-testid="send-to-console" onClick={() => executeR(rCode!, true, 'R copilot (manual)')} className="flex-1 py-4 bg-white text-slate-900 rounded-full text-[10px] font-black uppercase tracking-[0.2em] transition-all hover:bg-blue-50 hover:scale-[1.02] active:scale-95 flex items-center justify-center gap-2">
                                            {m.executed ? "Run Again" : "Send to Console"}
                                            <svg className="w-3 h-3" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" d="M13 5l7 7m0 0l-7 7m7-7H3"></path></svg>
                                        </button>
                                        <button onClick={() => copyToClipboard(rCode!, 'Code')} className="px-5 py-4 bg-slate-800 text-slate-400 rounded-full text-[9px] font-black uppercase tracking-widest hover:text-white transition-all">Copy</button>
                                    </div>
                                </div>
                            )}
                        </div>
                    );
                })}
                {isAiLoading && <div className="flex gap-1.5 p-4"><div className="w-1 h-1 bg-slate-300 rounded-full animate-bounce"></div><div className="w-1 h-1 bg-slate-300 rounded-full animate-bounce [animation-delay:0.2s]"></div><div className="w-1 h-1 bg-slate-300 rounded-full animate-bounce [animation-delay:0.4s]"></div></div>}
                <div ref={chatBottomRef} className="h-px w-full shrink-0" />
            </div>
            <form onSubmit={onChat} className="p-6 bg-[#F4F7FA] border-t border-slate-300/60 shadow-inner">
                <div className="relative">
                    <input data-testid="chat-input" disabled={isAiLoading} className="w-full bg-[#FBFCFE] border border-slate-300 p-5 pr-14 rounded-[1.5rem] text-sm outline-none focus:bg-white focus:border-slate-900 transition-all font-bold placeholder:text-slate-300" placeholder={isAiLoading ? "Processing..." : "Ask R copilot..."} value={chatInput} onChange={e => setChatInput(e.target.value)} />
                    <button data-testid="chat-submit" type="submit" className="absolute right-3 top-1/2 -translate-y-1/2 w-9 h-9 bg-slate-900 text-white rounded-xl flex items-center justify-center transition-all hover:scale-110 active:scale-90"><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" d="M5 10l7-7m0 0l7 7m-7-7v18"></path></svg></button>
                </div>
            </form>
        </section>

        <div className="w-[1px] bg-slate-200 relative z-10 hover:bg-slate-900 transition-colors cursor-col-resize group">
            <div className="absolute inset-y-0 -left-2 -right-2 z-20" onMouseDown={() => { activeResizer.current = 'copilot'; document.body.style.cursor = 'col-resize'; }} />
        </div>

        {/* CENTER: CONSOLE (Grey) */}
        <section className="flex-1 flex flex-col bg-[#ECEFF3] overflow-hidden">
            <div className="h-12 border-b border-slate-200 bg-[#E2E8F0] flex items-center px-8 justify-between shrink-0">
                <div className="flex items-center gap-3">
                    <svg className="w-3.5 h-3.5 text-slate-400" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M8 9l3 3-3 3m5 0h3M5 20h14a2 2 0 002-2V6a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"></path></svg>
                    <span className="text-[9px] font-black uppercase tracking-[0.3em] text-slate-500">R Console</span>
                </div>
                <div className="flex items-center gap-6">
                    <span className="text-[8px] font-black text-emerald-700/60 uppercase tracking-tighter">Status: Active ({lastRunTime})</span>
                    <button onClick={() => setConsoleLog([])} className="text-slate-400 hover:text-slate-700 transition-colors"><svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="2.5" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"></path></svg></button>
                </div>
            </div>
            <div className="flex-1 overflow-y-auto p-10 font-mono text-[13px] leading-relaxed text-slate-800 scroll-smooth custom-scrollbar">
                {consoleLog.map((line, i) => (
                    <div key={i} className={`mb-6 ${line.type === 'input' ? 'text-blue-900 bg-blue-50 p-4 rounded-xl border-l-2 border-blue-400 relative group/line' : line.type === 'error' ? 'text-rose-800 bg-rose-50 p-6 rounded-2xl border-l-2 border-rose-400' : line.type === 'system' ? 'text-slate-400 text-[9px] font-black uppercase tracking-[0.4em] py-8 text-center border-y border-slate-200 my-4' : 'pl-6 text-slate-700'} whitespace-pre-wrap`}>
                        {line.type === 'input' && <span className="absolute -top-3 left-4 px-2 bg-[#ECEFF3] text-[7px] font-black uppercase tracking-widest text-slate-500">{line.prov}</span>}
                        {typeof line.t === 'string' ? line.t : JSON.stringify(line.t)}
                    </div>
                ))}
                {consoleLog.length === 0 && <div className="h-full flex items-center justify-center text-slate-300 italic font-black uppercase tracking-[0.8em] text-xs">Environment Ready</div>}
                <div ref={consoleBottomRef} className="h-px w-full shrink-0" />
            </div>
            <div className="p-6 bg-[#E2E8F0] border-t border-slate-200 flex items-center gap-4 shadow-2xl">
                <span className="text-blue-700 font-bold font-mono text-xl">{'>'}</span>
                <input data-testid="repl-input" className="flex-1 bg-white border border-slate-300 p-4 rounded-xl outline-none text-slate-900 font-mono text-sm placeholder:text-slate-300 focus:border-blue-500 transition-all shadow-inner" placeholder="Submit R code..." value={replInput} onChange={e => setReplInput(e.target.value)} onKeyDown={e => {
                    if (e.key === 'Enter') { e.preventDefault(); executeR(replInput, false, 'You'); }
                    else if (e.key === 'ArrowUp') { e.preventDefault(); const n = historyIndex + 1; if (n < commandHistory.length) { setHistoryIndex(n); setReplInput(commandHistory[n]); } }
                    else if (e.key === 'ArrowDown') { e.preventDefault(); const n = historyIndex - 1; if (n >= 0) { setHistoryIndex(n); setReplInput(commandHistory[n]); } else { setHistoryIndex(-1); setReplInput(''); } }
                }} />
                <button data-testid="repl-submit" onClick={() => executeR(replInput, false, 'You')} className="w-12 h-12 bg-blue-600 text-white rounded-xl flex items-center justify-center transition-all hover:bg-blue-500 active:scale-95 shadow-lg"><svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="4" d="M13 5l7 7m0 0l-7 7m7-7H3"></path></svg></button>
            </div>
        </section>

        <div className="w-[1px] bg-slate-200 relative z-10 hover:bg-slate-900 transition-colors cursor-col-resize group">
            <div className="absolute inset-y-0 -left-2 -right-2 z-20" onMouseDown={() => { activeResizer.current = 'right'; document.body.style.cursor = 'col-resize'; }} />
        </div>

        {/* RIGHT: UTILITY (Dark Grey) */}
        <aside className="bg-[#CBD5E1] flex flex-col shrink-0 overflow-hidden border-l border-slate-400/50" style={{ width: `${rightWidth}%` }}>
            <div className="h-12 border-b border-slate-400/40 flex px-4 bg-[#D6DEE8] sticky top-0 z-10 shrink-0">
                {(['plots', 'env', 'history'] as const).map(t => (
                    <button key={t} onClick={() => setActiveRightTab(t)} className={`flex-1 text-[9px] font-black uppercase tracking-[0.2em] transition-all relative ${activeRightTab === t ? 'text-slate-900' : 'text-slate-500 hover:text-slate-700'}`}>
                        {t}
                        {activeRightTab === t && <div className="absolute bottom-0 left-4 right-4 h-1 bg-slate-900 rounded-t-full"></div>}
                    </button>
                ))}
            </div>
            
            <div className="flex-1 overflow-y-auto p-6 space-y-6 custom-scrollbar">
                {activeRightTab === 'plots' && (
                    <div className="space-y-6">
                        <div className="flex justify-between items-center px-2">
                            <h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-600">Current Plots</h3>
                            {plots.length > 0 && <button onClick={() => setPlots([])} className="text-[8px] font-black text-rose-500 hover:text-rose-700 transition-colors uppercase tracking-widest">Clear All</button>}
                        </div>
                        {plots.length === 0 ? (
                            <div className="bg-[#E2E8F0] border border-slate-300 rounded-[2rem] p-12 text-center shadow-sm">
                                <p className="text-[9px] font-black text-slate-500 uppercase tracking-widest">No Visuals Generated</p>
                            </div>
                        ) : plots.map((url, i) => (
                            <div key={i} className="group relative bg-[#E2E8F0] p-4 rounded-[2.5rem] border border-slate-300 shadow-lg transition-all hover:shadow-2xl">
                                <img src={url.startsWith('http') ? url : `${api.API_BASE}${url}`} alt="Plot" className="w-full rounded-[2rem] border border-slate-50" />
                                <button onClick={() => window.open(url)} className="absolute top-8 right-8 bg-slate-900 text-white p-4 rounded-full opacity-0 group-hover:opacity-100 transition-all hover:scale-110 shadow-2xl"><svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path strokeLinecap="round" strokeLinejoin="round" strokeWidth="3" d="M4 16v1a2 2 0 002 2h12a2 2 0 002-2v-1m-4-4l-4 4m0 0l-4-4m4 4V4"></path></svg></button>
                            </div>
                        ))}
                    </div>
                )}
                {activeRightTab === 'env' && (
                    <div className="space-y-3">
                        <div className="px-2 mb-4"><h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-600">Global Environment</h3></div>
                        {objects.length === 0 ? <div className="p-8 text-center text-[9px] font-black text-slate-500 uppercase tracking-widest bg-[#E2E8F0] border border-slate-300 rounded-3xl">Empty</div> : objects.map((obj, i) => (
                            <div key={i} className="bg-[#E2E8F0] border border-slate-300 p-5 rounded-[1.5rem] shadow-sm hover:border-slate-900 transition-all group flex flex-col gap-1">
                                <p className="text-[11px] font-black text-slate-900 uppercase truncate">{obj.name}</p>
                                <div className="flex justify-between items-center opacity-50 group-hover:opacity-80 transition-opacity">
                                    <span className="text-[9px] font-bold uppercase">{obj.type}</span>
                                    <span className="text-[8px] italic">{obj.details}</span>
                                </div>
                            </div>
                        ))}
                    </div>
                )}
                {activeRightTab === 'history' && (
                    <div className="space-y-4">
                        <div className="px-2 mb-4"><h3 className="text-[10px] font-black uppercase tracking-[0.2em] text-slate-600">Command History</h3></div>
                        {history.length === 0 ? <div className="p-8 text-center text-[9px] font-black text-slate-500 uppercase tracking-widest">None</div> : history.map((e, i) => (
                            <div key={i} className="border-l-2 border-slate-400 pl-4 py-1 group hover:border-slate-900 transition-all">
                                <p className="text-[8px] font-black uppercase text-slate-500 group-hover:text-slate-700 transition-colors mb-1">{e.authorship}</p>
                                <code className="text-slate-700 text-[10px] block truncate font-mono bg-[#E2E8F0] border border-slate-300 p-2 rounded-lg group-hover:text-slate-900 transition-colors">{e.code}</code>
                            </div>
                        ))}
                    </div>
                )}
            </div>
        </aside>
      </main>
    </div>
  );
}

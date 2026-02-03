"use client";

import React, { useState, useEffect, useRef } from "react";

// Standard SVG Icons (Modern 2026 Style)
const Icons = {
  Terminal: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polyline points="4 17 10 11 4 5"></polyline><line x1="12" y1="19" x2="20" y2="19"></line></svg>
  ),
  Users: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M17 21v-2a4 4 0 0 0-4-4H5a4 4 0 0 0-4 4v2"></path><circle cx="9" cy="7" r="4"></circle><path d="M23 21v-2a4 4 0 0 0-3-3.87"></path><path d="M16 3.13a4 4 0 0 1 0 7.75"></path></svg>
  ),
  Search: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
  ),
  Plus: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><line x1="12" y1="5" x2="12" y2="19"></line><line x1="5" y1="12" x2="19" y2="12"></line></svg>
  ),
  Power: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><path d="M18.36 6.64a9 9 0 1 1-12.73 0"></path><line x1="12" y1="2" x2="12" y2="12"></line></svg>
  ),
  Zap: () => (
    <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
  )
};

export default function Dashboard() {
  const [logs, setLogs] = useState<any[]>([]);
  const [phone, setPhone] = useState("");
  const [apiId, setApiId] = useState("");
  const [apiHash, setApiHash] = useState("");
  const [otp, setOtp] = useState("");
  const [isAuth, setIsAuth] = useState(false);
  const [step, setStep] = useState(1); // 1: Creds, 2: OTP

  const [sourceGroup, setSourceGroup] = useState("");
  const [targetGroup, setTargetGroup] = useState("");
  const [scrapedMembers, setScrapedMembers] = useState<any[]>([]);
  const [isScraping, setIsScraping] = useState(false);
  const [isAdding, setIsAdding] = useState(false);

  const [activeSection, setActiveSection] = useState("Dashboard");
  const [errorPrompt, setErrorPrompt] = useState<string | null>(null);
  const [wsStatus, setWsStatus] = useState<"connecting" | "connected" | "disconnected">("connecting");
  const logEndRef = useRef<HTMLDivElement>(null);

  const API_BASE = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");
  const WS_BASE = API_BASE.startsWith("https")
    ? API_BASE.replace("https", "wss")
    : API_BASE.replace("http", "ws");

  useEffect(() => {
    let ws: WebSocket;
    let reconnectTimer: any;

    const connect = () => {
      setWsStatus("connecting");
      ws = new WebSocket(`${WS_BASE}/ws/logs`);
      ws.onopen = () => setWsStatus("connected");
      ws.onmessage = (event) => {
        const data = JSON.parse(event.data);
        setLogs((prev) => {
          const newLogs = [...prev, data];
          return newLogs.slice(-200); // Keep buffer manageable
        });
      };
      ws.onclose = () => {
        setWsStatus("disconnected");
        reconnectTimer = setTimeout(connect, 3000);
      };
      ws.onerror = () => ws.close();
    };

    connect();
    return () => {
      clearTimeout(reconnectTimer);
      if (ws) ws.close();
    };
  }, [WS_BASE]);

  useEffect(() => {
    logEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [logs]);

  // Check for existing session
  const checkSession = async () => {
    if (!phone || !apiId || !apiHash) {
      setErrorPrompt("Please enter Phone, API ID, and Hash to resume session.");
      return;
    }
    setErrorPrompt(null);
    try {
      const res = await fetch(`${API_BASE}/auth/session`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, api_id: apiId, api_hash: apiHash })
      });
      if (res.ok) {
        setIsAuth(true);
        setErrorPrompt(null); // Clear any previous errors
      } else {
        const err = await res.json();
        setErrorPrompt(err.detail || "No active session found. Please login.");
      }
    } catch (e) {
      setErrorPrompt("Connection Error: Could not check session.");
    }
  };

  const handleSendCode = async () => {
    setErrorPrompt(null);
    try {
      const res = await fetch(`${API_BASE}/auth/send-code`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, api_id: apiId, api_hash: apiHash })
      });
      if (res.ok) {
        setStep(2);
      } else {
        const err = await res.json();
        setErrorPrompt(err.detail || "Failed to send code");
      }
    } catch (e) {
      setErrorPrompt("Connection Error: Check if API is running and URL is correct.");
      console.error(e);
    }
  };

  const handleVerify = async () => {
    setErrorPrompt(null);
    try {
      const res = await fetch(`${API_BASE}/auth/verify`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ phone, code: otp })
      });
      if (res.ok) {
        setIsAuth(true);
      } else {
        const err = await res.json();
        setErrorPrompt(err.detail || "Authentication failed. Check your code.");
      }
    } catch (e) {
      setErrorPrompt("Connection Error during verification.");
      console.error(e);
    }
  };

  const handleScrape = async () => {
    setIsScraping(true);
    setErrorPrompt(null);
    setScrapedMembers([]);

    try {
      // 1. Start the scrape job
      const res = await fetch(`${API_BASE}/scrape?phone=${phone}&group_link=${sourceGroup}`, { method: "POST" });
      const data = await res.json();

      if (!res.ok) {
        throw new Error(data.detail || "Failed to start scraping");
      }

      // 2. Poll for results
      const pollInterval = setInterval(async () => {
        try {
          const pollRes = await fetch(`${API_BASE}/scrape/results?phone=${phone}`);
          const pollData = await pollRes.json();

          if (pollData.status === "completed") {
            clearInterval(pollInterval);
            setScrapedMembers(pollData.members);
            setIsScraping(false);
          } else if (pollData.status === "error") {
            clearInterval(pollInterval);
            setIsScraping(false);
            setErrorPrompt("Scraping failed during background process. Check logs.");
          }
          // If "scraping" or "idle", keep polling...
        } catch (e) {
          console.error("Polling error", e);
        }
      }, 2000);

    } catch (e: any) {
      setErrorPrompt(e.message || "Connection Error during scraping.");
      setIsScraping(false);
    }
  };

  const handleAdd = async () => {
    setIsAdding(true);
    setErrorPrompt(null);
    try {
      const res = await fetch(`${API_BASE}/add?target_group=${targetGroup}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(scrapedMembers)
      });
      if (!res.ok) {
        const data = await res.json();
        setErrorPrompt(data.detail || "Adding failed.");
      }
    } catch (e) {
      setErrorPrompt("Connection Error during adding.");
    } finally {
      setIsAdding(false);
    }
  };

  return (
    <div className="flex h-screen w-full bg-[#030712] text-gray-100 overflow-hidden">
      {/* Sidebar */}
      <div className="w-16 md:w-64 border-r border-white/5 bg-gray-900/50 backdrop-blur-xl flex flex-col items-center py-6">
        <div className="flex items-center gap-3 px-4 mb-10 w-full justify-center md:justify-start">
          <div className="w-8 h-8 rounded-lg bg-blue-600 flex items-center justify-center shadow-lg shadow-blue-600/20">
            <Icons.Zap />
          </div>
          <span className="hidden md:block font-bold text-lg tracking-tight">SWIFT ADDER</span>
        </div>

        <nav className="flex-1 w-full space-y-2 px-2">
          {["Dashboard", "Accounts", "Groups", "Settings"].map((item) => (
            <div
              key={item}
              onClick={() => setActiveSection(item)}
              className={`flex items-center gap-3 px-3 py-2 rounded-xl cursor-pointer transition-all ${activeSection === item ? "bg-blue-600/10 text-blue-400" : "hover:bg-white/5 text-gray-400"}`}
            >
              {item === "Dashboard" && <Icons.Zap />}
              {item === "Accounts" && <Icons.Users />}
              {item === "Groups" && <Icons.Search />}
              {item === "Settings" && <Icons.Power />}
              <span className="hidden md:block font-medium">{item}</span>
            </div>
          ))}
        </nav>
      </div>

      {/* Main Content */}
      <div className="flex-1 flex flex-col h-full overflow-y-auto">
        <header className="h-16 border-b border-white/5 flex items-center justify-between px-8 bg-gray-900/30 backdrop-blur-md sticky top-0 z-10">
          <h2 className="text-xl font-semibold">Command Center</h2>
          <div className="flex items-center gap-4">
            <div className="flex items-center gap-2 px-3 py-1 bg-green-500/10 border border-green-500/20 rounded-full">
              <div className="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
              <span className="text-xs font-medium text-green-500 uppercase tracking-wider">System Online</span>
            </div>
          </div>
        </header>

        <main className="p-8 grid grid-cols-1 xl:grid-cols-12 gap-6">
          {/* Auth Card */}
          <div className="xl:col-span-4 space-y-6">
            <div className="glass-card p-6 rounded-3xl relative overflow-hidden group">
              <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:scale-110 transition-transform">
                <Icons.Users />
              </div>
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <Icons.Plus /> {isAuth ? "Account Active" : "Connect Account"}
              </h3>

              {!isAuth ? (
                <div className="space-y-4">
                  {errorPrompt && (
                    <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-xl text-red-500 text-xs font-mono">
                      {errorPrompt}
                    </div>
                  )}
                  {step === 1 ? (
                    <>
                      <input type="text" placeholder="Phone (+123...)" value={phone} onChange={e => setPhone(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-blue-600 transition-all font-mono text-sm" />
                      <input type="text" placeholder="API ID" value={apiId} onChange={e => setApiId(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-blue-600 transition-all font-mono text-sm" />
                      <input type="password" placeholder="API Hash" value={apiHash} onChange={e => setApiHash(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-blue-600 transition-all font-mono text-sm" />
                      <div className="flex gap-2">
                        <button onClick={handleSendCode} className="flex-1 py-3 bg-blue-600 hover:bg-blue-500 rounded-xl font-bold transition-all shadow-lg shadow-blue-600/30 active:scale-95">Send OTP Code</button>
                        <button onClick={checkSession} className="px-4 py-3 bg-white/5 hover:bg-white/10 border border-white/10 rounded-xl font-bold transition-all text-xs uppercase tracking-wider" title="Resume Session">Resume</button>
                      </div>
                    </>
                  ) : (
                    <>
                      <input type="text" placeholder="Verification Code" value={otp} onChange={e => setOtp(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-blue-600 transition-all font-mono text-center text-lg tracking-[0.5em]" />
                      <button onClick={handleVerify} className="w-full py-3 bg-blue-600 hover:bg-blue-500 rounded-xl font-bold transition-all shadow-lg shadow-blue-600/30 active:scale-95">Verify & Connect</button>
                      <button onClick={() => setStep(1)} className="w-full text-[10px] text-gray-500 uppercase font-bold hover:text-gray-400 mt-2">← Back to credentials</button>
                    </>
                  )}
                </div>
              ) : (
                <div className="text-center py-6">
                  <div className="w-20 h-20 rounded-full bg-green-500/20 flex items-center justify-center mx-auto mb-4 border border-green-500/30">
                    <Icons.Plus />
                  </div>
                  <p className="font-mono text-sm text-green-400">{phone}</p>
                  <p className="text-xs text-gray-500 mt-1 uppercase">Authenticated</p>
                </div>
              )}
            </div>

            {/* Task Controls */}
            <div className="glass-card p-6 rounded-3xl">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <Icons.Power /> Member Scraper
              </h3>
              <div className="space-y-4">
                <input type="text" placeholder="Source Group (e.g. t.me/group)" value={sourceGroup} onChange={e => setSourceGroup(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-blue-600 transition-all text-sm" />
                <button onClick={handleScrape} disabled={isScraping || !isAuth} className="w-full py-3 border border-white/10 hover:bg-white/5 rounded-xl font-bold transition-all flex items-center justify-center gap-2 group disabled:opacity-50">
                  {isScraping ? <div className="w-4 h-4 border-2 border-white/30 border-t-white rounded-full animate-spin"></div> : <Icons.Search />}
                  Scrape Members
                </button>
              </div>
            </div>

            <div className="glass-card p-6 rounded-3xl">
              <h3 className="text-lg font-bold mb-4 flex items-center gap-2">
                <Icons.Terminal /> Swift Adder
              </h3>
              <div className="space-y-4">
                <input type="text" placeholder="Target Group Username" value={targetGroup} onChange={e => setTargetGroup(e.target.value)} className="w-full bg-black/40 border border-white/10 rounded-xl px-4 py-3 focus:outline-none focus:border-blue-600 transition-all text-sm" />
                <button onClick={handleAdd} disabled={isAdding || scrapedMembers.length === 0} className="w-full py-3 bg-gradient-to-r from-blue-600 to-indigo-600 hover:from-blue-500 hover:to-indigo-500 rounded-xl font-bold transition-all shadow-lg shadow-blue-600/30 flex items-center justify-center gap-2 disabled:opacity-50">
                  {isAdding ? <div className="w-4 h-4 border-2 border-primary-foreground/30 border-t-primary-foreground rounded-full animate-spin"></div> : <Icons.Plus />}
                  Start Swifting
                </button>
                <p className="text-[10px] text-gray-500 text-center uppercase tracking-widest leading-relaxed">Ensure delay settings match 2026 API standards to avoid limits</p>
              </div>
            </div>
          </div>

          {/* Results & Logs */}
          <div className="xl:col-span-8 space-y-6">
            {/* Stats Row */}
            <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
              {[
                { label: "Scraped", val: scrapedMembers.length, color: "text-blue-400" },
                { label: "Added", val: logs.filter(l => l.message.includes("Added")).length, color: "text-green-400" },
                { label: "Errors", val: logs.filter(l => l.level === "ERROR").length, color: "text-red-400" }
              ].map(stat => (
                <div key={stat.label} className="glass-card p-4 rounded-2xl flex flex-col justify-center">
                  <span className="text-xs uppercase tracking-wider text-gray-500 font-semibold">{stat.label}</span>
                  <span className={`text-3xl font-bold mt-1 ${stat.color}`}>{stat.val}</span>
                </div>
              ))}
            </div>

            {/* Terminal Log */}
            <div className="glass-card rounded-3xl flex flex-col h-[500px] overflow-hidden border border-white/5">
              <div className="bg-white/5 px-6 py-3 border-b border-white/5 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <Icons.Terminal />
                  <span className="text-xs font-mono font-bold tracking-widest text-gray-400">REALTIME_LOG_STREAM</span>
                  <div className={`flex items-center gap-1.5 ml-4 px-2 py-0.5 rounded-full border text-[9px] font-bold uppercase tracking-tighter ${wsStatus === "connected" ? "bg-green-500/10 border-green-500/20 text-green-500" :
                    wsStatus === "connecting" ? "bg-yellow-500/10 border-yellow-500/20 text-yellow-500 animate-pulse" :
                      "bg-red-500/10 border-red-500/20 text-red-500"
                    }`}>
                    <div className={`w-1.5 h-1.5 rounded-full ${wsStatus === "connected" ? "bg-green-500" : wsStatus === "connecting" ? "bg-yellow-500" : "bg-red-500"}`}></div>
                    {wsStatus}
                  </div>
                </div>
                <button onClick={() => setLogs([])} className="text-[10px] uppercase font-bold text-gray-500 hover:text-white transition-colors">Clear Buffer</button>
              </div>
              <div className="flex-1 p-6 font-mono text-xs overflow-y-auto bg-black/20 custom-scrollbar">
                {logs.length === 0 && <div className="text-gray-600 animate-pulse-subtle">Waiting for logs...</div>}
                {logs.map((log, i) => (
                  <div key={i} className="mb-2 flex gap-3 leading-relaxed">
                    <span className="text-gray-600 shrink-0">[{new Date(log.timestamp).toLocaleTimeString()}]</span>
                    <span className={`shrink-0 font-bold ${log.level === "ERROR" ? "text-red-500" : log.level === "WARNING" ? "text-yellow-500" : "text-blue-500"}`}>{log.level}</span>
                    <span className="text-gray-300 break-all">{log.message}</span>
                  </div>
                ))}
                <div ref={logEndRef} />
              </div>
            </div>

            {/* Member Preview */}
            <div className="glass-card rounded-3xl p-6">
              <h4 className="text-sm font-bold uppercase tracking-widest text-gray-500 mb-4">Member Preview</h4>
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {scrapedMembers.map((m, i) => (
                  <div key={i} className="bg-white/5 rounded-xl p-2 border border-white/5 flex items-center gap-2">
                    <div className="w-8 h-8 rounded-lg bg-gray-800 flex items-center justify-center text-[10px] font-bold text-blue-400 uppercase">{m.name?.[0] || "?"}</div>
                    <div className="min-w-0">
                      <p className="text-[10px] font-bold truncate">@{m.username}</p>
                      <p className="text-[8px] text-gray-500 truncate">{m.id}</p>
                    </div>
                  </div>
                ))}
                {scrapedMembers.length === 0 && <p className="col-span-4 text-center text-xs text-gray-600 py-4 uppercase tracking-[0.2em]">No members in queue</p>}
              </div>
            </div>
          </div>
        </main>

        <footer className="mt-auto py-6 px-8 text-center text-[10px] font-mono text-gray-600 uppercase tracking-[0.3em] border-t border-white/5">
          Swift Adder Engine v3.0 // 2026 Core Protocol
        </footer>
      </div>

      <style jsx global>{`
        .custom-scrollbar::-webkit-scrollbar {
          width: 4px;
        }
        .custom-scrollbar::-webkit-scrollbar-track {
          background: transparent;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb {
          background: rgba(255, 255, 255, 0.1);
          border-radius: 10px;
        }
        .custom-scrollbar::-webkit-scrollbar-thumb:hover {
          background: rgba(255, 255, 255, 0.2);
        }
      `}</style>
    </div>
  );
}

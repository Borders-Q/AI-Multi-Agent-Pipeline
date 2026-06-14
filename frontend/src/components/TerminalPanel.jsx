import React, { useEffect, useRef, useState } from 'react';
import { Terminal } from '@xterm/xterm';
import { FitAddon } from '@xterm/addon-fit';
import '@xterm/xterm/css/xterm.css';

const API_BASE = `http://${window.location.hostname}:8000`;
const WS_BASE = `ws://${window.location.hostname}:8000`;

export default function TerminalPanel({ workspacePath, active, queuedCommand, onQueuedCommandConsumed }) {
  const hostRef = useRef(null);
  const termRef = useRef(null);
  const fitRef = useRef(null);
  const socketRef = useRef(null);
  const sessionRef = useRef(null);
  const lineRef = useRef('');
  const readyRef = useRef(false);
  const [status, setStatus] = useState('idle');

  const writePrompt = () => {
    const cwd = workspacePath || '天韬（SkyT） workspace';
    termRef.current?.write(`\r\nPS ${cwd}> `);
  };

  const sendLine = (command) => {
    if (!socketRef.current || socketRef.current.readyState !== WebSocket.OPEN) return;
    socketRef.current.send(JSON.stringify({ type: 'stdin', data: `${command}\r\n` }));
  };

  useEffect(() => {
    if (!active || !hostRef.current || termRef.current) return undefined;

    const terminal = new Terminal({
      cursorBlink: true,
      fontFamily: 'Cascadia Mono, Consolas, monospace',
      fontSize: 13,
      lineHeight: 1.25,
      convertEol: true,
      theme: {
        background: '#0c0d10',
        foreground: '#e5e7eb',
        cursor: '#f8fafc',
        selectionBackground: '#314158',
        black: '#0f172a',
        blue: '#60a5fa',
        cyan: '#22d3ee',
        green: '#34d399',
        magenta: '#c084fc',
        red: '#fb7185',
        white: '#f8fafc',
        yellow: '#facc15',
      }
    });
    const fit = new FitAddon();
    terminal.loadAddon(fit);
    terminal.open(hostRef.current);
    fit.fit();
    termRef.current = terminal;
    fitRef.current = fit;

    terminal.write('天韬（SkyT） PowerShell 正在启动...\r\n');
    const onResize = () => fit.fit();
    window.addEventListener('resize', onResize);

    terminal.onData((data) => {
      if (!readyRef.current) return;
      if (data === '\r') {
        const command = lineRef.current;
        lineRef.current = '';
        terminal.write('\r\n');
        if (command.trim()) sendLine(command);
        else writePrompt();
        return;
      }
      if (data === '\u0003') {
        socketRef.current?.send(JSON.stringify({ type: 'stdin', data: '\u0003' }));
        terminal.write('^C');
        writePrompt();
        lineRef.current = '';
        return;
      }
      if (data === '\u007f') {
        if (lineRef.current.length > 0) {
          lineRef.current = lineRef.current.slice(0, -1);
          terminal.write('\b \b');
        }
        return;
      }
      if (data >= ' ') {
        lineRef.current += data;
        terminal.write(data);
      }
    });

    return () => {
      window.removeEventListener('resize', onResize);
      socketRef.current?.close();
      terminal.dispose();
      termRef.current = null;
      fitRef.current = null;
      readyRef.current = false;
    };
  }, [active]);

  useEffect(() => {
    if (!active || !termRef.current || socketRef.current) return undefined;
    let cancelled = false;

    async function connect() {
      setStatus('connecting');
      const res = await fetch(`${API_BASE}/api/terminal/sessions`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ cwd: workspacePath || undefined, shell: 'powershell' })
      });
      const session = await res.json();
      if (cancelled) return;
      sessionRef.current = session.session_id;

      const socket = new WebSocket(`${WS_BASE}/api/terminal/sessions/${session.session_id}`);
      socketRef.current = socket;
      socket.onopen = () => setStatus('connected');
      socket.onmessage = (event) => {
        const payload = JSON.parse(event.data);
        if (payload.type === 'ready') {
          readyRef.current = true;
          termRef.current?.write('已连接到 天韬（SkyT） PowerShell\r\n');
          writePrompt();
        } else if (payload.type === 'stdout' || payload.type === 'stderr') {
          termRef.current?.write(payload.data);
        } else if (payload.type === 'prompt') {
          writePrompt();
        } else if (payload.type === 'exit') {
          if (payload.code && payload.code !== 0) {
            termRef.current?.write(`\r\n[exit ${payload.code}]\r\n`);
          }
          setStatus('closed');
        } else if (payload.type === 'error') {
          termRef.current?.write(`\r\n[error] ${payload.data}\r\n`);
          setStatus('error');
        }
      };
      socket.onclose = () => setStatus('closed');
      socket.onerror = () => setStatus('error');
    }

    connect().catch((err) => {
      setStatus('error');
      termRef.current?.write(`\r\n终端启动失败：${err.message}\r\n`);
    });

    return () => {
      cancelled = true;
      if (sessionRef.current) {
        fetch(`${API_BASE}/api/terminal/sessions/${sessionRef.current}`, { method: 'DELETE' }).catch(() => {});
      }
    };
  }, [active, workspacePath]);

  useEffect(() => {
    if (!active || !queuedCommand || !readyRef.current) return;
    lineRef.current = queuedCommand;
    termRef.current?.write(queuedCommand);
    sendLine(queuedCommand);
    lineRef.current = '';
    onQueuedCommandConsumed?.();
  }, [active, queuedCommand, onQueuedCommandConsumed]);

  return (
    <div className="terminal-panel">
      <div className="terminal-status">
        <span className={`status-dot ${status}`} />
        PowerShell · {workspacePath || '默认 天韬（SkyT） 工作区'}
      </div>
      <div ref={hostRef} className="terminal-host" />
    </div>
  );
}

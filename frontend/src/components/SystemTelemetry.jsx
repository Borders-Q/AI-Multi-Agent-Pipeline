import React, { useState, useEffect } from 'react';
import { Activity, Cpu, HardDrive, Network } from 'lucide-react';

export default function SystemTelemetry() {
  const [telemetry, setTelemetry] = useState({
    cpu_usage: 0,
    ram_usage: 0,
    ram_total: 0,
    ram_used: 0,
    latency: 0
  });

  useEffect(() => {
    const fetchTelemetry = async () => {
      try {
        const startTime = Date.now();
        const res = await fetch(`http://${window.location.hostname}:8000/api/telemetry`);
        const latency = Date.now() - startTime;
        
        if (res.ok) {
          const data = await res.json();
          setTelemetry({ ...data, latency });
        }
      } catch (e) {
        // Silent fail for telemetry
      }
    };

    fetchTelemetry();
    const interval = setInterval(fetchTelemetry, 2000);
    return () => clearInterval(interval);
  }, []);

  return (
    <div style={{
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'space-between',
      padding: '4px 16px',
      backgroundColor: 'rgba(0,0,0,0.4)',
      borderBottom: '1px solid rgba(255,255,255,0.05)',
      fontSize: '0.75rem',
      color: '#00ff9d',
      fontFamily: 'monospace',
      height: '30px',
      backdropFilter: 'blur(10px)',
      boxShadow: '0 0 10px rgba(0,255,157,0.1)'
    }}>
      <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Activity size={12} className="animate-pulse" />
          <span>天韬（SkyT） OS [v3.0.0]</span>
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Network size={12} />
          <span>Cloud Router: Connected</span>
        </span>
      </div>
      
      <div style={{ display: 'flex', gap: '24px', alignItems: 'center' }}>
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Cpu size={12} />
          <span>NPU/CPU: {telemetry.cpu_usage.toFixed(1)}%</span>
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <HardDrive size={12} />
          <span>VRAM/RAM: {telemetry.ram_used}GB / {telemetry.ram_total}GB ({telemetry.ram_usage}%)</span>
        </span>
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Activity size={12} />
          <span>Ping: <span style={{ color: telemetry.latency < 50 ? '#00ff9d' : '#ffc107' }}>{telemetry.latency}ms</span></span>
        </span>
      </div>
    </div>
  );
}

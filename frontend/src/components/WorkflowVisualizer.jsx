import React, { useMemo } from 'react';
import { ReactFlow, Background, Controls, MarkerType } from '@xyflow/react';
import '@xyflow/react/dist/style.css';

// Cyberpunk / Glowing style definitions
const colors = {
  running: '#00ff9d', // Neon Green/Cyan for running
  done: '#b142ff',    // Neon Purple for done
  pending: '#4a4a4a', // Dark Gray for pending
  bg: 'transparent'
};

export default function WorkflowVisualizer({ activeWorkflow }) {
  const { nodes, edges } = useMemo(() => {
    if (!activeWorkflow || activeWorkflow.length === 0) {
      return { nodes: [], edges: [] };
    }

    const newNodes = [];
    const newEdges = [];

    activeWorkflow.forEach((wfNode, idx) => {
      let borderColor = colors.pending;
      let boxShadow = 'none';
      let textColor = 'var(--sys-color-on-surface-variant)';
      let animation = 'none';

      if (wfNode.state === 'running') {
        borderColor = colors.running;
        boxShadow = `0 0 20px ${colors.running}, inset 0 0 10px ${colors.running}`;
        textColor = colors.running;
        animation = 'pulse 1.5s infinite alternate';
      } else if (wfNode.state === 'done') {
        borderColor = colors.done;
        textColor = '#ffffff';
        boxShadow = `0 0 10px ${colors.done}`;
      }

      newNodes.push({
        id: `node-${idx}`,
        position: { x: 50, y: 50 + idx * 120 },
        data: { 
          label: (
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '4px' }}>
              <span style={{ fontSize: '0.7rem', textTransform: 'uppercase', opacity: 0.7 }}>
                {wfNode.state === 'running' ? 'EXECUTING' : (wfNode.state === 'done' ? 'COMPLETED' : 'STANDBY')}
              </span>
              <span style={{ fontFamily: 'monospace', fontWeight: 'bold', letterSpacing: '1px' }}>
                {wfNode.node}
              </span>
            </div>
          )
        },
        style: {
          padding: '12px 20px',
          borderRadius: '4px',
          border: `2px solid ${borderColor}`,
          backgroundColor: 'rgba(0, 0, 0, 0.7)',
          backdropFilter: 'blur(5px)',
          color: textColor,
          width: '240px',
          textAlign: 'center',
          boxShadow: boxShadow,
          transition: 'all 0.4s ease',
          animation: animation,
          textShadow: wfNode.state === 'running' ? `0 0 5px ${colors.running}` : 'none'
        }
      });

      if (idx > 0) {
        newEdges.push({
          id: `edge-${idx - 1}-${idx}`,
          source: `node-${idx - 1}`,
          target: `node-${idx}`,
          animated: wfNode.state === 'running',
          style: { 
            stroke: wfNode.state === 'running' ? colors.running : (wfNode.state === 'done' ? colors.done : colors.pending), 
            strokeWidth: wfNode.state === 'running' ? 3 : 2,
            opacity: 0.8,
            filter: wfNode.state === 'running' ? `drop-shadow(0 0 5px ${colors.running})` : 'none'
          },
          markerEnd: {
            type: MarkerType.ArrowClosed,
            color: wfNode.state === 'running' ? colors.running : (wfNode.state === 'done' ? colors.done : colors.pending),
          },
        });
      }
    });

    return { nodes: newNodes, edges: newEdges };
  }, [activeWorkflow]);

  if (nodes.length === 0) {
    return (
      <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', opacity: 0.3, fontFamily: 'monospace', color: 'var(--sys-color-primary)' }}>
        <div style={{ fontSize: '2rem', marginBottom: '16px' }}>⚡</div>
        <p>AWAITING NEURAL LINK...</p>
        <p style={{ fontSize: '0.8rem' }}>SYSTEM IDLE</p>
      </div>
    );
  }

  return (
    <div style={{ width: '100%', height: '100%', backgroundColor: 'rgba(0,0,0,0.5)', backgroundImage: 'radial-gradient(circle at center, rgba(177, 66, 255, 0.05) 0%, transparent 70%)' }}>
      <ReactFlow
        nodes={nodes}
        edges={edges}
        fitView
        attributionPosition="bottom-right"
        colorMode="dark"
      >
        <Background color="#333" gap={24} size={1} />
        <Controls showInteractive={false} style={{ fill: 'var(--sys-color-primary)' }} />
        <style>
          {`
            @keyframes pulse {
              from { box-shadow: 0 0 10px ${colors.running}, inset 0 0 5px ${colors.running}; }
              to { box-shadow: 0 0 30px ${colors.running}, inset 0 0 15px ${colors.running}; }
            }
          `}
        </style>
      </ReactFlow>
    </div>
  );
}

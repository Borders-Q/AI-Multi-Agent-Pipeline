import React, { useEffect, useRef } from 'react';
import mermaid from 'mermaid';

mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'loose',
});

const MermaidChart = ({ chart }) => {
  const containerRef = useRef(null);

  useEffect(() => {
    if (chart && containerRef.current) {
      mermaid.render(`mermaid-${Math.random().toString(36).substr(2, 9)}`, chart)
        .then((result) => {
          containerRef.current.innerHTML = result.svg;
        })
        .catch((error) => {
          console.error('Mermaid rendering error', error);
        });
    }
  }, [chart]);

  return <div ref={containerRef} className="mermaid-container" style={{ margin: '16px 0', padding: '16px', background: 'rgba(255,255,255,0.05)', borderRadius: '8px' }} />;
};

export default MermaidChart;

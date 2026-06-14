import React, { useEffect, useState } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { FileText, Copy, Check, Clock, Search } from 'lucide-react';

export default function Reports() {
  const [reports, setReports] = useState([]);
  const [selectedReport, setSelectedReport] = useState(null);
  const [copied, setCopied] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');

  useEffect(() => {
    fetch(`http://${window.location.hostname}:8000/api/reports`)
      .then(res => res.json())
      .then(data => {
        setReports(data.reports || []);
        if (data.reports && data.reports.length > 0) {
          setSelectedReport(data.reports[0]);
        }
      })
      .catch(e => console.error("Failed to load reports", e));
  }, []);

  const handleCopy = () => {
    if (selectedReport) {
      navigator.clipboard.writeText(selectedReport.content);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    }
  };

  const filteredReports = reports.filter(r => 
    r.title.toLowerCase().includes(searchQuery.toLowerCase())
  );

  return (
    <div style={{ padding: '32px', overflowY: 'hidden', height: '100%', boxSizing: 'border-box', display: 'flex', flexDirection: 'column' }}>
      
      {/* Header */}
      <div style={{ marginBottom: '24px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '16px' }}>
        <div>
          <h1 style={{ fontSize: '1.8rem', display: 'flex', alignItems: 'center', gap: '12px', margin: 0, color: '#cdd6f4' }}>
            <FileText size={28} color="#cba6f7" />
            报告中心 (Reports)
          </h1>
          <p style={{ color: '#a6adc8', margin: '8px 0 0', fontSize: '0.9rem' }}>
            浏览由 天韬（SkyT） 自动分析生成的结构化深度报告。
          </p>
        </div>
        
        <div style={{ position: 'relative', width: '300px' }}>
          <Search size={16} color="#a6adc8" style={{ position: 'absolute', left: '12px', top: '50%', transform: 'translateY(-50%)' }} />
          <input 
            type="text" 
            placeholder="搜索报告标题..." 
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
            style={{ width: '100%', padding: '8px 12px 8px 36px', background: 'rgba(30, 30, 46, 0.8)', border: '1px solid #313244', borderRadius: '8px', color: '#cdd6f4', outline: 'none', boxSizing: 'border-box' }}
          />
        </div>
      </div>

      <div style={{ display: 'flex', flex: 1, gap: '24px', overflow: 'hidden' }}>
        
        {/* List Panel (Left) */}
        <div style={{ 
          width: '350px', overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: '8px', paddingRight: '8px' 
        }}>
          {filteredReports.map((r, idx) => {
            const isSelected = selectedReport?.id === r.id;
            return (
              <div 
                key={idx} 
                onClick={() => setSelectedReport(r)}
                style={{ 
                  padding: '16px', borderRadius: '8px', cursor: 'pointer',
                  backgroundColor: isSelected ? 'rgba(203, 166, 247, 0.15)' : 'rgba(30, 30, 46, 0.6)',
                  borderTop: `1px solid ${isSelected ? '#cba6f7' : '#313244'}`,
                  borderRight: `1px solid ${isSelected ? '#cba6f7' : '#313244'}`,
                  borderBottom: `1px solid ${isSelected ? '#cba6f7' : '#313244'}`,
                  borderLeft: `4px solid ${isSelected ? '#cba6f7' : 'transparent'}`,
                  transition: 'all 0.2s'
                }}
              >
                <div style={{ fontSize: '1rem', fontWeight: 'bold', color: isSelected ? '#cba6f7' : '#cdd6f4', marginBottom: '8px', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                  {r.title}
                </div>
                <div style={{ fontSize: '0.8rem', color: '#a6adc8', display: 'flex', alignItems: 'center', gap: '4px' }}>
                  <Clock size={12} /> {new Date(r.created_at).toLocaleString()}
                </div>
              </div>
            );
          })}
          {filteredReports.length === 0 && (
            <div style={{ textAlign: 'center', padding: '48px', color: '#6c7086' }}>
              暂无报告...
            </div>
          )}
        </div>

        {/* Markdown Preview Panel (Right) */}
        <div className="markdown-body" style={{ 
          flex: 1, overflowY: 'auto', padding: '40px', position: 'relative',
          background: 'linear-gradient(135deg, rgba(30, 30, 46, 0.8), rgba(49, 50, 68, 0.6))',
          border: '1px solid #313244', borderRadius: '12px', backdropFilter: 'blur(10px)',
          color: '#cdd6f4'
        }}>
          {selectedReport ? (
            <div className="animate-fade-in" style={{ maxWidth: '900px', margin: '0 auto' }}>
              <button 
                onClick={handleCopy} 
                style={{ 
                  position: 'absolute', top: '24px', right: '24px', display: 'flex', alignItems: 'center', gap: '8px', 
                  padding: '8px 16px', borderRadius: '16px', background: copied ? 'rgba(166, 227, 161, 0.2)' : 'rgba(203, 166, 247, 0.2)',
                  color: copied ? '#a6e3a1' : '#cba6f7', border: 'none', cursor: 'pointer', transition: 'all 0.2s', fontWeight: 'bold'
                }}
              >
                {copied ? <Check size={16} /> : <Copy size={16} />}
                {copied ? '已复制' : '复制全文'}
              </button>
              
              <h1 style={{ borderBottom: '2px solid #313244', paddingBottom: '16px', marginBottom: '32px', color: '#cba6f7' }}>
                {selectedReport.title}
              </h1>
              
              <ReactMarkdown
                remarkPlugins={[remarkGfm]}
                components={{
                  code({ node, inline, className, children, ...props }) {
                    const match = /language-(\w+)/.exec(className || '')
                    return !inline && match ? (
                      <div style={{ borderRadius: '8px', overflow: 'hidden', margin: '24px 0', border: '1px solid #313244' }}>
                        <div style={{ backgroundColor: '#181825', padding: '8px 16px', fontSize: '0.8rem', color: '#a6adc8', borderBottom: '1px solid #313244', display: 'flex', justifyContent: 'space-between' }}>
                          <span>{match[1]}</span>
                        </div>
                        <SyntaxHighlighter
                          {...props}
                          children={String(children).replace(/\n$/, '')}
                          style={vscDarkPlus}
                          language={match[1]}
                          PreTag="div"
                          customStyle={{ margin: 0, borderTopLeftRadius: 0, borderTopRightRadius: 0, background: '#1e1e2e' }}
                          showLineNumbers={true}
                        />
                      </div>
                    ) : (
                      <code {...props} className={className} style={{ backgroundColor: 'rgba(203, 166, 247, 0.15)', color: '#cba6f7', padding: '2px 6px', borderRadius: '4px', fontSize: '0.9em' }}>
                        {children}
                      </code>
                    )
                  },
                  h2: ({node, ...props}) => <h2 style={{ color: '#89b4fa', marginTop: '32px', borderBottom: '1px solid #313244', paddingBottom: '8px' }} {...props} />,
                  h3: ({node, ...props}) => <h3 style={{ color: '#f5c2e7', marginTop: '24px' }} {...props} />,
                  a: ({node, ...props}) => <a style={{ color: '#89dceb', textDecoration: 'none' }} {...props} />,
                  blockquote: ({node, ...props}) => <blockquote style={{ borderLeft: '4px solid #cba6f7', margin: '16px 0', padding: '8px 16px', background: 'rgba(203, 166, 247, 0.1)', color: '#bac2de', borderRadius: '0 8px 8px 0' }} {...props} />,
                  table: ({node, ...props}) => <table style={{ width: '100%', borderCollapse: 'collapse', margin: '24px 0' }} {...props} />,
                  th: ({node, ...props}) => <th style={{ background: 'rgba(30, 30, 46, 0.8)', padding: '12px', border: '1px solid #313244', color: '#cba6f7' }} {...props} />,
                  td: ({node, ...props}) => <td style={{ padding: '12px', border: '1px solid #313244' }} {...props} />
                }}
              >
                {selectedReport.content}
              </ReactMarkdown>
            </div>
          ) : (
            <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: '#6c7086', flexDirection: 'column', gap: '16px' }}>
              <FileText size={48} style={{ opacity: 0.5 }} />
              <p>请在左侧选择报告以预览</p>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}

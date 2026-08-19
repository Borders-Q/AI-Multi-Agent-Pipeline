import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';

export default function CodeBlock(props) {
  return <SyntaxHighlighter {...props} style={vscDarkPlus} />;
}

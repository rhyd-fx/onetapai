"use client";

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

// Some models emit headers without the required space ("##Title") or stray
// bullet chars; normalize so GitHub-flavored markdown parses cleanly.
function normalize(md: string): string {
  return md
    .replace(/^(#{1,6})([^#\s])/gm, '$1 $2') // "##Title" -> "## Title"
    .replace(/\r\n/g, '\n');
}

export default function Markdown({ children }: { children: string }) {
  return (
    <div className="text-sm leading-relaxed [word-break:break-word]">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        components={{
          h1: ({ children }) => <h1 className="mb-1 mt-3 text-base font-bold text-white first:mt-0">{children}</h1>,
          h2: ({ children }) => <h2 className="mb-1 mt-3 text-[0.8rem] font-bold uppercase tracking-wide text-brand-red first:mt-0">{children}</h2>,
          h3: ({ children }) => <h3 className="mb-1 mt-2 text-sm font-semibold text-brand-blue first:mt-0">{children}</h3>,
          p: ({ children }) => <p className="my-1.5">{children}</p>,
          strong: ({ children }) => <strong className="font-semibold text-white">{children}</strong>,
          em: ({ children }) => <em className="italic text-white/90">{children}</em>,
          ul: ({ children }) => <ul className="my-1.5 ml-4 list-disc space-y-1 marker:text-brand-red">{children}</ul>,
          ol: ({ children }) => <ol className="my-1.5 ml-4 list-decimal space-y-1 marker:text-brand-red">{children}</ol>,
          li: ({ children }) => <li className="pl-1">{children}</li>,
          a: ({ children, href }) => (
            <a href={href} target="_blank" rel="noreferrer" className="text-brand-blue underline underline-offset-2">
              {children}
            </a>
          ),
          blockquote: ({ children }) => (
            <blockquote className="my-2 border-l-2 border-brand-red/60 pl-3 text-white/80">{children}</blockquote>
          ),
          hr: () => <hr className="my-3 border-line/60" />,
          code: ({ children }) => (
            <code className="rounded bg-ink-900/70 px-1.5 py-0.5 text-[0.8em] text-brand-blue">{children}</code>
          ),
          pre: ({ children }) => (
            <pre className="my-2 overflow-x-auto rounded-lg bg-ink-900/70 p-3 text-xs">{children}</pre>
          ),
          table: ({ children }) => (
            <div className="my-2 overflow-x-auto rounded-lg border border-line/60">
              <table className="w-full border-collapse text-xs">{children}</table>
            </div>
          ),
          thead: ({ children }) => <thead className="bg-ink-900/60">{children}</thead>,
          tr: ({ children }) => <tr className="border-b border-line/40 last:border-0">{children}</tr>,
          th: ({ children }) => <th className="px-2.5 py-1.5 text-left font-semibold text-white">{children}</th>,
          td: ({ children }) => <td className="px-2.5 py-1.5 align-top text-white/85">{children}</td>,
        }}
      >
        {normalize(children)}
      </ReactMarkdown>
    </div>
  );
}

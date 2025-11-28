import React from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';

interface Props {
    children: string;
}

export const MarkdownRenderer = ({ children }: Props) => {
    return (
        <div style={{ color: 'black', fontFamily: 'system-ui' }}>
            <ReactMarkdown remarkPlugins={[remarkGfm]}>{children}</ReactMarkdown>
        </div>
    );
};

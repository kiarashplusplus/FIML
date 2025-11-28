import React from 'react';
import Markdown from 'react-native-markdown-display';

interface Props {
    children: string;
}

export const MarkdownRenderer = ({ children }: Props) => {
    return <Markdown style={{ body: { color: 'black' } }}>{children}</Markdown>;
};

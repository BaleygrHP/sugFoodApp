"use client";
import React from 'react';
import { Restaurant } from '@/app/page';

interface AIMessageContentProps {
  text: string;
  restaurants: Restaurant[];
}

export default function AIMessageContent({ text, restaurants }: AIMessageContentProps) {
  // Format markdown text to JSX with proper styling
  const formatMarkdown = (text: string) => {
    const lines = text.split('\n').filter(line => line.trim());
    
    return (
      <div className="space-y-3">
        {lines.map((line, index) => {
          const trimmedLine = line.trim();
          
          // Skip empty lines
          if (!trimmedLine) return null;
          
          // Bullet point (starts with * or -)
          if (trimmedLine.match(/^[\*\-\•]\s+/)) {
            const content = trimmedLine.replace(/^[\*\-\•]\s+/, '').trim();
            
            // Parse content with bold text and other formatting
            const parts: React.ReactNode[] = [];
            let lastIndex = 0;
            const boldRegex = /\*\*(.*?)\*\*/g;
            let match;
            
            while ((match = boldRegex.exec(content)) !== null) {
              // Add text before bold
              if (match.index > lastIndex) {
                const beforeText = content.substring(lastIndex, match.index);
                parts.push(<span key={`text-${match.index}`}>{beforeText}</span>);
              }
              // Add bold text (restaurant name)
              parts.push(
                <strong key={`bold-${match.index}`} className="font-semibold text-primary-orange">
                  {match[1]}
                </strong>
              );
              lastIndex = match.index + match[0].length;
            }
            
            // Add remaining text
            if (lastIndex < content.length) {
              parts.push(<span key={`text-end`}>{content.substring(lastIndex)}</span>);
            }
            
            return (
              <div key={index} className="flex items-start gap-3">
                <span className="text-primary-orange mt-1.5 flex-shrink-0">•</span>
                <div className="flex-1">
                  <p className="text-sm text-neutral-800 leading-relaxed">
                    {parts.length > 0 ? parts : content}
                  </p>
                </div>
              </div>
            );
          } 
          // Regular paragraph
          else {
            // Parse bold text in paragraph
            const parts: React.ReactNode[] = [];
            let lastIndex = 0;
            const boldRegex = /\*\*(.*?)\*\*/g;
            let match;
            
            while ((match = boldRegex.exec(trimmedLine)) !== null) {
              // Add text before bold
              if (match.index > lastIndex) {
                const beforeText = trimmedLine.substring(lastIndex, match.index);
                parts.push(<span key={`text-${match.index}`}>{beforeText}</span>);
              }
              // Add bold text
              parts.push(
                <strong key={`bold-${match.index}`} className="font-semibold text-neutral-900">
                  {match[1]}
                </strong>
              );
              lastIndex = match.index + match[0].length;
            }
            
            // Add remaining text
            if (lastIndex < trimmedLine.length) {
              parts.push(<span key={`text-end`}>{trimmedLine.substring(lastIndex)}</span>);
            }
            
            return (
              <p key={index} className="text-sm text-neutral-800 leading-relaxed">
                {parts.length > 0 ? parts : trimmedLine}
              </p>
            );
          }
        })}
      </div>
    );
  };

  return formatMarkdown(text);
}


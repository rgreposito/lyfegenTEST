import React, { useState, useRef, useEffect } from 'react';
import { Send, MessageCircle, Bot, User, FileText, Sparkles } from 'lucide-react';
import { chatApi } from '../services/api';
import { ChatMessage, ChatResponse, Source } from '../types';
import toast from 'react-hot-toast';

interface ChatInterfaceProps {
  sessionId?: string;
  onSessionCreated?: (sessionId: string) => void;
}

const ChatInterface: React.FC<ChatInterfaceProps> = ({
  sessionId: initialSessionId,
  onSessionCreated,
}) => {
  const [sessionId, setSessionId] = useState<string | undefined>(initialSessionId);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [suggestions, setSuggestions] = useState<string[]>([]);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (initialSessionId) {
      loadSession(initialSessionId);
    } else {
      createNewSession();
    }
  }, [initialSessionId]);

  const createNewSession = async () => {
    try {
      const session = await chatApi.createSession('New Chat');
      setSessionId(session.session_id);
      setMessages([]);
      if (onSessionCreated) {
        onSessionCreated(session.session_id);
      }
    } catch (error: any) {
      toast.error('Failed to create chat session');
    }
  };

  const loadSession = async (id: string) => {
    try {
      const session = await chatApi.getSession(id);
      setMessages(session.messages);
    } catch (error: any) {
      toast.error('Failed to load chat session');
    }
  };

  const sendMessage = async () => {
    if (!inputMessage.trim() || !sessionId || isLoading) return;

    const userMessage: ChatMessage = {
      id: Date.now(),
      content: inputMessage,
      role: 'user',
      timestamp: new Date().toISOString(),
    };

    setMessages(prev => [...prev, userMessage]);
    setInputMessage('');
    setIsLoading(true);

    try {
      const response: ChatResponse = await chatApi.sendMessage({
        message: inputMessage,
        session_id: sessionId,
      });

      const assistantMessage: ChatMessage = {
        id: Date.now() + 1,
        content: response.response,
        role: 'assistant',
        timestamp: new Date().toISOString(),
      };

      setMessages(prev => [...prev, assistantMessage]);

      // Get follow-up suggestions
      if (response.sources.length > 0) {
        try {
          const suggestionsResponse = await chatApi.getSuggestions(sessionId, inputMessage);
          setSuggestions(suggestionsResponse.suggestions);
        } catch (error) {
          // Silently fail for suggestions
        }
      }

    } catch (error: any) {
      toast.error('Failed to send message');
      const errorMessage: ChatMessage = {
        id: Date.now() + 1,
        content: 'Sorry, I encountered an error. Please try again.',
        role: 'assistant',
        timestamp: new Date().toISOString(),
      };
      setMessages(prev => [...prev, errorMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  };

  const useSuggestion = (suggestion: string) => {
    setInputMessage(suggestion);
    setSuggestions([]);
  };

  const formatTimestamp = (timestamp: string) => {
    return new Date(timestamp).toLocaleTimeString([], { 
      hour: '2-digit', 
      minute: '2-digit' 
    });
  };

  const SourceCard: React.FC<{ source: Source }> = ({ source }) => (
    <div className="bg-gray-50 rounded-lg p-3 mb-2">
      <div className="flex items-center space-x-2 mb-1">
        <FileText className="h-4 w-4 text-gray-500" />
        <span className="text-sm font-medium text-gray-700">{source.filename}</span>
        <span className="text-xs text-gray-500">({source.document_type})</span>
      </div>
      <p className="text-sm text-gray-600">{source.content}</p>
      <div className="flex items-center justify-between mt-2">
        <span className="text-xs text-gray-500">
          Confidence: {Math.round(source.score * 100)}%
        </span>
      </div>
    </div>
  );

  return (
    <div className="flex flex-col h-full bg-white rounded-lg shadow-sm border">
      {/* Header */}
      <div className="flex items-center justify-between p-4 border-b">
        <div className="flex items-center space-x-2">
          <MessageCircle className="h-5 w-5 text-primary-600" />
          <h2 className="text-lg font-semibold text-gray-900">Document Chat</h2>
        </div>
        {sessionId && (
          <button
            onClick={createNewSession}
            className="text-sm text-primary-600 hover:text-primary-700 font-medium"
          >
            New Chat
          </button>
        )}
      </div>

      {/* Messages */}
      <div className="flex-1 overflow-y-auto p-4 space-y-4">
        {messages.length === 0 && !isLoading && (
          <div className="text-center py-8">
            <Bot className="h-12 w-12 text-gray-400 mx-auto mb-4" />
            <h3 className="text-lg font-medium text-gray-900 mb-2">
              Start a conversation
            </h3>
            <p className="text-gray-500">
              Ask questions about your uploaded documents and get AI-powered answers.
            </p>
          </div>
        )}

        {messages.map((message) => (
          <div
            key={message.id}
            className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
          >
            <div
              className={`max-w-xs lg:max-w-md px-4 py-2 rounded-lg ${
                message.role === 'user'
                  ? 'bg-primary-600 text-white'
                  : 'bg-gray-100 text-gray-900'
              }`}
            >
              <div className="flex items-start space-x-2">
                {message.role === 'assistant' && (
                  <Bot className="h-4 w-4 text-gray-500 mt-0.5 flex-shrink-0" />
                )}
                <div className="flex-1">
                  <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                  <p className={`text-xs mt-1 ${
                    message.role === 'user' ? 'text-primary-100' : 'text-gray-500'
                  }`}>
                    {formatTimestamp(message.timestamp)}
                  </p>
                </div>
                {message.role === 'user' && (
                  <User className="h-4 w-4 text-primary-100 mt-0.5 flex-shrink-0" />
                )}
              </div>
            </div>
          </div>
        ))}

        {isLoading && (
          <div className="flex justify-start">
            <div className="bg-gray-100 text-gray-900 max-w-xs lg:max-w-md px-4 py-2 rounded-lg">
              <div className="flex items-center space-x-2">
                <Bot className="h-4 w-4 text-gray-500" />
                <div className="flex space-x-1">
                  <div className="animate-bounce h-2 w-2 bg-gray-500 rounded-full"></div>
                  <div className="animate-bounce h-2 w-2 bg-gray-500 rounded-full" style={{ animationDelay: '0.1s' }}></div>
                  <div className="animate-bounce h-2 w-2 bg-gray-500 rounded-full" style={{ animationDelay: '0.2s' }}></div>
                </div>
              </div>
            </div>
          </div>
        )}

        <div ref={messagesEndRef} />
      </div>

      {/* Suggestions */}
      {suggestions.length > 0 && (
        <div className="px-4 py-2 border-t bg-gray-50">
          <div className="flex items-center space-x-2 mb-2">
            <Sparkles className="h-4 w-4 text-primary-600" />
            <span className="text-sm font-medium text-gray-700">Suggested questions:</span>
          </div>
          <div className="flex flex-wrap gap-2">
            {suggestions.map((suggestion, index) => (
              <button
                key={index}
                onClick={() => useSuggestion(suggestion)}
                className="text-xs bg-white border border-gray-300 rounded-full px-3 py-1 text-gray-700 hover:bg-gray-50 transition-colors"
              >
                {suggestion}
              </button>
            ))}
          </div>
        </div>
      )}

      {/* Input */}
      <div className="p-4 border-t">
        <div className="flex space-x-2">
          <div className="flex-1">
            <textarea
              value={inputMessage}
              onChange={(e) => setInputMessage(e.target.value)}
              onKeyPress={handleKeyPress}
              placeholder="Ask a question about your documents..."
              className="w-full px-3 py-2 border border-gray-300 rounded-lg resize-none focus:outline-none focus:ring-2 focus:ring-primary-500 focus:border-transparent"
              rows={1}
              disabled={isLoading}
            />
          </div>
          <button
            onClick={sendMessage}
            disabled={!inputMessage.trim() || isLoading}
            className="px-4 py-2 bg-primary-600 text-white rounded-lg hover:bg-primary-700 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
          >
            <Send className="h-4 w-4" />
          </button>
        </div>
      </div>
    </div>
  );
};

export default ChatInterface;
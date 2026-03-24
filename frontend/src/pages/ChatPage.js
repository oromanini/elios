import React, { useState, useEffect, useRef } from 'react';
import { useLocation } from 'react-router-dom';
import Layout from '../components/Layout';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Input } from '../components/ui/input';
import { ScrollArea } from '../components/ui/scroll-area';
import { aiAPI } from '../services/api';
import { toast } from 'sonner';
import { useAuth } from '../context/AuthContext';
import {
  Send,
  Loader2,
  MessageSquare,
  Trash2,
  Sparkles,
  User
} from 'lucide-react';
import { motion, AnimatePresence } from 'framer-motion';

const ChatPage = () => {
  const { user } = useAuth();
  const location = useLocation();
  const [messages, setMessages] = useState([]);
  const [input, setInput] = useState('');
  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);
  const messagesEndRef = useRef(null);
  const inputRef = useRef(null);

  const context = location.state?.context || null;

  useEffect(() => {
    loadHistory();
  }, []);

  useEffect(() => {
    scrollToBottom();
  }, [messages]);

  useEffect(() => {
    if (context) {
      setInput(`Quero conversar sobre o pilar: ${context}`);
      inputRef.current?.focus();
    }
  }, [context]);

  const loadHistory = async () => {
    try {
      const response = await aiAPI.getChatHistory();
      const formattedMessages = response.data.flatMap(msg => [
        { role: 'user', content: msg.user_message },
        { role: 'assistant', content: msg.assistant_message }
      ]);
      setMessages(formattedMessages);
    } catch (error) {
      console.error('Error loading history:', error);
    } finally {
      setHistoryLoading(false);
    }
  };

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  };

  const handleSend = async () => {
    if (!input.trim() || loading) return;

    const userMessage = input.trim();
    setInput('');
    setMessages(prev => [...prev, { role: 'user', content: userMessage }]);
    setLoading(true);

    try {
      const response = await aiAPI.chat({
        message: userMessage,
        context: context
      });

      setMessages(prev => [...prev, { role: 'assistant', content: response.data.response }]);
    } catch (error) {
      toast.error('Erro ao enviar mensagem');
      setMessages(prev => [...prev, { 
        role: 'assistant', 
        content: 'Desculpe, não consegui processar sua mensagem. Tente novamente.' 
      }]);
    } finally {
      setLoading(false);
    }
  };

  const handleClearHistory = async () => {
    try {
      await aiAPI.clearChatHistory();
      setMessages([]);
      toast.success('Histórico limpo');
    } catch (error) {
      toast.error('Erro ao limpar histórico');
    }
  };

  const handleKeyPress = (e) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  };

  return (
    <Layout>
      <div className="h-[calc(100vh-8rem)] flex flex-col" data-testid="chat-page">
        {/* Header */}
        <div className="flex items-center justify-between mb-4">
          <div>
            <h1 className="text-2xl md:text-3xl font-bold text-white flex items-center gap-3">
              <MessageSquare className="text-primary" />
              ELIOS Chat
            </h1>
            <p className="text-slate-400 text-sm mt-1">
              Seu assistente de performance pessoal
            </p>
          </div>
          <Button
            variant="ghost"
            size="sm"
            onClick={handleClearHistory}
            className="text-slate-400 hover:text-red-400"
            data-testid="clear-history-btn"
          >
            <Trash2 size={16} className="mr-2" />
            Limpar Histórico
          </Button>
        </div>

        {/* Chat Container */}
        <Card className="flex-1 glass-card border-white/10 flex flex-col overflow-hidden">
          {/* Messages Area */}
          <ScrollArea className="flex-1 p-4">
            {historyLoading ? (
              <div className="flex items-center justify-center h-full">
                <div className="spinner" />
              </div>
            ) : messages.length === 0 ? (
              <div className="flex flex-col items-center justify-center h-full text-center">
                <div className="w-20 h-20 rounded-full bg-primary/20 flex items-center justify-center mb-4">
                  <Sparkles className="w-10 h-10 text-primary" />
                </div>
                <h3 className="text-xl font-semibold text-white mb-2">
                  Olá, {user?.full_name?.split(' ')[0]}!
                </h3>
                <p className="text-slate-400 max-w-md">
                  Sou ELIOS, seu assistente de performance. Como posso ajudá-lo hoje?
                  Podemos conversar sobre seus pilares, metas ou estratégias de crescimento.
                </p>
                <div className="flex flex-wrap justify-center gap-2 mt-6">
                  {['Como melhorar minhas finanças?', 'Me ajude com gestão do tempo', 'Quero definir novas metas'].map((suggestion) => (
                    <Button
                      key={suggestion}
                      variant="outline"
                      size="sm"
                      onClick={() => setInput(suggestion)}
                      className="border-primary/30 text-primary hover:bg-primary/10"
                    >
                      {suggestion}
                    </Button>
                  ))}
                </div>
              </div>
            ) : (
              <div className="space-y-4">
                <AnimatePresence>
                  {messages.map((message, index) => (
                    <motion.div
                      key={index}
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                      <div
                        className={`max-w-[80%] rounded-lg p-4 chat-message ${
                          message.role === 'user'
                            ? 'user-message ml-auto'
                            : 'ai-message'
                        }`}
                      >
                        <div className="flex items-start gap-3">
                          <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
                            message.role === 'user' 
                              ? 'bg-accent/20' 
                              : 'bg-primary/20'
                          }`}>
                            {message.role === 'user' ? (
                              <User size={16} className="text-accent" />
                            ) : (
                              <Sparkles size={16} className="text-primary" />
                            )}
                          </div>
                          <div className="flex-1">
                            <p className="text-xs text-slate-500 mb-1">
                              {message.role === 'user' ? 'Você' : 'ELIOS'}
                            </p>
                            <p className="text-slate-200 whitespace-pre-wrap">
                              {message.content}
                            </p>
                          </div>
                        </div>
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>
                
                {loading && (
                  <motion.div
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="flex justify-start"
                  >
                    <div className="ai-message rounded-lg p-4">
                      <div className="flex items-center gap-2">
                        <div className="flex gap-1">
                          <span className="w-2 h-2 bg-primary rounded-full typing-dot" />
                          <span className="w-2 h-2 bg-primary rounded-full typing-dot" />
                          <span className="w-2 h-2 bg-primary rounded-full typing-dot" />
                        </div>
                        <span className="text-slate-400 text-sm">ELIOS está digitando...</span>
                      </div>
                    </div>
                  </motion.div>
                )}
                
                <div ref={messagesEndRef} />
              </div>
            )}
          </ScrollArea>

          {/* Input Area */}
          <div className="p-4 border-t border-white/10 bg-slate-900/50">
            <div className="flex gap-3">
              <Input
                ref={inputRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder="Digite sua mensagem..."
                className="flex-1 bg-slate-800/50 border-slate-700 text-white placeholder:text-slate-500 h-12"
                disabled={loading}
                data-testid="chat-input"
              />
              <Button
                onClick={handleSend}
                disabled={!input.trim() || loading}
                className="btn-primary h-12 px-6"
                data-testid="send-message-btn"
              >
                {loading ? (
                  <Loader2 className="animate-spin" size={20} />
                ) : (
                  <Send size={20} />
                )}
              </Button>
            </div>
          </div>
        </Card>
      </div>
    </Layout>
  );
};

export default ChatPage;

"use client";

import { useState, useRef, useEffect } from "react";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from "./ui/card";
import { Avatar } from "./ui/avatar";
import { SearchResults } from "./search-results";
import { RefreshCw } from "lucide-react";

interface Message {
  content: string;
  role: "user" | "assistant";
  timestamp: string;
}

interface SearchQuery {
  origin: string;
  destination: string;
  depart_date: string;
  return_date: string;
  budget?: number;
  travelers: number;
}

interface ChatResponse {
  message: string;
  missing_info: string[];
  has_complete_details: boolean;
  search_queries: SearchQuery[];
  session_id: string;
}

export function ChatInterface() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [searchResults, setSearchResults] = useState<SearchQuery[]>([]);
  const [showResults, setShowResults] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  // Auto-scroll to bottom on new messages
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  // Add reset function
  const handleReset = () => {
    setMessages([]);
    setSessionId(null);
    setSearchResults([]);
    setShowResults(false);
    setInput("");
  };

  const handleSendMessage = async () => {
    if (!input.trim()) return;
    
    // Add user message to chat
    const userMessage: Message = {
      content: input,
      role: "user",
      timestamp: new Date().toISOString(),
    };
    
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    
    try {
      // Call API through Next.js proxy to avoid CORS issues
      const response = await fetch("/api/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify({
          message: input,
          session_id: sessionId,
          user_id: "test-user",
        }),
      });
      
      if (!response.ok) {
        throw new Error("Failed to get response");
      }
      
      const data: ChatResponse = await response.json();
      
      // Save session ID for continuous conversation
      if (data.session_id) {
        setSessionId(data.session_id);
      }
      
      // Add assistant response to chat
      const assistantMessage: Message = {
        content: data.message,
        role: "assistant",
        timestamp: new Date().toISOString(),
      };
      
      setMessages((prev) => [...prev, assistantMessage]);
      
      // Only show search results when has_complete_details is true
      if (data.has_complete_details && data.search_queries.length > 0) {
        setSearchResults(data.search_queries);
        setShowResults(true);
        
        const searchResultsMessage: Message = {
          content: `Found ${data.search_queries.length} travel options for you!`,
          role: "assistant",
          timestamp: new Date().toISOString(),
        };
        
        setMessages((prev) => [...prev, searchResultsMessage]);
      } else if (data.search_queries.length > 0) {
        // Save search queries but don't display yet
        setSearchResults(data.search_queries); 
        setShowResults(false);
      } else {
        setShowResults(false);
      }
    } catch (error) {
      console.error("Error sending message:", error);
      
      // Add error message
      const errorMessage: Message = {
        content: "Sorry, there was an error processing your request. Please try again.",
        role: "assistant",
        timestamp: new Date().toISOString(),
      };
      
      setMessages((prev) => [...prev, errorMessage]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="flex flex-col space-y-4 max-w-4xl mx-auto p-4">
      <Card className="w-full mx-auto h-[500px] flex flex-col">
        <CardHeader className="flex flex-row items-center justify-between pb-2">
          <CardTitle className="text-center">Travel Assistant</CardTitle>
          <Button 
            variant="outline" 
            size="sm" 
            onClick={handleReset}
            className="flex items-center gap-1"
            title="Reset conversation"
          >
            <RefreshCw className="h-4 w-4" />
            <span>Reset</span>
          </Button>
        </CardHeader>
        
        <CardContent className="flex-grow overflow-y-auto p-4">
          {messages.length === 0 ? (
            <div className="text-center text-muted-foreground h-full flex items-center justify-center">
              <p>Welcome to the Travel Assistant! How can I help plan your trip today?</p>
            </div>
          ) : (
            <div className="space-y-4">
              {messages.map((message, index) => (
                <div
                  key={index}
                  className={`flex ${
                    message.role === "user" ? "justify-end" : "justify-start"
                  }`}
                >
                  <div className="flex items-start max-w-[80%] gap-2">
                    {message.role === "assistant" && (
                      <Avatar className="w-8 h-8 bg-primary text-primary-foreground">
                        <span className="text-xs">AI</span>
                      </Avatar>
                    )}
                    
                    <div
                      className={`p-3 rounded-lg ${
                        message.role === "user"
                          ? "bg-primary text-primary-foreground"
                          : "bg-muted"
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{message.content}</p>
                    </div>
                    
                    {message.role === "user" && (
                      <Avatar className="w-8 h-8 bg-secondary text-secondary-foreground">
                        <span className="text-xs">You</span>
                      </Avatar>
                    )}
                  </div>
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          )}
        </CardContent>
        
        <CardFooter className="p-4 border-t">
          <div className="flex w-full items-center space-x-2">
            <Input
              placeholder="Type your message..."
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === "Enter" && !e.shiftKey) {
                  e.preventDefault();
                  handleSendMessage();
                }
              }}
              disabled={loading}
              className="flex-grow"
            />
            <Button onClick={handleSendMessage} disabled={loading}>
              {loading ? "Sending..." : "Send"}
            </Button>
          </div>
        </CardFooter>
      </Card>
      
      {showResults && <SearchResults queries={searchResults} />}
    </div>
  );
} 
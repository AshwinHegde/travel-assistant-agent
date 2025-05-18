import { ChatInterface } from "@/components/chat-interface";

export default function Home() {
  return (
    <main className="min-h-screen bg-background p-4 md:p-8">
      <div className="container mx-auto">
        <h1 className="text-3xl font-bold text-center mb-8">Travel Assistant Agent</h1>
        <ChatInterface />
      </div>
    </main>
  );
}

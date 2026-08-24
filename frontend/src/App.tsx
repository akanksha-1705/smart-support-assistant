import { useState } from "react";
import "./App.css";

interface ChatRequest {
  conversation_id: number;
  message: string;
}

interface ChatResponse {
  conversation_id: number;
  message: string;
}

interface Message {
  role: "user" | "assistant" | "error";
  content: string;
}

function App() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const conversationId = 1;

  const sendMessage = async () => {
    if (!message.trim() || loading) {
      return;
    }

    const userMessage = message;

    setMessages((previous) => [
      ...previous,
      {
        role: "user",
        content: userMessage,
      },
    ]);

    setMessage("");
    setError("");
    setLoading(true);

    const request: ChatRequest = {
      conversation_id: conversationId,
      message: userMessage,
    };

    try {
      const response = await fetch("http://127.0.0.1:8000/chat", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
        },
        body: JSON.stringify(request),
      });

      if (!response.ok) {
        throw new Error("Backend request failed");
      }

      const data: ChatResponse = await response.json();

      setMessages((previous) => [
        ...previous,
        {
          role: "assistant",
          content: data.message,
        },
      ]);
    } catch (error) {
      setError("Unable to connect to the backend.");

      setMessages((previous) => [
        ...previous,
        {
          role: "error",
          content: "Unable to connect to the backend.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  const handleKeyDown = (
    event: React.KeyboardEvent<HTMLInputElement>
  ) => {
    if (event.key === "Enter") {
      sendMessage();
    }
  };

  return (
    <div className="app">
      <h1>Smart Support Assistant</h1>

      <div className="chat-container">
        {messages.length === 0 && (
          <p className="empty-message">
            Start a conversation...
          </p>
        )}

        {messages.map((msg, index) => (
          <div
            key={index}
            className={`message ${msg.role}`}
          >
            <strong>
              {msg.role === "user"
                ? "You"
                : msg.role === "assistant"
                ? "Assistant"
                : "Error"}
            </strong>

            <p>{msg.content}</p>
          </div>
        ))}

        {loading && (
          <div className="message assistant">
            <strong>Assistant</strong>
            <p>Sending...</p>
          </div>
        )}
      </div>

      {error && (
        <div className="error-message">
          {error}
        </div>
      )}

      <div className="input-area">
        <input
          type="text"
          value={message}
          onChange={(event) => setMessage(event.target.value)}
          onKeyDown={handleKeyDown}
          placeholder="Type your message..."
          disabled={loading}
        />

        <button
          onClick={sendMessage}
          disabled={loading || !message.trim()}
        >
          {loading ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  );
}

export default App;
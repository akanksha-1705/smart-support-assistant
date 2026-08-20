import { useState } from "react";
import axios from "axios";
import "./App.css";

interface ChatRequest {
  message: string;
}

interface ChatResponse {
  reply: string;
}

interface Message {
  role: "user" | "assistant" | "error";
  content: string;
}

export default function App() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState<string>("");
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string>("");

  const sendMessage = async () => {
    if (!input.trim()) return;

    const userMessage: Message = {
      role: "user",
      content: input,
    };

    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setLoading(true);
    setError("");

    try {
      const request: ChatRequest = {
        message: userMessage.content,
      };

      const res = await axios.post<ChatResponse>(
        "http://localhost:8000/chat",
        request
      );

      const botMessage: Message = {
        role: "assistant",
        content: res.data.reply,
      };

      setMessages((prev) => [...prev, botMessage]);
    } catch (err) {
      setError("Backend is not responding ❌");

      setMessages((prev) => [
        ...prev,
        {
          role: "error",
          content: "Something went wrong with backend",
        },
      ]);
    } finally {
      setLoading(false);
    }
  };

  return (
    <div style={styles.container}>
      <h2>Smart Support Chat</h2>

      <div style={styles.chatBox}>
        {messages.map((msg, index) => (
          <div
            key={index}
            style={{
              ...styles.message,
              alignSelf:
                msg.role === "user" ? "flex-end" : "flex-start",
              backgroundColor:
                msg.role === "user"
                  ? "#DCF8C6"
                  : msg.role === "error"
                  ? "#ffcccc"
                  : "#f1f1f1",
            }}
          >
            {msg.content}
          </div>
        ))}

        {loading && <div style={styles.loading}>Typing...</div>}
      </div>

      {error && <p style={{ color: "red" }}>{error}</p>}

      <div style={styles.inputBox}>
        <input
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              sendMessage();
            }
          }}
          placeholder="Type a message..."
          disabled={loading}
          style={styles.input}
        />

        <button
          onClick={sendMessage}
          disabled={loading}
          style={styles.button}
        >
          {loading ? "Sending..." : "Send"}
        </button>
      </div>
    </div>
  );
}

const styles: Record<string, React.CSSProperties> = {};

(styles as any).container = {
  width: "100%",
  maxWidth: "600px",
  margin: "0 auto",
  fontFamily: "Arial",
};

(styles as any).chatBox = {
  height: "400px",
  border: "1px solid #ccc",
  padding: "10px",
  overflowY: "auto",
  display: "flex",
  flexDirection: "column",
  gap: "8px",
};

(styles as any).message = {
  padding: "10px",
  borderRadius: "10px",
  maxWidth: "70%",
};

(styles as any).inputBox = {
  display: "flex",
  marginTop: "10px",
};

(styles as any).input = {
  flex: 1,
  padding: "10px",
};

(styles as any).button = {
  padding: "10px 15px",
  cursor: "pointer",
};

(styles as any).loading = {
  fontStyle: "italic",
  color: "gray",
};
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

interface SummaryResponse {
  title?: string;
  summary?: string;
  key_points?: string[];
  keywords?: string[];
}

function App() {
  const [message, setMessage] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [documentId, setDocumentId] = useState("");
  const [summary, setSummary] = useState<SummaryResponse | null>(null);
  const [summaryLoading, setSummaryLoading] = useState(false);
  const [summaryError, setSummaryError] = useState("");

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

  const generateSummary = async () => {
    if (!documentId.trim() || summaryLoading) {
      return;
    }

    setSummaryLoading(true);
    setSummaryError("");
    setSummary(null);

    try {
      const response = await fetch(
        "http://127.0.0.1:8001/documents/summary",
        {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({
            document_id: documentId.trim(),
          }),
        }
      );

      const data = await response.json();

      console.log("SUMMARY RESPONSE:", data);

      if (!response.ok) {
        throw new Error(
          data?.detail || "Unable to generate summary."
        );
      }

      setSummary(data);
    } catch (error) {
      console.error("SUMMARY ERROR:", error);

      setSummaryError(
        error instanceof Error
          ? error.message
          : "Unable to generate summary."
      );
    } finally {
      setSummaryLoading(false);
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

      {/* CHAT SECTION */}
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
          onChange={(event) =>
            setMessage(event.target.value)
          }
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

      {/* DOCUMENT SUMMARY SECTION */}
      <div className="summary-section">
        <h2>Document Summary</h2>

        <input
          type="text"
          value={documentId}
          onChange={(event) =>
            setDocumentId(event.target.value)
          }
          placeholder="Enter document ID"
          disabled={summaryLoading}
        />

        <button
          onClick={generateSummary}
          disabled={
            summaryLoading || !documentId.trim()
          }
        >
          {summaryLoading
            ? "Generating..."
            : "Generate Summary"}
        </button>

        {/* LOADING */}
        {summaryLoading && (
          <div className="summary-result">
            <h3>Generating Summary...</h3>
            <p>
              Please wait while the document is being
              processed.
            </p>
          </div>
        )}

        {/* ERROR */}
        {summaryError && (
          <div className="error-message">
            {summaryError}
          </div>
        )}

        {/* RESULT */}
        {!summaryLoading && summary && (
          <div className="summary-result">
            <h3>
              {summary.title || "Document Summary"}
            </h3>

            <h4>Summary</h4>

            <p>
              {summary.summary ||
                "No summary was returned."}
            </p>

            <h4>Key Points</h4>

            {summary.key_points &&
            summary.key_points.length > 0 ? (
              <ul>
                {summary.key_points.map(
                  (point, index) => (
                    <li key={index}>{point}</li>
                  )
                )}
              </ul>
            ) : (
              <p>No key points returned.</p>
            )}

            <h4>Keywords</h4>

            {summary.keywords &&
            summary.keywords.length > 0 ? (
              <ul>
                {summary.keywords.map(
                  (keyword, index) => (
                    <li key={index}>{keyword}</li>
                  )
                )}
              </ul>
            ) : (
              <p>No keywords returned.</p>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

export default App;
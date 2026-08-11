import { useState, useEffect, useRef, FormEvent } from "react";
import Head from "next/head";
import { sendMessage, ChatResponse } from "../utils/api";

interface Message {
  role: "user" | "assistant";
  content: string;
}

export default function Home() {
  const [messages, setMessages] = useState<Message[]>([]);
  const [input, setInput] = useState("");
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [calibrated, setCalibrated] = useState(false);
  const [progress, setProgress] = useState(0);
  const [loading, setLoading] = useState(false);
  const bottomRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    const text = input.trim();
    if (!text || loading) return;

    setMessages((prev) => [...prev, { role: "user", content: text }]);
    setInput("");
    setLoading(true);

    try {
      const resp: ChatResponse = await sendMessage(text, sessionId);

      if (!sessionId && resp.session_id) {
        setSessionId(resp.session_id);
      }

      setCalibrated(resp.calibrated);
      setProgress(resp.progress);

      if (resp.reply) {
        setMessages((prev) => [
          ...prev,
          { role: "assistant", content: resp.reply },
        ]);
      }
    } catch (err) {
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          content: "Something went wrong. Please try again.",
        },
      ]);
    } finally {
      setLoading(false);
    }
  }

  return (
    <>
      <Head>
        <title>Zoya -- Mental Health Support</title>
        <meta
          name="description"
          content="Zoya is a CBT-grounded conversational agent for mental health support."
        />
      </Head>

      <div className="chat-container">
        {/* Header */}
        <header className="chat-header">
          <div>
            <h1>Zoya</h1>
            <span className="subtitle">Mental health support</span>
          </div>
        </header>

        {/* Calibration progress bar -- visible until calibrated */}
        {!calibrated && progress > 0 && (
          <div className="calibration-bar">
            <div className="calibration-label">
              <span>Getting to know you</span>
              <span>{Math.min(Math.round(progress), 100)}%</span>
            </div>
            <div className="calibration-track">
              <div
                className="calibration-fill"
                style={{ width: `${Math.min(progress, 100)}%` }}
              />
            </div>
          </div>
        )}

        {/* Messages */}
        <div className="messages">
          {messages.length === 0 && (
            <div
              style={{
                textAlign: "center",
                color: "var(--text-secondary)",
                marginTop: "40vh",
                transform: "translateY(-50%)",
              }}
            >
              <p style={{ fontSize: "1.1rem", marginBottom: "8px" }}>
                Hi, I&#39;m Zoya.
              </p>
              <p style={{ fontSize: "0.9rem" }}>
                Tell me how you&#39;re feeling today.
              </p>
            </div>
          )}

          {messages.map((msg, i) => (
            <div key={i} className={`message ${msg.role}`}>
              {msg.content}
            </div>
          ))}

          {loading && (
            <div className="message assistant">
              <div className="loading-dots">
                <span />
                <span />
                <span />
              </div>
            </div>
          )}

          <div ref={bottomRef} />
        </div>

        {/* Input */}
        <form className="input-area" onSubmit={handleSubmit}>
          <input
            type="text"
            placeholder="Type your message..."
            value={input}
            onChange={(e) => setInput(e.target.value)}
            disabled={loading}
            autoFocus
          />
          <button type="submit" disabled={!input.trim() || loading}>
            Send
          </button>
        </form>
      </div>
    </>
  );
}

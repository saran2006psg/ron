import React, { useState, useEffect, useRef } from "react";
import { createRoot } from "react-dom/client";
import "./style.css";

interface JobError {
  code: string;
  message: string;
  retryable?: boolean;
  details?: Record<string, unknown>;
}

interface Job {
  job_id: string;
  status: "queued" | "running" | "succeeded" | "failed";
  progress: number;
  error?: JobError;
  warnings: string[];
  result_links: Record<string, string>;
}

const API_BASE = (
  import.meta.env.VITE_API_URL ||
  (typeof window !== "undefined" && window.location.port === "3000"
    ? "http://localhost:8000"
    : typeof window !== "undefined"
    ? window.location.origin
    : "http://localhost:8000")
).replace(/\/$/, "");

const VOICES = [
  { id: "en-IN-female", label: "English (India) - Neerja (Female)" },
  { id: "en-IN-male", label: "English (India) - Prabhat (Male)" },
  { id: "en-US-female", label: "English (US) - Jenny (Female)" },
  { id: "en-US-male", label: "English (US) - Guy (Male)" },
  { id: "en-GB-female", label: "English (UK) - Sonia (Female)" },
  { id: "hi-IN-female", label: "Hindi (India) - Swara (Female)" },
  { id: "hi-IN-male", label: "Hindi (India) - Madhur (Male)" },
  { id: "ta-IN-female", label: "Tamil (India) - Pallavi (Female)" },
  { id: "ta-IN-male", label: "Tamil (India) - Valluvar (Male)" },
];

function getStageDescription(progress: number, status: string): string {
  if (status === "failed") return "Job failed safely (no unverified media rendered)";
  if (status === "succeeded") return "Completed: All artifacts and media ready";
  if (progress <= 5) return "Queued & Initializing workspace...";
  if (progress <= 25) return "Synthesizing voiceover & planning scene timing...";
  if (progress <= 55) return "Searching & verifying commercially licensed B-roll clips...";
  if (progress <= 70) return "Downloading & validating video clips with FFprobe...";
  if (progress <= 75) return "Generating provenance audit manifest & timeline...";
  if (progress <= 95) return "Composing video & burning captions with FFmpeg...";
  return "Finalizing job outputs...";
}

export function App() {
  const [tab, setTab] = useState<"script" | "upload" | "scenes">("script");

  // Form states
  const [script, setScript] = useState(
    "Cloud computing is transforming how modern enterprises operate. Teams can collaborate securely from anywhere in the world."
  );
  const [scenesJson, setScenesJson] = useState(
    JSON.stringify(
      [
        { text: "Renewable energy powers our sustainable future.", visual_hint: "solar panels on rooftop" },
        { text: "Wind turbines generate clean power across the horizon.", visual_hint: "wind turbines in open field" },
      ],
      null,
      2
    )
  );
  const [audioFile, setAudioFile] = useState<File | null>(null);

  // Options
  const [aspectRatios, setAspectRatios] = useState<string[]>(["16:9"]);
  const [voice, setVoice] = useState("en-IN-female");
  const [style, setStyle] = useState("bright, modern, cinematic footage");
  const [avoid, setAvoid] = useState("violence, logos, weapons, snakes");
  const [burnInCaptions, setBurnInCaptions] = useState(true);
  const [generateSrt, setGenerateSrt] = useState(true);

  // Job execution states
  const [job, setJob] = useState<Job | null>(null);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [clientError, setClientError] = useState("");
  const [showInspector, setShowInspector] = useState(false);

  const pollIntervalRef = useRef<number | null>(null);

  // Toggle aspect ratios
  const toggleRatio = (ratio: string) => {
    if (aspectRatios.includes(ratio)) {
      if (aspectRatios.length > 1) {
        setAspectRatios(aspectRatios.filter((r) => r !== ratio));
      }
    } else {
      setAspectRatios([...aspectRatios, ratio]);
    }
  };

  const startPolling = (jobId: string) => {
    if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);

    pollIntervalRef.current = window.setInterval(async () => {
      try {
        const res = await fetch(`${API_BASE}/api/v1/jobs/${jobId}`);
        if (!res.ok) throw new Error(`Polling HTTP ${res.status}`);
        const data: Job = await res.json();
        setJob(data);

        if (data.status === "succeeded" || data.status === "failed") {
          if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
          setIsSubmitting(false);
        }
      } catch (err) {
        console.warn("Poll connection retry...", err);
      }
    }, 1200);
  };

  useEffect(() => {
    return () => {
      if (pollIntervalRef.current) clearInterval(pollIntervalRef.current);
    };
  }, []);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setClientError("");
    setIsSubmitting(true);

    const idempotencyKey = `ui-${Date.now()}-${Math.random().toString(36).slice(2, 8)}`;

    try {
      if (tab === "upload") {
        if (!audioFile) {
          throw new Error("Please select or drop an MP3, WAV, or M4A audio file.");
        }
        const formData = new FormData();
        formData.append("audio", audioFile);
        formData.append("voice", voice);
        formData.append("aspect_ratios", aspectRatios.join(","));
        formData.append("style", style);
        formData.append("avoid", avoid);
        formData.append("burn_in", String(burnInCaptions));
        formData.append("srt", String(generateSrt));
        if (script.trim()) formData.append("script", script);

        const res = await fetch(`${API_BASE}/api/v1/broll/jobs/upload`, {
          method: "POST",
          headers: { "Idempotency-Key": idempotencyKey },
          body: formData,
        });
        const body = await res.json();
        if (!res.ok) throw new Error(body.error?.message || `Upload failed (${res.status})`);

        setJob({ job_id: body.job_id, status: "queued", progress: 0, warnings: [], result_links: {} });
        startPolling(body.job_id);
      } else {
        // JSON submission
        let payload: Record<string, unknown> = {
          aspect_ratios: aspectRatios,
          voice,
          style,
          avoid: avoid.split(",").map((s) => s.trim()).filter(Boolean),
          captions: { burn_in: burnInCaptions, srt: generateSrt },
        };

        if (tab === "script") {
          if (!script.trim()) throw new Error("Please provide narration script text.");
          payload.script = script.trim();
        } else if (tab === "scenes") {
          try {
            const parsed = JSON.parse(scenesJson);
            if (!Array.isArray(parsed) || parsed.length === 0) {
              throw new Error("Scenes must be a non-empty JSON array.");
            }
            payload.scenes = parsed;
          } catch (jsonErr) {
            throw new Error(`Invalid JSON in scenes: ${(jsonErr as Error).message}`);
          }
        }

        const res = await fetch(`${API_BASE}/api/v1/broll/jobs`, {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
            "Idempotency-Key": idempotencyKey,
          },
          body: JSON.stringify(payload),
        });
        const body = await res.json();
        if (!res.ok) throw new Error(body.error?.message || `Submission failed (${res.status})`);

        setJob({ job_id: body.job_id, status: "queued", progress: 0, warnings: [], result_links: {} });
        startPolling(body.job_id);
      }
    } catch (err) {
      setClientError((err as Error).message || "An unexpected error occurred");
      setIsSubmitting(false);
    }
  };

  // Find previewable video URL
  const videoEntries = Object.entries(job?.result_links || {}).filter(([k]) => k.startsWith("video_"));
  const firstVideoUrl = videoEntries.length > 0 ? videoEntries[0][1] : null;

  return (
    <div className="app-container">
      <header className="app-header">
        <div className="brand-badge">
          <span className="pulse-dot"></span>
          IncuBrix Engine v0.1.0 • Commercial Grade
        </div>
        <h1 className="title-gradient">Script to B-roll Video Engine</h1>
        <p className="subtitle">
          Turn your narration scripts, voiceovers, or structured scenes into licensed, commercial-ready video compositions in 16:9, 9:16, and 1:1.
        </p>
      </header>

      <main className="main-grid">
        {/* Left Column: Creator Studio */}
        <section className="card">
          <h2 className="card-title">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <polygon points="23 7 16 12 23 17 23 7"></polygon>
              <rect x="1" y="5" width="15" height="14" rx="2" ry="2"></rect>
            </svg>
            Project Studio
          </h2>

          {/* Input Mode Tabs */}
          <div className="tabs">
            <button
              type="button"
              className={`tab-btn ${tab === "script" ? "active" : ""}`}
              onClick={() => setTab("script")}
            >
              ✍️ Narration Script
            </button>
            <button
              type="button"
              className={`tab-btn ${tab === "upload" ? "active" : ""}`}
              onClick={() => setTab("upload")}
            >
              🎙️ Audio File Upload
            </button>
            <button
              type="button"
              className={`tab-btn ${tab === "scenes" ? "active" : ""}`}
              onClick={() => setTab("scenes")}
            >
              🎬 Scene Breakdown
            </button>
          </div>

          <form onSubmit={handleSubmit}>
            {tab === "script" && (
              <div className="form-group">
                <label className="form-label">Voiceover Script Text</label>
                <textarea
                  className="form-textarea"
                  rows={4}
                  value={script}
                  onChange={(e) => setScript(e.target.value)}
                  placeholder="Enter narration text. The engine will segment into natural scenes..."
                />
              </div>
            )}

            {tab === "upload" && (
              <div className="form-group">
                <label className="form-label">Upload Master Voiceover Audio</label>
                <div
                  className="file-dropzone"
                  onClick={() => document.getElementById("audio-file-input")?.click()}
                >
                  <input
                    id="audio-file-input"
                    type="file"
                    accept=".mp3,.wav,.m4a,audio/*"
                    style={{ display: "none" }}
                    onChange={(e) => {
                      if (e.target.files?.[0]) setAudioFile(e.target.files[0]);
                    }}
                  />
                  <span className="dropzone-icon">🎵</span>
                  <p className="dropzone-text">
                    {audioFile ? audioFile.name : "Click to select or drop audio file"}
                  </p>
                  <p className="dropzone-hint">Supports MP3, WAV, M4A up to 100 MB (max 10 min)</p>
                </div>
              </div>
            )}

            {tab === "scenes" && (
              <div className="form-group">
                <label className="form-label">IncuBrix Structured Scenes (JSON)</label>
                <textarea
                  className="form-textarea"
                  style={{ fontFamily: "var(--font-mono)", fontSize: "0.85rem" }}
                  rows={5}
                  value={scenesJson}
                  onChange={(e) => setScenesJson(e.target.value)}
                  placeholder="[{ 'text': '...', 'visual_hint': '...' }]"
                />
              </div>
            )}

            {/* Target Aspect Ratios */}
            <div className="form-group">
              <label className="form-label">Target Aspect Ratios (1080p class)</label>
              <div className="ratio-selector">
                <div
                  className={`ratio-chip ${aspectRatios.includes("16:9") ? "active" : ""}`}
                  onClick={() => toggleRatio("16:9")}
                >
                  16:9 Landscape
                </div>
                <div
                  className={`ratio-chip ${aspectRatios.includes("9:16") ? "active" : ""}`}
                  onClick={() => toggleRatio("9:16")}
                >
                  9:16 Vertical
                </div>
                <div
                  className={`ratio-chip ${aspectRatios.includes("1:1") ? "active" : ""}`}
                  onClick={() => toggleRatio("1:1")}
                >
                  1:1 Square
                </div>
              </div>
            </div>

            {/* Voice & Style Settings */}
            <div className="form-grid-2">
              <div className="form-group">
                <label className="form-label">Neural TTS Voice</label>
                <select
                  className="form-select"
                  value={voice}
                  onChange={(e) => setVoice(e.target.value)}
                >
                  {VOICES.map((v) => (
                    <option key={v.id} value={v.id}>
                      {v.label}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label">Visual Style Prompt</label>
                <input
                  type="text"
                  className="form-input"
                  value={style}
                  onChange={(e) => setStyle(e.target.value)}
                  placeholder="e.g. cinematic, documentary, vibrant"
                />
              </div>
            </div>

            {/* Avoid List */}
            <div className="form-group">
              <label className="form-label">Safety & Avoid Keywords (comma separated)</label>
              <input
                type="text"
                className="form-input"
                value={avoid}
                onChange={(e) => setAvoid(e.target.value)}
                placeholder="e.g. logos, text overlays, violence, cartoon"
              />
            </div>

            {/* Captions Options */}
            <div className="form-grid-2" style={{ marginBottom: "1.25rem" }}>
              <div className="toggle-row">
                <span>Burn In Captions</span>
                <input
                  type="checkbox"
                  checked={burnInCaptions}
                  onChange={(e) => setBurnInCaptions(e.target.checked)}
                />
              </div>
              <div className="toggle-row">
                <span>Export Captions.srt</span>
                <input
                  type="checkbox"
                  checked={generateSrt}
                  onChange={(e) => setGenerateSrt(e.target.checked)}
                />
              </div>
            </div>

            {clientError && (
              <div className="alert alert-error">
                <span>⚠️</span>
                <span>{clientError}</span>
              </div>
            )}

            <button type="submit" className="btn-submit" disabled={isSubmitting}>
              {isSubmitting ? (
                <>
                  <span className="pulse-dot"></span>
                  Processing Pipeline...
                </>
              ) : (
                <>Generate B-roll Video &rarr;</>
              )}
            </button>
          </form>
        </section>

        {/* Right Column: Execution Monitor & Output Assets */}
        <section className="card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: "1rem" }}>
            <h2 className="card-title" style={{ margin: 0 }}>
              <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10"></circle>
                <polyline points="12 6 12 12 16 14"></polyline>
              </svg>
              Execution Monitor
            </h2>
            {job && <span className={`status-badge ${job.status}`}>{job.status}</span>}
          </div>

          {!job ? (
            <div style={{ textAlign: "center", padding: "3rem 1rem", color: "var(--text-subtle)" }}>
              <p style={{ fontSize: "2.5rem", marginBottom: "0.5rem" }}>⚡</p>
              <p style={{ fontWeight: 600 }}>Ready to generate</p>
              <p style={{ fontSize: "0.85rem" }}>Configure narration and launch a job to see real-time progress and media outputs.</p>
            </div>
          ) : (
            <div>
              <div className="progress-container">
                <div className="progress-header">
                  <span>{getStageDescription(job.progress, job.status)}</span>
                  <span>{job.progress}%</span>
                </div>
                <div className="progress-track">
                  <div className="progress-fill" style={{ width: `${job.progress}%` }}></div>
                </div>
              </div>

              {/* Warnings List */}
              {job.warnings && job.warnings.length > 0 && (
                <div className="alert alert-warning">
                  <span>⚠️</span>
                  <div style={{ fontSize: "0.8rem" }}>
                    {job.warnings.map((w, idx) => (
                      <p key={idx}>{w}</p>
                    ))}
                  </div>
                </div>
              )}

              {/* Error Callout */}
              {job.error && (
                <div className="alert alert-error">
                  <span>⛔</span>
                  <div>
                    <strong>{job.error.code}:</strong> {job.error.message}
                    {job.error.retryable && <p style={{ fontSize: "0.75rem", marginTop: "0.25rem" }}>This error is retryable.</p>}
                  </div>
                </div>
              )}

              {/* Video Player Preview if Available */}
              {firstVideoUrl && (
                <div className="video-preview-wrapper">
                  <video controls src={firstVideoUrl} preload="metadata">
                    Your browser does not support the video tag.
                  </video>
                </div>
              )}

              {/* Downloads & Provenance Artifacts */}
              {job.result_links && Object.keys(job.result_links).length > 0 && (
                <div>
                  <h3 style={{ fontSize: "0.95rem", fontWeight: 700, margin: "1.25rem 0 0.5rem" }}>
                    Verified Deliverables
                  </h3>
                  <div className="downloads-grid">
                    {Object.entries(job.result_links).map(([name, url]) => (
                      <a
                        key={name}
                        href={url}
                        target="_blank"
                        rel="noreferrer"
                        className="download-link"
                      >
                        <span>
                          {name.startsWith("video") ? "🎬" : name === "timeline" ? "📋" : name === "manifest" ? "📜" : "📝"}
                        </span>
                        <span>{name.replace("_", " ").toUpperCase()}</span>
                      </a>
                    ))}
                  </div>
                </div>
              )}

              {/* Inspect JSON Provenance button */}
              <div style={{ marginTop: "1.5rem" }}>
                <button
                  type="button"
                  className="tab-btn"
                  style={{ width: "100%", border: "1px solid var(--border-subtle)", background: "var(--bg-input)" }}
                  onClick={() => setShowInspector(!showInspector)}
                >
                  {showInspector ? "Hide Audit Data" : "Inspect Raw Job Record"}
                </button>
                {showInspector && (
                  <pre className="code-block" style={{ marginTop: "0.75rem" }}>
                    {JSON.stringify(job, null, 2)}
                  </pre>
                )}
              </div>
            </div>
          )}
        </section>
      </main>

      <footer className="footer">
        <p>IncuBrix B-roll Engine • Built with FastAPI, FFmpeg & Modern Web Standards • Strict Provenance Verified</p>
      </footer>
    </div>
  );
}

const rootEl = document.getElementById("root");
if (rootEl) {
  createRoot(rootEl).render(<App />);
}

"use client";

export default function BackgroundLayer() {
  return (
    <div
      className="fixed inset-0 pointer-events-none overflow-hidden"
      style={{ zIndex: 0 }}
      aria-hidden="true"
    >
      {/* Blob 1 — top left */}
      <div
        style={{
          position: "absolute",
          top: "-10%",
          left: "-5%",
          width: "45vw",
          height: "45vw",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(0,230,118,0.06) 0%, transparent 70%)",
        }}
      />
      {/* Blob 2 — bottom right */}
      <div
        style={{
          position: "absolute",
          bottom: "-15%",
          right: "-8%",
          width: "50vw",
          height: "50vw",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(0,200,83,0.05) 0%, transparent 70%)",
        }}
      />
      {/* Blob 3 — center */}
      <div
        style={{
          position: "absolute",
          top: "40%",
          left: "35%",
          width: "30vw",
          height: "30vw",
          borderRadius: "50%",
          background: "radial-gradient(circle, rgba(0,230,118,0.03) 0%, transparent 70%)",
        }}
      />

      {/* Floating icon — lock (top-right) */}
      <svg
        className="float-icon"
        style={{
          position: "absolute",
          top: "8%",
          right: "10%",
          width: 64,
          height: 64,
          opacity: 0.08,
          animation: "float 7s ease-in-out infinite",
          color: "#00e676",
        }}
        viewBox="0 0 24 24"
        fill="currentColor"
      >
        <path d="M18 8h-1V6c0-2.76-2.24-5-5-5S7 3.24 7 6v2H6c-1.1 0-2 .9-2 2v10c0 1.1.9 2 2 2h12c1.1 0 2-.9 2-2V10c0-1.1-.9-2-2-2zm-6 9c-1.1 0-2-.9-2-2s.9-2 2-2 2 .9 2 2-.9 2-2 2zm3.1-9H8.9V6c0-1.71 1.39-3.1 3.1-3.1 1.71 0 3.1 1.39 3.1 3.1v2z" />
      </svg>

      {/* Floating icon — gear (bottom-left) */}
      <svg
        className="float-icon"
        style={{
          position: "absolute",
          bottom: "15%",
          left: "7%",
          width: 72,
          height: 72,
          opacity: 0.08,
          animation: "float 9s ease-in-out infinite 1.5s",
          color: "#00e676",
        }}
        viewBox="0 0 24 24"
        fill="currentColor"
      >
        <path d="M19.14 12.94c.04-.3.06-.61.06-.94 0-.32-.02-.64-.07-.94l2.03-1.58c.18-.14.23-.41.12-.61l-1.92-3.32c-.12-.22-.37-.29-.59-.22l-2.39.96c-.5-.38-1.03-.7-1.62-.94l-.36-2.54c-.04-.24-.24-.41-.48-.41h-3.84c-.24 0-.43.17-.47.41l-.36 2.54c-.59.24-1.13.57-1.62.94l-2.39-.96c-.22-.08-.47 0-.59.22L2.74 8.87c-.12.21-.08.47.12.61l2.03 1.58c-.05.3-.09.63-.09.94s.02.64.07.94l-2.03 1.58c-.18.14-.23.41-.12.61l1.92 3.32c.12.22.37.29.59.22l2.39-.96c.5.38 1.03.7 1.62.94l.36 2.54c.05.24.24.41.48.41h3.84c.24 0 .44-.17.47-.41l.36-2.54c.59-.24 1.13-.56 1.62-.94l2.39.96c.22.08.47 0 .59-.22l1.92-3.32c.12-.22.07-.47-.12-.61l-2.01-1.58zM12 15.6c-1.98 0-3.6-1.62-3.6-3.6s1.62-3.6 3.6-3.6 3.6 1.62 3.6 3.6-1.62 3.6-3.6 3.6z" />
      </svg>

      {/* Floating icon — cloud (center-left) */}
      <svg
        className="float-icon"
        style={{
          position: "absolute",
          top: "45%",
          left: "3%",
          width: 56,
          height: 56,
          opacity: 0.08,
          animation: "float 11s ease-in-out infinite 3s",
          color: "#00e676",
        }}
        viewBox="0 0 24 24"
        fill="currentColor"
      >
        <path d="M19.35 10.04C18.67 6.59 15.64 4 12 4 9.11 4 6.6 5.64 5.35 8.04 2.34 8.36 0 10.91 0 14c0 3.31 2.69 6 6 6h13c2.76 0 5-2.24 5-5 0-2.64-2.05-4.78-4.65-4.96z" />
      </svg>
    </div>
  );
}

interface GlassCardProps {
  children: React.ReactNode;
  className?: string;
}

export default function GlassCard({ children, className = "" }: GlassCardProps) {
  return (
    <div
      className={`glass ${className}`}
      style={{ padding: "1.5rem" }}
    >
      {children}
    </div>
  );
}

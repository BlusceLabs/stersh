interface SkeletonLoaderProps {
  count?: number;
  className?: string;
}

export default function SkeletonLoader({ count = 5, className }: SkeletonLoaderProps) {
  return (
    <>
      {Array.from({ length: count }).map((_, index) => (
        <div
          key={index}
          className={`bg-gray-800 rounded-lg animate-pulse ${className}`}
          style={{
            height: "300px",
            width: "200px",
            animationDuration: "1.5s",
          }}
        >
          <div className="h-3/4 bg-gray-700" style={{ width: "80%", height: "80%", marginLeft: "10%", marginTop: "10%" }} />
          <div className="h-1/4 bg-gray-700" style={{ width: "60%", height: "20%", marginLeft: "20%", marginTop: "5%" }} />
        </div>
      ))}
    </>
  );
}
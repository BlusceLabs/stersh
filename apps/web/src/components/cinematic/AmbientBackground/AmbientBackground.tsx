export function AmbientBackground() {
  return (
    <div
      className="
        pointer-events-none
        absolute
        inset-0
        overflow-hidden
      "
    >
      {/* TOP RIGHT */}
      <div
        className="
          absolute
          right-[-180px]
          top-[-180px]
          h-[520px]
          w-[520px]
          rounded-full
          bg-[#8B5CF6]/18
          blur-[160px]
        "
      />

      {/* LEFT */}
      <div
        className="
          absolute
          left-[-200px]
          top-[30%]
          h-[480px]
          w-[480px]
          rounded-full
          bg-[#22D3EE]/10
          blur-[150px]
        "
      />

      {/* BOTTOM */}
      <div
        className="
          absolute
          bottom-[-260px]
          left-1/2
          h-[620px]
          w-[620px]
          -translate-x-1/2
          rounded-full
          bg-[#7C3AED]/14
          blur-[180px]
        "
      />

      {/* GRID */}
      <div
        className="
          absolute
          inset-0
          opacity-[0.03]
          [background-image:linear-gradient(rgba(255,255,255,0.15)_1px,transparent_1px),linear-gradient(90deg,rgba(255,255,255,0.15)_1px,transparent_1px)]
          [background-size:80px_80px]
        "
      />
    </div>
  )
}

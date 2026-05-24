import React from "react"

interface Props {
  children: React.ReactNode
  fallback?: React.ReactNode
  onError?: (error: Error, errorInfo: React.ErrorInfo) => void
}

interface State {
  hasError: boolean
  error: Error | null
}

export class ErrorBoundary extends React.Component<Props, State> {
  constructor(props: Props) {
    super(props)
    this.state = { hasError: false, error: null }
  }

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error }
  }

  componentDidCatch(error: Error, errorInfo: React.ErrorInfo) {
    this.props.onError?.(error, errorInfo)
  }

  handleRetry = () => {
    this.setState({ hasError: false, error: null })
  }

  render() {
    if (this.state.hasError) {
      if (this.props.fallback) {
        return this.props.fallback
      }

      return (
        <main className="flex min-h-screen flex-col items-center justify-center bg-[#070B14] text-white">
          <div className="text-center">
            <div className="mx-auto mb-6 flex h-20 w-20 items-center justify-center rounded-full bg-red-500/10">
              <svg
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2"
                className="h-10 w-10 text-red-400"
              >
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="8" x2="12" y2="12" />
                <line x1="12" y1="16" x2="12.01" y2="16" />
              </svg>
            </div>

            <h2 className="text-2xl font-semibold">Something went wrong</h2>
            <p className="mt-3 max-w-md text-white/50">
              {this.state.error?.message || "An unexpected error occurred"}
            </p>

            <div className="mt-8 flex items-center justify-center gap-4">
              <button
                onClick={this.handleRetry}
                className="
                  rounded-full bg-[#8B5CF6] px-8 py-3
                  text-sm font-semibold
                  transition-all duration-300
                  hover:bg-[#7C3AED] hover:scale-105
                "
              >
                Try Again
              </button>

              <button
                onClick={() => (window.location.href = "/")}
                className="
                  rounded-full border border-white/[0.08]
                  bg-white/[0.04] px-8 py-3
                  text-sm font-medium text-white/80
                  backdrop-blur-3xl
                  transition-all duration-300
                  hover:bg-white/[0.08] hover:text-white
                "
              >
                Back to Home
              </button>
            </div>
          </div>
        </main>
      )
    }

    return this.props.children
  }
}

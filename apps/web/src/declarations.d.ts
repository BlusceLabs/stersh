declare module "*.css"

declare const process: {
  env: Record<string, string | undefined>
}

interface NodeModule {
  hot?: {
    accept(path: string, callback: () => void): void
  }
}

declare const module: NodeModule
declare function require(path: string): unknown

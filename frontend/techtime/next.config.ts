import type { NextConfig } from 'next'

const config: NextConfig = {
  // Enable static export for PyWebView
  output: 'export',

  // Disable image optimization (requires server)
  images: {
    unoptimized: true,
  },

  // Generate trailing slashes for static file compatibility
  trailingSlash: true,

  // Asset prefix for static loading
  assetPrefix: process.env.NODE_ENV === 'production' ? '' : undefined,

  // Disable server-only features
  typescript: {
    // Type checking in CI, not build
    ignoreBuildErrors: false,
  },
}

export default config

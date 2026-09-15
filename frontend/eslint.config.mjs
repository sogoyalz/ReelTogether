import nextVitals from 'eslint-config-next/core-web-vitals'
export default [
  ...nextVitals,
  { ignores: ['.next*/**', 'node_modules/**', 'test-results/**', 'playwright-report/**', 'next-env.d.ts'] },
]

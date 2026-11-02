export class UploadError extends Error {
  constructor(message: string, readonly status: number) { super(message) }
}

/** Bound both bytes and time, including a reader that never yields a chunk. */
export async function readRequestBody(stream: ReadableStream<Uint8Array> | null, signal: AbortSignal, limit = 64 * 1024, timeoutMs = 5000) {
  if (!stream) return undefined
  const reader = stream.getReader()
  const chunks: Uint8Array[] = []
  let size = 0
  let rejectRead: (reason: Error) => void = () => {}
  const interrupted = new Promise<never>((_, reject) => { rejectRead = reject })
  const abort = () => rejectRead(new UploadError('Request upload was cancelled', 408))
  const timer = setTimeout(() => rejectRead(new UploadError('Request upload timed out', 408)), timeoutMs)
  signal.addEventListener('abort', abort, { once: true })
  try {
    if (signal.aborted) throw new UploadError('Request upload was cancelled', 408)
    while (true) {
      if (signal.aborted) throw new UploadError('Request upload was cancelled', 408)
      const { done, value } = await Promise.race([reader.read(), interrupted])
      if (done) break
      size += value.byteLength
      if (size > limit) throw new UploadError('Request body is too large', 413)
      chunks.push(value)
    }
    const body = new Uint8Array(size)
    let offset = 0
    for (const chunk of chunks) { body.set(chunk, offset); offset += chunk.byteLength }
    return body
  } catch (error) {
    // Cancellation of an attacker-controlled stream may itself never resolve.
    void reader.cancel().catch(() => {})
    throw error
  } finally {
    clearTimeout(timer)
    signal.removeEventListener('abort', abort)
    reader.releaseLock()
  }
}

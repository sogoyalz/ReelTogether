import { test, expect } from '@playwright/test'
import { readRequestBody } from '../lib/proxy-body'

test('a stalled upload is cancelled within its deadline', async () => {
  let cancelled = false
  const stream = new ReadableStream<Uint8Array>({ cancel() { cancelled = true } })
  await expect(readRequestBody(stream, new AbortController().signal, 1024, 20)).rejects.toMatchObject({ status: 408 })
  expect(cancelled).toBe(true)
})

test('oversized and aborted uploads stop; bounded bytes survive unchanged', async () => {
  const stream = () => new ReadableStream<Uint8Array>({ start(c) { c.enqueue(new Uint8Array([1, 2, 3])); c.close() } })
  await expect(readRequestBody(stream(), new AbortController().signal, 2)).rejects.toMatchObject({ status: 413 })
  const abort = new AbortController(); abort.abort()
  await expect(readRequestBody(stream(), abort.signal)).rejects.toMatchObject({ status: 408 })
  expect(await readRequestBody(stream(), new AbortController().signal)).toEqual(new Uint8Array([1, 2, 3]))
})

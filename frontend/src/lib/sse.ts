export type SSEEvent = { event: string; data: string }

export function parseSSEChunk(buffer: string): { events: SSEEvent[]; rest: string } {
  const events: SSEEvent[] = []
  const parts = buffer.split("\n\n")
  const rest = parts.pop() ?? ""
  for (const part of parts) {
    if (!part.trim()) continue
    const lines = part.split("\n")
    let event = "message"
    let data = ""
    for (const line of lines) {
      if (line.startsWith("event:")) event = line.slice(6).trim()
      else if (line.startsWith("data:")) data += line.slice(5).trimStart()
    }
    events.push({ event, data })
  }
  return { events, rest }
}

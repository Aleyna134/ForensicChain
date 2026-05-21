import client from './client'

export interface CustodyEvent {
  event_id: string
  event_type: string
  actor_id: string
  actor_role: string
  timestamp: string
  reason: string | null
  ip_address: string | null
  event_hash: string
  previous_event_hash: string | null
}

export interface Timeline {
  artifact_id: string
  total_events: number
  chain_valid: boolean
  events: CustodyEvent[]
}

export async function getTimeline(artifactId: string): Promise<Timeline> {
  const res = await client.get<Timeline>(`/custody/${artifactId}/timeline`)
  return res.data
}

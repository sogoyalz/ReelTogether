'use client'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { isAxiosError } from 'axios'
import { api } from './api'

type Film = { id:number; slug:string; title:string; poster_url:string|null; year:number; genres:string[] }
type Result = { movie_id:number; yes:number; vetoes:number; eligible:boolean; top_match:boolean; reason:string }
export type Room = { revision:string; id:string; title:string; state:string; round_id:number; is_host:boolean; expired:boolean; expires_at:string; winner_id:number|null; members:{account_id:number;username:string;is_host:boolean;complete:boolean}[]; preferences:{genres:string[];favorites:number[]}; favorite_movies:{id:number;title:string}[]; movies:Film[]; my_votes:Record<string,string>; results:Result[] }

export function useRoom(accountId: number | undefined, roomId: string) {
  const client = useQueryClient()
  const queryKey = ['movie-night', accountId, roomId]
  return useQuery({
    queryKey, enabled: !!accountId && !!roomId,
    queryFn: async () => {
      const cached = client.getQueryData<Room>(queryKey)
      if (cached) {
        const current = (await api.get<{revision:string}>(`/api/movie-nights/${roomId}/version`)).data
        if (current.revision === cached.revision) return cached
      }
      return (await api.get<Room>(`/api/movie-nights/${roomId}`)).data
    },
    retry: 2, refetchOnWindowFocus: true, refetchIntervalInBackground: false,
    refetchInterval: query => {
      const status = isAxiosError(query.state.error) ? query.state.error.response?.status : undefined
      if ([401,403,404,410].includes(status ?? 0) || query.state.data?.expired || query.state.data?.state === 'selected') return false
      if (query.state.error) return Math.min(30000, 5000 * 2 ** query.state.fetchFailureCount)
      return query.state.data?.state === 'revealed' ? 10000 : 3000
    },
  })
}

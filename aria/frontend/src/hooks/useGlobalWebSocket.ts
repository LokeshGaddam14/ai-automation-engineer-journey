import { useEffect, useCallback } from 'react';
import { useWebSocket } from './useWebSocket';
import { useStore } from '../store/useStore';
import { WS_BASE_URL, analyticsAPI } from '../services/api';
import type { LiveCall, Analytics } from '../types';

export function useGlobalWebSocket() {
  const {
    setWsConnected,
    setActiveCalls,
    updateActiveCall,
    removeActiveCall,
    setLiveStats,
  } = useStore();

  const handleMessage = useCallback(
    (data: unknown) => {
      if (!data || typeof data !== 'object') return;
      const msg = data as { type?: string; data?: unknown };

      if (msg.type === 'active_calls') {
        setActiveCalls((msg.data || []) as LiveCall[]);
      } else if (msg.type === 'call_update' && msg.data) {
        updateActiveCall(msg.data as LiveCall);
      } else if (msg.type === 'call_ended' && msg.data) {
        const ended = msg.data as { call_id?: string };
        if (ended.call_id) {
          removeActiveCall(ended.call_id);
        }
      } else if (msg.type === 'stats_update' && msg.data) {
        setLiveStats(msg.data as Analytics);
      }
    },
    [setActiveCalls, updateActiveCall, removeActiveCall, setLiveStats]
  );

  const { connected } = useWebSocket(`${WS_BASE_URL}/ws/live-calls`, handleMessage);

  useEffect(() => {
    setWsConnected(connected);
  }, [connected, setWsConnected]);

  // Initial REST fetch for stats on app mount
  useEffect(() => {
    analyticsAPI
      .getStats()
      .then((stats) => {
        setLiveStats(stats);
      })
      .catch((e) => {
        console.error('Failed to fetch initial stats:', e);
      });
  }, [setLiveStats]);
}

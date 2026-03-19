import { useState, useEffect, useCallback } from 'react';
import { useAuth } from './useAuth';
import { endpoint } from '../api';

export interface UserStats {
  total_scans: number;
  scans_this_month: number;
  avg_risk: number | null;
  avg_hemoglobin: number | null;
  high_concern_count: number;
  low_risk_count: number;
  last_scan_at: string | null;
}

export function useStats() {
  const { getAccessToken, isAuthenticated } = useAuth();
  const [stats, setStats] = useState<UserStats | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  const fetch_ = useCallback(async () => {
    const token = getAccessToken();
    if (!token) return;
    setIsLoading(true);
    try {
      const res = await fetch(endpoint('/api/auth/me/stats'), {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (res.ok) setStats(await res.json());
    } finally {
      setIsLoading(false);
    }
  }, [getAccessToken]);

  useEffect(() => {
    if (isAuthenticated) fetch_();
  }, [isAuthenticated, fetch_]);

  return { stats, isLoading, refresh: fetch_ };
}

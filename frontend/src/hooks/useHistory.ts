/**
 * Screening history hook — fetches and manages past screenings from the API.
 */

import { useState, useEffect, useCallback } from 'react';
import { useAuth } from './useAuth';

const API_BASE = (import.meta.env.VITE_API_BASE_URL ?? '').replace(/\/$/, '');
function endpoint(path: string): string {
  return API_BASE ? `${API_BASE}${path}` : path;
}

export interface ScreeningHistoryItem {
  uid: string;
  triage_band: string;
  triage_label: string;
  triage_score: number;
  anemia_risk: number | null;
  predicted_hemoglobin: number | null;
  confidence: number | null;
  screening_label: string | null;
  urgency_label: string | null;
  headline: string | null;
  guidance_source: string;
  processing_time_ms: number;
  created_at: string;
}

interface HistoryState {
  screenings: ScreeningHistoryItem[];
  total: number;
  page: number;
  pageSize: number;
  isLoading: boolean;
  error: string | null;
  loadMore: () => void;
  refresh: () => void;
  deleteScreening: (uid: string) => Promise<void>;
}

export function useHistory(): HistoryState {
  const { getAccessToken, isAuthenticated } = useAuth();
  const [screenings, setScreenings] = useState<ScreeningHistoryItem[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [pageSize] = useState(20);
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchPage = useCallback(async (pageNum: number, append = false) => {
    const token = getAccessToken();
    if (!token) return;

    setIsLoading(true);
    setError(null);
    try {
      const res = await fetch(
        endpoint(`/api/screenings?page=${pageNum}&page_size=${pageSize}`),
        { headers: { Authorization: `Bearer ${token}` } }
      );
      if (!res.ok) throw new Error('Failed to load screening history');
      const data = await res.json();
      setScreenings(prev => append ? [...prev, ...data.screenings] : data.screenings);
      setTotal(data.total);
      setPage(pageNum);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to load history');
    } finally {
      setIsLoading(false);
    }
  }, [getAccessToken, pageSize]);

  useEffect(() => {
    if (isAuthenticated) fetchPage(1);
  }, [isAuthenticated, fetchPage]);

  const loadMore = useCallback(() => {
    if (screenings.length < total) {
      fetchPage(page + 1, true);
    }
  }, [fetchPage, page, screenings.length, total]);

  const refresh = useCallback(() => {
    fetchPage(1);
  }, [fetchPage]);

  const deleteScreening = useCallback(async (uid: string) => {
    const token = getAccessToken();
    if (!token) return;
    try {
      const res = await fetch(endpoint(`/api/screenings/${uid}`), {
        method: 'DELETE',
        headers: { Authorization: `Bearer ${token}` },
      });
      if (!res.ok) throw new Error('Failed to delete screening');
      setScreenings(prev => prev.filter(s => s.uid !== uid));
      setTotal(prev => prev - 1);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  }, [getAccessToken]);

  return {
    screenings, total, page, pageSize,
    isLoading, error,
    loadMore, refresh, deleteScreening,
  };
}

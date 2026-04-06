/**
 * VirtualizedHistoryList — react-window-based virtualized list for screening history.
 *
 * Features:
 * - Renders only visible items (O(1) DOM nodes regardless of list size)
 * - Smooth scroll with AnimatePresence-compatible animations for visible items
 * - Load-more trigger when scrolling near the bottom
 * - Skeleton loader support
 */

import { memo, useCallback } from 'react';
import { FixedSizeList as List } from 'react-window';
import { motion, AnimatePresence } from 'framer-motion';
import {
  AlertTriangle, Clock, Trash2,
} from 'lucide-react';
import type { ScreeningHistoryItem } from '../../hooks/useHistory';

const E = [0.22, 1, 0.36, 1] as const;

/* ------------------------------------------------------------------ */
/*  Helpers                                                            */
/* ------------------------------------------------------------------ */

function bandColor(band?: string | null): string {
  switch (band) {
    case 'low_risk': return '#10B981';
    case 'moderate_risk': return '#F59E0B';
    case 'high_concern': return '#EF4444';
    case 'uncertain_retake_needed': return '#8B5CF6';
    default: return '#64748B';
  }
}

function bandLabel(band?: string | null): string {
  switch (band) {
    case 'low_risk': return 'Low Risk';
    case 'moderate_risk': return 'Moderate';
    case 'high_concern': return 'High Concern';
    case 'uncertain_retake_needed': return 'Retake Needed';
    default: return (band ?? 'unknown').replace(/_/g, ' ');
  }
}

function formatDateTime(date: string): string {
  return new Date(date).toLocaleDateString('en-US', {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
  });
}

/* ------------------------------------------------------------------ */
/*  Single row (memoized)                                             */
/* ------------------------------------------------------------------ */

interface HistoryRowProps {
  index: number;
  style: React.CSSProperties;
  data: {
    screenings: ScreeningHistoryItem[];
    onDelete: (uid: string) => void;
  };
}

const HistoryRow = memo(function HistoryRow({ index, style, data }: HistoryRowProps) {
  const { screenings, onDelete } = data;
  const screening = screenings[index];
  if (!screening) return null;

  const color = bandColor(screening.triage_band);

  return (
    <motion.div
      style={{
        ...style,
        padding: '0.75rem 1rem',
        display: 'grid',
        gridTemplateColumns: '8px minmax(0, 1fr) auto',
        gap: '0.75rem',
        alignItems: 'stretch',
        borderRadius: '0.75rem',
        background: 'rgba(255,255,255,0.02)',
        border: '1px solid rgba(255,255,255,0.06)',
        transition: 'background 0.2s, border-color 0.2s',
        marginBottom: '0.5rem',
        overflow: 'hidden',
      }}
      whileHover={{ background: 'rgba(255,255,255,0.05)', borderColor: 'rgba(255,255,255,0.1)' }}
      initial={{ opacity: 0, x: -8 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3, ease: E }}
    >
      {/* Color indicator */}
      <div
        style={{
          borderRadius: '999px',
          background: color,
          boxShadow: `0 0 10px ${color}44`,
          width: 8,
          alignSelf: 'stretch',
        }}
      />

      {/* Content */}
      <div style={{ minWidth: 0, display: 'flex', flexDirection: 'column', gap: '0.35rem' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', flexWrap: 'wrap' }}>
          <span
            style={{
              fontSize: '0.5rem',
              fontFamily: 'var(--mono)',
              textTransform: 'uppercase',
              letterSpacing: '0.1em',
              padding: '0.12rem 0.35rem',
              borderRadius: '0.3rem',
              background: `${color}15`,
              color,
              border: `1px solid ${color}28`,
              fontWeight: 700,
            }}
          >
            {bandLabel(screening.triage_band)}
          </span>
          {screening.urgency_label && (
            <span style={{ fontSize: '0.55rem', fontFamily: 'var(--mono)', color: 'var(--text-dim)', textTransform: 'uppercase', letterSpacing: '0.08em' }}>
              {screening.urgency_label}
            </span>
          )}
        </div>

        {screening.headline && (
          <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', lineHeight: 1.4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {screening.headline}
          </div>
        )}

        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', fontSize: '0.62rem', color: 'var(--text-dim)' }}>
          <Clock size={10} />
          <span>{formatDateTime(screening.created_at)}</span>
          {screening.anemia_risk !== null && (
            <>
              <span>|</span>
              <span>Risk: {Math.round(screening.anemia_risk * 100)}%</span>
            </>
          )}
          {screening.confidence !== null && (
            <>
              <span>|</span>
              <span>Confidence: {Math.round(screening.confidence * 100)}%</span>
            </>
          )}
        </div>
      </div>

      {/* Actions */}
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '0.25rem', justifyContent: 'center' }}>
        <button
          type="button"
          onClick={(e) => {
            e.stopPropagation();
            onDelete(screening.uid);
          }}
          style={{
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            color: 'rgba(239,68,68,0.5)',
            padding: '0.25rem',
            borderRadius: '0.35rem',
            display: 'flex',
            alignItems: 'center',
            transition: 'color 0.2s',
          }}
          onMouseEnter={(e) => (e.currentTarget.style.color = '#EF4444')}
          onMouseLeave={(e) => (e.currentTarget.style.color = 'rgba(239,68,68,0.5)')}
          title="Delete screening"
        >
          <Trash2 size={13} />
        </button>
      </div>
    </motion.div>
  );
});

/* ------------------------------------------------------------------ */
/*  Main virtualized list                                             */
/* ------------------------------------------------------------------ */

interface VirtualizedHistoryListProps {
  screenings: ScreeningHistoryItem[];
  isLoading: boolean;
  onDelete: (uid: string) => void;
  onLoadMore: () => void;
  hasMore: boolean;
  itemHeight?: number;
  maxVisibleItems?: number;
}

export function VirtualizedHistoryList({
  screenings,
  isLoading,
  onDelete,
  onLoadMore,
  hasMore,
  itemHeight = 110,
  maxVisibleItems = 8,
}: VirtualizedHistoryListProps) {
  const height = maxVisibleItems * itemHeight;

  const handleLoadMore = useCallback(
    ({ visibleStartIndex, visibleStopIndex }: { visibleStartIndex: number; visibleStopIndex: number }) => {
      if (hasMore && !isLoading && visibleStopIndex >= screenings.length - 3) {
        onLoadMore();
      }
    },
    [hasMore, isLoading, onLoadMore, screenings.length],
  );

  if (screenings.length === 0 && !isLoading) {
    return (
      <div
        style={{
          padding: '2.5rem 1rem',
          textAlign: 'center',
          color: 'var(--text-dim)',
          fontSize: '0.82rem',
          borderRadius: '1rem',
          background: 'rgba(255,255,255,0.02)',
          border: '1px solid rgba(255,255,255,0.05)',
        }}
      >
        No screenings yet. Run your first scan to unlock trends, follow-up insights, and history export.
      </div>
    );
  }

  const rowData = { screenings, onDelete };

  return (
    <div style={{ position: 'relative' }}>
      <List
        height={height}
        itemCount={screenings.length}
        itemSize={itemHeight}
        width="100%"
        itemData={rowData}
        onItemsRendered={handleLoadMore}
        style={{
          overflowX: 'hidden',
        }}
      >
        {HistoryRow}
      </List>

      {/* Load more indicator */}
      {isLoading && hasMore && (
        <div
          style={{
            textAlign: 'center',
            padding: '0.75rem',
            fontSize: '0.72rem',
            color: 'var(--text-dim)',
          }}
        >
          Loading more screenings...
        </div>
      )}

      {/* End of list */}
      {!hasMore && screenings.length > 0 && (
        <div
          style={{
            textAlign: 'center',
            padding: '0.5rem',
            fontSize: '0.65rem',
            color: 'var(--text-dim)',
            fontFamily: 'var(--mono)',
          }}
        >
          End of history
        </div>
      )}
    </div>
  );
}

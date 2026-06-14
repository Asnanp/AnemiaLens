/**
 * Real-time event service using Server-Sent Events (SSE)
 * Provides live updates for orders, kitchen display, and waiter notifications
 */
import { useState, useEffect, useCallback, useRef } from 'react';

export interface RealtimeEvent {
  type: 'order' | 'kitchen' | 'waiter' | 'service' | 'table';
  data: unknown;
  timestamp: number;
}

export interface OrderEvent {
  type: 'order';
  data: {
    orderId: number;
    tableCode: string;
    status: string;
    guestLabel: string;
    totalAmount: number;
  };
  timestamp: number;
}

export interface KitchenEvent {
  type: 'kitchen';
  data: {
    orderId: number;
    status: string;
    items: Array<{
      name: string;
      quantity: number;
      notes: string;
    }>;
  };
  timestamp: number;
}

export interface WaiterEvent {
  type: 'waiter';
  data: {
    tableCode: string;
    message: string;
    urgency: 'low' | 'medium' | 'high';
  };
  timestamp: number;
}

export interface ServiceEvent {
  type: 'service';
  data: {
    tableId: number;
    tableCode: string;
    requestType: string;
    status: string;
  };
  timestamp: number;
}

export interface TableEvent {
  type: 'table';
  data: {
    tableCode: string;
    status: string;
  };
  timestamp: number;
}

// Client-side SSE connection manager
export class RealtimeClient {
  private eventSource: EventSource | null = null;
  private listeners: Map<string, Set<(event: RealtimeEvent) => void>> = new Map();
  private reconnectAttempts = 0;
  private maxReconnectAttempts = 5;
  private reconnectDelay = 1000;

  constructor(private baseUrl: string = '/api/realtime') {}

  connect(eventTypes: string[] = ['order', 'kitchen', 'waiter', 'service', 'table']) {
    if (this.eventSource) {
      this.disconnect();
    }

    const url = `${this.baseUrl}?events=${eventTypes.join(',')}`;
    this.eventSource = new EventSource(url);

    this.eventSource.onopen = () => {
      console.log('Realtime connection established');
      this.reconnectAttempts = 0;
    };

    this.eventSource.onerror = (error) => {
      console.error('Realtime connection error:', error);
      this.handleReconnect();
    };

    this.eventSource.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data) as RealtimeEvent;
        this.notifyListeners(data.type, data);
      } catch (error) {
        console.error('Failed to parse realtime event:', error);
      }
    };

    // Set up type-specific listeners
    eventTypes.forEach(eventType => {
      this.eventSource!.addEventListener(eventType, (event) => {
        try {
          const data = JSON.parse((event as MessageEvent).data) as RealtimeEvent;
          this.notifyListeners(eventType, data);
        } catch (error) {
          console.error(`Failed to parse ${eventType} event:`, error);
        }
      });
    });
  }

  private handleReconnect() {
    if (this.reconnectAttempts < this.maxReconnectAttempts) {
      this.reconnectAttempts++;
      const delay = this.reconnectDelay * Math.pow(2, this.reconnectAttempts - 1);
      console.log(`Attempting to reconnect in ${delay}ms (attempt ${this.reconnectAttempts})`);
      setTimeout(() => {
        this.connect();
      }, delay);
    } else {
      console.error('Max reconnection attempts reached');
      this.disconnect();
    }
  }

  on(eventType: string, callback: (event: RealtimeEvent) => void) {
    if (!this.listeners.has(eventType)) {
      this.listeners.set(eventType, new Set());
    }
    this.listeners.get(eventType)!.add(callback);
  }

  off(eventType: string, callback: (event: RealtimeEvent) => void) {
    const listeners = this.listeners.get(eventType);
    if (listeners) {
      listeners.delete(callback);
    }
  }

  private notifyListeners(eventType: string, event: RealtimeEvent) {
    const listeners = this.listeners.get(eventType);
    if (listeners) {
      listeners.forEach(callback => callback(event));
    }
  }

  disconnect() {
    if (this.eventSource) {
      this.eventSource.close();
      this.eventSource = null;
    }
  }
}

// React hook for real-time updates
export function useRealtime(eventTypes: string[] = ['order', 'kitchen', 'waiter', 'service', 'table']) {
  const [isConnected, setIsConnected] = useState(false);
  const [lastEvent, setLastEvent] = useState<RealtimeEvent | null>(null);
  const clientRef = useRef<RealtimeClient | null>(null);

  useEffect(() => {
    const client = new RealtimeClient();
    clientRef.current = client;

    client.connect(eventTypes);

    client.on('connection', () => setIsConnected(true));
    client.on('error', () => setIsConnected(false));

    eventTypes.forEach(type => {
      client.on(type, (event) => {
        setLastEvent(event);
      });
    });

    return () => {
      client.disconnect();
    };
  }, [eventTypes]);

  const subscribe = useCallback((eventType: string, callback: (event: RealtimeEvent) => void) => {
    const client = clientRef.current;
    if (client) {
      client.on(eventType, callback);
      return () => client.off(eventType, callback);
    }
  }, []);

  return { isConnected, lastEvent, subscribe };
}

// Server-side SSE utilities
export function sendSSEEvent(res: any, event: RealtimeEvent) {
  res.write(`event: ${event.type}\n`);
  res.write(`data: ${JSON.stringify(event)}\n\n`);
}

export function setSSEHeaders(res: any) {
  res.setHeader('Content-Type', 'text/event-stream');
  res.setHeader('Cache-Control', 'no-cache, no-transform');
  res.setHeader('Connection', 'keep-alive');
  res.setHeader('X-Accel-Buffering', 'no'); // Disable nginx buffering
}
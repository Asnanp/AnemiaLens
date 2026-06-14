/**
 * Real-time event service using Server-Sent Events (SSE)
 * Provides live updates for orders, kitchen display, and waiter notifications
 */

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
import { NextRequest } from 'next/server';
import { sendSSEEvent, setSSEHeaders } from '@/lib/realtime';

export const dynamic = 'force-dynamic';

/**
 * SSE endpoint for real-time updates
 * Clients can subscribe to specific event types: order, kitchen, waiter, service, table
 * 
 * Example: /api/realtime?events=order,kitchen,waiter
 */
export async function GET(req: NextRequest) {
  const { searchParams } = new URL(req.url);
  const eventTypes = searchParams.get('events')?.split(',') || ['order', 'kitchen', 'waiter', 'service', 'table'];
  
  // Create a readable stream for SSE
  const stream = new ReadableStream({
    start(controller) {
      setSSEHeaders({
        setHeader: (name: string, value: string) => {
          // In Next.js, we handle headers differently
          // This is a placeholder for the actual header setting
        }
      });

      // Send initial connection message
      const connectEvent = {
        type: 'connection',
        data: { status: 'connected', eventTypes },
        timestamp: Date.now()
      };
      
      controller.enqueue(`event: connection\n`);
      controller.enqueue(`data: ${JSON.stringify(connectEvent)}\n\n`);

      // Simulate real-time events (replace with actual database polling/WebSocket)
      const interval = setInterval(() => {
        // This is a placeholder - in production, you'd use:
        // - PostgreSQL LISTEN/NOTIFY
        // - Redis pub/sub
        // - WebSocket connections
        // - Database change notifications
        
        const mockEvent = {
          type: eventTypes[Math.floor(Math.random() * eventTypes.length)],
          data: { message: 'Real-time update' },
          timestamp: Date.now()
        };
        
        controller.enqueue(`event: ${mockEvent.type}\n`);
        controller.enqueue(`data: ${JSON.stringify(mockEvent)}\n\n`);
      }, 5000);

      // Clean up on connection close
      req.signal?.addEventListener('abort', () => {
        clearInterval(interval);
        controller.close();
      });
    }
  });

  return new Response(stream, {
    headers: {
      'Content-Type': 'text/event-stream',
      'Cache-Control': 'no-cache, no-transform',
      'Connection': 'keep-alive',
      'X-Accel-Buffering': 'no',
    },
  });
}
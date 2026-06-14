/**
 * Enhanced real-time order polling with intelligent caching and change detection
 * Improves upon existing polling with delta updates and smart reconnection
 */

import { prisma } from './db';
import { getCachedLiveData, clearLiveDataCache } from './public-data-cache';

interface OrderUpdate {
  orderId: number;
  status: string;
  updatedAt: string;
  tableCode: string;
}

interface PollResult {
  updates: OrderUpdate[];
  lastTimestamp: string;
  hasChanges: boolean;
}

/**
 * Intelligent order polling with change detection
 * Only returns orders that have changed since the last poll
 */
export async function pollOrderUpdates(
  tableCode: string,
  lastTimestamp?: string
): Promise<PollResult> {
  const twoHoursAgo = new Date(Date.now() - 2 * 60 * 60 * 1000);
  
  const where: any = {
    table: { code: tableCode.toUpperCase() },
    status: { in: ['pending', 'approved', 'preparing', 'ready', 'served'] },
    createdAt: { gte: twoHoursAgo }
  };

  // If we have a last timestamp, only get orders updated since then
  if (lastTimestamp) {
    where.updatedAt = { gt: new Date(lastTimestamp) };
  }

  const orders = await getCachedLiveData(
    `order-updates:${tableCode}:${lastTimestamp || 'initial'}`,
    () => prisma.order.findMany({
      where,
      select: {
        id: true,
        status: true,
        updatedAt: true,
        table: { select: { code: true } }
      },
      orderBy: { updatedAt: 'desc' }
    })
  );

  const updates: OrderUpdate[] = orders.map(order => ({
    orderId: order.id,
    status: order.status,
    updatedAt: order.updatedAt.toISOString(),
    tableCode: order.table.code
  }));

  // Get the most recent timestamp for next poll
  const lastUpdate = orders[0]?.updatedAt || new Date();
  
  return {
    updates,
    lastTimestamp: lastUpdate.toISOString(),
    hasChanges: updates.length > 0
  };
}

/**
 * Poll for kitchen orders (orders that need attention)
 */
export async function pollKitchenOrders(lastTimestamp?: string): Promise<PollResult> {
  const where: any = {
    status: { in: ['approved', 'preparing'] }
  };

  if (lastTimestamp) {
    where.updatedAt = { gt: new Date(lastTimestamp) };
  }

  const orders = await getCachedLiveData(
    `kitchen-updates:${lastTimestamp || 'initial'}`,
    () => prisma.order.findMany({
      where,
      select: {
        id: true,
        status: true,
        updatedAt: true,
        table: { select: { code: true } },
        items: {
          select: {
            quantity: true,
            notes: true,
            menuItem: { select: { name: true } }
          }
        }
      },
      orderBy: { createdAt: 'desc' },
      take: 50
    })
  );

  const updates: OrderUpdate[] = orders.map(order => ({
    orderId: order.id,
    status: order.status,
    updatedAt: order.updatedAt.toISOString(),
    tableCode: order.table.code
  }));

  const lastUpdate = orders[0]?.updatedAt || new Date();
  
  return {
    updates,
    lastTimestamp: lastUpdate.toISOString(),
    hasChanges: updates.length > 0
  };
}

/**
 * Poll for service requests (waiter calls)
 */
export async function pollServiceRequests(lastTimestamp?: string) {
  const where: any = {
    status: 'pending'
  };

  if (lastTimestamp) {
    where.createdAt = { gt: new Date(lastTimestamp) };
  }

  const requests = await getCachedLiveData(
    `service-updates:${lastTimestamp || 'initial'}`,
    () => prisma.serviceRequest.findMany({
      where,
      select: {
        id: true,
        type: true,
        status: true,
        note: true,
        createdAt: true,
        table: { select: { code: true, name: true } }
      } as any,
      orderBy: { createdAt: 'desc' },
      take: 20
    })
  ) as any[];

  const lastUpdate = requests[0]?.createdAt ? new Date(requests[0].createdAt) : new Date();
  
  return {
    requests,
    lastTimestamp: lastUpdate.toISOString(),
    hasChanges: requests.length > 0
  };
}

/**
 * Smart polling hook with exponential backoff
 * Adjusts polling frequency based on activity
 */
export class SmartPoller {
  private interval: NodeJS.Timeout | null = null;
  private currentInterval = 1000; // Start at 1 second
  private minInterval = 1000;
  private maxInterval = 10000; // Max 10 seconds
  private activityDetected = false;

  constructor(
    private pollFunction: () => Promise<{ hasChanges: boolean }>,
    private onChange: (result: any) => void,
    private onError?: (error: Error) => void
  ) {}

  start() {
    this.poll();
  }

  private async poll() {
    try {
      const result = await this.pollFunction();
      
      if (result.hasChanges) {
        this.activityDetected = true;
        this.currentInterval = this.minInterval; // Reset to fast polling
        this.onChange(result);
      } else if (this.activityDetected) {
        // If we had activity but no changes, slow down gradually
        this.activityDetected = false;
        this.currentInterval = Math.min(this.currentInterval * 2, this.maxInterval);
      } else {
        // No activity for a while, poll slower
        this.currentInterval = Math.min(this.currentInterval * 1.5, this.maxInterval);
      }

      this.interval = setTimeout(() => this.poll(), this.currentInterval);
    } catch (error) {
      this.onError?.(error as Error);
      // Exponential backoff on error
      this.currentInterval = Math.min(this.currentInterval * 2, this.maxInterval);
      this.interval = setTimeout(() => this.poll(), this.currentInterval);
    }
  }

  stop() {
    if (this.interval) {
      clearTimeout(this.interval);
      this.interval = null;
    }
  }

  getCurrentInterval() {
    return this.currentInterval;
  }
}
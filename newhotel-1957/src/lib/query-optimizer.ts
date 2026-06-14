/**
 * Database query optimizer with intelligent select projection
 * Reduces over-fetching and improves query performance
 */

import { prisma } from './db';

/**
 * Optimized query builder with select projection
 */
export class QueryOptimizer {
  /**
   * Build optimized select object based on required fields
   */
  static buildSelect(fields: string[]): Record<string, boolean | object> {
    const select: Record<string, boolean | object> = {};
    
    fields.forEach(field => {
      if (field.includes('.')) {
        // Handle nested selects (e.g., 'table.code')
        const [relation, nestedField] = field.split('.');
        if (!select[relation]) {
          select[relation] = {};
        }
        if (typeof select[relation] === 'object') {
          (select[relation] as Record<string, boolean>)[nestedField] = true;
        }
      } else {
        select[field] = true;
      }
    });

    return select;
  }

  /**
   * Optimized menu item query with minimal data transfer
   */
  static async getMenuItems(options: {
    categoryId?: number;
    availableOnly?: boolean;
    fields?: string[];
  }) {
    const { categoryId, availableOnly, fields = ['id', 'name', 'price', 'image'] } = options;
    
    const where: any = {};
    if (categoryId) where.categoryId = categoryId;
    if (availableOnly) where.isAvailable = true;

    const select = this.buildSelect(fields);
    
    return prisma.menuItem.findMany({
      where,
      select: Object.keys(select).length > 0 ? select : undefined,
      orderBy: [{ isPopular: 'desc' }, { name: 'asc' }]
    });
  }

  /**
   * Optimized order query with intelligent relation loading
   */
  static async getOrder(orderId: number, options: {
    includeItems?: boolean;
    includeTable?: boolean;
    itemFields?: string[];
  }) {
    const { includeItems = true, includeTable = true, itemFields = ['id', 'quantity'] } = options;
    
    const select: any = {
      id: true,
      status: true,
      totalAmount: true,
      createdAt: true,
      updatedAt: true
    };

    if (includeTable) {
      select.table = {
        select: { id: true, code: true, name: true }
      };
    }

    if (includeItems) {
      select.items = {
        select: {
          id: true,
          quantity: true,
          notes: true,
          menuItem: {
            select: {
              id: true,
              name: true,
              price: true,
              isVeg: true,
              prepTime: true
            }
          }
        }
      };
    }

    return prisma.order.findUnique({
      where: { id: orderId },
      select
    });
  }

  /**
   * Batch query optimization for loading multiple related records
   */
  static async batchLoad<T>(
    ids: number[],
    model: 'menuItem' | 'order' | 'table' | 'category',
    select?: Record<string, boolean | object>
  ): Promise<T[]> {
    if (ids.length === 0) return [];

    let result: T[] = [];
    
    switch (model) {
      case 'menuItem':
        result = await prisma.menuItem.findMany({
          where: { id: { in: ids } },
          select: select as any
        }) as T[];
        break;
      case 'order':
        result = await prisma.order.findMany({
          where: { id: { in: ids } },
          select: select as any
        }) as T[];
        break;
      case 'table':
        result = await prisma.restaurantTable.findMany({
          where: { id: { in: ids } },
          select: select as any
        }) as T[];
        break;
      case 'category':
        result = await prisma.category.findMany({
          where: { id: { in: ids } },
          select: select as any
        }) as T[];
        break;
    }
    
    return result;
  }

  /**
   * Pagination helper with optimized counting
   */
  static async paginate<T>(
    model: 'menuItem' | 'order' | 'table',
    options: {
      where?: any;
      orderBy?: any;
      page?: number;
      limit?: number;
      select?: Record<string, boolean | object>;
    }
  ) {
    const { where = {}, orderBy = {}, page = 1, limit = 50, select } = options;
    const skip = (page - 1) * limit;

    let data: T[] = [];
    let total = 0;
    
    switch (model) {
      case 'menuItem':
        [data, total] = await Promise.all([
          prisma.menuItem.findMany({
            where,
            orderBy,
            skip,
            take: limit,
            select: select as any
          }) as Promise<T[]>,
          prisma.menuItem.count({ where })
        ]);
        break;
      case 'order':
        [data, total] = await Promise.all([
          prisma.order.findMany({
            where,
            orderBy,
            skip,
            take: limit,
            select: select as any
          }) as Promise<T[]>,
          prisma.order.count({ where })
        ]);
        break;
      case 'table':
        [data, total] = await Promise.all([
          prisma.restaurantTable.findMany({
            where,
            orderBy,
            skip,
            take: limit,
            select: select as any
          }) as Promise<T[]>,
          prisma.restaurantTable.count({ where })
        ]);
        break;
    }

    return {
      data,
      pagination: {
        page,
        limit,
        total,
        totalPages: Math.ceil(total / limit),
        hasNext: page * limit < total,
        hasPrev: page > 1
      }
    };
  }

  /**
   * Optimized full-text search with ranking
   */
  static async searchMenuItems(query: string, options: {
    limit?: number;
    categoryIds?: number[];
  }) {
    const { limit = 20, categoryIds } = options;
    const searchTerm = query.toLowerCase();

    const where: any = {
      isAvailable: true,
      OR: [
        { name: { contains: searchTerm, mode: 'insensitive' } },
        { description: { contains: searchTerm, mode: 'insensitive' } }
      ]
    };

    if (categoryIds && categoryIds.length > 0) {
      where.categoryId = { in: categoryIds };
    }

    return prisma.menuItem.findMany({
      where,
      select: {
        id: true,
        name: true,
        description: true,
        price: true,
        image: true,
        category: { select: { id: true, name: true, slug: true } },
        isVeg: true,
        isSpicy: true,
        isPopular: true,
        prepTime: true
      },
      orderBy: [
        { isPopular: 'desc' },
        { name: 'asc' }
      ],
      take: limit
    });
  }

  /**
   * Analytics query with date range optimization
   */
  static async getAnalytics(startDate: Date, endDate: Date) {
    const where = {
      createdAt: { gte: startDate, lte: endDate },
      status: { in: ['completed', 'served'] }
    };

    const [
      totalOrders,
      totalRevenue,
      popularItems,
      ordersByHour
    ] = await Promise.all([
      prisma.order.count({ where }),
      prisma.order.aggregate({
        where,
        _sum: { totalAmount: true }
      }),
      prisma.orderItem.groupBy({
        by: ['menuItemId'],
        where: {
          order: where
        },
        _sum: { quantity: true },
        orderBy: { _sum: { quantity: 'desc' } },
        take: 10
      }),
      // Hourly distribution
      prisma.$queryRaw<Array<{ hour: number; count: bigint }>>`
        SELECT EXTRACT(HOUR FROM "createdAt") as hour, COUNT(*) as count
        FROM "Order"
        WHERE "createdAt" >= ${startDate} AND "createdAt" <= ${endDate}
        AND status IN ('completed', 'served')
        GROUP BY hour
        ORDER BY hour
      `
    ]);

    // Fetch details for popular items
    const popularItemIds = popularItems.map(item => item.menuItemId);
    const itemDetails = await this.batchLoad(popularItemIds, 'menuItem', {
      name: true,
      price: true,
      category: { select: { name: true } }
    });

    return {
      totalOrders,
      totalRevenue: totalRevenue._sum.totalAmount || 0,
      popularItems: popularItems.map((item, index) => ({
        ...item,
        details: itemDetails[index]
      })),
      ordersByHour: ordersByHour.map(({ hour, count }) => ({
        hour: Number(hour),
        count: Number(count)
      }))
    };
  }
}
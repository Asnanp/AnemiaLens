/**
 * Premium Analytics Dashboard for Hotel Owners
 * Real-time insights, revenue tracking, and performance metrics
 */

'use client';

import { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import { 
  TrendingUp, 
  DollarSign, 
  Users, 
  Clock, 
  Star,
  ArrowUpRight,
  ArrowDownRight,
  Calendar,
  Download,
  RefreshCw
} from 'lucide-react';

interface AnalyticsData {
  totalRevenue: number;
  totalOrders: number;
  averageOrderValue: number;
  customerCount: number;
  revenueGrowth: number;
  orderGrowth: number;
  popularItems: Array<{
    name: string;
    orders: number;
    revenue: number;
    growth: number;
  }>;
  hourlyData: Array<{
    hour: number;
    orders: number;
    revenue: number;
  }>;
  recentActivity: Array<{
    id: number;
    type: 'order' | 'service' | 'review';
    message: string;
    time: string;
  }>;
}

export default function AnalyticsDashboard() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);
  const [dateRange, setDateRange] = useState('today');
  const [refreshing, setRefreshing] = useState(false);

  useEffect(() => {
    loadAnalytics();
  }, [dateRange]);

  const loadAnalytics = async () => {
    setLoading(true);
    try {
      // Simulated API call - replace with actual analytics endpoint
      await new Promise(resolve => setTimeout(resolve, 1000));
      
      // Mock data for demonstration
      setData({
        totalRevenue: 45230,
        totalOrders: 342,
        averageOrderValue: 132.18,
        customerCount: 289,
        revenueGrowth: 15.3,
        orderGrowth: 8.7,
        popularItems: [
          { name: 'Kerala Chicken Curry', orders: 89, revenue: 3560, growth: 12 },
          { name: 'Appam with Stew', orders: 76, revenue: 2280, growth: 8 },
          { name: 'Fish Moily', orders: 65, revenue: 2925, growth: 15 },
          { name: 'Beef Fry', orders: 58, revenue: 2900, growth: -3 },
          { name: 'Vegetable Thali', orders: 54, revenue: 1620, growth: 22 }
        ],
        hourlyData: Array.from({ length: 24 }, (_, i) => ({
          hour: i,
          orders: Math.floor(Math.random() * 30) + 5,
          revenue: Math.floor(Math.random() * 2000) + 500
        })),
        recentActivity: [
          { id: 1, type: 'order', message: 'New order from Table AC3 - ₹450', time: '2 min ago' },
          { id: 2, type: 'service', message: 'Table 5 requested water refill', time: '5 min ago' },
          { id: 3, type: 'review', message: '5-star review from Table 2', time: '12 min ago' },
          { id: 4, type: 'order', message: 'Order #1234 completed - ₹280', time: '15 min ago' },
          { id: 5, type: 'service', message: 'Table AC1 requested bill', time: '20 min ago' }
        ]
      });
    } catch (error) {
      console.error('Failed to load analytics:', error);
    } finally {
      setLoading(false);
    }
  };

  const handleRefresh = async () => {
    setRefreshing(true);
    await loadAnalytics();
    setRefreshing(false);
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-b-2 border-amber-500" />
      </div>
    );
  }

  if (!data) return null;

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-2xl font-bold text-stone-900 font-display">
            Analytics Dashboard
          </h2>
          <p className="text-stone-600 mt-1">
            Real-time insights for New Hotel 1957
          </p>
        </div>
        
        <div className="flex items-center gap-3">
          <select
            value={dateRange}
            onChange={(e) => setDateRange(e.target.value)}
            className="px-4 py-2 rounded-lg border border-stone-300 bg-white focus:outline-none focus:ring-2 focus:ring-amber-500"
          >
            <option value="today">Today</option>
            <option value="week">This Week</option>
            <option value="month">This Month</option>
            <option value="year">This Year</option>
          </select>
          
          <button
            onClick={handleRefresh}
            disabled={refreshing}
            className="p-2 rounded-lg border border-stone-300 hover:bg-stone-100 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-5 h-5 ${refreshing ? 'animate-spin' : ''}`} />
          </button>
          
          <button className="flex items-center gap-2 px-4 py-2 bg-amber-500 text-white rounded-lg hover:bg-amber-600 transition-colors">
            <Download className="w-4 h-4" />
            Export
          </button>
        </div>
      </div>

      {/* KPI Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6">
        <KPICard
          title="Total Revenue"
          value={`₹${data.totalRevenue.toLocaleString()}`}
          change={data.revenueGrowth}
          icon={<DollarSign className="w-5 h-5" />}
          positive
        />
        <KPICard
          title="Total Orders"
          value={data.totalOrders.toString()}
          change={data.orderGrowth}
          icon={<Clock className="w-5 h-5" />}
          positive
        />
        <KPICard
          title="Avg. Order Value"
          value={`₹${data.averageOrderValue.toFixed(2)}`}
          change={5.2}
          icon={<TrendingUp className="w-5 h-5" />}
          positive
        />
        <KPICard
          title="Customers"
          value={data.customerCount.toString()}
          change={12.8}
          icon={<Users className="w-5 h-5" />}
          positive
        />
      </div>

      {/* Charts Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        {/* Revenue Chart */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-white rounded-2xl p-6 shadow-lg border border-stone-200"
        >
          <h3 className="text-lg font-semibold text-stone-900 mb-4">
            Revenue Over Time
          </h3>
          <RevenueChart data={data.hourlyData} />
        </motion.div>

        {/* Popular Items */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="bg-white rounded-2xl p-6 shadow-lg border border-stone-200"
        >
          <h3 className="text-lg font-semibold text-stone-900 mb-4">
            Popular Items
          </h3>
          <div className="space-y-4">
            {data.popularItems.map((item, index) => (
              <div key={index} className="flex items-center justify-between">
                <div className="flex items-center gap-3">
                  <span className="text-lg font-bold text-amber-600 w-6">
                    {index + 1}
                  </span>
                  <div>
                    <p className="font-medium text-stone-900">{item.name}</p>
                    <p className="text-sm text-stone-600">
                      {item.orders} orders • ₹{item.revenue.toLocaleString()}
                    </p>
                  </div>
                </div>
                <div className={`flex items-center gap-1 text-sm ${
                  item.growth >= 0 ? 'text-green-600' : 'text-red-600'
                }`}>
                  {item.growth >= 0 ? (
                    <ArrowUpRight className="w-4 h-4" />
                  ) : (
                    <ArrowDownRight className="w-4 h-4" />
                  )}
                  {Math.abs(item.growth)}%
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      </div>

      {/* Recent Activity */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: 0.2 }}
        className="bg-white rounded-2xl p-6 shadow-lg border border-stone-200"
      >
        <h3 className="text-lg font-semibold text-stone-900 mb-4">
          Recent Activity
        </h3>
        <div className="space-y-3">
          {data.recentActivity.map((activity) => (
            <ActivityItem key={activity.id} {...activity} />
          ))}
        </div>
      </motion.div>
    </div>
  );
}

function KPICard({ 
  title, 
  value, 
  change, 
  icon, 
  positive 
}: { 
  title: string; 
  value: string; 
  change: number; 
  icon: React.ReactNode; 
  positive: boolean;
}) {
  return (
    <motion.div
      whileHover={{ scale: 1.02 }}
      className="bg-gradient-to-br from-white to-stone-50 rounded-2xl p-6 shadow-lg border border-stone-200"
    >
      <div className="flex items-start justify-between">
        <div>
          <p className="text-sm font-medium text-stone-600">{title}</p>
          <p className="text-3xl font-bold text-stone-900 mt-2">{value}</p>
        </div>
        <div className="p-3 bg-amber-100 rounded-xl">
          {icon}
        </div>
      </div>
      <div className={`flex items-center gap-1 mt-4 text-sm ${
        change >= 0 ? 'text-green-600' : 'text-red-600'
      }`}>
        {change >= 0 ? (
          <ArrowUpRight className="w-4 h-4" />
        ) : (
          <ArrowDownRight className="w-4 h-4" />
        )}
        <span className="font-semibold">{Math.abs(change)}%</span>
        <span className="text-stone-600 ml-1">vs last period</span>
      </div>
    </motion.div>
  );
}

function RevenueChart({ data }: { data: Array<{ hour: number; orders: number; revenue: number }> }) {
  const maxRevenue = Math.max(...data.map(d => d.revenue));

  return (
    <div className="h-48 flex items-end gap-1">
      {data.map((item) => {
        const height = (item.revenue / maxRevenue) * 100;
        return (
          <div
            key={item.hour}
            className="flex-1 bg-gradient-to-t from-amber-500 to-amber-300 rounded-t-lg hover:from-amber-600 hover:to-amber-400 transition-all cursor-pointer relative group"
            style={{ height: `${height}%` }}
          >
            <div className="absolute -top-8 left-1/2 -translate-x-1/2 bg-stone-900 text-white text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity whitespace-nowrap">
              ₹{item.revenue}
            </div>
          </div>
        );
      })}
    </div>
  );
}

function ActivityItem({ type, message, time }: { type: string; message: string; time: string }) {
  const icons = {
    order: <Clock className="w-4 h-4" />,
    service: <Star className="w-4 h-4" />,
    review: <Star className="w-4 h-4" />
  };

  const colors = {
    order: 'bg-blue-100 text-blue-600',
    service: 'bg-green-100 text-green-600',
    review: 'bg-amber-100 text-amber-600'
  };

  return (
    <div className="flex items-center gap-3 p-3 rounded-lg hover:bg-stone-50 transition-colors">
      <div className={`p-2 rounded-lg ${colors[type as keyof typeof colors]}`}>
        {icons[type as keyof typeof icons]}
      </div>
      <div className="flex-1">
        <p className="text-sm font-medium text-stone-900">{message}</p>
        <p className="text-xs text-stone-600">{time}</p>
      </div>
    </div>
  );
}
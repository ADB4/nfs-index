'use client';

import { Line } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function PriceChart({ data, listings }: { data: any[], listings: any[] }) {
  if (!listings || listings.length === 0) {
    return <div>No listings to display</div>;
  }

  const calculateTrendsFromListings = () => {
    const monthlyData = new Map();

    listings.forEach(listing => {
      if (!listing.sale_price || !listing.sale_date) return;

      const date = new Date(listing.sale_date);
      const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}-01`;

      if (!monthlyData.has(monthKey)) {
        monthlyData.set(monthKey, []);
      }
      monthlyData.get(monthKey).push(listing.sale_price);
    });

    const trends = Array.from(monthlyData.entries())
      .map(([period, prices]) => {
        return {
          period,
          avg_price: prices.reduce((a: any, b: any) => a + b, 0) / prices.length,
          min_price: Math.min(...prices),
          max_price: Math.max(...prices),
          count: prices.length
        };
      })
      .sort((a, b) => a.period.localeCompare(b.period));

    return trends;
  };

  const trendsToDisplay = calculateTrendsFromListings();

  if (trendsToDisplay.length === 0) {
    return <div>No price data available for chart</div>;
  }

  const chartData = {
    labels: trendsToDisplay.map(d => {
      const date = new Date(d.period);
      return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
    }),
    datasets: [
      {
        label: 'Average Price',
        data: trendsToDisplay.map(d => d.avg_price),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
      },
      {
        label: 'Max Price',
        data: trendsToDisplay.map(d => d.max_price),
        borderColor: '#ef4444',
        borderDash: [5, 5],
        fill: false,
      },
      {
        label: 'Min Price',
        data: trendsToDisplay.map(d => d.min_price),
        borderColor: '#10b981',
        borderDash: [5, 5],
        fill: false,
      },
    ],
  };

  const options = {
    responsive: true,
    maintainAspectRatio: false,
    plugins: {
      title: {
        display: true,
        text: 'Price Trends Over Time',
      },
      tooltip: {
        callbacks: {
          label: function(context: any) {
            return `${context.dataset.label}: $${context.parsed.y.toLocaleString()}`;
          }
        }
      }
    },
    scales: {
      y: {
        ticks: {
          callback: function(value: any) {
            return '$' + value.toLocaleString();
          }
        }
      }
    }
  };

  return (
    <div style={{ height: '400px', marginBottom: '30px' }}>
      <Line data={chartData} options={options} />
    </div>
  );
}
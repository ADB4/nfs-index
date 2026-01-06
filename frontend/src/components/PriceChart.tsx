'use client';

import { Scatter } from 'react-chartjs-2';
import {
  Chart as ChartJS,
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  TimeScale,
  Title,
  Tooltip,
  Legend,
  Filler
} from 'chart.js';
import 'chartjs-adapter-date-fns';

ChartJS.register(
  CategoryScale,
  LinearScale,
  PointElement,
  LineElement,
  TimeScale,
  Title,
  Tooltip,
  Legend,
  Filler
);

export default function PriceChart({ data, listings }: { data: any[], listings: any[] }) {
  if (!listings || listings.length === 0) {
    return <div>No listings to display</div>;
  }

  const salesData = listings
    .filter(l => l.sale_price && l.sale_date)
    .map(l => ({
      x: new Date(l.sale_date),
      y: l.sale_price
    }))
    .sort((a, b) => a.x.getTime() - b.x.getTime());

  if (salesData.length === 0) {
    return <div>No price data available for chart</div>;
  }

  const chartData = {
    datasets: [
      {
        label: 'Sale Price',
        data: salesData,
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.6)',
        pointRadius: 5,
        pointHoverRadius: 7,
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
            const date = new Date(context.parsed.x);
            return [
              `Price: $${context.parsed.y.toLocaleString()}`,
              `Date: ${date.toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' })}`
            ];
          }
        }
      }
    },
    scales: {
      x: {
        type: 'time' as const,
        time: {
          unit: 'month',
          displayFormats: {
            month: 'MMM yyyy'
          }
        },
        title: {
          display: true,
          text: 'Sale Date'
        }
      },
      y: {
        title: {
          display: true,
          text: 'Price'
        },
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
      <Scatter data={chartData} options={options} />
    </div>
  );
}
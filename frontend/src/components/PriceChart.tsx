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

export default function PriceChart({ data }: { data: any[] }) {
  if (!data || data.length === 0) {
    return <div>No data</div>;
  }

  const chartData = {
    labels: data.map(d => {
      const date = new Date(d.period);
      return date.toLocaleDateString('en-US', { year: 'numeric', month: 'short' });
    }),
    datasets: [
      {
        label: 'Average Price',
        data: data.map(d => d.avg_price),
        borderColor: '#3b82f6',
        backgroundColor: 'rgba(59, 130, 246, 0.1)',
        fill: true,
      },
      {
        label: 'Max Price',
        data: data.map(d => d.max_price),
        borderColor: '#ef4444',
        borderDash: [5, 5],
        fill: false,
      },
      {
        label: 'Min Price',
        data: data.map(d => d.min_price),
        borderColor: '#10b981',
        borderDash: [5, 5],
        fill: false,
      },
    ],
  };

  const options = {
    responsive: true,
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

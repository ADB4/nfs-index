'use client';

import { useEffect, useState } from 'react';
import { listingsAPI, analyticsAPI } from '@/lib/api';
import PriceChart from '@/components/PriceChart';
import StatCard from '@/components/StatCard';

type Model = {
  id: number;
  name: string;
  make_name: string;
};

export default function Home() {
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);
  const [listings, setListings] = useState<any[]>([]);
  const [trends, setTrends] = useState<any[]>([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    listingsAPI.getModels().then(res => {
      setModels(res.data);
      const slr = res.data.find((m: Model) => m.name === 'SLR McLaren');
      if (slr) setSelectedModel(slr);
    });
  }, []);

  useEffect(() => {
    if (!selectedModel) return;
    
    setLoading(true);
    Promise.all([
      listingsAPI.getListings({ model_id: selectedModel.id }),
      analyticsAPI.getTrends(selectedModel.id),
      analyticsAPI.getStats(selectedModel.id)
    ])
      .then(([listingsRes, trendsRes, statsRes]) => {
        setListings(listingsRes.data.listings);
        setTrends(trendsRes.data.trends);
        setStats(statsRes.data);
      })
      .finally(() => setLoading(false));
  }, [selectedModel]);

  const formatCurrency = (value: number | null) => {
    if (!value) return '-';
    return `$${value.toLocaleString()}`;
  };

  return (
    <>
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1 style={{ marginBottom: '20px' }}>NFS Index</h1>
      
      <div style={{ marginBottom: '30px' }}>
        <label style={{ marginRight: '10px', fontWeight: '500' }}>Model:</label>
        <select 
          value={selectedModel?.id || ''} 
          onChange={(e) => {
            const model = models.find(m => m.id === parseInt(e.target.value));
            setSelectedModel(model || null);
          }}
          style={{
            padding: '8px 12px',
            border: '1px solid #d1d5db',
            borderRadius: '6px',
            fontSize: '14px'
          }}
        >
          <option value="">Select a model...</option>
          {models.map(model => (
            <option key={model.id} value={model.id}>
              {model.make_name} {model.name}
            </option>
          ))}
        </select>
      </div>

      {loading && <p>Loading...</p>}

      {!loading && stats && (
        <div style={{ 
          display: 'grid', 
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', 
          gap: '15px',
          marginBottom: '30px' 
        }}>
          <StatCard label="Total Sales" value={stats.total_sales || 0} />
          <StatCard label="Average Price" value={formatCurrency(stats.avg_price)} />
          <StatCard 
            label="Price Range" 
            value={`${formatCurrency(stats.min_price)} - ${formatCurrency(stats.max_price)}`} 
          />
          <StatCard 
            label="Average Mileage" 
            value={stats.avg_mileage ? `${stats.avg_mileage.toLocaleString()} mi` : '-'} 
          />
        </div>
      )}

      {!loading && trends.length > 0 && (
        <div style={{ marginBottom: '40px' }}>
          <PriceChart data={trends} />
        </div>
      )}

      {!loading && listings.length > 0 && (
        <div>
          <h2 style={{ marginBottom: '15px' }}>Recent Sales</h2>
          <div style={{ overflowX: 'auto' }}>
            <table style={{ width: '100%', borderCollapse: 'collapse' }}>
              <thead>
                <tr style={{ borderBottom: '2px solid #e5e7eb' }}>
                  <th style={{ padding: '12px', textAlign: 'left', fontWeight: '600' }}>Date</th>
                  <th style={{ padding: '12px', textAlign: 'left', fontWeight: '600' }}>Year</th>
                  <th style={{ padding: '12px', textAlign: 'left', fontWeight: '600' }}>Trim</th>
                  <th style={{ padding: '12px', textAlign: 'right', fontWeight: '600' }}>Price</th>
                  <th style={{ padding: '12px', textAlign: 'right', fontWeight: '600' }}>Mileage</th>
                  <th style={{ padding: '12px', textAlign: 'center', fontWeight: '600' }}>Bids</th>
                  <th style={{ padding: '12px', textAlign: 'left', fontWeight: '600' }}>Source</th>
                </tr>
              </thead>
              <tbody>
                {listings.map((listing: any) => (
                  <tr key={listing.id} style={{ borderBottom: '1px solid #f3f4f6' }}>
                    <td style={{ padding: '12px' }}>
                      {listing.sale_date}
                    </td>
                    <td style={{ padding: '12px' }}>{listing.year}</td>
                    <td style={{ padding: '12px' }}>{listing.trim || '-'}</td>
                    <td style={{ padding: '12px', textAlign: 'right', fontWeight: '500' }}>
                      {formatCurrency(listing.sale_price)}
                    </td>
                    <td style={{ padding: '12px', textAlign: 'right' }}>
                      {listing.mileage?.toLocaleString() || '-'}
                    </td>
                    <td style={{ padding: '12px', textAlign: 'center' }}>
                      {listing.number_of_bids || '-'}
                    </td>
                    <td style={{ padding: '12px' }}>
                      <a 
                        href={listing.listing_url} 
                        target="_blank" 
                        rel="noopener noreferrer"
                        style={{ color: '#3b82f6', textDecoration: 'none' }}
                      >
                        {listing.source === 'bringatrailer' ? 'BaT' : 'C&B'}
                      </a>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </div>
    </>
  );
}

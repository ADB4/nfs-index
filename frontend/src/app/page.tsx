'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';
import PriceChart from "@/components/PriceChart";

const API_URL = 'http://localhost:5000/api';
type Model = {
  id: number;
  name: string;
  make_name: string;
};
export default function Home() {
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);
  const [listings, setListings] = useState([]);
  const [trends, setTrends] = useState([]);
  const [stats, setStats] = useState<any>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    axios.get(`${API_URL}/models`)
      .then((res: { data: any[]; }) => {
        setModels(res.data);
        const slr = res.data.find((m: any) => m.name === 'SLR McLaren');
        if (slr) setSelectedModel(slr);
      });
  }, []);

  useEffect(() => {
    if (selectedModel) {
      setLoading(true);
      
      Promise.all([
        axios.get(`${API_URL}/listings?model_id=${selectedModel.id}`),
        axios.get(`${API_URL}/analytics/trends?model_id=${selectedModel.id}`),
        axios.get(`${API_URL}/analytics/stats?model_id=${selectedModel.id}`)
      ]).then(([listingsRes, trendsRes, statsRes]) => {
        setListings(listingsRes.data.listings);
        setTrends(trendsRes.data.trends);
        setStats(statsRes.data);
        setLoading(false);
      });
    }
  }, [selectedModel]);

  return (
    <>
    <div style={{ padding: '20px', maxWidth: '1200px', margin: '0 auto' }}>
      <h1>NFS Index</h1>
      
      <div style={{ marginBottom: '20px' }}>
        <label>Model: </label>
        <select 
          value={selectedModel?.id || ''} 
          onChange={(e) => {
            const model = models.find((m: any) => m.id === parseInt(e.target.value));
            setSelectedModel(model || null);
          }}
        >
          <option value="">Select...</option>
          {models.map((model: any) => (
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
          gridTemplateColumns: 'repeat(auto-fit, minmax(150px, 1fr))', 
          gap: '15px',
          marginBottom: '30px' 
        }}>
          <div style={{ padding: '15px', background: '#f3f4f6', borderRadius: '8px' }}>
            <div style={{ fontSize: '12px', color: '#666' }}>Total Sales</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold' }}>{stats.total_sales}</div>
          </div>
          <div style={{ padding: '15px', background: '#f3f4f6', borderRadius: '8px' }}>
            <div style={{ fontSize: '12px', color: '#666' }}>Avg Price</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
              ${stats.avg_price?.toLocaleString()}
            </div>
          </div>
          <div style={{ padding: '15px', background: '#f3f4f6', borderRadius: '8px' }}>
            <div style={{ fontSize: '12px', color: '#666' }}>Price Range</div>
            <div style={{ fontSize: '18px', fontWeight: 'bold' }}>
              ${stats.min_price?.toLocaleString()} - ${stats.max_price?.toLocaleString()}
            </div>
          </div>
          <div style={{ padding: '15px', background: '#f3f4f6', borderRadius: '8px' }}>
            <div style={{ fontSize: '12px', color: '#666' }}>Avg Mileage</div>
            <div style={{ fontSize: '24px', fontWeight: 'bold' }}>
              {stats.avg_mileage?.toLocaleString()}
            </div>
          </div>
        </div>
      )}

      {!loading && trends.length > 0 && (
        <PriceChart data={trends} />
      )}

      {!loading && listings.length > 0 && (
        <>
          <h2>Recent Sales</h2>
          <table style={{ width: '100%', borderCollapse: 'collapse' }}>
            <thead>
              <tr style={{ borderBottom: '2px solid #ddd' }}>
                <th style={{ padding: '10px', textAlign: 'left' }}>Date</th>
                <th style={{ padding: '10px', textAlign: 'left' }}>Year</th>
                <th style={{ padding: '10px', textAlign: 'left' }}>Trim</th>
                <th style={{ padding: '10px', textAlign: 'right' }}>Price</th>
                <th style={{ padding: '10px', textAlign: 'right' }}>Mileage</th>
                <th style={{ padding: '10px', textAlign: 'center' }}>Bids</th>
                <th style={{ padding: '10px', textAlign: 'left' }}>Source</th>
              </tr>
            </thead>
            <tbody>
              {listings.map((listing: any) => (
                <tr key={listing.id} style={{ borderBottom: '1px solid #eee' }}>
                  <td style={{ padding: '10px' }}>{listing.sale_date}</td>
                  <td style={{ padding: '10px' }}>{listing.year}</td>
                  <td style={{ padding: '10px' }}>{listing.trim || '-'}</td>
                  <td style={{ padding: '10px', textAlign: 'right' }}>
                    ${listing.sale_price?.toLocaleString() || '-'}
                  </td>
                  <td style={{ padding: '10px', textAlign: 'right' }}>
                    {listing.mileage?.toLocaleString() || '-'}
                  </td>
                  <td style={{ padding: '10px', textAlign: 'center' }}>
                    {listing.number_of_bids || '-'}
                  </td>
                  <td style={{ padding: '10px' }}>
                    <a href={listing.listing_url} target="_blank" rel="noopener noreferrer">
                      {listing.source === 'bringatrailer' ? 'BaT' : 'C&B'}
                    </a>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </>
      )}
    </div>
    </>
  );
}

'use client';

import { useEffect, useState } from 'react';
import axios from 'axios';

type Model = {
  id: number;
  name: string;
  make_name: string;
};

export default function Home() {
  const [models, setModels] = useState<Model[]>([]);
  const [selectedModel, setSelectedModel] = useState<Model | null>(null);
  const [listings, setListings] = useState([]);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    axios.get('http://localhost:5000/api/models')
      .then(res => {
        setModels(res.data);
        const slr = res.data.find((m: any) => m.name === 'SLR McLaren');
        if (slr) setSelectedModel(slr);
      });
  }, []);

  useEffect(() => {
    if (selectedModel) {
      setLoading(true);
      axios.get(`http://localhost:5000/api/listings?model_id=${selectedModel.id}`)
        .then(res => {
          setListings(res.data.listings);
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

      {!loading && listings.length > 0 && (
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
      )}
    </div>
    </>
  );
}
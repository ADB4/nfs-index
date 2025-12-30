import axios from 'axios';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api';

const api = axios.create({
  baseURL: API_URL,
});

export const listingsAPI = {
  getListings: (params?: { model_id?: number; page?: number; per_page?: number }) =>
    api.get('/listings', { params }),
  
  getModels: () =>
    api.get('/models'),
};

export const analyticsAPI = {
  getTrends: (modelId: number) =>
    api.get('/analytics/trends', { params: { model_id: modelId } }),
  
  getStats: (modelId: number) =>
    api.get('/analytics/stats', { params: { model_id: modelId } }),
};

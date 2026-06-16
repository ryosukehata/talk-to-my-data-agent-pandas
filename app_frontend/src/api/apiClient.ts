import axios from 'axios';
import { getApiUrl } from '@/lib/utils';

const apiClient = axios.create({
  baseURL: getApiUrl(),
  headers: {
    Accept: 'application/json',
    'Content-type': 'application/json',
  },
  withCredentials: true,
});

export default apiClient;

export { apiClient };

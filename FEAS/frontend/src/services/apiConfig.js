/**
 * Global API & Media URL Configuration
 * 
 * Supports both local development (localhost:8000 via Vite proxy) and 
 * cloud deployment (Firebase Hosting frontend + Render backend).
 * 
 * Environment Variable:
 *   VITE_API_URL: e.g. "https://feas-backend.onrender.com"
 *   (Leave blank or unset in local development to use relative proxy).
 */

export const API_BASE_URL = (import.meta.env.VITE_API_URL || '').replace(/\/+$/, '');

/**
 * Resolve an API endpoint against the configured base URL.
 * @param {string} endpoint - e.g. "/api/v1/cctv/analyze"
 * @returns {string} Fully qualified URL or relative path
 */
export const getApiUrl = (endpoint = '') => {
  if (!endpoint) return API_BASE_URL;
  if (
    endpoint.startsWith('http://') || 
    endpoint.startsWith('https://') || 
    endpoint.startsWith('blob:') || 
    endpoint.startsWith('data:')
  ) {
    return endpoint;
  }
  const cleanPath = endpoint.startsWith('/') ? endpoint : `/${endpoint}`;
  return `${API_BASE_URL}${cleanPath}`;
};

/**
 * Resolve static artifact URLs (e.g. /results/cctv/... or /storage/...)
 * @param {string} mediaPath
 * @returns {string} Fully qualified URL or relative path
 */
export const getMediaUrl = (mediaPath = '') => {
  return getApiUrl(mediaPath);
};

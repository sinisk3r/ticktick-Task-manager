/**
 * Backend API Client
 *
 * Provides utilities for calling the FastAPI backend.
 */

// Get backend URL from localStorage if available, otherwise use environment variable or default
export const getApiBase = (): string => {
  if (typeof window !== 'undefined') {
    return localStorage.getItem('backend_url') || process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5400';
  }
  return process.env.NEXT_PUBLIC_API_URL || 'http://localhost:5400';
};

export const API_BASE = getApiBase();

interface ApiError {
  message: string;
  status: number;
  data?: any;
}

class APIClient {
  private baseURL: string;

  constructor(baseURL: string = API_BASE) {
    this.baseURL = baseURL;
  }

  /**
   * Generic fetch wrapper with error handling
   */
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseURL}${endpoint}`;

    const config: RequestInit = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...options.headers,
      },
    };

    try {
      const response = await fetch(url, config);

      if (!response.ok) {
        const error: ApiError = {
          message: `API Error: ${response.statusText}`,
          status: response.status,
        };

        try {
          error.data = await response.json();
        } catch {
          // Response body is not JSON
        }

        throw error;
      }

      // Handle empty responses
      const contentType = response.headers.get('content-type');
      if (contentType && contentType.includes('application/json')) {
        return await response.json();
      }

      return {} as T;
    } catch (error) {
      if (error instanceof Error && 'status' in error) {
        throw error; // Re-throw API errors
      }

      // Network or other errors
      throw {
        message: error instanceof Error ? error.message : 'Network error',
        status: 0,
      } as ApiError;
    }
  }

  /**
   * GET request
   */
  async get<T>(endpoint: string, options?: RequestInit): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'GET' });
  }

  /**
   * POST request
   */
  async post<T>(
    endpoint: string,
    data?: any,
    options?: RequestInit
  ): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'POST',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * PUT request
   */
  async put<T>(
    endpoint: string,
    data?: any,
    options?: RequestInit
  ): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PUT',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * PATCH request
   */
  async patch<T>(
    endpoint: string,
    data?: any,
    options?: RequestInit
  ): Promise<T> {
    return this.request<T>(endpoint, {
      ...options,
      method: 'PATCH',
      body: data ? JSON.stringify(data) : undefined,
    });
  }

  /**
   * DELETE request
   */
  async delete<T>(endpoint: string, options?: RequestInit): Promise<T> {
    return this.request<T>(endpoint, { ...options, method: 'DELETE' });
  }

  /**
   * Health check
   */
  async healthCheck(): Promise<{ status: string }> {
    return this.get('/health');
  }
}

// Export singleton instance
export const api = new APIClient();

// ============================================================================
// Settings API
// ============================================================================

export type LLMProvider = 'ollama' | 'openrouter' | 'anthropic' | 'openai' | 'gemini';

export interface Settings {
  id: number;
  user_id: number;
  llm_provider: LLMProvider;
  llm_model: string | null;
  llm_api_key: string | null;
  llm_base_url: string | null;
  llm_temperature: number | null;
  llm_max_tokens: number | null;
}

export interface SettingsUpdate {
  llm_provider?: LLMProvider;
  llm_model?: string;
  llm_api_key?: string;
  llm_base_url?: string;
  llm_temperature?: number;
  llm_max_tokens?: number;
}

export const settingsAPI = {
  /**
   * Get user settings for LLM configuration
   */
  async getSettings(userId: number): Promise<Settings> {
    return api.get(`/api/settings?user_id=${userId}`);
  },

  /**
   * Update user settings for LLM configuration
   */
  async updateSettings(userId: number, settings: SettingsUpdate): Promise<Settings> {
    return api.put(`/api/settings?user_id=${userId}`, settings);
  },
};

// Export types
export type { ApiError };

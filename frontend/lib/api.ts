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

      // Handle empty responses (204 No Content, etc.)
      if (response.status === 204 || response.headers.get('content-length') === '0') {
        return {} as T;
      }

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
// LLM Configuration API
// ============================================================================

export type LLMProvider = 'ollama' | 'openrouter' | 'anthropic' | 'openai' | 'gemini';

export interface LLMConfiguration {
  id: number;
  user_id: number;
  name: string;
  provider: LLMProvider;
  model: string;
  api_key?: string | null; // Masked in responses
  base_url?: string | null;
  temperature: number;
  max_tokens: number;
  is_default: boolean;
  connection_status: string;
  connection_error?: string | null;
  last_tested_at?: string | null;
  display_name: string;
  requires_api_key: boolean;
  requires_base_url: boolean;
  created_at: string;
  updated_at: string;
}

export interface LLMConfigurationCreate {
  name: string;
  provider: LLMProvider;
  model: string;
  api_key?: string;
  base_url?: string;
  temperature?: number;
  max_tokens?: number;
  is_default?: boolean;
}

export interface LLMConfigurationUpdate {
  name?: string;
  provider?: LLMProvider;
  model?: string;
  api_key?: string;
  base_url?: string;
  temperature?: number;
  max_tokens?: number;
  is_default?: boolean;
}

export interface ConnectionTestResult {
  success: boolean;
  error?: string;
  response_time_ms?: number;
  model_info?: Record<string, any>;
}

export interface ProviderDefaults {
  provider: string;
  model: string;
  has_api_key: boolean;
  base_url?: string | null;
}

export interface EnvDefaultsResponse {
  active_provider: string;
  providers: Record<string, ProviderDefaults>;
}

export const llmConfigAPI = {
  /**
   * Get default LLM configuration from environment variables
   */
  async getEnvDefaults(): Promise<EnvDefaultsResponse> {
    return api.get('/api/llm-configurations/defaults');
  },

  /**
   * List all LLM configurations for a user
   */
  async listConfigurations(userId: number): Promise<LLMConfiguration[]> {
    return api.get(`/api/llm-configurations?user_id=${userId}`);
  },

  /**
   * Create a new LLM configuration
   */
  async createConfiguration(userId: number, config: LLMConfigurationCreate): Promise<LLMConfiguration> {
    return api.post(`/api/llm-configurations?user_id=${userId}`, config);
  },

  /**
   * Get a specific LLM configuration
   */
  async getConfiguration(configId: number, userId: number): Promise<LLMConfiguration> {
    return api.get(`/api/llm-configurations/${configId}?user_id=${userId}`);
  },

  /**
   * Update an LLM configuration
   */
  async updateConfiguration(configId: number, userId: number, config: LLMConfigurationUpdate): Promise<LLMConfiguration> {
    return api.put(`/api/llm-configurations/${configId}?user_id=${userId}`, config);
  },

  /**
   * Delete an LLM configuration
   */
  async deleteConfiguration(configId: number, userId: number): Promise<{ message: string }> {
    return api.delete(`/api/llm-configurations/${configId}?user_id=${userId}`);
  },

  /**
   * Test connection to an LLM configuration
   */
  async testConnection(configId: number, userId: number): Promise<ConnectionTestResult> {
    return api.post(`/api/llm-configurations/${configId}/test?user_id=${userId}`);
  },

  /**
   * Set a configuration as active
   */
  async setActiveConfiguration(configId: number, userId: number): Promise<{ message: string; config_id: number }> {
    return api.post(`/api/llm-configurations/${configId}/set-active?user_id=${userId}`);
  },
};

// ============================================================================
// Settings API (Updated)
// ============================================================================

export interface ActiveLLMConfig {
  id: number;
  name: string;
  provider: LLMProvider;
  model: string;
  base_url?: string | null;
  temperature: number;
  max_tokens: number;
  connection_status: string;
  display_name: string;
}

export interface Settings {
  id: number;
  user_id: number;
  active_llm_config_id?: number | null;
  active_llm_config?: ActiveLLMConfig | null;
}

export interface SettingsUpdate {
  active_llm_config_id?: number | null;
}

export const settingsAPI = {
  /**
   * Get user settings including active LLM configuration
   */
  async getSettings(userId: number): Promise<Settings> {
    return api.get(`/api/settings?user_id=${userId}`);
  },

  /**
   * Update user settings (currently only active LLM config)
   */
  async updateSettings(userId: number, settings: SettingsUpdate): Promise<Settings> {
    return api.put(`/api/settings?user_id=${userId}`, settings);
  },
};

// Export types
export type { ApiError };

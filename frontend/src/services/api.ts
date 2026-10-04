import type {
  AnalyticsOverview,
  DomainAnalyticsItem,
  StateAnalyticsItem,
  RootCauseItem,
  FlaggedEntry,
  FlaggedConfig,
  GdbEntry,
  WhatsAppSimulateResponse,
  FarmerSession,
  WeeklyDigestItem,
  WeatherZone,
  CropSmartAdvisoryResponse
} from '../types';



const BASE_URL = '/api';

export const api = {
  // Analytics
  async getOverview(): Promise<AnalyticsOverview> {
    const res = await fetch(`${BASE_URL}/analytics/overview`);
    if (!res.ok) throw new Error(`Failed to load overview: ${res.statusText}`);
    return res.json();
  },

  async getDomains(): Promise<DomainAnalyticsItem[]> {
    const res = await fetch(`${BASE_URL}/analytics/domains`);
    if (!res.ok) throw new Error(`Failed to load domain stats: ${res.statusText}`);
    return res.json();
  },

  async getStates(): Promise<StateAnalyticsItem[]> {
    const res = await fetch(`${BASE_URL}/analytics/states`);
    if (!res.ok) throw new Error(`Failed to load state stats: ${res.statusText}`);
    return res.json();
  },

  async getRootCauses(): Promise<RootCauseItem[]> {
    const res = await fetch(`${BASE_URL}/analytics/root-causes`);
    if (!res.ok) throw new Error(`Failed to load root causes: ${res.statusText}`);
    return res.json();
  },

  // Flagged Reviews
  async getFlaggedQueue(status?: string): Promise<{ total: number; queue: FlaggedEntry[] }> {
    const url = status && status !== 'ALL'
      ? `${BASE_URL}/flagged/queue?status=${encodeURIComponent(status)}`
      : `${BASE_URL}/flagged/queue`;
    const res = await fetch(url);
    if (!res.ok) throw new Error(`Failed to load flagged queue: ${res.statusText}`);
    return res.json();
  },

  async resolveFlaggedEntry(
    gdbId: string,
    payload: {
      revised_answer_hi: string;
      revised_answer_en: string;
      reviewer_note: string;
      action?: string;
    }
  ): Promise<any> {
    const res = await fetch(`${BASE_URL}/flagged/${gdbId}/resolve`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`Failed to resolve entry: ${res.statusText}`);
    return res.json();
  },

  async getFlaggedConfig(): Promise<FlaggedConfig> {
    const res = await fetch(`${BASE_URL}/flagged/config`);
    if (!res.ok) throw new Error(`Failed to get config: ${res.statusText}`);
    return res.json();
  },

  async updateFlaggedConfig(config: FlaggedConfig): Promise<any> {
    const res = await fetch(`${BASE_URL}/flagged/config`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(config)
    });
    if (!res.ok) throw new Error(`Failed to update config: ${res.statusText}`);
    return res.json();
  },

  async getCronStatus(): Promise<any> {
    const res = await fetch(`${BASE_URL}/flagged/cron/status`);
    if (!res.ok) throw new Error(`Failed to get cron status: ${res.statusText}`);
    return res.json();
  },

  async triggerCronNow(): Promise<any> {
    const res = await fetch(`${BASE_URL}/flagged/cron/run-now`, { method: 'POST' });
    if (!res.ok) throw new Error(`Failed to trigger cron: ${res.statusText}`);
    return res.json();
  },

  async getGdbEntries(params?: {
    crop?: string;
    domain?: string;
    status?: string;
    is_flagged?: boolean;
    search?: string;
    page?: number;
    limit?: number;
  }): Promise<{ total: number; page: number; limit: number; entries: GdbEntry[] }> {
    const searchParams = new URLSearchParams();
    if (params?.crop) searchParams.set('crop', params.crop);
    if (params?.domain) searchParams.set('domain', params.domain);
    if (params?.status) searchParams.set('status', params.status);
    if (params?.is_flagged !== undefined) searchParams.set('is_flagged', String(params.is_flagged));
    if (params?.search) searchParams.set('search', params.search);
    if (params?.page) searchParams.set('page', String(params.page));
    if (params?.limit) searchParams.set('limit', String(params.limit));

    const res = await fetch(`${BASE_URL}/gdb/entries?${searchParams.toString()}`);
    if (!res.ok) throw new Error(`Failed to load GDB entries: ${res.statusText}`);
    return res.json();
  },

  async getGdbEntry(gdbId: string): Promise<GdbEntry> {
    const res = await fetch(`${BASE_URL}/gdb/entries/${gdbId}`);
    if (!res.ok) throw new Error(`Failed to load GDB entry: ${res.statusText}`);
    return res.json();
  },

  // WhatsApp Simulator
  async simulateWhatsAppTurn(payload: {
    phone_number: string;
    message_body?: string;
    farmer_state?: string;
    language?: string;
    input_type?: string;
    voice_audio_note?: string;
    button_value?: number;
    root_cause_selected?: string;
  }): Promise<WhatsAppSimulateResponse> {
    const res = await fetch(`${BASE_URL}/whatsapp/simulate-turn`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(payload)
    });
    if (!res.ok) throw new Error(`Failed to simulate WhatsApp: ${res.statusText}`);
    return res.json();
  },

  async getFarmerSession(phoneNumber: string): Promise<FarmerSession> {
    const res = await fetch(`${BASE_URL}/whatsapp/session/${encodeURIComponent(phoneNumber)}`);
    if (!res.ok) throw new Error(`Failed to load farmer session: ${res.statusText}`);
    return res.json();
  },

  async resetFarmerSession(phoneNumber: string): Promise<any> {
    const res = await fetch(`${BASE_URL}/whatsapp/session/${encodeURIComponent(phoneNumber)}/reset`, {
      method: 'POST'
    });
    if (!res.ok) throw new Error(`Failed to reset farmer session: ${res.statusText}`);
    return res.json();
  },

  // Weekly Digest
  async getWeeklyDigest(): Promise<WeeklyDigestItem> {
    const res = await fetch(`${BASE_URL}/digest/weekly`);
    if (!res.ok) throw new Error(`Failed to load weekly digest: ${res.statusText}`);
    return res.json();
  },

  // Weather
  async getWeatherAlerts(): Promise<WeatherZone[]> {
    const res = await fetch(`${BASE_URL}/weather/alerts`);
    if (!res.ok) throw new Error(`Failed to load weather alerts: ${res.statusText}`);
    const data = await res.json();
    if (data && Array.isArray(data.zones)) {
      return data.zones;
    }
    return Array.isArray(data) ? data : [];
  },

  async getCropAdvisory(crop: string, city = 'Ludhiana'): Promise<CropSmartAdvisoryResponse> {
    const res = await fetch(`${BASE_URL}/weather/crop-advisory?crop=${encodeURIComponent(crop)}&city=${encodeURIComponent(city)}`);
    if (!res.ok) throw new Error(`Failed to load crop advisory: ${res.statusText}`);
    return res.json();
  },

  async getCityWeather(city: string, crop = 'Wheat'): Promise<WeatherZone> {
    const res = await fetch(`${BASE_URL}/weather/city?city=${encodeURIComponent(city)}&crop=${encodeURIComponent(crop)}`);
    if (!res.ok) throw new Error(`Failed to load weather for ${city}: ${res.statusText}`);
    return res.json();
  },


  // Health
  async checkHealth(): Promise<{ status: string; project: string; version: string }> {
    const res = await fetch('/');
    if (!res.ok) throw new Error('Health check failed');
    return res.json();
  }
};

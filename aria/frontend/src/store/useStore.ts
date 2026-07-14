import { create } from 'zustand';
import type { Page } from '../types';

interface AppStore {
  // Navigation
  currentPage: Page;
  setCurrentPage: (page: Page) => void;

  // Sidebar
  sidebarCollapsed: boolean;
  toggleSidebar: () => void;

  // WebSocket connection status
  wsConnected: boolean;
  setWsConnected: (connected: boolean) => void;

  // Selected call for transcript view
  selectedCallId: string | null;
  setSelectedCallId: (id: string | null) => void;

  // Search state
  searchQuery: string;
  setSearchQuery: (q: string) => void;

  // Theme
  theme: 'light' | 'dark';
  toggleTheme: () => void;

  // Notification toast
  toast: { message: string; type: 'success' | 'error' | 'info' } | null;
  showToast: (message: string, type?: 'success' | 'error' | 'info') => void;
  clearToast: () => void;
}

export const useStore = create<AppStore>((set) => ({
  currentPage: 'dashboard',
  setCurrentPage: (page) => set({ currentPage: page }),

  sidebarCollapsed: false,
  toggleSidebar: () => set((s) => ({ sidebarCollapsed: !s.sidebarCollapsed })),

  wsConnected: false,
  setWsConnected: (connected) => set({ wsConnected: connected }),

  selectedCallId: null,
  setSelectedCallId: (id) => set({ selectedCallId: id }),

  searchQuery: '',
  setSearchQuery: (q) => set({ searchQuery: q }),

  theme: (localStorage.getItem('theme') as 'light' | 'dark') || 'dark',
  toggleTheme: () => set((s) => {
    const next = s.theme === 'dark' ? 'light' : 'dark';
    localStorage.setItem('theme', next);
    return { theme: next };
  }),

  toast: null,
  showToast: (message, type = 'info') => {
    set({ toast: { message, type } });
    setTimeout(() => set({ toast: null }), 3500);
  },
  clearToast: () => set({ toast: null }),
}));

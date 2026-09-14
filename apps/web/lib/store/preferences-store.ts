"use client";

import { create } from "zustand";
import { DEFAULT_PREFERENCES, type PreferencesState } from "@/types/preferences";

const STORAGE_KEY = "automind-preferences";

interface PreferencesStore {
  preferences: PreferencesState;
  update: (patch: Partial<PreferencesState>) => void;
  hydrate: () => void;
}

function loadInitial(): PreferencesState {
  if (typeof window === "undefined") return DEFAULT_PREFERENCES;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return DEFAULT_PREFERENCES;
    return { ...DEFAULT_PREFERENCES, ...(JSON.parse(raw) as Partial<PreferencesState>) };
  } catch {
    return DEFAULT_PREFERENCES;
  }
}

export const usePreferencesStore = create<PreferencesStore>((set, get) => ({
  preferences: DEFAULT_PREFERENCES,
  update: (patch) => {
    const next = { ...get().preferences, ...patch };
    if (typeof window !== "undefined") {
      window.localStorage.setItem(STORAGE_KEY, JSON.stringify(next));
    }
    set({ preferences: next });
  },
  hydrate: () => set({ preferences: loadInitial() }),
}));

/**
 * Svelte stores for global state management
 */

import { writable, derived } from 'svelte/store';
import type { Story, MapStory, VectorPoint, Frameworks, Stats, StoryType } from './api';

// Selected filters
export const selectedFramework = writable<string | null>(null);
export const selectedFrameworkCategory = writable<string | null>(null);
export const selectedStoryType = writable<string | null>(null);
export const searchQuery = writable<string>('');

// Data stores
export const stories = writable<Story[]>([]);
export const mapStories = writable<MapStory[]>([]);
export const vectorPoints = writable<VectorPoint[]>([]);
export const frameworks = writable<Frameworks>({});
export const storyTypes = writable<StoryType[]>([]);
export const stats = writable<Stats | null>(null);

// UI state
export const selectedStoryId = writable<string | null>(null);
export const isLoading = writable<boolean>(false);
export const viewMode = writable<'map' | 'vector' | 'list'>('map');
export const sidebarOpen = writable<boolean>(false);

// Performance state
export const performanceMode = writable<'high' | 'medium'>('high');

// Derived stores
export const frameworkCategories = derived(
  [frameworks, selectedFramework],
  ([$frameworks, $selectedFramework]) => {
    if (!$selectedFramework || !$frameworks[$selectedFramework]) {
      return [];
    }
    return Object.keys($frameworks[$selectedFramework].categories);
  }
);

export const filteredStoryTypes = derived(
  [frameworks, selectedFramework, selectedFrameworkCategory],
  ([$frameworks, $selectedFramework, $selectedFrameworkCategory]) => {
    if (!$selectedFramework || !$frameworks[$selectedFramework]) {
      return [];
    }
    const fw = $frameworks[$selectedFramework];
    if ($selectedFrameworkCategory && fw.categories[$selectedFrameworkCategory]) {
      return fw.categories[$selectedFrameworkCategory];
    }
    // Return all types in this framework
    const allTypes = new Set<string>();
    for (const types of Object.values(fw.categories)) {
      for (const type of types) {
        allTypes.add(type);
      }
    }
    return Array.from(allTypes);
  }
);

// Story type color mapping
export const storyTypeColors: Record<string, string> = {
  ghost: '#F472B6', // Pink 400
  shadow_person: '#A78BFA', // Violet 400
  cryptid: '#34D399', // Emerald 400
  ufo: '#60A5FA', // Blue 400
  alien_encounter: '#2DD4BF', // Teal 400
  haunting: '#E879F9', // Fuchsia 400
  poltergeist: '#FB7185', // Rose 400
  precognition: '#FBBF24', // Amber 400
  nde: '#FB923C', // Orange 400
  obe: '#22D3EE', // Cyan 400
  time_slip: '#818CF8', // Indigo 400
  doppelganger: '#F87171', // Red 400
  sleep_paralysis: '#94A3B8', // Slate 400
  possession: '#EF4444', // Red 500
  other: '#CBD5E1', // Slate 300
};

export function getStoryTypeColor(type: string | undefined): string {
  return storyTypeColors[type || ''] || '#95a5a6';
}

export function formatStoryType(type: string): string {
  return type
    .split('_')
    .map(word => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

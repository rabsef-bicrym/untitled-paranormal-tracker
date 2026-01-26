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
  ghost: '#9b59b6',
  shadow_person: '#2c3e50',
  cryptid: '#27ae60',
  ufo: '#3498db',
  alien_encounter: '#1abc9c',
  haunting: '#8e44ad',
  poltergeist: '#e74c3c',
  precognition: '#f39c12',
  nde: '#e67e22',
  obe: '#16a085',
  time_slip: '#2980b9',
  doppelganger: '#c0392b',
  sleep_paralysis: '#7f8c8d',
  possession: '#d35400',
  other: '#95a5a6',
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

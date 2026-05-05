// Shared source/category constants used across the application

export type Language = 'bn' | 'en';

export interface LocalizedText {
  bn: string;
  en: string;
}

const fallbackLanguage = (): Language => {
  if (typeof localStorage !== 'undefined') {
    const saved = localStorage.getItem('language');
    if (saved === 'bn' || saved === 'en') return saved;
  }
  if (typeof navigator !== 'undefined' && navigator.language?.toLowerCase().startsWith('bn')) {
    return 'bn';
  }
  return 'en';
};

export const getCurrentLanguage = (): Language => fallbackLanguage();

export const getLocalizedText = (value: string | LocalizedText, language: Language = getCurrentLanguage()): string => {
  if (typeof value === 'string') return value;
  return value[language] || value.en;
};

const sourceLabels = {
  prothom_alo: { bn: 'প্রথম আলো', en: 'Prothom Alo' },
  daily_star: { bn: 'ডেইলি স্টার', en: 'The Daily Star' },
  jugantor: { bn: 'যুগান্তর', en: 'Jugantor' },
  samakal: { bn: 'সমকাল', en: 'Samakal' },
  naya_diganta: { bn: 'নয়া দিগন্ত', en: 'Naya Diganta' },
  ittefaq: { bn: 'ইত্তেফাক', en: 'Ittefaq' },
} as const;

export const SOURCE_LABELS: Record<string, string> = new Proxy(sourceLabels as Record<string, LocalizedText>, {
  get(target, prop: string) {
    const label = target[prop];
    return label ? getLocalizedText(label) : prop;
  },
}) as unknown as Record<string, string>;

export const SOURCE_COLORS: Record<string, string> = {
  prothom_alo: 'bg-orange-500',
  daily_star: 'bg-sky-500',
  jugantor: 'bg-rose-500',
  samakal: 'bg-violet-500',
  naya_diganta: 'bg-green-500',
  ittefaq: 'bg-teal-500',
};

export const SOURCE_TEXT_COLORS: Record<string, string> = {
  prothom_alo: 'text-orange-400',
  daily_star: 'text-sky-400',
  jugantor: 'text-rose-400',
  samakal: 'text-violet-400',
  naya_diganta: 'text-green-400',
  ittefaq: 'text-teal-400',
};

export const SOURCE_LOGOS: Record<string, string> = {
  prothom_alo: '/prothomalo.png',
  daily_star: '/dailystar.png',
  jugantor: '/jugantor.png',
  samakal: '/samakal.png',
  naya_diganta: '/nayadiganta.png',
  ittefaq: '/ittefaq.png',
};

interface CategoryEntry {
  key: string;
  label: string;
  sublabel: string;
  icon: string;
  gradient: string;
  accent: string;
  bg: string;
  ring: string;
}

const createCategory = (
  key: string,
  label: LocalizedText,
  sublabel: LocalizedText,
  icon: string,
  gradient: string,
  accent: string,
  bg: string,
  ring: string,
): CategoryEntry => {
  const category = {
    key,
    label: label.en,
    sublabel: sublabel.en,
    icon,
    gradient,
    accent,
    bg,
    ring,
  } as CategoryEntry;

  Object.defineProperties(category, {
    label: {
      get: () => getLocalizedText(label),
      enumerable: true,
    },
    sublabel: {
      get: () => getLocalizedText(sublabel),
      enumerable: true,
    },
  });

  return category;
};

export const CATEGORIES: CategoryEntry[] = [
  createCategory('রাজনীতি', { bn: 'রাজনীতি', en: 'Politics' }, { bn: 'রাজনীতি', en: 'Politics' }, '🏛️', 'from-blue-500 to-indigo-600', 'border-blue-500', 'bg-blue-500/5', 'ring-blue-500/20'),
  createCategory('বিশ্ব', { bn: 'বিশ্ব', en: 'World' }, { bn: 'বিশ্ব', en: 'World' }, '🌍', 'from-emerald-500 to-teal-600', 'border-emerald-500', 'bg-emerald-500/5', 'ring-emerald-500/20'),
  createCategory('মতামত', { bn: 'মতামত', en: 'Opinion' }, { bn: 'মতামত', en: 'Opinion' }, '💬', 'from-amber-500 to-orange-600', 'border-amber-500', 'bg-amber-500/5', 'ring-amber-500/20'),
  createCategory('বাংলাদেশ', { bn: 'বাংলাদেশ', en: 'Bangladesh' }, { bn: 'বাংলাদেশ', en: 'Bangladesh' }, '🇧🇩', 'from-red-500 to-rose-600', 'border-red-500', 'bg-red-500/5', 'ring-red-500/20'),
];

interface CategoryMetaEntry {
  icon: string;
  text: string;
  gradient: string;
}

const createCategoryMeta = (icon: string, text: LocalizedText, gradient: string): CategoryMetaEntry => {
  const meta = { icon, text: text.en, gradient } as CategoryMetaEntry;
  Object.defineProperty(meta, 'text', {
    get: () => getLocalizedText(text),
    enumerable: true,
  });
  return meta;
};

export const CATEGORY_META: Record<string, CategoryMetaEntry> = {
  'রাজনীতি': createCategoryMeta('🏛️', { bn: 'রাজনীতি', en: 'Politics' }, 'from-blue-500 to-indigo-600'),
  'বিশ্ব': createCategoryMeta('🌍', { bn: 'বিশ্ব', en: 'World' }, 'from-emerald-500 to-teal-600'),
  'মতামত': createCategoryMeta('💬', { bn: 'মতামত', en: 'Opinion' }, 'from-amber-500 to-orange-600'),
  'বাংলাদেশ': createCategoryMeta('🇧🇩', { bn: 'বাংলাদেশ', en: 'Bangladesh' }, 'from-red-500 to-rose-600'),
};

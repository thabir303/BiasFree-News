// Shared source/category constants used across the application

export const SOURCE_LABELS: Record<string, string> = {
  prothom_alo: 'প্রথম আলো',
  daily_star: 'ডেইলি স্টার',
  jugantor: 'যুগান্তর',
  samakal: 'সমকাল',
  naya_diganta: 'নয়া দিগন্ত',
  ittefaq: 'ইত্তেফাক',
};

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

export const CATEGORIES = [
  { key: 'রাজনীতি', label: 'রাজনীতি', sublabel: 'Politics', icon: '🏛️', gradient: 'from-blue-500 to-indigo-600', accent: 'border-blue-500', bg: 'bg-blue-500/5', ring: 'ring-blue-500/20' },
  { key: 'বিশ্ব', label: 'বিশ্ব', sublabel: 'World', icon: '🌍', gradient: 'from-emerald-500 to-teal-600', accent: 'border-emerald-500', bg: 'bg-emerald-500/5', ring: 'ring-emerald-500/20' },
  { key: 'মতামত', label: 'মতামত', sublabel: 'Opinion', icon: '💬', gradient: 'from-amber-500 to-orange-600', accent: 'border-amber-500', bg: 'bg-amber-500/5', ring: 'ring-amber-500/20' },
  { key: 'বাংলাদেশ', label: 'বাংলাদেশ', sublabel: 'Bangladesh', icon: '🇧🇩', gradient: 'from-red-500 to-rose-600', accent: 'border-red-500', bg: 'bg-red-500/5', ring: 'ring-red-500/20' },
];

export const CATEGORY_META: Record<string, { icon: string; text: string; gradient: string }> = {
  'রাজনীতি': { icon: '🏛️', text: 'রাজনীতি (Politics)', gradient: 'from-blue-500 to-indigo-600' },
  'বিশ্ব':   { icon: '🌍', text: 'বিশ্ব (World)',       gradient: 'from-emerald-500 to-teal-600' },
  'মতামত':   { icon: '💬', text: 'মতামত (Opinion)',     gradient: 'from-amber-500 to-orange-600' },
  'বাংলাদেশ': { icon: '🇧🇩', text: 'বাংলাদেশ (Bangladesh)', gradient: 'from-red-500 to-rose-600' },
};

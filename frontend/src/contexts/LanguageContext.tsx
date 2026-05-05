import React, { createContext, useContext, useEffect, useMemo, useState, ReactNode } from 'react';
import type { Language } from '../constants/sources';
import { getLocalizedText } from '../constants/sources';

interface LanguageContextType {
  language: Language;
  setLanguage: (language: Language) => void;
  toggleLanguage: () => void;
  translate: (bn: string, en: string) => string;
}

const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export const LanguageProvider: React.FC<{ children: ReactNode }> = ({ children }) => {
  const [language, setLanguageState] = useState<Language>(() => {
    if (typeof localStorage !== 'undefined') {
      const saved = localStorage.getItem('language');
      if (saved === 'bn' || saved === 'en') return saved;
    }
    if (typeof navigator !== 'undefined' && navigator.language?.toLowerCase().startsWith('bn')) {
      return 'bn';
    }
    return 'en';
  });

  useEffect(() => {
    if (typeof localStorage !== 'undefined') {
      localStorage.setItem('language', language);
    }
    if (typeof document !== 'undefined') {
      document.documentElement.lang = language;
      document.documentElement.dir = 'ltr';
    }
  }, [language]);

  const setLanguage = (nextLanguage: Language) => {
    setLanguageState(nextLanguage);
  };

  const toggleLanguage = () => {
    setLanguageState((prev) => (prev === 'bn' ? 'en' : 'bn'));
  };

  const value = useMemo<LanguageContextType>(() => ({
    language,
    setLanguage,
    toggleLanguage,
    translate: (bn: string, en: string) => getLocalizedText({ bn, en }, language),
  }), [language]);

  return <LanguageContext.Provider value={value}>{children}</LanguageContext.Provider>;
};

export const useLanguage = (): LanguageContextType => {
  const context = useContext(LanguageContext);
  if (!context) throw new Error('useLanguage must be used within LanguageProvider');
  return context;
};
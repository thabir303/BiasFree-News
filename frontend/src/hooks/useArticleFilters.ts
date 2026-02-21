import { useState, useCallback } from 'react';

export interface FilterState {
  source: string;
  is_biased: string;
  date_from: string;
  date_to: string;
  skip: number;
  limit: number;
}

export const useArticleFilters = (initialLimit: number = 12) => {
  const [filters, setFilters] = useState<FilterState>({
    source: '',
    is_biased: '',
    date_from: '',
    date_to: '',
    skip: 0,
    limit: initialLimit,
  });

  const handleFilterChange = useCallback((key: string, value: any) => {
    if (key === 'skip') {
      setFilters((prev) => ({ ...prev, [key]: value }));
    } else {
      setFilters((prev) => ({ ...prev, [key]: value, skip: 0 }));
    }
  }, []);

  const handleClearAll = useCallback(() => {
    setFilters((prev) => ({ source: '', is_biased: '', date_from: '', date_to: '', skip: 0, limit: prev.limit }));
  }, []);

  const handlePageChange = useCallback((direction: 'next' | 'prev') => {
    setFilters((prev) => ({
      ...prev,
      skip: direction === 'next' ? prev.skip + prev.limit : Math.max(0, prev.skip - prev.limit),
    }));
  }, []);

  const handleDirectPageChange = useCallback((page: number) => {
    setFilters((prev) => ({ ...prev, skip: (page - 1) * prev.limit }));
  }, []);

  const getActiveFiltersCount = useCallback(() => {
    return [filters.source, filters.is_biased, filters.date_from, filters.date_to].filter(Boolean).length;
  }, [filters.source, filters.is_biased, filters.date_from, filters.date_to]);

  const getCurrentPage = useCallback(() => {
    return Math.floor(filters.skip / filters.limit) + 1;
  }, [filters.skip, filters.limit]);

  const getTotalPages = useCallback((total: number) => {
    return Math.ceil(total / filters.limit);
  }, [filters.limit]);

  return {
    filters,
    setFilters,
    handleFilterChange,
    handleClearAll,
    handlePageChange,
    handleDirectPageChange,
    getActiveFiltersCount,
    getCurrentPage,
    getTotalPages,
  };
};
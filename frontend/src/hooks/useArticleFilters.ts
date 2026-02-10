import { useState, useCallback } from 'react';

export interface FilterState {
  source: string;
  is_biased: string;
  skip: number;
  limit: number;
}

export const useArticleFilters = (initialLimit: number = 12) => {
  const [filters, setFilters] = useState<FilterState>({
    source: '',
    is_biased: '',
    skip: 0,
    limit: initialLimit,
  });

  const handleFilterChange = useCallback((key: string, value: any) => {
    setFilters((prev) => ({ ...prev, [key]: value, skip: 0 }));
  }, []);

  const handleClearAll = useCallback(() => {
    setFilters((prev) => ({ source: '', is_biased: '', skip: 0, limit: prev.limit }));
  }, []);

  const handlePageChange = useCallback((direction: 'next' | 'prev') => {
    setFilters((prev) => ({
      ...prev,
      skip: direction === 'next' ? prev.skip + prev.limit : Math.max(0, prev.skip - prev.limit),
    }));
  }, []);

  const getActiveFiltersCount = useCallback(() => {
    return [filters.source, filters.is_biased].filter(Boolean).length;
  }, [filters.source, filters.is_biased]);

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
    getActiveFiltersCount,
    getCurrentPage,
    getTotalPages,
  };
};
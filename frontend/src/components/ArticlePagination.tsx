interface ArticlePaginationProps {
  total: number;
  currentPage: number;
  totalPages: number;
  onPageChange: (page: number) => void;
  onPrevNext: (direction: 'next' | 'prev') => void;
  loading?: boolean;
}
import { ArrowLeft,ArrowRight } from 'lucide-react';

const ArticlePagination: React.FC<ArticlePaginationProps> = ({
  currentPage,
  totalPages,
  onPageChange,
  onPrevNext,
  loading = false,
}) => {
  if (loading || totalPages <= 1) return null;

  /* ── Build page number array with ellipsis ─── */
  const getPageNumbers = (): (number | '...')[] => {
    if (totalPages <= 7) return Array.from({ length: totalPages }, (_, i) => i + 1);
    const pages: (number | '...')[] = [1];
    const left = Math.max(2, currentPage - 1);
    const right = Math.min(totalPages - 1, currentPage + 1);
    if (left > 2) pages.push('...');
    for (let i = left; i <= right; i++) pages.push(i);
    if (right < totalPages - 1) pages.push('...');
    pages.push(totalPages);
    return pages;
  };

  return (
    <div className="flex items-center justify-center gap-1.5 pt-2 pb-4\">
      {/* Prev */}
      <button
        onClick={() => onPrevNext('prev')}
        disabled={currentPage === 1}
        className="inline-flex items-center gap-1 px-3.5 py-2 rounded-xl text-xs font-medium border border-gray-800/60 text-gray-400 hover:text-white hover:border-gray-700 hover:bg-gray-800/40 disabled:opacity-30 disabled:cursor-not-allowed transition-all\"
      >
        <ArrowLeft className='w-4 h-4'/>
        Prev
      </button>

      {/* Page numbers */}
      {getPageNumbers().map((p, i) =>
        p === '...' ? (
          <span key={`ellipsis-${i}`} className="w-9 h-9 flex items-center justify-center text-xs text-gray-600\">
            ···
          </span>
        ) : (
          <button
            key={p}
            onClick={() => onPageChange(p as number)}
            className={`w-9 h-9 rounded-xl text-xs font-medium transition-all ${
              p === currentPage
                ? 'bg-primary-500 text-white shadow-md shadow-primary-500/20'
                : 'text-gray-400 hover:text-white hover:bg-gray-800/60'
            }`}
          >
            {p}
          </button>
        )
      )}

      {/* Next */}
      <button
        onClick={() => onPrevNext('next')}
        disabled={currentPage === totalPages}
        className="inline-flex items-center gap-1 px-3.5 py-2 rounded-xl text-xs font-medium border border-gray-800/60 text-gray-400 hover:text-white hover:border-gray-700 hover:bg-gray-800/40 disabled:opacity-30 disabled:cursor-not-allowed transition-all\"
      >
        Next
        <span className=' '>
         <ArrowRight className='w-4 h-4' />
        </span>
      </button>
    </div>
  );
};

export default ArticlePagination;
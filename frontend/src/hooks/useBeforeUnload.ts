import { useEffect } from 'react';

/**
 * Shows a browser beforeunload warning when `active` is true.
 * Prevents accidental tab close during long operations.
 */
const useBeforeUnload = (active: boolean, message = 'Operation in progress. Are you sure you want to leave?') => {
  useEffect(() => {
    if (!active) return;

    const handler = (e: BeforeUnloadEvent) => {
      e.preventDefault();
      // Modern browsers ignore custom messages, but returnValue is still needed
      e.returnValue = message;
      return message;
    };

    window.addEventListener('beforeunload', handler);
    return () => window.removeEventListener('beforeunload', handler);
  }, [active, message]);
};

export default useBeforeUnload;

import { useEffect } from 'react';

const BASE_TITLE = 'BiasFree News';

/**
 * Sets the browser tab title. Resets to base title on unmount.
 */
const usePageTitle = (title?: string) => {
  useEffect(() => {
    document.title = title ? `${title} | ${BASE_TITLE}` : BASE_TITLE;
    return () => {
      document.title = BASE_TITLE;
    };
  }, [title]);
};

export default usePageTitle;

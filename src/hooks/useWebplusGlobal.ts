import { useEffect, useState } from 'react';
import { SET_GLOBALS_EVENT_TYPE, SetGlobalsEvent, OpenAiGlobals } from '../types/openai';

/**
 * Hook to read a specific global value from window.openai and listen for changes
 * @param key - The key from OpenAiGlobals to observe
 * @returns The current value of the global
 */
export function useWebplusGlobal<K extends keyof OpenAiGlobals>(
  key: K
): OpenAiGlobals[K] {
  const [value, setValue] = useState<OpenAiGlobals[K]>(
    () => window.openai?.[key]
  );

  useEffect(() => {
    const handleGlobalsChange = (event: SetGlobalsEvent) => {
      if (event.detail.globals[key] !== undefined) {
        setValue(event.detail.globals[key] as OpenAiGlobals[K]);
      }
    };

    window.addEventListener(SET_GLOBALS_EVENT_TYPE, handleGlobalsChange);

    return () => {
      window.removeEventListener(SET_GLOBALS_EVENT_TYPE, handleGlobalsChange);
    };
  }, [key]);

  return value;
}

import type { API, OpenAiGlobals, SetGlobalsEvent } from './openai';

declare global {
  interface Window {
    openai: API & OpenAiGlobals;
  }

  interface WindowEventMap {
    'openai:set_globals': SetGlobalsEvent;
  }
}

export {};

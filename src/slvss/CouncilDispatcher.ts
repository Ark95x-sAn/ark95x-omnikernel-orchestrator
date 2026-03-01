/**
 * CouncilDispatcher.ts - Decision Council for ARK95X
 * Analyzes chamber states and dispatches AI-driven decisions
 * ARK95X Omnikernel Orchestrator - SLVSS Module
 */

import { OllamaRouter } from './OllamaRouter';
import { ChamberRegistry, ChamberState, ChamberDecision } from './ChamberRegistry';

export class CouncilDispatcher {
  private router: OllamaRouter;
  private registry: ChamberRegistry;

  constructor(router: OllamaRouter, registry: ChamberRegistry) {
    this.router = router;
    this.registry = registry;
  }

  async dispatch(states: ChamberState[]): Promise<ChamberDecision[]> {
    const decisions: ChamberDecision[] = [];
    const overloaded = states.filter((s) => s.load > 5);
    const idle = states.filter((s) => s.status === 'idle' && s.taskQueue.length > 0);
    const errored = states.filter((s) => s.status === 'error');

    for (const chamber of errored) {
      decisions.push({
        chamber: chamber.name,
        action: 'restart',
        priority: 100,
        payload: { reason: 'error-recovery', previousStatus: chamber.status },
      });
    }

    for (const chamber of overloaded) {
      decisions.push({
        chamber: chamber.name,
        action: 'scale-up',
        priority: 80,
        payload: { currentLoad: chamber.load, threshold: 5 },
      });
    }

    for (const chamber of idle) {
      decisions.push({
        chamber: chamber.name,
        action: 'activate',
        priority: 60,
        payload: { pendingTasks: chamber.taskQueue.length },
      });
    }

    if (decisions.length === 0 && states.length > 0) {
      const analysis = await this.analyzeWithAI(states);
      if (analysis) decisions.push(...analysis);
    }

    decisions.sort((a, b) => b.priority - a.priority);
    console.log(`[CouncilDispatcher] ${decisions.length} decisions dispatched`);
    return decisions;
  }

  private async analyzeWithAI(states: ChamberState[]): Promise<ChamberDecision[]> {
    try {
      const summary = states.map((s) => `${s.name}: status=${s.status} load=${s.load} queue=${s.taskQueue.length} role=${this.registry.getRole(s.name)}`).join('\n');
      const prompt = `Analyze these chamber states and suggest optimizations. Return JSON array of {chamber, action, priority, payload}:\n${summary}`;
      const res = await this.router.routeAndGenerate(prompt, 'reasoning', 'You are the ARK95X Council. Analyze system chambers and output optimization decisions as JSON.');
      const parsed = this.extractJSON(res.response);
      return parsed || [];
    } catch (err) {
      console.error('[CouncilDispatcher] AI analysis failed:', err);
      return [];
    }
  }

  private extractJSON(text: string): ChamberDecision[] | null {
    try {
      const match = text.match(/\[[\s\S]*\]/);
      if (match) return JSON.parse(match[0]);
    } catch {}
    return null;
  }
}

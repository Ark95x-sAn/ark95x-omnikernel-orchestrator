/**
 * SLVSSRunner.ts - Sovereign Loop Velocity Scaling System
 * Wires to Ollama (localhost:11434) and Qdrant (localhost:6333)
 * ARK95X Omnikernel Orchestrator
 */

import { OllamaRouter } from './OllamaRouter';
import { QdrantMemory } from './QdrantMemory';
import { ChamberRegistry } from './ChamberRegistry';
import { CouncilDispatcher } from './CouncilDispatcher';
import { ScalingEngine } from './ScalingEngine';

export interface SLVSSConfig {
  ollamaHost: string;
  qdrantHost: string;
  chambers: string[];
  tickInterval: number;
  maxIterations: number;
}

const DEFAULT_CONFIG: SLVSSConfig = {
  ollamaHost: 'http://localhost:11434',
  qdrantHost: 'http://localhost:6333',
  chambers: ['alpha', 'beta', 'gamma', 'delta', 'epsilon', 'zeta', 'eta', 'theta', 'iota'],
  tickInterval: 5000,
  maxIterations: -1,
};

export class SLVSSRunner {
  private config: SLVSSConfig;
  private ollama: OllamaRouter;
  private memory: QdrantMemory;
  private registry: ChamberRegistry;
  private council: CouncilDispatcher;
  private scaling: ScalingEngine;
  private iteration = 0;
  private running = false;

  constructor(config: Partial<SLVSSConfig> = {}) {
    this.config = { ...DEFAULT_CONFIG, ...config };
    this.ollama = new OllamaRouter(this.config.ollamaHost);
    this.memory = new QdrantMemory(this.config.qdrantHost);
    this.registry = new ChamberRegistry(this.config.chambers);
    this.council = new CouncilDispatcher(this.ollama, this.registry);
    this.scaling = new ScalingEngine(this.ollama, this.memory);
  }

  async start(): Promise<void> {
    console.log('[SLVSS] Initializing Sovereign Loop...');
    await this.ollama.healthCheck();
    await this.memory.ensureCollection('slvss_state');
    this.running = true;

    while (this.running) {
      this.iteration++;
      console.log(`[SLVSS] ===== ITERATION #${this.iteration} =====`);

      const states = await this.registry.gatherStates();
      const decisions = await this.council.dispatch(states);

      for (const decision of decisions) {
        const result = await this.scaling.execute(decision);
        await this.memory.upsert('slvss_state', {
          iteration: this.iteration,
          chamber: decision.chamber,
          action: decision.action,
          result: result.status,
          timestamp: Date.now(),
        });
      }

      await this.memory.upsert('slvss_telemetry', {
        iteration: this.iteration,
        decisionsCount: decisions.length,
        timestamp: Date.now(),
      });

      if (this.config.maxIterations > 0 && this.iteration >= this.config.maxIterations) {
        console.log('[SLVSS] Max iterations reached. Stopping.');
        this.running = false;
        break;
      }

      await this.sleep(this.config.tickInterval);
    }
  }

  async stop(): Promise<void> {
    this.running = false;
    console.log('[SLVSS] Loop stopped.');
  }

  status(): { running: boolean; iteration: number } {
    return { running: this.running, iteration: this.iteration };
  }

  private sleep(ms: number): Promise<void> {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }
}

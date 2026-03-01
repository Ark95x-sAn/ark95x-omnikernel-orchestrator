/**
 * ScalingEngine.ts - Execution & Scaling Engine for ARK95X
 * Executes council decisions and manages resource scaling
 * ARK95X Omnikernel Orchestrator - SLVSS Module
 */

import { OllamaRouter } from './OllamaRouter';
import { QdrantMemory } from './QdrantMemory';
import { ChamberDecision } from './ChamberRegistry';

export interface ExecutionResult {
  decision: ChamberDecision;
  status: 'success' | 'failed' | 'skipped';
  duration: number;
  output?: string;
  error?: string;
}

export interface ScalingMetrics {
  totalExecutions: number;
  successCount: number;
  failCount: number;
  avgDuration: number;
  scalingEvents: number;
}

export class ScalingEngine {
  private router: OllamaRouter;
  private memory: QdrantMemory;
  private metrics: ScalingMetrics = {
    totalExecutions: 0,
    successCount: 0,
    failCount: 0,
    avgDuration: 0,
    scalingEvents: 0,
  };

  constructor(router: OllamaRouter, memory: QdrantMemory) {
    this.router = router;
    this.memory = memory;
  }

  async execute(decision: ChamberDecision): Promise<ExecutionResult> {
    const start = Date.now();
    this.metrics.totalExecutions++;
    try {
      let output: string;
      switch (decision.action) {
        case 'restart':
          output = await this.handleRestart(decision);
          break;
        case 'scale-up':
          output = await this.handleScaleUp(decision);
          break;
        case 'scale-down':
          output = await this.handleScaleDown(decision);
          break;
        case 'activate':
          output = await this.handleActivate(decision);
          break;
        case 'optimize':
          output = await this.handleOptimize(decision);
          break;
        default:
          output = await this.handleGeneric(decision);
      }
      const duration = Date.now() - start;
      this.metrics.successCount++;
      this.updateAvgDuration(duration);
      return { decision, status: 'success', duration, output };
    } catch (err: any) {
      const duration = Date.now() - start;
      this.metrics.failCount++;
      this.updateAvgDuration(duration);
      return { decision, status: 'failed', duration, error: err.message };
    }
  }

  private async handleRestart(d: ChamberDecision): Promise<string> {
    console.log(`[ScalingEngine] Restarting chamber: ${d.chamber}`);
    await this.memory.upsert('scaling_events', {
      payload: { type: 'restart', chamber: d.chamber, timestamp: Date.now(), reason: d.payload.reason },
    });
    this.metrics.scalingEvents++;
    return `Chamber ${d.chamber} restart initiated`;
  }

  private async handleScaleUp(d: ChamberDecision): Promise<string> {
    console.log(`[ScalingEngine] Scaling UP: ${d.chamber} (load: ${d.payload.currentLoad})`);
    const res = await this.router.routeAndGenerate(
      `Chamber ${d.chamber} is overloaded at ${d.payload.currentLoad}. Suggest resource allocation strategy.`,
      'reasoning'
    );
    await this.memory.upsert('scaling_events', {
      payload: { type: 'scale-up', chamber: d.chamber, timestamp: Date.now(), aiSuggestion: res.response.substring(0, 200) },
    });
    this.metrics.scalingEvents++;
    return `Scale-up: ${res.response.substring(0, 100)}`;
  }

  private async handleScaleDown(d: ChamberDecision): Promise<string> {
    console.log(`[ScalingEngine] Scaling DOWN: ${d.chamber}`);
    this.metrics.scalingEvents++;
    return `Chamber ${d.chamber} scaled down`;
  }

  private async handleActivate(d: ChamberDecision): Promise<string> {
    console.log(`[ScalingEngine] Activating: ${d.chamber} (${d.payload.pendingTasks} tasks pending)`);
    return `Chamber ${d.chamber} activated with ${d.payload.pendingTasks} pending tasks`;
  }

  private async handleOptimize(d: ChamberDecision): Promise<string> {
    const res = await this.router.routeAndGenerate(
      `Optimize chamber ${d.chamber} with current config: ${JSON.stringify(d.payload)}`,
      'reasoning'
    );
    return `Optimization: ${res.response.substring(0, 100)}`;
  }

  private async handleGeneric(d: ChamberDecision): Promise<string> {
    console.log(`[ScalingEngine] Generic action '${d.action}' on ${d.chamber}`);
    return `Executed ${d.action} on ${d.chamber}`;
  }

  private updateAvgDuration(duration: number): void {
    const n = this.metrics.totalExecutions;
    this.metrics.avgDuration += (duration - this.metrics.avgDuration) / n;
  }

  getMetrics(): ScalingMetrics {
    return { ...this.metrics };
  }
}

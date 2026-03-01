/**
 * ChamberRegistry.ts - HLM-9 Chamber State Manager
 * Manages the 9 sovereign chambers (alpha through iota)
 * ARK95X Omnikernel Orchestrator - SLVSS Module
 */

export interface ChamberState {
  id: string;
  name: string;
  status: 'idle' | 'active' | 'processing' | 'error' | 'scaling';
  load: number;
  lastTick: number;
  taskQueue: string[];
  metrics: {
    processed: number;
    errors: number;
    avgLatency: number;
  };
}

export interface ChamberDecision {
  chamber: string;
  action: string;
  priority: number;
  payload: Record<string, unknown>;
}

const CHAMBER_ROLES: Record<string, string> = {
  alpha: 'command-routing',
  beta: 'data-ingestion',
  gamma: 'browser-ops',
  delta: 'financial-analysis',
  epsilon: 'clone-management',
  zeta: 'memory-persistence',
  eta: 'scaling-decisions',
  theta: 'security-gatekeeper',
  iota: 'telemetry-reporting',
};

export class ChamberRegistry {
  private chambers: Map<string, ChamberState> = new Map();
  private chamberNames: string[];

  constructor(chamberNames: string[]) {
    this.chamberNames = chamberNames;
    for (const name of chamberNames) {
      this.chambers.set(name, {
        id: crypto.randomUUID(),
        name,
        status: 'idle',
        load: 0,
        lastTick: Date.now(),
        taskQueue: [],
        metrics: { processed: 0, errors: 0, avgLatency: 0 },
      });
    }
    console.log(`[ChamberRegistry] Initialized ${chamberNames.length} chambers`);
  }

  async gatherStates(): Promise<ChamberState[]> {
    const states: ChamberState[] = [];
    for (const [, chamber] of this.chambers) {
      chamber.lastTick = Date.now();
      states.push({ ...chamber });
    }
    return states;
  }

  getChamber(name: string): ChamberState | undefined {
    return this.chambers.get(name);
  }

  updateChamber(name: string, update: Partial<ChamberState>): void {
    const chamber = this.chambers.get(name);
    if (!chamber) return;
    Object.assign(chamber, update);
  }

  setChamberStatus(name: string, status: ChamberState['status']): void {
    const chamber = this.chambers.get(name);
    if (chamber) chamber.status = status;
  }

  enqueueTask(chamberName: string, task: string): void {
    const chamber = this.chambers.get(chamberName);
    if (chamber) {
      chamber.taskQueue.push(task);
      chamber.load = chamber.taskQueue.length;
    }
  }

  dequeueTask(chamberName: string): string | undefined {
    const chamber = this.chambers.get(chamberName);
    if (!chamber) return undefined;
    const task = chamber.taskQueue.shift();
    chamber.load = chamber.taskQueue.length;
    return task;
  }

  getRole(chamberName: string): string {
    return CHAMBER_ROLES[chamberName] || 'unknown';
  }

  getActiveChambers(): ChamberState[] {
    return Array.from(this.chambers.values()).filter((c) => c.status === 'active' || c.status === 'processing');
  }

  getOverloadedChambers(threshold: number = 5): ChamberState[] {
    return Array.from(this.chambers.values()).filter((c) => c.load >= threshold);
  }

  recordMetric(chamberName: string, latency: number, isError: boolean = false): void {
    const chamber = this.chambers.get(chamberName);
    if (!chamber) return;
    chamber.metrics.processed++;
    if (isError) chamber.metrics.errors++;
    const prev = chamber.metrics.avgLatency;
    const count = chamber.metrics.processed;
    chamber.metrics.avgLatency = prev + (latency - prev) / count;
  }

  getAllNames(): string[] {
    return [...this.chamberNames];
  }

  toJSON(): Record<string, ChamberState> {
    const obj: Record<string, ChamberState> = {};
    for (const [k, v] of this.chambers) obj[k] = { ...v };
    return obj;
  }
}

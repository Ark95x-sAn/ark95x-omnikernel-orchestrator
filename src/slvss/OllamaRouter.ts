/**
 * OllamaRouter.ts - Sovereign 9-Model HLM Router for ARK95X
 * Routes inference across 9 Ollama models aligned to HLM-9 neural channels
 * Browser operations sync, advancement systems, alignment level-ups
 * ARK95X Omnikernel Orchestrator - SLVSS Module
 */

export interface OllamaModel {
  name: string;
  size: number;
  digest: string;
  modifiedAt: string;
}

export interface GenerateRequest {
  model: string;
  prompt: string;
  system?: string;
  temperature?: number;
  stream?: boolean;
  context?: number[];
}

export interface GenerateResponse {
  model: string;
  response: string;
  context: number[];
  totalDuration: number;
  evalCount: number;
  channel?: string;
  alignmentLevel?: number;
}

export interface EmbeddingResponse {
  embedding: number[];
}

export interface RouterMetrics {
  totalRequests: number;
  totalLatency: number;
  modelHits: Record<string, number>;
  errors: number;
  lastHealthCheck: number;
  channelSync: Record<string, ChannelState>;
}

export interface ChannelState {
  model: string;
  level: number;
  xp: number;
  xpToNext: number;
  status: 'idle' | 'active' | 'syncing' | 'advancing';
  lastSync: number;
}

export interface BrowserOpsState {
  activeTabs: number;
  syncedAgents: string[];
  lastBrowserSync: number;
  operationsQueue: string[];
}

const HLM9_CHANNELS: Record<string, { model: string; priority: number; role: string }> = {
  alpha:   { model: 'deepseek-r1:latest',       priority: 100, role: 'reasoning-core' },
  beta:    { model: 'llama3.1:70b',              priority: 95,  role: 'analysis-engine' },
  gamma:   { model: 'mixtral:8x7b',              priority: 90,  role: 'general-ops' },
  delta:   { model: 'llama3.1:8b',               priority: 85,  role: 'fast-response' },
  epsilon: { model: 'mistral:latest',            priority: 80,  role: 'task-executor' },
  zeta:    { model: 'phi3:latest',               priority: 75,  role: 'light-compute' },
  eta:     { model: 'codellama:34b',             priority: 70,  role: 'code-generation' },
  theta:   { model: 'nomic-embed-text:latest',   priority: 65,  role: 'embedding-memory' },
  iota:    { model: 'qwen2:7b',                  priority: 60,  role: 'browser-ops' },
};

const TASK_MODEL_MAP: Record<string, string[]> = {
  reasoning:  ['alpha', 'beta', 'gamma'],
  code:       ['alpha', 'eta', 'beta'],
  embedding:  ['theta'],
  fast:       ['delta', 'epsilon', 'zeta'],
  general:    ['gamma', 'delta', 'epsilon'],
  browser:    ['iota', 'delta', 'zeta'],
  analysis:   ['beta', 'alpha', 'gamma'],
  operations: ['epsilon', 'delta', 'iota'],
};

const LEVEL_XP_TABLE = [0, 100, 300, 600, 1000, 1500, 2100, 2800, 3600, 4500];

export class OllamaRouter {
  private host: string;
  private availableModels: OllamaModel[] = [];
  private channels: Record<string, ChannelState> = {};
  private browserOps: BrowserOpsState = {
    activeTabs: 0,
    syncedAgents: [],
    lastBrowserSync: 0,
    operationsQueue: [],
  };
  private metrics: RouterMetrics = {
    totalRequests: 0,
    totalLatency: 0,
    modelHits: {},
    errors: 0,
    lastHealthCheck: 0,
    channelSync: {},
  };

  constructor(host: string = 'http://localhost:11434') {
    this.host = host.replace(/\/$/, '');
    this.initChannels();
  }

  private initChannels(): void {
    for (const [name, cfg] of Object.entries(HLM9_CHANNELS)) {
      this.channels[name] = {
        model: cfg.model,
        level: 1,
        xp: 0,
        xpToNext: LEVEL_XP_TABLE[1],
        status: 'idle',
        lastSync: 0,
      };
    }
    this.metrics.channelSync = { ...this.channels };
    console.log(`[OllamaRouter] 9 HLM channels initialized`);
  }

  async healthCheck(): Promise<boolean> {
    try {
      const res = await fetch(`${this.host}/api/tags`);
      if (!res.ok) throw new Error(`Ollama ${res.status}`);
      const data = await res.json();
      this.availableModels = data.models || [];
      this.metrics.lastHealthCheck = Date.now();
      this.syncChannelAvailability();
      return true;
    } catch (err) {
      this.metrics.errors++;
      return false;
    }
  }

  private syncChannelAvailability(): void {
    const available = this.availableModels.map((m) => m.name);
    for (const [name, state] of Object.entries(this.channels)) {
      state.lastSync = Date.now();
    }
  }

  selectModel(taskType: string = 'general'): string {
    const channelNames = TASK_MODEL_MAP[taskType] || TASK_MODEL_MAP.general;
    const available = this.availableModels.map((m) => m.name);
    for (const chName of channelNames) {
      const ch = this.channels[chName];
      if (ch && available.includes(ch.model)) {
        ch.status = 'active';
        return ch.model;
      }
    }
    return available[0] || 'mistral:latest';
  }

  private getChannelByModel(model: string): string {
    for (const [name, cfg] of Object.entries(HLM9_CHANNELS)) {
      if (cfg.model === model) return name;
    }
    return '';
  }

  private awardXP(channelName: string, xp: number): void {
    const ch = this.channels[channelName];
    if (!ch) return;
    ch.xp += xp;
    while (ch.xp >= ch.xpToNext && ch.level < LEVEL_XP_TABLE.length - 1) {
      ch.level++;
      ch.status = 'advancing';
      ch.xpToNext = LEVEL_XP_TABLE[ch.level] || ch.xpToNext * 2;
      console.log(`[LEVEL UP] ${channelName} => Lv${ch.level}`);
    }
    ch.status = 'idle';
    this.metrics.channelSync[channelName] = { ...ch };
  }

  async generate(req: GenerateRequest): Promise<GenerateResponse> {
    const start = Date.now();
    this.metrics.totalRequests++;
    this.metrics.modelHits[req.model] = (this.metrics.modelHits[req.model] || 0) + 1;
    const channelName = this.getChannelByModel(req.model);
    if (channelName) this.channels[channelName].status = 'active';
    try {
      const res = await fetch(`${this.host}/api/generate`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ...req, stream: false }),
      });
      if (!res.ok) throw new Error(`Generate failed: ${res.status}`);
      const data = await res.json();
      const latency = Date.now() - start;
      this.metrics.totalLatency += latency;
      const xpGain = Math.max(10, Math.floor(100 - latency / 100));
      if (channelName) this.awardXP(channelName, xpGain);
      return {
        model: data.model,
        response: data.response,
        context: data.context || [],
        totalDuration: data.total_duration || latency,
        evalCount: data.eval_count || 0,
        channel: channelName || undefined,
        alignmentLevel: channelName ? this.channels[channelName].level : undefined,
      };
    } catch (err) {
      this.metrics.errors++;
      if (channelName) this.channels[channelName].status = 'idle';
      throw err;
    }
  }

  async embed(text: string, model?: string): Promise<EmbeddingResponse> {
    const embedModel = model || this.selectModel('embedding');
    const res = await fetch(`${this.host}/api/embeddings`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ model: embedModel, prompt: text }),
    });
    if (!res.ok) throw new Error(`Embedding failed: ${res.status}`);
    const data = await res.json();
    this.awardXP('theta', 15);
    return { embedding: data.embedding };
  }

  async routeAndGenerate(prompt: string, taskType: string = 'general', systemPrompt?: string): Promise<GenerateResponse> {
    const model = this.selectModel(taskType);
    return this.generate({ model, prompt, system: systemPrompt, temperature: taskType === 'reasoning' ? 0.1 : 0.7 });
  }

  async syncAll(): Promise<Record<string, ChannelState>> {
    console.log('[OllamaRouter] === FULL SYNC ALL 9 CHANNELS ===');
    await this.healthCheck();
    for (const [name, ch] of Object.entries(this.channels)) {
      ch.status = 'syncing';
      ch.lastSync = Date.now();
      ch.status = 'idle';
    }
    this.metrics.channelSync = { ...this.channels };
    return { ...this.channels };
  }

  syncBrowserOps(tabs: number, agents: string[]): BrowserOpsState {
    this.browserOps = { activeTabs: tabs, syncedAgents: agents, lastBrowserSync: Date.now(), operationsQueue: [] };
    this.awardXP('iota', 5 * tabs);
    return { ...this.browserOps };
  }

  getAlignmentStatus(): Record<string, { level: number; xp: number; model: string; role: string }> {
    const status: Record<string, any> = {};
    for (const [name, ch] of Object.entries(this.channels)) {
      status[name] = { level: ch.level, xp: ch.xp, model: ch.model, role: HLM9_CHANNELS[name]?.role || 'unknown' };
    }
    return status;
  }

  getMetrics(): RouterMetrics { return { ...this.metrics }; }
  getAvailableModels(): OllamaModel[] { return [...this.availableModels]; }
  getChannels(): Record<string, ChannelState> { return { ...this.channels }; }
  getBrowserOps(): BrowserOpsState { return { ...this.browserOps }; }
  getHost(): string { return this.host; }
}

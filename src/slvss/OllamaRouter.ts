/**
 * OllamaRouter.ts - Sovereign Model Router for ARK95X
 * Routes inference requests across local Ollama models
 * Handles health checks, model selection, and load balancing
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
}

const MODEL_PRIORITY: Record<string, number> = {
  'deepseek-r1:latest': 100,
  'llama3.1:70b': 95,
  'mixtral:8x7b': 90,
  'llama3.1:8b': 80,
  'mistral:latest': 75,
  'phi3:latest': 60,
  'nomic-embed-text:latest': 50,
};

const TASK_MODEL_MAP: Record<string, string[]> = {
  reasoning: ['deepseek-r1:latest', 'llama3.1:70b', 'mixtral:8x7b'],
  code: ['deepseek-r1:latest', 'llama3.1:70b'],
  embedding: ['nomic-embed-text:latest'],
  fast: ['llama3.1:8b', 'mistral:latest', 'phi3:latest'],
  general: ['mixtral:8x7b', 'llama3.1:8b', 'mistral:latest'],
};

export class OllamaRouter {
  private host: string;
  private availableModels: OllamaModel[] = [];
  private metrics: RouterMetrics = {
    totalRequests: 0,
    totalLatency: 0,
    modelHits: {},
    errors: 0,
    lastHealthCheck: 0,
  };

  constructor(host: string = 'http://localhost:11434') {
    this.host = host.replace(/\/$/, '');
  }

  async healthCheck(): Promise<boolean> {
    try {
      const res = await fetch(`${this.host}/api/tags`);
      if (!res.ok) throw new Error(`Ollama returned ${res.status}`);
      const data = await res.json();
      this.availableModels = data.models || [];
      this.metrics.lastHealthCheck = Date.now();
      console.log(`[OllamaRouter] Health OK - ${this.availableModels.length} models loaded`);
      for (const m of this.availableModels) {
        console.log(`  -> ${m.name} (${(m.size / 1e9).toFixed(1)}GB)`);
      }
      return true;
    } catch (err) {
      console.error(`[OllamaRouter] Health check FAILED:`, err);
      this.metrics.errors++;
      return false;
    }
  }

  selectModel(taskType: string = 'general'): string {
    const candidates = TASK_MODEL_MAP[taskType] || TASK_MODEL_MAP.general;
    const available = this.availableModels.map((m) => m.name);
    for (const candidate of candidates) {
      if (available.includes(candidate)) return candidate;
    }
    if (available.length > 0) {
      return available.sort(
        (a, b) => (MODEL_PRIORITY[b] || 0) - (MODEL_PRIORITY[a] || 0)
      )[0];
    }
    return 'mistral:latest';
  }

  async generate(req: GenerateRequest): Promise<GenerateResponse> {
    const start = Date.now();
    this.metrics.totalRequests++;
    this.metrics.modelHits[req.model] = (this.metrics.modelHits[req.model] || 0) + 1;
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
      console.log(`[OllamaRouter] ${req.model} responded in ${latency}ms`);
      return {
        model: data.model,
        response: data.response,
        context: data.context || [],
        totalDuration: data.total_duration || latency,
        evalCount: data.eval_count || 0,
      };
    } catch (err) {
      this.metrics.errors++;
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
    return { embedding: data.embedding };
  }

  async routeAndGenerate(
    prompt: string,
    taskType: string = 'general',
    systemPrompt?: string
  ): Promise<GenerateResponse> {
    const model = this.selectModel(taskType);
    return this.generate({
      model,
      prompt,
      system: systemPrompt,
      temperature: taskType === 'reasoning' ? 0.1 : 0.7,
    });
  }

  getMetrics(): RouterMetrics {
    return { ...this.metrics };
  }

  getAvailableModels(): OllamaModel[] {
    return [...this.availableModels];
  }

  getHost(): string {
    return this.host;
  }
}

/**
 * QdrantMemory.ts - Vector Memory Store for ARK95X
 * Wires to Qdrant (localhost:6333) for persistent vector storage
 * ARK95X Omnikernel Orchestrator - SLVSS Module
 */

import { OllamaRouter, EmbeddingResponse } from './OllamaRouter';

export interface MemoryPoint {
  id?: string;
  vector?: number[];
  payload: Record<string, unknown>;
}

export interface SearchResult {
  id: string;
  score: number;
  payload: Record<string, unknown>;
}

export class QdrantMemory {
  private host: string;
  private router?: OllamaRouter;
  private vectorSize = 768;

  constructor(host: string = 'http://localhost:6333', router?: OllamaRouter) {
    this.host = host.replace(/\/$/, '');
    this.router = router;
  }

  async ensureCollection(name: string): Promise<void> {
    try {
      const check = await fetch(`${this.host}/collections/${name}`);
      if (check.ok) {
        console.log(`[QdrantMemory] Collection '${name}' exists`);
        return;
      }
    } catch {}
    const res = await fetch(`${this.host}/collections/${name}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        vectors: { size: this.vectorSize, distance: 'Cosine' },
      }),
    });
    if (!res.ok) throw new Error(`Failed to create collection '${name}': ${res.status}`);
    console.log(`[QdrantMemory] Created collection '${name}'`);
  }

  async upsert(collection: string, point: MemoryPoint): Promise<void> {
    const id = point.id || crypto.randomUUID();
    let vector = point.vector;
    if (!vector && this.router) {
      const text = JSON.stringify(point.payload);
      const emb = await this.router.embed(text);
      vector = emb.embedding;
    }
    if (!vector) {
      vector = Array.from({ length: this.vectorSize }, () => Math.random() * 0.01);
    }
    const res = await fetch(`${this.host}/collections/${collection}/points`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        points: [{ id, vector, payload: point.payload }],
      }),
    });
    if (!res.ok) throw new Error(`Upsert failed: ${res.status}`);
  }

  async search(collection: string, queryVector: number[], limit: number = 5): Promise<SearchResult[]> {
    const res = await fetch(`${this.host}/collections/${collection}/points/search`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ vector: queryVector, limit, with_payload: true }),
    });
    if (!res.ok) throw new Error(`Search failed: ${res.status}`);
    const data = await res.json();
    return (data.result || []).map((r: any) => ({
      id: r.id,
      score: r.score,
      payload: r.payload,
    }));
  }

  async semanticSearch(collection: string, query: string, limit: number = 5): Promise<SearchResult[]> {
    if (!this.router) throw new Error('OllamaRouter required for semantic search');
    const emb = await this.router.embed(query);
    return this.search(collection, emb.embedding, limit);
  }

  async getCollectionInfo(name: string): Promise<Record<string, unknown>> {
    const res = await fetch(`${this.host}/collections/${name}`);
    if (!res.ok) throw new Error(`Collection info failed: ${res.status}`);
    return res.json();
  }

  async deleteCollection(name: string): Promise<void> {
    const res = await fetch(`${this.host}/collections/${name}`, { method: 'DELETE' });
    if (!res.ok) throw new Error(`Delete collection failed: ${res.status}`);
    console.log(`[QdrantMemory] Deleted collection '${name}'`);
  }
}

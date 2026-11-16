"use client";
import { useEffect, useRef, useState } from "react";
import { subscribeBrainFeed, type FeedState } from "@/lib/brainFeed";
import { BRAIN_SOURCES, type BrainSource } from "@/lib/types";

export const SOURCE_COLORS: Record<BrainSource, string> = {
  brain: "#5eead4", scrape: "#38bdf8", audit: "#a78bfa", mirror: "#34d399", telegram: "#fbbf24",
};

type Node = { x: number; y: number; r: number; hub?: BrainSource; glow: number; phase: number };
type Edge = [number, number];
type Pulse = { e: number; t: number; speed: number; color: string; dir: 1 | -1 };

function buildGraph(count: number, w: number, h: number, seed = 7) {
  let s = seed;
  const rnd = () => ((s = (s * 9301 + 49297) % 233280) / 233280);
  const nodes: Node[] = [];
  const cx = w / 2, cy = h / 2, rx = w * 0.44, ry = h * 0.40;
  // hubs: one per source, spread around the brain
  BRAIN_SOURCES.forEach((src, i) => {
    const a = (i / BRAIN_SOURCES.length) * Math.PI * 2 - Math.PI / 2;
    nodes.push({ x: cx + Math.cos(a) * rx * 0.55, y: cy + Math.sin(a) * ry * 0.6, r: 3.2, hub: src, glow: 0, phase: rnd() * 6 });
  });
  for (let i = nodes.length; i < count; i++) {
    const a = rnd() * Math.PI * 2, d = Math.sqrt(rnd());
    // two lobes: nudge x away from the centre line
    const lobe = rnd() < 0.5 ? -1 : 1;
    const x = cx + Math.cos(a) * rx * d + lobe * w * 0.06;
    const y = cy + Math.sin(a) * ry * d * (0.85 + 0.3 * Math.abs(Math.cos(a)));
    nodes.push({ x, y, r: 1.2 + rnd() * 1.4, glow: 0, phase: rnd() * 6 });
  }
  const edges: Edge[] = [];
  const seen = new Set<string>();
  nodes.forEach((n, i) => {
    const near = nodes.map((m, j) => ({ j, d: Math.hypot(m.x - n.x, m.y - n.y) }))
      .filter((o) => o.j !== i).sort((a, b) => a.d - b.d).slice(0, n.hub ? 4 : 2);
    for (const { j } of near) {
      const key = i < j ? `${i}-${j}` : `${j}-${i}`;
      if (!seen.has(key)) { seen.add(key); edges.push([i, j]); }
    }
  });
  return { nodes, edges };
}

export default function BrainCanvas({ compact = false, idle = false, showLegend = false }:
  { compact?: boolean; idle?: boolean; showLegend?: boolean }) {
  const ref = useRef<HTMLCanvasElement>(null);
  const feed = useRef<FeedState>({ recent10m: 0, lastBySource: {}, available: false });
  const [badge, setBadge] = useState<FeedState | null>(null);
  const burst = useRef(0); // extra pulses queued by live events (model calls burst harder)

  useEffect(() => {
    if (idle) return;
    return subscribeBrainFeed((s) => { feed.current = s; setBadge(s); }, (e) => { burst.current += e.data?.kind === "llm" ? 6 : 2; });
  }, [idle]);

  useEffect(() => {
    const canvas = ref.current!;
    const ctx = canvas.getContext("2d")!;
    let raf = 0, w = 0, h = 0, dpr = 1;
    let graph = buildGraph(compact ? 34 : 70, 300, 150);
    const pulses: Pulse[] = [];
    let spawnAcc = 0, last = performance.now();

    const resize = () => {
      const rect = canvas.getBoundingClientRect();
      dpr = Math.min(2, window.devicePixelRatio || 1);
      w = Math.max(1, rect.width); h = Math.max(1, rect.height);
      canvas.width = w * dpr; canvas.height = h * dpr;
      graph = buildGraph(compact ? 34 : 70, w, h);
      pulses.length = 0;
    };
    const ro = new ResizeObserver(resize); ro.observe(canvas); resize();

    const spawn = (color?: string, from?: number) => {
      const { edges, nodes } = graph;
      let e: number;
      if (from !== undefined) {
        const cands = edges.map((ed, i) => (ed[0] === from || ed[1] === from ? i : -1)).filter((i) => i >= 0);
        if (!cands.length) return;
        e = cands[Math.floor(Math.random() * cands.length)];
      } else e = Math.floor(Math.random() * edges.length);
      const dir: 1 | -1 = from !== undefined ? (edges[e][0] === from ? 1 : -1) : Math.random() < 0.5 ? 1 : -1;
      const hubColor = color ?? (nodes[edges[e][0]].hub ? SOURCE_COLORS[nodes[edges[e][0]].hub!] : "#5eead4");
      pulses.push({ e, t: 0, speed: 0.35 + Math.random() * 0.5, color: hubColor, dir });
    };

    const draw = (now: number) => {
      const dt = Math.min(0.1, (now - last) / 1000); last = now;
      const f = feed.current;
      const breath = 0.5 + 0.5 * Math.sin(now / 2400);
      const activity = idle || !f.available ? 0 : Math.min(1, f.recent10m / 40);
      // pulse rate: idle 0.5/s breathing; up to ~8/s under load
      const rate = 0.4 + 0.6 * breath + activity * 8;
      spawnAcc += rate * dt;
      while (spawnAcc > 1) { spawnAcc -= 1; spawn(); }
      if (burst.current > 0 && Math.random() < 0.5) { burst.current -= 1; spawn(SOURCE_COLORS.brain, 0); }

      ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.clearRect(0, 0, w, h);
      const { nodes, edges } = graph;

      // hub glow from recent events (60 s decay)
      for (const n of nodes) {
        if (!n.hub) continue;
        const t = f.lastBySource[n.hub];
        n.glow = t ? Math.max(0, 1 - (Date.now() - t) / 60_000) : 0;
        if (n.glow > 0 && Math.random() < n.glow * 0.08) spawn(SOURCE_COLORS[n.hub], nodes.indexOf(n));
      }

      ctx.lineWidth = 0.7;
      for (const [a, b] of edges) {
        ctx.strokeStyle = `rgba(94,234,212,${0.10 + 0.08 * breath})`;
        ctx.beginPath(); ctx.moveTo(nodes[a].x, nodes[a].y); ctx.lineTo(nodes[b].x, nodes[b].y); ctx.stroke();
      }

      for (let i = pulses.length - 1; i >= 0; i--) {
        const p = pulses[i]; p.t += p.speed * dt;
        if (p.t >= 1) { pulses.splice(i, 1); continue; }
        const [a, b] = edges[p.e];
        const from = p.dir === 1 ? nodes[a] : nodes[b], to = p.dir === 1 ? nodes[b] : nodes[a];
        const x = from.x + (to.x - from.x) * p.t, y = from.y + (to.y - from.y) * p.t;
        ctx.fillStyle = p.color; ctx.globalAlpha = 0.9 * Math.sin(p.t * Math.PI);
        ctx.beginPath(); ctx.arc(x, y, 1.6, 0, Math.PI * 2); ctx.fill();
        ctx.globalAlpha = 1;
      }

      for (const n of nodes) {
        const tw = 0.6 + 0.4 * Math.sin(now / 900 + n.phase);
        if (n.hub) {
          const c = SOURCE_COLORS[n.hub];
          const g = ctx.createRadialGradient(n.x, n.y, 0, n.x, n.y, 10 + 14 * n.glow + 3 * breath);
          g.addColorStop(0, c + "cc"); g.addColorStop(1, c + "00");
          ctx.fillStyle = g; ctx.beginPath(); ctx.arc(n.x, n.y, 10 + 14 * n.glow + 3 * breath, 0, Math.PI * 2); ctx.fill();
          ctx.fillStyle = c; ctx.beginPath(); ctx.arc(n.x, n.y, n.r + n.glow * 1.5, 0, Math.PI * 2); ctx.fill();
        } else {
          ctx.fillStyle = `rgba(166,230,220,${0.35 + 0.45 * tw * (0.6 + 0.4 * breath)})`;
          ctx.beginPath(); ctx.arc(n.x, n.y, n.r, 0, Math.PI * 2); ctx.fill();
        }
      }
      raf = requestAnimationFrame(draw);
    };
    raf = requestAnimationFrame(draw);
    return () => { cancelAnimationFrame(raf); ro.disconnect(); };
  }, [compact, idle]);

  return (
    <div className="relative h-full w-full">
      <canvas ref={ref} className="block h-full w-full" aria-hidden />
      {showLegend && (
        <div className="pointer-events-none absolute bottom-2 left-3 right-3 flex flex-wrap items-center gap-3 text-[11px] text-muted">
          {BRAIN_SOURCES.map((s) => (
            <span key={s} className="inline-flex items-center gap-1">
              <span className="inline-block h-2 w-2 rounded-full" style={{ background: SOURCE_COLORS[s] }} />{s}
            </span>
          ))}
          <span className="ml-auto mono">
            {badge === null ? "connecting…" : !badge.available ? "log offline (run migration 002)" : `${badge.recent10m} events / 10 min`}
          </span>
        </div>
      )}
    </div>
  );
}

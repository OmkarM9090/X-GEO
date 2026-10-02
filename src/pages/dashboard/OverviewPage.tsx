import { Link, useNavigate } from "react-router-dom";
import {
  CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";
import {
  Activity, ArrowRight, ArrowUpRight, FlaskConical, Plus, ScanSearch, ShieldCheck, Target,
} from "lucide-react";
import { useUIStore } from "@/lib/store";
import { useReveal } from "@/hooks/useScrollTrigger";
import { DASHBOARD_METRICS, ENGINE_LABELS, RECENT_AUDITS, TREND_DATA } from "@/lib/mock-data";
import type { AuditStatus, Engine } from "@/types";
import { cn } from "@/lib/utils";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { MetricCard } from "@/components/dashboard/MetricCard";
import { EmptyState } from "@/components/dashboard/EmptyState";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card } from "@/components/ui/card";

const STATUS_STYLES: Record<AuditStatus, { label: string; className: string; pulse?: boolean }> = {
  completed: { label: "Completed", className: "border-success/30 bg-success/10 text-success" },
  running: { label: "Running", className: "border-accent/30 bg-accent/10 text-accent", pulse: true },
  scheduled: { label: "Scheduled", className: "border-border bg-muted/50 text-muted-foreground" },
  failed: { label: "Failed", className: "border-danger/30 bg-danger/10 text-danger" },
};

const ENGINE_DOT: Record<Engine, string> = {
  chatgpt: "bg-[hsl(var(--chart-1))]",
  aio: "bg-[hsl(var(--chart-3))]",
  perplexity: "bg-[hsl(var(--chart-2))]",
};

const SERIES: { key: Engine; label: string; color: string }[] = [
  { key: "chatgpt", label: ENGINE_LABELS.chatgpt, color: "hsl(var(--chart-1))" },
  { key: "aio", label: ENGINE_LABELS.aio, color: "hsl(var(--chart-3))" },
  { key: "perplexity", label: ENGINE_LABELS.perplexity, color: "hsl(var(--chart-2))" },
];

interface TrendTooltipEntry {
  dataKey?: string | number;
  value?: number | string;
  color?: string;
}

interface TrendTooltipProps {
  active?: boolean;
  payload?: readonly TrendTooltipEntry[];
  label?: string | number;
}

function TrendTooltip({ active, payload, label }: TrendTooltipProps) {
  if (!active || !payload || payload.length === 0) return null;
  return (
    <div className="rounded-lg border border-border bg-card px-3.5 py-2.5 shadow-card">
      <p className="font-mono text-[11px] uppercase tracking-wider text-muted-foreground">{String(label ?? "")}</p>
      <div className="mt-1.5 space-y-1">
        {payload.map((entry) => {
          const key = String(entry.dataKey ?? "") as Engine;
          return (
            <p key={key} className="flex items-center gap-2 text-xs">
              <span className="size-2 rounded-full" style={{ background: entry.color }} />
              <span className="text-muted-foreground">{ENGINE_LABELS[key] ?? key}</span>
              <span className="ml-auto pl-4 font-mono text-foreground">{Number(entry.value ?? 0).toFixed(2)}</span>
            </p>
          );
        })}
      </div>
    </div>
  );
}

function StatusBadge({ status }: { status: AuditStatus }) {
  const style = STATUS_STYLES[status];
  return (
    <span className={cn("inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-medium", style.className)}>
      {style.pulse && <span className="size-1.5 animate-pulse rounded-full bg-current" />}
      {style.label}
    </span>
  );
}

export default function OverviewPage() {
  const mockEmpty = useUIStore((s) => s.mockEmpty);
  const toggleMockEmpty = useUIStore((s) => s.toggleMockEmpty);
  const navigate = useNavigate();
  const metricsRef = useReveal<HTMLDivElement>({ stagger: 0.08, start: "top 92%" });
  const bodyRef = useReveal<HTMLDivElement>({ stagger: 0.12, start: "top 90%" });

  return (
    <div>
      <PageHeader title="Overview" description="Acme Docs Team · trailing 28 days · 42 tracked queries">
        <Button variant="ghost" size="sm" onClick={toggleMockEmpty} className="text-muted-foreground">
          <FlaskConical className="size-4" />
          {mockEmpty ? "Show mock data" : "Preview empty state"}
        </Button>
        <Button variant="accent" size="sm" asChild>
          <Link to="/dashboard/audits">
            <Plus className="size-4" />
            New audit
          </Link>
        </Button>
      </PageHeader>

      <div ref={metricsRef} className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">
        <MetricCard label="Avg CPI" Icon={Target} value={DASHBOARD_METRICS.avgCpi.value} format="percent" delta={DASHBOARD_METRICS.avgCpi.delta} hint="vs prior 28d" />
        <MetricCard label="NLI Precision" Icon={ShieldCheck} value={DASHBOARD_METRICS.nliPrecision.value} format="percent" decimals={1} delta={DASHBOARD_METRICS.nliPrecision.delta} hint="claim entailment" />
        <MetricCard label="Active Audits" Icon={ScanSearch} value={DASHBOARD_METRICS.activeAudits.value} delta={DASHBOARD_METRICS.activeAudits.delta} deltaKind="count" hint="2 running now" />
        <MetricCard label="Monthly Runs" Icon={Activity} value={DASHBOARD_METRICS.monthlyRuns.value} delta={DASHBOARD_METRICS.monthlyRuns.delta} deltaKind="count" hint={`of ${DASHBOARD_METRICS.monthlyRuns.limit.toLocaleString()} quota`} />
      </div>

      {mockEmpty ? (
        <div className="mt-6">
          <EmptyState
            Icon={ScanSearch}
            title="No audits yet"
            description="Queue your first Monte Carlo audit to start measuring citation probability across ChatGPT Search, Google AIO, and Perplexity."
            actionLabel="Run your first audit"
            actionTo="/dashboard/audits"
            className="min-h-[420px]"
          />
        </div>
      ) : (
        <div ref={bodyRef} className="mt-6 grid gap-4 xl:grid-cols-5">
          {/* Recent audits */}
          <Card data-reveal className="overflow-hidden xl:col-span-3">
            <div className="flex items-center justify-between border-b border-border px-6 py-4">
              <h2 className="font-heading text-[15px] font-semibold text-foreground">Recent audits</h2>
              <Link
                to="/dashboard/audits"
                className="inline-flex items-center gap-1 text-xs text-muted-foreground transition-colors hover:text-accent"
              >
                View all
                <ArrowUpRight className="size-3.5" />
              </Link>
            </div>
            <div className="overflow-x-auto">
              <table className="w-full min-w-[560px] text-sm">
                <thead>
                  <tr className="text-left text-[11px] uppercase tracking-[0.12em] text-muted-foreground">
                    <th className="px-6 py-3 font-medium">Query</th>
                    <th className="px-3 py-3 font-medium">Engine</th>
                    <th className="px-3 py-3 font-medium">CPI</th>
                    <th className="px-3 py-3 font-medium">Δ 7d</th>
                    <th className="px-6 py-3 font-medium">Status</th>
                  </tr>
                </thead>
                <tbody>
                  {RECENT_AUDITS.map((audit) => (
                    <tr
                      key={audit.id}
                      onClick={() => navigate(`/dashboard/audits?id=${audit.id}`)}
                      className="cursor-pointer border-t border-border/60 transition-colors hover:bg-muted/40"
                    >
                      <td className="max-w-[220px] px-6 py-3.5">
                        <p className="truncate font-medium text-foreground">{audit.query}</p>
                        <p className="mt-0.5 font-mono text-[11px] text-muted-foreground">{audit.id} · {audit.updatedAt}</p>
                      </td>
                      <td className="px-3 py-3.5">
                        <span className="flex items-center gap-2 text-xs text-muted-foreground">
                          <span className={cn("size-1.5 rounded-full", ENGINE_DOT[audit.engine])} />
                          {ENGINE_LABELS[audit.engine]}
                        </span>
                      </td>
                      <td className="px-3 py-3.5">
                        <p className="font-mono text-[13px] text-foreground">{audit.cpi.toFixed(2)}</p>
                        <p className="font-mono text-[10px] text-muted-foreground">
                          [{audit.lower.toFixed(2)}, {audit.upper.toFixed(2)}]
                        </p>
                      </td>
                      <td className="px-3 py-3.5">
                        <span className={cn("font-mono text-xs", audit.delta >= 0 ? "text-success" : "text-danger")}>
                          {audit.delta >= 0 ? "+" : "−"}{Math.abs(audit.delta * 100).toFixed(1)}pp
                        </span>
                      </td>
                      <td className="px-6 py-3.5">
                        <StatusBadge status={audit.status} />
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </Card>

          {/* Citation trends */}
          <Card data-reveal className="flex flex-col xl:col-span-2">
            <div className="flex flex-wrap items-center justify-between gap-2 border-b border-border px-6 py-4">
              <h2 className="font-heading text-[15px] font-semibold text-foreground">Citation trends</h2>
              <Badge variant="outline" className="font-mono text-[10px]">12 weeks</Badge>
            </div>
            <div className="flex flex-wrap gap-4 px-6 pt-4">
              {SERIES.map((s) => (
                <span key={s.key} className="flex items-center gap-1.5 text-xs text-muted-foreground">
                  <span className="size-2 rounded-full" style={{ background: s.color }} />
                  {s.label}
                </span>
              ))}
            </div>
            <div className="h-[300px] flex-1 px-2 pb-4 pt-4">
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={TREND_DATA} margin={{ top: 8, right: 12, bottom: 0, left: -18 }}>
                  <CartesianGrid stroke="hsl(var(--border))" strokeDasharray="3 5" vertical={false} />
                  <XAxis
                    dataKey="date"
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10, fontFamily: "Geist Mono, monospace" }}
                    tickLine={false}
                    axisLine={{ stroke: "hsl(var(--border))" }}
                    interval={2}
                  />
                  <YAxis
                    domain={[0.3, 0.8]}
                    tick={{ fill: "hsl(var(--muted-foreground))", fontSize: 10, fontFamily: "Geist Mono, monospace" }}
                    tickLine={false}
                    axisLine={false}
                    tickFormatter={(v: number) => v.toFixed(2)}
                  />
                  <Tooltip content={<TrendTooltip />} cursor={{ stroke: "hsl(var(--border))", strokeWidth: 1 }} />
                  {SERIES.map((s) => (
                    <Line
                      key={s.key}
                      type="monotone"
                      dataKey={s.key}
                      stroke={s.color}
                      strokeWidth={2}
                      dot={false}
                      activeDot={{ r: 4, strokeWidth: 0 }}
                    />
                  ))}
                </LineChart>
              </ResponsiveContainer>
            </div>
            <p className="border-t border-border px-6 py-3 text-xs text-muted-foreground">
              All three engines trending up<span className="mx-1.5 text-border">·</span>
              <span className="inline-flex items-center gap-1 text-success">
                +11pp combined <ArrowRight className="size-3 -rotate-45" />
              </span>
            </p>
          </Card>
        </div>
      )}
    </div>
  );
}

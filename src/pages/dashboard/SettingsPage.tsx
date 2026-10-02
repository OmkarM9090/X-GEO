import { useState } from "react";
import { Check, Copy, KeyRound, TriangleAlert } from "lucide-react";
import { PageHeader } from "@/components/dashboard/PageHeader";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { Label } from "@/components/ui/label";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { cn } from "@/lib/utils";

const MOCK_KEY = "xgeo_sk_live_9f2e1c7ab44d6e88b0c1d2e3f4a5b6c7";

function ToggleRow({
  label,
  description,
  defaultOn,
}: {
  label: string;
  description: string;
  defaultOn: boolean;
}) {
  const [on, setOn] = useState(defaultOn);
  return (
    <button
      type="button"
      role="switch"
      aria-checked={on}
      onClick={() => setOn(!on)}
      className="flex w-full items-center justify-between gap-4 rounded-xl border border-border/70 px-4 py-3.5 text-left transition-colors hover:border-muted-foreground/30"
    >
      <span>
        <span className="block text-sm font-medium text-foreground">{label}</span>
        <span className="mt-0.5 block text-xs text-muted-foreground">{description}</span>
      </span>
      <span
        className={cn(
          "relative h-6 w-11 shrink-0 rounded-full transition-colors duration-300",
          on ? "bg-accent" : "bg-muted",
        )}
      >
        <span
          className={cn(
            "absolute top-0.5 size-5 rounded-full bg-white shadow transition-all duration-300 ease-out-expo",
            on ? "left-[22px]" : "left-0.5",
          )}
        />
      </span>
    </button>
  );
}

export default function SettingsPage() {
  const [copied, setCopied] = useState(false);

  const copyKey = async () => {
    try {
      await navigator.clipboard.writeText(MOCK_KEY);
    } catch {
      /* clipboard unavailable — still show feedback */
    }
    setCopied(true);
    window.setTimeout(() => setCopied(false), 1600);
  };

  return (
    <div>
      <PageHeader title="Settings" description="Workspace preferences. Persisted changes ship with the Phase 2 backend." />

      <div className="grid gap-4 lg:grid-cols-2">
        {/* Profile */}
        <Card>
          <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
            <div>
              <CardTitle className="text-[17px]">Profile</CardTitle>
              <CardDescription>How you appear to your workspace.</CardDescription>
            </div>
            <Badge>Phase 2</Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center gap-3">
              <Avatar className="size-11">
                <AvatarFallback className="text-sm">AR</AvatarFallback>
              </Avatar>
              <Button variant="outline" size="sm" disabled>Change avatar</Button>
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="s-name">Full name</Label>
              <Input id="s-name" defaultValue="Alex Rivera" disabled />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="s-email">Email</Label>
              <Input id="s-email" defaultValue="alex@acme.dev" disabled />
            </div>
            <Button disabled>Save changes</Button>
          </CardContent>
        </Card>

        {/* Workspace */}
        <Card>
          <CardHeader className="flex-row items-start justify-between gap-4 space-y-0">
            <div>
              <CardTitle className="text-[17px]">Workspace</CardTitle>
              <CardDescription>Shared defaults for all projects.</CardDescription>
            </div>
            <Badge>Phase 2</Badge>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="space-y-1.5">
              <Label htmlFor="s-ws">Workspace name</Label>
              <Input id="s-ws" defaultValue="Acme Docs Team" disabled />
            </div>
            <div className="space-y-1.5">
              <Label htmlFor="s-region">Processing region</Label>
              <Input id="s-region" defaultValue="EU (Frankfurt)" disabled />
            </div>
            <div className="flex items-center justify-between rounded-xl border border-border/70 px-4 py-3">
              <span className="text-sm text-foreground">Current plan</span>
              <span className="flex items-center gap-3">
                <Badge variant="accent">Pro</Badge>
                <a href="/pricing" className="text-xs text-muted-foreground underline-offset-4 hover:text-accent hover:underline">
                  Manage
                </a>
              </span>
            </div>
          </CardContent>
        </Card>

        {/* API access */}
        <Card>
          <CardHeader>
            <CardTitle className="text-[17px]">API access</CardTitle>
            <CardDescription>Bearer key for the sampling API (mock value).</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <div className="relative flex-1">
                <KeyRound className="absolute left-3 top-1/2 size-4 -translate-y-1/2 text-muted-foreground" />
                <Input
                  readOnly
                  value="xgeo_sk_live_••••••••••••••••b6c7"
                  aria-label="API key (masked)"
                  className="pl-9 font-mono text-xs"
                />
              </div>
              <Button variant="outline" onClick={copyKey} aria-live="polite">
                {copied ? <Check className="size-4 text-success" /> : <Copy className="size-4" />}
                {copied ? "Copied" : "Copy"}
              </Button>
            </div>
            <div className="flex items-center gap-3">
              <Button variant="outline" disabled>Roll key</Button>
              <Badge>Phase 2</Badge>
            </div>
          </CardContent>
        </Card>

        {/* Notifications */}
        <Card>
          <CardHeader>
            <CardTitle className="text-[17px]">Notifications</CardTitle>
            <CardDescription>Choose what lands in your inbox.</CardDescription>
          </CardHeader>
          <CardContent className="space-y-3">
            <ToggleRow label="Drift alerts" description="When a CPI moves beyond ±3σ of baseline." defaultOn />
            <ToggleRow label="Weekly digest" description="Monday summary across all tracked queries." defaultOn />
            <ToggleRow label="Patch approvals" description="When a teammate accepts a surgical patch." defaultOn={false} />
          </CardContent>
        </Card>

        {/* Danger zone */}
        <Card className="border-danger/30 lg:col-span-2">
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-[17px] text-danger">
              <TriangleAlert className="size-4" />
              Danger zone
            </CardTitle>
            <CardDescription>
              Deleting a workspace removes crawls, intervals, and patch history within 24 hours.
            </CardDescription>
          </CardHeader>
          <CardContent className="flex items-center gap-3">
            <Button variant="danger" disabled>Delete workspace</Button>
            <Badge>Phase 2</Badge>
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

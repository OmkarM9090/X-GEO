import { useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  Bell, Check, ChevronsUpDown, CircleAlert, FileText, LogOut, Menu, Plus,
  ScanSearch, Settings, User,
} from "lucide-react";
import { useUIStore } from "@/lib/store";
import { NOTIFICATIONS } from "@/data/mock-audits";
import { cn } from "@/lib/utils";
import { ThemeToggle } from "@/components/shared/ThemeToggle";
import { CommandPalette } from "@/components/dashboard/CommandPalette";
import { SidebarContent } from "@/components/dashboard/Sidebar";
import { Avatar, AvatarFallback } from "@/components/ui/avatar";
import { Sheet, SheetContent, SheetHeader, SheetTitle, SheetTrigger } from "@/components/ui/sheet";
import {
  DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuLabel,
  DropdownMenuSeparator, DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu";

const WORKSPACES = ["Acme Docs Team", "Acme Marketing", "Beta — Client Pilot"];

const NOTIF_ICONS = { audit: ScanSearch, alert: CircleAlert, report: FileText } as const;

function NotificationsMenu() {
  const unread = NOTIFICATIONS.filter((n) => n.unread).length;
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <button
          type="button"
          aria-label={`Notifications — ${unread} unread`}
          className="relative grid size-9 place-items-center rounded-lg border border-border/60 text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground"
        >
          <Bell className="size-[17px]" />
          {unread > 0 && (
            <span className="absolute -right-0.5 -top-0.5 grid size-4 place-items-center rounded-full bg-accent font-mono text-[9px] font-semibold text-accent-foreground">
              {unread}
            </span>
          )}
        </button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-[340px]">
        <DropdownMenuLabel className="flex items-center justify-between">
          Notifications
          <span className="font-mono text-[10px] font-normal text-muted-foreground">{unread} new</span>
        </DropdownMenuLabel>
        <DropdownMenuSeparator />
        {NOTIFICATIONS.map((n) => {
          const Icon = NOTIF_ICONS[n.kind];
          return (
            <DropdownMenuItem key={n.id} className="items-start gap-3 py-3">
              <span
                className={cn(
                  "mt-0.5 grid size-7 shrink-0 place-items-center rounded-md",
                  n.kind === "alert" ? "bg-warning/10 text-warning" : "bg-accent/10 text-accent",
                )}
              >
                <Icon className="size-3.5" />
              </span>
              <span className="min-w-0 flex-1">
                <span className="block truncate text-sm font-medium text-foreground">
                  {n.title}
                  {n.unread && <span className="ml-2 inline-block size-1.5 rounded-full bg-accent align-middle" />}
                </span>
                <span className="mt-0.5 block text-xs leading-snug text-muted-foreground">{n.description}</span>
                <span className="mt-1 block font-mono text-[10px] text-muted-foreground/70">{n.time}</span>
              </span>
            </DropdownMenuItem>
          );
        })}
        <DropdownMenuSeparator />
        <DropdownMenuItem className="justify-center text-xs text-accent">View all activity</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  );
}

export function TopBar() {
  const setCommandOpen = useUIStore((s) => s.setCommandOpen);
  const [mobileOpen, setMobileOpen] = useState(false);
  const navigate = useNavigate();

  return (
    <header className="sticky top-0 z-20 flex h-14 items-center gap-3 border-b border-border/60 glass px-4 sm:px-6">
      {/* Mobile nav */}
      <Sheet open={mobileOpen} onOpenChange={setMobileOpen}>
        <SheetTrigger asChild>
          <button
            type="button"
            aria-label="Open navigation"
            className="grid size-9 place-items-center rounded-lg border border-border/60 text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground lg:hidden"
          >
            <Menu className="size-[18px]" />
          </button>
        </SheetTrigger>
        <SheetContent side="left" className="w-[280px] p-0">
          <SheetHeader className="sr-only">
            <SheetTitle>Dashboard navigation</SheetTitle>
          </SheetHeader>
          <SidebarContent onNavigate={() => setMobileOpen(false)} />
        </SheetContent>
      </Sheet>

      {/* Workspace switcher */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button
            type="button"
            className="flex items-center gap-2.5 rounded-lg border border-border/60 py-1.5 pl-1.5 pr-2.5 transition-colors hover:bg-muted/50"
            aria-label="Switch workspace"
          >
            <span className="grid size-6 place-items-center rounded-md bg-gradient-to-br from-accent to-accent-glow font-heading text-[11px] font-bold text-accent-foreground">
              A
            </span>
            <span className="hidden text-sm font-medium text-foreground sm:block">Acme Docs Team</span>
            <ChevronsUpDown className="size-3.5 text-muted-foreground" />
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start" className="w-60">
          <DropdownMenuLabel>Workspaces</DropdownMenuLabel>
          {WORKSPACES.map((ws, i) => (
            <DropdownMenuItem key={ws} className="justify-between">
              <span className="flex items-center gap-2.5">
                <span className="grid size-5 place-items-center rounded bg-accent/15 font-heading text-[10px] font-bold text-accent">
                  {ws[0]}
                </span>
                {ws}
              </span>
              {i === 0 && <Check className="size-4 text-accent" />}
            </DropdownMenuItem>
          ))}
          <DropdownMenuSeparator />
          <DropdownMenuItem>
            <Plus className="size-4" />
            New workspace
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <div className="flex-1" />

      {/* Global search trigger */}
      <button
        type="button"
        onClick={() => setCommandOpen(true)}
        className="hidden h-9 items-center gap-2.5 rounded-lg border border-border/60 bg-background/50 px-3 text-sm text-muted-foreground transition-colors hover:border-muted-foreground/30 hover:text-foreground sm:flex sm:w-52 md:w-64"
        aria-label="Open command palette"
      >
        <span aria-hidden="true" className="text-[15px] leading-none">⌕</span>
        <span className="flex-1 text-left">Search or jump to…</span>
        <kbd className="rounded-md border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px]">⌘K</kbd>
      </button>
      <button
        type="button"
        onClick={() => setCommandOpen(true)}
        aria-label="Open command palette"
        className="grid size-9 place-items-center rounded-lg border border-border/60 text-muted-foreground transition-colors hover:bg-muted/50 hover:text-foreground sm:hidden"
      >
        <span aria-hidden="true" className="text-lg leading-none">⌕</span>
      </button>

      <NotificationsMenu />
      <ThemeToggle />

      {/* Account */}
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <button type="button" aria-label="Account menu" className="rounded-full transition-transform hover:scale-105">
            <Avatar className="size-9 border border-border">
              <AvatarFallback>AR</AvatarFallback>
            </Avatar>
          </button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="end" className="w-56">
          <DropdownMenuLabel>
            <p className="text-sm font-medium text-foreground">Alex Rivera</p>
            <p className="mt-0.5 text-xs font-normal text-muted-foreground">alex@acme.dev</p>
          </DropdownMenuLabel>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => navigate("/dashboard/settings")}>
            <User className="size-4" />
            Profile
          </DropdownMenuItem>
          <DropdownMenuItem onClick={() => navigate("/dashboard/settings")}>
            <Settings className="size-4" />
            Settings
          </DropdownMenuItem>
          <DropdownMenuSeparator />
          <DropdownMenuItem onClick={() => navigate("/signin")} className="text-danger focus:bg-danger/10 [&_svg]:text-danger">
            <LogOut className="size-4" />
            Log out
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>

      <CommandPalette />
    </header>
  );
}

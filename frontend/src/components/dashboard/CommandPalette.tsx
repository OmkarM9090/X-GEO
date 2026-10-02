import { useEffect, useMemo, useState } from "react";
import { useNavigate } from "react-router-dom";
import { Search } from "lucide-react";
import { COMMAND_ITEMS } from "@/data/mock-audits";
import { useUIStore } from "@/lib/store";
import { Dialog, DialogContent, DialogTitle } from "@/components/ui/dialog";

/** Cmd/Ctrl+K search for dashboard destinations and common actions. */
export function CommandPalette() {
  const open = useUIStore((state) => state.commandOpen);
  const setOpen = useUIStore((state) => state.setCommandOpen);
  const [query, setQuery] = useState("");
  const navigate = useNavigate();

  useEffect(() => {
    const onKeyDown = (event: KeyboardEvent) => {
      if ((event.metaKey || event.ctrlKey) && event.key.toLowerCase() === "k") {
        event.preventDefault();
        const nextOpen = !useUIStore.getState().commandOpen;
        setOpen(nextOpen);
        if (!nextOpen) setQuery("");
      }
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, [setOpen]);

  const filtered = useMemo(
    () => COMMAND_ITEMS.filter((item) => item.label.toLowerCase().includes(query.trim().toLowerCase())),
    [query],
  );
  const groups = useMemo(() => {
    const map = new Map<string, typeof filtered>();
    filtered.forEach((item) => map.set(item.group, [...(map.get(item.group) ?? []), item]));
    return Array.from(map.entries());
  }, [filtered]);

  const run = (id: string) => {
    setOpen(false);
    setQuery("");
    if (id === "c1") navigate("/dashboard");
    else if (id === "c2") navigate("/dashboard/projects");
    else if (id === "c3") navigate("/dashboard/settings");
    else navigate("/dashboard/audits");
  };

  return (
    <Dialog
      open={open}
      onOpenChange={(nextOpen) => {
        setOpen(nextOpen);
        if (!nextOpen) setQuery("");
      }}
    >
      <DialogContent hideClose className="top-[22%] max-w-xl translate-y-0 gap-0 overflow-hidden p-0">
        <DialogTitle className="sr-only">Command palette</DialogTitle>
        <div className="flex items-center gap-3 border-b border-border px-4">
          <Search className="size-4 text-muted-foreground" aria-hidden="true" />
          <input
            autoFocus
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search audits, jump to pages, run actions…"
            aria-label="Command palette search"
            className="flex-1 bg-transparent py-4 text-body text-foreground outline-none placeholder:text-muted-foreground/60"
          />
          <kbd className="rounded-md border border-border bg-muted px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">ESC</kbd>
        </div>
        <div className="max-h-[320px] overflow-y-auto p-2" data-lenis-prevent>
          {groups.length === 0 && (
            <p className="px-3 py-8 text-center text-sm text-muted-foreground">No results for “{query}”.</p>
          )}
          {groups.map(([group, items]) => (
            <div key={group} className="py-1.5">
              <p className="px-3 pb-1 text-[11px] font-medium uppercase tracking-[0.14em] text-muted-foreground">{group}</p>
              {items.map((item) => (
                <button
                  key={item.id}
                  type="button"
                  onClick={() => run(item.id)}
                  className="flex w-full items-center justify-between rounded-lg px-3 py-2.5 text-sm text-foreground/90 transition-colors hover:bg-muted focus-visible:bg-muted"
                >
                  <span>{item.label}</span>
                  <kbd className="rounded-md border border-border bg-background px-1.5 py-0.5 font-mono text-[10px] text-muted-foreground">{item.hint}</kbd>
                </button>
              ))}
            </div>
          ))}
        </div>
      </DialogContent>
    </Dialog>
  );
}

/**
 * 출처: @base-ui/react/popover 1.8.x — Root, Trigger, Positioner, Popup and focus handling.
 * Application-owned composition using the existing Button and workspace tokens.
 */
import { Popover } from "@base-ui/react/popover";
import { useEffect, useState, type ReactNode } from "react";
import { Button } from "./Button";

/** Auxiliary tools open beside their trigger without moving the working surface. */
export function ToolPanel({ label, accessibleLabel, children, active = false }: {
  label: string; accessibleLabel?: string; children: ReactNode; active?: boolean;
}) {
  const [host, setHost] = useState<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(active);
  useEffect(() => { if (active) setOpen(true); }, [active]);
  return <div ref={setHost} className="tool-panel" data-tool-name={label}>
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger render={<Button variant="quiet" size="sm" />} aria-label={accessibleLabel}>
        {label}
      </Popover.Trigger>
      <Popover.Portal container={host} keepMounted>
        <Popover.Positioner positionMethod="fixed" sideOffset={6} collisionPadding={12} align="start" className="tool-panel-positioner">
          <Popover.Popup className="tool-panel-popup">
            <header className="tool-panel-heading">
              <Popover.Title>{label}</Popover.Title>
              <Popover.Close render={<Button variant="ghost" size="sm" />}>닫기</Popover.Close>
            </header>
            <div className="tool-panel-body" onClick={(event) => {
              const button = (event.target as HTMLElement).closest("button[data-action]");
              if (button && !(button as HTMLButtonElement).disabled) setOpen(false);
            }}>{children}</div>
          </Popover.Popup>
        </Popover.Positioner>
      </Popover.Portal>
    </Popover.Root>
  </div>;
}

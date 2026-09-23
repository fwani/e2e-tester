/**
 * 출처: @base-ui/react/popover 1.8.x — Root, Trigger, Positioner, Popup and focus handling.
 * Application-owned composition using the existing Button and workspace tokens.
 */
import { Popover } from "@base-ui/react/popover";
import { useEffect, useState, type ReactNode } from "react";
import { IconButton } from "./IconButton";
import type { ControlIconName } from "./ControlIcon";
import { Button, type ButtonSize } from "./Button";

/** Auxiliary tools open beside their trigger without moving the working surface. */
export function ToolPanel({ label, accessibleLabel, children, active = false, triggerSize = "sm", icon }: {
  label: string; accessibleLabel?: string; children: ReactNode; active?: boolean; triggerSize?: ButtonSize; icon?: ControlIconName;
}) {
  const [host, setHost] = useState<HTMLDivElement | null>(null);
  const [open, setOpen] = useState(active);
  useEffect(() => { if (active) setOpen(true); }, [active]);
  return <div ref={setHost} className="tool-panel" data-tool-name={label}>
    <Popover.Root open={open} onOpenChange={setOpen}>
      <Popover.Trigger render={icon ? <IconButton label={accessibleLabel ?? label} icon={icon} variant="quiet" size={triggerSize} /> : <Button variant="quiet" size={triggerSize} />} aria-label={accessibleLabel}>
        {icon ? null : label}
      </Popover.Trigger>
      <Popover.Portal container={host} keepMounted>
        <Popover.Positioner positionMethod="fixed" sideOffset={6} collisionPadding={12} align="start" className="tool-panel-positioner">
          <Popover.Popup className="tool-panel-popup">
            <header className="tool-panel-heading">
              <Popover.Title>{label}</Popover.Title>
              <Popover.Close render={<IconButton label="닫기" icon="close" variant="ghost" />} />
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

/**
 * 출처: @base-ui/react/tooltip 1.8.x — existing Button and Tooltip composition.
 */
import { Button, type ButtonProps } from "./Button";
import { ControlIcon, type ControlIconName } from "./ControlIcon";
import { Tooltip } from "./Tooltip";

export function IconButton({ label, icon, size = "sm", ...props }: Omit<ButtonProps, "children"> & { label: string; icon: ControlIconName }) {
  return <Tooltip content={label}>
    <Button {...props} size={size} aria-label={label} data-icon-only>
      <ControlIcon name={icon} />
    </Button>
  </Tooltip>;
}

import type { ComponentProps } from "react";
import { ChevronDown } from "lucide-react";
import { cn } from "@/utils/cn";
import { fieldStyles } from "./input";

export interface SelectOption<T extends string = string> {
  value: T;
  label: string;
  disabled?: boolean;
}

interface SelectProps extends Omit<ComponentProps<"select">, "size"> {
  size?: "sm" | "md";
  wrapperClassName?: string;
}

/** Native select (keyboard + mobile friendly) with the design-system look. */
export function Select({ className, wrapperClassName, size = "md", children, ...props }: SelectProps) {
  return (
    <div className={cn("relative", wrapperClassName)}>
      <select className={cn(fieldStyles, "cursor-pointer appearance-none pr-9", size === "sm" && "h-9", className)} {...props}>
        {children}
      </select>
      <ChevronDown className="pointer-events-none absolute right-3 top-1/2 size-4 -translate-y-1/2 text-muted" aria-hidden />
    </div>
  );
}

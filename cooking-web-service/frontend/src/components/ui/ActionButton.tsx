import type { ButtonHTMLAttributes } from "react";
import { cn } from "../../lib/utils";

interface ActionButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  /** 主操作用实心蓝，次操作用描边蓝；不同用途不强制同色。 */
  variant?: "primary" | "secondary";
}

/**
 * 底部操作栏按钮：统一高度、圆角、字号与字重，避免各页面风格漂移。
 *
 * - ``primary``：实心蓝（新增 / 生成 / 保存等主操作）。
 * - ``secondary``：描边蓝（返回 / 导航等次操作）。
 */
export default function ActionButton({
  variant = "primary",
  className,
  ...props
}: ActionButtonProps) {
  return (
    <button
      {...props}
      className={cn(
        "flex h-12 w-full items-center justify-center rounded-lg text-lg font-semibold transition disabled:cursor-not-allowed disabled:opacity-40",
        variant === "primary"
          ? "bg-blue-600 text-white hover:bg-blue-700"
          : "border-2 border-blue-600 bg-white text-blue-600 hover:bg-blue-50",
        className,
      )}
    />
  );
}

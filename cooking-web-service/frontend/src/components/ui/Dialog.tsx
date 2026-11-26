import * as DialogPrimitive from "@radix-ui/react-dialog";
import type { ReactNode } from "react";

interface DialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** 弹窗标题。 */
  title: string;
  /** 弹窗内容（含操作区）。 */
  children: ReactNode;
}

/** 通用弹窗组件：标题 + 自定义内容，供各页面对话框功能复用。 */
export default function Dialog({
  open,
  onOpenChange,
  title,
  children,
}: DialogProps) {
  return (
    <DialogPrimitive.Root open={open} onOpenChange={onOpenChange}>
      <DialogPrimitive.Portal>
        <DialogPrimitive.Overlay className="fixed inset-0 z-40 bg-black/40" />
        <DialogPrimitive.Content className="fixed left-1/2 top-1/2 z-50 w-[calc(100%-2.5rem)] max-w-sm -translate-x-1/2 -translate-y-1/2 rounded-xl bg-white p-5 shadow-xl">
          <DialogPrimitive.Title className="mb-3 text-base font-semibold text-gray-800">
            {title}
          </DialogPrimitive.Title>
          {children}
        </DialogPrimitive.Content>
      </DialogPrimitive.Portal>
    </DialogPrimitive.Root>
  );
}

import { cn } from "../../lib/utils";
import Dialog from "./Dialog";

interface ConfirmDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  /** 弹窗标题。 */
  title: string;
  /** 确认说明文案。 */
  description: string;
  /** 确认按钮文案，默认「确认」。 */
  confirmText?: string;
  /** 取消按钮文案，默认「取消」。 */
  cancelText?: string;
  /** 危险操作样式（红色确认按钮）。 */
  danger?: boolean;
  /** 确认中（禁用按钮并显示处理中）。 */
  loading?: boolean;
  /** 确认回调。 */
  onConfirm: () => void;
}

/** 通用确认对话框：用于删除等需要二次确认的操作，供各页面复用。 */
export default function ConfirmDialog({
  open,
  onOpenChange,
  title,
  description,
  confirmText = "确认",
  cancelText = "取消",
  danger = false,
  loading = false,
  onConfirm,
}: ConfirmDialogProps) {
  return (
    <Dialog open={open} onOpenChange={onOpenChange} title={title}>
      <p className="text-sm text-gray-600">{description}</p>
      <div className="mt-5 flex justify-end gap-3">
        <button
          type="button"
          onClick={() => onOpenChange(false)}
          disabled={loading}
          className="rounded-full border-2 border-gray-200 px-5 py-2 text-sm text-gray-600 disabled:opacity-40"
        >
          {cancelText}
        </button>
        <button
          type="button"
          onClick={onConfirm}
          disabled={loading}
          className={cn(
            "rounded-full px-5 py-2 text-sm text-white disabled:opacity-40",
            danger
              ? "bg-red-600 transition hover:bg-red-700"
              : "bg-blue-600 transition hover:bg-blue-700",
          )}
        >
          {loading ? "处理中…" : confirmText}
        </button>
      </div>
    </Dialog>
  );
}

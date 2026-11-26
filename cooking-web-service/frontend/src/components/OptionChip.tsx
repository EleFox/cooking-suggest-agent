import { cn } from "../lib/utils";

interface OptionChipProps {
  selected: boolean;
  onClick: () => void;
  children: React.ReactNode;
}

/** 可选中的选项 chip（菜谱表单手段多选 / 难度单选）。 */
export default function OptionChip({
  selected,
  onClick,
  children,
}: OptionChipProps) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border-2 px-4 py-2 text-base font-medium transition",
        selected
          ? "border-blue-600 bg-blue-50 text-blue-600"
          : "border-gray-200 bg-white text-gray-700",
      )}
    >
      {children}
    </button>
  );
}

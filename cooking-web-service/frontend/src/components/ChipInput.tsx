import { useState } from "react";

interface ChipInputProps {
  /** 已添加条目名称列表。 */
  chips: string[];
  /** 确认添加回调（名称已去除首尾空白）。 */
  onAdd: (name: string) => void;
  /** 按索引移除回调。 */
  onRemove: (index: number) => void;
  /** 输入框占位提示。 */
  placeholder: string;
}

/** 自由文本「输入 + 确认」chips 编辑器，供成员表单与菜谱表单复用。 */
export default function ChipInput({
  chips,
  onAdd,
  onRemove,
  placeholder,
}: ChipInputProps) {
  const [value, setValue] = useState("");

  // 确认添加：空值忽略，成功后清空输入框。
  const confirm = () => {
    const name = value.trim();
    if (!name) return;
    onAdd(name);
    setValue("");
  };

  return (
    <div className="flex flex-col gap-2">
      {chips.length > 0 && (
        <div className="flex flex-wrap gap-2">
          {chips.map((name, index) => (
            <span
              key={`${name}-${index}`}
              className="flex items-center gap-2 rounded-full border-2 border-gray-200 bg-white px-4 py-2 text-base text-gray-700"
            >
              {name}
              <button
                type="button"
                aria-label={`移除 ${name}`}
                onClick={() => onRemove(index)}
                className="text-gray-400 transition hover:text-red-600"
              >
                ×
              </button>
            </span>
          ))}
        </div>
      )}

      <div className="flex items-center gap-3">
        <input
          type="text"
          value={value}
          onChange={(e) => setValue(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter") {
              e.preventDefault();
              confirm();
            }
          }}
          placeholder={placeholder}
          className="h-11 min-w-0 flex-1 rounded-lg border-2 border-gray-200 px-4 text-base text-gray-800 outline-none focus:border-blue-600"
        />
        <button
          type="button"
          onClick={confirm}
          disabled={!value.trim()}
          className="h-11 shrink-0 rounded-lg bg-blue-600 px-4 text-base font-medium text-white transition hover:bg-blue-700 disabled:opacity-40"
        >
          确认
        </button>
      </div>
    </div>
  );
}

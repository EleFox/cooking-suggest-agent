import { Utensils } from "lucide-react";
import type { RecipeCard as RecipeCardType } from "../types/decision";

interface RecipeCardProps {
  card: RecipeCardType;
  onDelete: (id: number) => void;
  /** 编辑回调；传入时进入「管理」形态：底部文字操作栏（编辑 / 删除），无右上角删除角标。 */
  onEdit?: () => void;
  /** 卡片整体点击回调（跳转详情）；内部按钮已阻止冒泡，不会与其冲突。 */
  onOpen?: () => void;
}

/** 各难度对应的文字颜色。 */
const DIFFICULTY_COLORS: Record<string, string> = {
  简单: "text-green-600",
  一般: "text-blue-600",
  困难: "text-red-600",
};

/**
 * 菜谱卡片组件。
 *
 * - 结果页（不传 ``onEdit``）：右上角红色角标删除。
 * - 管理页（传 ``onEdit``）：底部右对齐文字操作栏（编辑 / 删除），与成员卡片一致。
 * - 传 ``onOpen`` 时卡片整体可点击跳转详情；删除 / 编辑按钮已阻断冒泡优先响应。
 *
 * 卡片字段由 ``elements`` 按 ``type`` 推导（ingredient 食材 / time 时间 /
 * difficulty 难度 / taste 口味）；某类型要素缺失时不渲染对应字段。
 */
export default function RecipeCard({
  card,
  onDelete,
  onEdit,
  onOpen,
}: RecipeCardProps) {
  const ingredients = card.elements
    .filter((item) => item.type === "ingredient")
    .map((item) => item.name);
  const tastes = card.elements
    .filter((item) => item.type === "taste")
    .map((item) => item.name);
  const timeElement = card.elements.find((item) => item.type === "time");
  const difficultyElement = card.elements.find(
    (item) => item.type === "difficulty",
  );
  const difficultyColor = difficultyElement
    ? (DIFFICULTY_COLORS[difficultyElement.name] ?? "text-blue-600")
    : "text-blue-600";
  const manageable = onEdit !== undefined;

  return (
    <div
      // overflow-hidden 让结果页右上角删除角标随卡片圆角裁切，避免超出圆角。
      onClick={onOpen}
      onKeyUp={onOpen ? (e) => e.key === "Enter" && onOpen() : undefined}
      role={onOpen ? "button" : undefined}
      tabIndex={onOpen ? 0 : undefined}
      className={`relative w-full overflow-hidden rounded-xl border-2 border-gray-200 bg-white ${
        onOpen ? "cursor-pointer transition hover:border-blue-300" : ""
      }`}
    >
      {!manageable && (
        // 删除热区（44px）：右上角竖直两边贴边，弧边朝卡片内部。
        <button
          type="button"
          aria-label={`删除 ${card.name}`}
          onClick={(e) => {
            // 阻止冒泡，避免触发卡片整体的详情跳转。
            e.stopPropagation();
            onDelete(card.id);
          }}
          className="absolute -right-0.5 -top-0.5 z-10 flex h-11 w-11 items-start justify-end"
        >
          <span className="flex h-[2.0625rem] w-[2.0625rem] items-center justify-center rounded-bl-[2.75rem] bg-red-600">
            <span
              className="translate-x-[3px] -translate-y-[3px] text-lg font-semibold leading-none text-white"
              aria-hidden="true"
            >
              ×
            </span>
          </span>
        </button>
      )}

      <div className="flex gap-3 p-4">
        <div
          className="flex h-24 w-24 shrink-0 items-center justify-center rounded-xl bg-blue-50"
          aria-hidden="true"
        >
          <Utensils className="h-8 w-8 text-blue-600" />
        </div>

        <div className="flex min-w-0 flex-col justify-center gap-1">
          <h2 className="truncate text-lg font-semibold text-gray-800">
            {card.name}
          </h2>

          {ingredients.length > 0 && (
            <div>
              <p className="text-[0.8125rem] font-medium text-gray-500">
                需要食材
              </p>
              <p className="line-clamp-2 text-sm text-gray-800">
                {ingredients.join("、")}
              </p>
            </div>
          )}

          {(timeElement || difficultyElement || tastes.length > 0) && (
            <div className="mt-0.5 flex flex-wrap gap-x-4 gap-y-1">
              {timeElement && (
                <div>
                  <p className="text-[0.8125rem] font-medium text-gray-500">
                    所需时间
                  </p>
                  <p className="text-sm text-blue-600">
                    约 {timeElement.name} 分钟
                  </p>
                </div>
              )}
              {difficultyElement && (
                <div>
                  <p className="text-[0.8125rem] font-medium text-gray-500">
                    烹饪难度
                  </p>
                  <p className={`text-sm ${difficultyColor}`}>
                    {difficultyElement.name}
                  </p>
                </div>
              )}
              {tastes.length > 0 && (
                <div>
                  <p className="text-[0.8125rem] font-medium text-gray-500">
                    口味
                  </p>
                  <p className="text-sm text-gray-800">{tastes.join("、")}</p>
                </div>
              )}
            </div>
          )}
        </div>
      </div>

      {manageable && (
        <div className="flex justify-end gap-4 px-4 pb-4">
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onEdit();
            }}
            className="text-base font-medium text-blue-600"
          >
            编辑
          </button>
          <button
            type="button"
            onClick={(e) => {
              e.stopPropagation();
              onDelete(card.id);
            }}
            className="text-base font-medium text-red-600"
          >
            删除
          </button>
        </div>
      )}
    </div>
  );
}

import type { ElementType } from "../types/decision";
import type { ElementItem } from "../types/element";
import type { Envelope } from "../types/decision";

/**
 * 按类型查询要素字典（设置页勾选选项 / 菜谱表单选项来源）。
 * @param type 要素类型（technique / time / difficulty）
 * @returns 统一信封包裹的要素数组
 */
export async function fetchElements(
  type: Extract<ElementType, "technique" | "time" | "difficulty">,
): Promise<Envelope<ElementItem[]>> {
  const res = await fetch(`/api/elements?type=${type}`);

  if (!res.ok) {
    throw new Error(`Elements request failed: ${res.status}`);
  }

  return (await res.json()) as Envelope<ElementItem[]>;
}

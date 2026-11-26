import type { DecisionRequest, Envelope, RecipeCard } from "../types/decision";

/**
 * 发起一次决策请求（首次生成与"再来一道"复用同一接口）。
 * @param payload 决策请求（数量、去重列表、要素偏好）
 * @returns 统一信封包裹的决策结果（data 直接为卡片数组）
 */
export async function requestDecisions(
  payload: DecisionRequest,
): Promise<Envelope<RecipeCard[]>> {
  const res = await fetch("/api/decisions", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });

  if (!res.ok) {
    throw new Error(`Decision request failed: ${res.status}`);
  }

  return (await res.json()) as Envelope<RecipeCard[]>;
}

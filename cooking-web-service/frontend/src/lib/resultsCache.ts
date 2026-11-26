import type { DecisionElement, RecipeCard } from "../types/decision";

/** sessionStorage 中缓存最近一次推荐结果的键。 */
const CACHE_KEY = "cooking.results.cache.v2";
/** sessionStorage 中标记「本次为一次新决策」的键。 */
const INTENT_KEY = "cooking.results.intent.v2";

/** 推荐结果的缓存内容（决策输入 + 卡片 + 提示）。 */
export interface ResultsCache {
  elements: DecisionElement[];
  count: number;
  dedupIds: number[];
  cards: RecipeCard[];
  notice: string | null;
}

/** 标记下一次进入结果页需要执行一次新决策。 */
export function markNewDecision(): void {
  try {
    sessionStorage.setItem(INTENT_KEY, "1");
  } catch {
    // sessionStorage 不可用时静默忽略（退化为每次重新决策）。
  }
}

/** 消费「新决策」标记：有则返回 true 并清除。 */
export function consumeNewDecision(): boolean {
  try {
    const value = sessionStorage.getItem(INTENT_KEY);
    if (value === null) return false;
    sessionStorage.removeItem(INTENT_KEY);
    return value === "1";
  } catch {
    return false;
  }
}

/** 读取缓存的推荐结果，无缓存或解析失败返回 null。 */
export function readResultsCache(): ResultsCache | null {
  try {
    const raw = sessionStorage.getItem(CACHE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as ResultsCache;
    if (
      !parsed ||
      !Array.isArray(parsed.cards) ||
      !Array.isArray(parsed.elements)
    ) {
      return null;
    }
    return parsed;
  } catch {
    return null;
  }
}

/** 写入推荐结果缓存。 */
export function writeResultsCache(cache: ResultsCache): void {
  try {
    sessionStorage.setItem(CACHE_KEY, JSON.stringify(cache));
  } catch {
    // 存储不可用时静默忽略。
  }
}

/** 从缓存的结果卡片中移除指定菜谱（菜谱被删除时保持缓存一致）。 */
export function removeRecipeFromCache(recipeId: number): void {
  const cache = readResultsCache();
  if (!cache) return;
  const cards = cache.cards.filter((card) => card.id !== recipeId);
  if (cards.length === cache.cards.length) return;
  writeResultsCache({ ...cache, cards });
}

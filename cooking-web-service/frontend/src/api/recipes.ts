import type { Envelope } from "../types/decision";
import type {
  RecipeCreateRequest,
  RecipeDeleteRequest,
  RecipeDetail,
  RecipeListData,
  RecipeSummary,
  RecipeUpdateRequest,
} from "../types/recipe";

/** 菜谱 CRUD 的公共请求封装，返回统一信封。 */
async function request<T>(
  url: string,
  init?: RequestInit,
): Promise<Envelope<T>> {
  const res = await fetch(url, init);

  if (!res.ok) {
    throw new Error(`Recipe request failed: ${res.status}`);
  }

  return (await res.json()) as Envelope<T>;
}

/** 分页查询菜谱列表（支持菜名关键字）。 */
export async function listRecipes(
  params: { keyword?: string; page?: number; page_size?: number } = {},
): Promise<Envelope<RecipeListData>> {
  const search = new URLSearchParams();
  if (params.keyword) search.set("keyword", params.keyword);
  if (params.page) search.set("page", String(params.page));
  if (params.page_size) search.set("page_size", String(params.page_size));
  const query = search.toString();
  return request(`/api/recipes${query ? `?${query}` : ""}`);
}

/** 批量查询菜谱详情（编辑回显取数组首项）。 */
export async function getRecipeDetails(
  ids: number[],
): Promise<Envelope<RecipeDetail[]>> {
  return request(`/api/recipes/detail?ids=${ids.join(",")}`);
}

/** 创建菜谱。 */
export async function createRecipe(
  payload: RecipeCreateRequest,
): Promise<Envelope<RecipeSummary>> {
  return request("/api/recipes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/** 更新菜谱（要素为增量操作）。 */
export async function updateRecipe(
  payload: RecipeUpdateRequest,
): Promise<Envelope<RecipeSummary>> {
  return request("/api/recipes", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/** 删除菜谱。 */
export async function deleteRecipe(
  payload: RecipeDeleteRequest,
): Promise<Envelope<null>> {
  return request("/api/recipes", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

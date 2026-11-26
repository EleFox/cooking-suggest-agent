import type { ElementType, RecipeElement } from "./decision";

/** 菜谱摘要（列表 / 创建 / 更新 / 决策卡片返回）。 */
export interface RecipeSummary {
  id: number;
  name: string;
  elements: RecipeElement[];
  has_detail: boolean;
}

/** 菜谱详情（批量详情 / 编辑回显）。 */
export interface RecipeDetail {
  id: number;
  name: string;
  elements: RecipeElement[];
  detail: string | null;
}

/** 菜谱分页列表的 data 内层结构。 */
export interface RecipeListData {
  list: RecipeSummary[];
  has_next: boolean;
  total: number;
  page: number;
  page_size: number;
}

/** 创建菜谱时的要素引用。 */
export interface RecipeRef {
  name: string;
  type: ElementType;
}

/** 更新菜谱时的要素增量操作项。 */
export interface RecipeOperate {
  name: string;
  type: ElementType;
  id?: number;
  operate: "add" | "remove" | "edit";
}

/** 创建菜谱请求体。 */
export interface RecipeCreateRequest {
  name: string;
  elements: RecipeRef[];
  detail?: string | null;
}

/** 更新菜谱请求体。 */
export interface RecipeUpdateRequest {
  id: number;
  name: string;
  elements: RecipeOperate[];
  detail?: string | null;
}

/** 删除菜谱请求体。 */
export interface RecipeDeleteRequest {
  id: number;
}

/** 决策相关的 TypeScript 类型定义，与后端接口契约保持一致。 */

/** 要素类型：食材 / 料理手段 / 料理时间 / 过敏原 / 口味 / 烹饪难度。 */
export type ElementType =
  "ingredient" | "technique" | "time" | "allergen" | "taste" | "difficulty";

/** 要素关系类型：偏好 / 禁忌。 */
export type RelationType = "preference" | "taboo";

/** 单个要素偏好项。 */
export interface DecisionElement {
  type: ElementType;
  /** 指向 t_element.id 的具体偏好要素。 */
  element_id: number;
  /** 关系类型：preference 偏好，taboo 禁忌。 */
  relation_type: RelationType;
}

/** 决策请求体。 */
export interface DecisionRequest {
  /** 本次生成数量。 */
  count: number;
  /** 已展示的菜谱 id（去重列表）。 */
  dedup_ids: number[];
  /** 要素偏好数组。 */
  elements: DecisionElement[];
}

/** 菜谱关联的单个要素。 */
export interface RecipeElement {
  id: number;
  type: ElementType;
  name: string;
  sort_order: number;
}

/** 菜谱结果卡片（与菜谱列表项同构）。 */
export interface RecipeCard {
  id: number;
  name: string;
  elements: RecipeElement[];
  has_detail: boolean;
}

/** 统一响应信封。 */
export interface Envelope<T> {
  code: number;
  data: T | null;
  message: string;
}

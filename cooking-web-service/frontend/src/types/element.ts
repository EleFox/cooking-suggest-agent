import type { ElementType } from "./decision";

/** 烹饪要素字典项（来自 GET /api/elements）。 */
export interface ElementItem {
  id: number;
  type: ElementType;
  name: string;
  sort_order: number;
}

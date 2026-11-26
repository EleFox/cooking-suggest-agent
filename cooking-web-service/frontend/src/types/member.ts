import type { ElementType } from "./decision";

/** 成员关联的要素（含要素 id）。 */
export interface MemberElement {
  id: number;
  name: string;
  type: ElementType;
}

/** 成员对象（来自 GET /api/members）。 */
export interface Member {
  id: number;
  name: string;
  preferences: MemberElement[];
  taboos: MemberElement[];
  created_at: string;
  updated_at: string;
}

/** 创建成员时的要素引用（{name, type}）。 */
export interface MemberRef {
  name: string;
  type: ElementType;
}

/** 更新成员时的要素增量操作项。 */
export interface MemberOperate {
  name: string;
  type: ElementType;
  id?: number;
  operate: "add" | "remove" | "edit";
}

/** 创建成员请求体。 */
export interface MemberCreateRequest {
  name: string;
  preferences: MemberRef[];
  taboos: MemberRef[];
}

/** 更新成员请求体。 */
export interface MemberUpdateRequest {
  id: number;
  name: string;
  preferences: MemberOperate[];
  taboos: MemberOperate[];
}

/** 删除成员请求体。 */
export interface MemberDeleteRequest {
  id: number;
}

/** 表单内的 chip 项：已存在项带 element id，用于编辑时生成差异。 */
export interface MemberChip {
  id?: number;
  name: string;
  type: ElementType;
}

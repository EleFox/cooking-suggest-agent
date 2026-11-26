/** 料理偏好方案相关类型定义，与后端接口契约保持一致。 */

/** 料理偏好方案对象。 */
export interface PreferenceScheme {
  id: number;
  name: string;
  /** 1=默认方案，0=非默认。 */
  is_default: number;
  /** 偏好要素 id 数组。 */
  element_ids: number[];
  created_at: string;
  updated_at: string;
}

/** 方案列表的分页信封内层结构。 */
export interface PreferenceSchemeListData {
  list: PreferenceScheme[];
  has_next: boolean;
  total: number;
  page: number;
  page_size: number;
}

/** 创建方案请求体。 */
export interface PreferenceSchemeCreateRequest {
  name: string;
  element_ids: number[];
}

/** 更新方案请求体。 */
export interface PreferenceSchemeUpdateRequest {
  id: number;
  name: string;
  element_ids: number[];
  is_default: number;
}

/** 删除方案请求体。 */
export interface PreferenceSchemeDeleteRequest {
  id: number;
}

import type { Envelope } from "../types/decision";
import type {
  PreferenceScheme,
  PreferenceSchemeCreateRequest,
  PreferenceSchemeDeleteRequest,
  PreferenceSchemeListData,
  PreferenceSchemeUpdateRequest,
} from "../types/preferenceScheme";

/** 方案 CRUD 的公共请求封装，返回统一信封。 */
async function request<T>(
  url: string,
  init?: RequestInit,
): Promise<Envelope<T>> {
  const res = await fetch(url, init);

  if (!res.ok) {
    throw new Error(`Preference scheme request failed: ${res.status}`);
  }

  return (await res.json()) as Envelope<T>;
}

/** 创建料理偏好方案。 */
export async function createScheme(
  payload: PreferenceSchemeCreateRequest,
): Promise<Envelope<PreferenceScheme>> {
  return request("/api/preference-schemes", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/** 分页查询方案列表（每项含完整 element_ids）。 */
export async function listSchemes(): Promise<
  Envelope<PreferenceSchemeListData>
> {
  return request("/api/preference-schemes");
}

/** 查询默认方案；无默认方案时 data 为 null。 */
export async function getDefaultScheme(): Promise<
  Envelope<PreferenceScheme | null>
> {
  return request("/api/preference-schemes/default");
}

/** 更新方案名称 / 勾选项 / 默认标记。 */
export async function updateScheme(
  payload: PreferenceSchemeUpdateRequest,
): Promise<Envelope<PreferenceScheme>> {
  return request("/api/preference-schemes", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/** 删除方案。 */
export async function deleteScheme(
  payload: PreferenceSchemeDeleteRequest,
): Promise<Envelope<null>> {
  return request("/api/preference-schemes", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

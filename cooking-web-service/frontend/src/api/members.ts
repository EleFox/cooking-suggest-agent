import type { Envelope } from "../types/decision";
import type {
  Member,
  MemberCreateRequest,
  MemberDeleteRequest,
  MemberUpdateRequest,
} from "../types/member";

/** 成员 CRUD 的公共请求封装，返回统一信封。 */
async function request<T>(
  url: string,
  init?: RequestInit,
): Promise<Envelope<T>> {
  const res = await fetch(url, init);

  if (!res.ok) {
    throw new Error(`Member request failed: ${res.status}`);
  }

  return (await res.json()) as Envelope<T>;
}

/** 查询成员列表（不分页，含完整偏好 / 禁忌要素）。 */
export async function listMembers(): Promise<Envelope<Member[]>> {
  return request("/api/members");
}

/** 创建成员。 */
export async function createMember(
  payload: MemberCreateRequest,
): Promise<Envelope<Member>> {
  return request("/api/members", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/** 更新成员（要素为增量操作）。 */
export async function updateMember(
  payload: MemberUpdateRequest,
): Promise<Envelope<Member>> {
  return request("/api/members", {
    method: "PUT",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

/** 删除成员。 */
export async function deleteMember(
  payload: MemberDeleteRequest,
): Promise<Envelope<null>> {
  return request("/api/members", {
    method: "DELETE",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(payload),
  });
}

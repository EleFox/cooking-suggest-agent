import { create } from "zustand";
import { listMembers } from "../api/members";
import type { Member } from "../types/member";

interface MemberStore {
  /** 成员列表（设置页与结果页共享，结果页展开成员要素用）。 */
  members: Member[];
  loading: boolean;
  error: string | null;
  /** 拉取成员列表（每次调用都请求，保证启停前数据最新）。 */
  load: () => Promise<void>;
}

/** 成员列表共享缓存：设置页成员区与结果页成员要素展开共用。 */
export const useMemberStore = create<MemberStore>((set) => ({
  members: [],
  loading: false,
  error: null,
  load: async () => {
    set({ loading: true, error: null });
    try {
      const envelope = await listMembers();
      if (envelope.code !== 200 || !envelope.data) {
        set({ loading: false, error: envelope.message || "成员加载失败" });
        return;
      }
      set({ members: envelope.data, loading: false });
    } catch {
      set({ loading: false, error: "成员加载失败" });
    }
  },
}));

/** 按成员 id 集合筛选成员（结果页按 member_ids 展开用）。 */
export function membersByIds(ids: number[]): Member[] {
  const wanted = new Set(ids);
  return useMemberStore.getState().members.filter((m) => wanted.has(m.id));
}

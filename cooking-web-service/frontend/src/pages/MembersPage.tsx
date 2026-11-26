import { Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { deleteMember, listMembers } from "../api/members";
import ActionButton from "../components/ui/ActionButton";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import type { Member, MemberElement } from "../types/member";

/** 只读 chip 展示（成员卡片摘要）。 */
function ReadonlyChips({ items }: { items: MemberElement[] }) {
  if (items.length === 0)
    return <span className="text-sm text-gray-400">无</span>;
  return (
    <div className="flex flex-wrap gap-2">
      {items.map((item) => (
        <span
          key={item.id}
          className="rounded-full bg-gray-100 px-3 py-1 text-sm text-gray-700"
        >
          {item.name}
        </span>
      ))}
    </div>
  );
}

/** 成员管理页：成员列表展示与新增 / 编辑 / 删除。 */
export default function MembersPage() {
  const navigate = useNavigate();

  const [members, setMembers] = useState<Member[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<Member | null>(null);
  const [deleting, setDeleting] = useState(false);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const envelope = await listMembers();
      if (envelope.code !== 200 || !envelope.data) {
        setError(envelope.message || "加载成员失败");
        setMembers([]);
        return;
      }
      setMembers(envelope.data);
    } catch {
      setError("服务暂时不可用，请稍后重试");
      setMembers([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const confirmDelete = useCallback(async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      const envelope = await deleteMember({ id: deleteTarget.id });
      if (envelope.code !== 200) {
        setError(envelope.message || "删除失败");
        setDeleteTarget(null);
        return;
      }
      setMembers((prev) => prev.filter((item) => item.id !== deleteTarget.id));
      setDeleteTarget(null);
    } catch {
      setError("服务暂时不可用，请稍后重试");
      setDeleteTarget(null);
    } finally {
      setDeleting(false);
    }
  }, [deleteTarget]);

  return (
    <main className="min-h-dvh bg-white">
      <div className="flex w-full flex-col gap-4 px-5 pb-40 pt-4">
        <h1 className="text-2xl font-bold leading-8 text-gray-800">家庭成员</h1>

        {loading && (
          <div className="flex items-center justify-center gap-3 py-8">
            <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            <p className="text-sm text-gray-500">正在加载成员…</p>
          </div>
        )}

        {error && (
          <div className="rounded-xl border-2 border-red-200 bg-red-50 p-4 text-center text-sm text-red-600">
            {error}
          </div>
        )}

        {!loading && !error && members.length === 0 && (
          <div className="rounded-xl border-2 border-dashed border-gray-200 p-6 text-center text-sm text-gray-500">
            还没有家庭成员，点击下方按钮新增吧
          </div>
        )}

        {!loading && members.length > 0 && (
          <div className="flex flex-col gap-3">
            {members.map((member) => {
              const ingredients = member.preferences.filter(
                (item) => item.type === "ingredient",
              );
              const tastes = member.preferences.filter(
                (item) => item.type === "taste",
              );
              return (
                <article
                  key={member.id}
                  className="flex flex-col gap-3 rounded-xl border-2 border-gray-200 bg-white p-4"
                >
                  <h2 className="truncate text-lg font-semibold text-gray-800">
                    {member.name}
                  </h2>

                  <div className="flex flex-col gap-2">
                    <p className="text-base font-medium text-gray-800">偏好</p>
                    <div className="flex flex-col gap-1.5">
                      <p className="text-sm text-gray-500">食材</p>
                      <ReadonlyChips items={ingredients} />
                    </div>
                    <div className="flex flex-col gap-1.5">
                      <p className="text-sm text-gray-500">口味</p>
                      <ReadonlyChips items={tastes} />
                    </div>
                  </div>

                  <div className="flex flex-col gap-1.5">
                    <p className="text-base font-medium text-gray-800">
                      食材禁忌
                    </p>
                    <ReadonlyChips items={member.taboos} />
                  </div>

                  <div className="flex justify-end gap-4 pt-2">
                    <button
                      type="button"
                      onClick={() => navigate(`/members/form?id=${member.id}`)}
                      className="text-base font-medium text-blue-600"
                    >
                      编辑
                    </button>
                    <button
                      type="button"
                      onClick={() => setDeleteTarget(member)}
                      className="text-base font-medium text-red-600"
                    >
                      删除
                    </button>
                  </div>
                </article>
              );
            })}
          </div>
        )}
      </div>

      <div className="fixed inset-x-0 bottom-0 z-30 bg-white shadow-[0_-2px_12px_rgba(0,0,0,0.06)]">
        <div className="flex w-full flex-col gap-2 px-5 pb-4 pt-2">
          <ActionButton
            type="button"
            variant="secondary"
            onClick={() => navigate("/preferences")}
          >
            返回偏好设置
          </ActionButton>
          <ActionButton type="button" onClick={() => navigate("/members/form")}>
            新增成员
          </ActionButton>
        </div>
      </div>

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title="删除成员"
        description={
          deleteTarget ? `确定删除成员「${deleteTarget.name}」？` : ""
        }
        confirmText="删除"
        danger
        loading={deleting}
        onConfirm={confirmDelete}
      />
    </main>
  );
}

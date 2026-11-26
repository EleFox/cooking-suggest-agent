import { Loader2 } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import {
  deleteScheme,
  listSchemes,
  updateScheme,
} from "../api/preferenceSchemes";
import ActionButton from "../components/ui/ActionButton";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import {
  elementNameById,
  timeTierLabel,
  useElementStore,
} from "../stores/elementStore";
import type { PreferenceScheme } from "../types/preferenceScheme";

/** 由 element_ids 反查要素名，生成方案摘要文案。 */
function schemeSummary(elementIds: number[]): string {
  const techniqueNames: string[] = [];
  let timeLabel: string | null = null;
  for (const id of elementIds) {
    const name = elementNameById(id);
    if (name === null) continue;
    // 时间档位要素的 name 为纯数字分钟数。
    if (/^\d+$/.test(name)) {
      timeLabel = timeTierLabel(name);
    } else {
      techniqueNames.push(name);
    }
  }
  const parts = [techniqueNames.join("、")];
  if (timeLabel) parts.push(timeLabel);
  return parts.filter(Boolean).join(" · ") || "未选择偏好";
}

/** 料理偏好方案管理页：列表展示与默认开关 / 调出 / 编辑 / 删除。 */
export default function SchemesPage() {
  const navigate = useNavigate();

  const loadOptions = useElementStore((s) => s.load);
  const [schemes, setSchemes] = useState<PreferenceScheme[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  // 待删除确认的方案；非空时弹出确认对话框。
  const [deleteTarget, setDeleteTarget] = useState<PreferenceScheme | null>(
    null,
  );
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadOptions();
  }, [loadOptions]);

  const refresh = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const envelope = await listSchemes();
      if (envelope.code !== 200 || !envelope.data) {
        setError(envelope.message || "加载方案失败");
        setSchemes([]);
        return;
      }
      setSchemes(envelope.data.list);
    } catch {
      setError("服务暂时不可用，请稍后重试");
      setSchemes([]);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const handleDefaultToggle = useCallback(async (scheme: PreferenceScheme) => {
    const nextDefault = scheme.is_default === 1 ? 0 : 1;
    try {
      const envelope = await updateScheme({
        id: scheme.id,
        name: scheme.name,
        element_ids: scheme.element_ids,
        is_default: nextDefault,
      });
      if (envelope.code !== 200) {
        setError(envelope.message || "操作失败");
        return;
      }
      setError(null);
      setSchemes((prev) =>
        prev.map((item) =>
          item.id === scheme.id
            ? { ...item, is_default: nextDefault }
            : nextDefault === 1
              ? { ...item, is_default: 0 }
              : item,
        ),
      );
    } catch {
      setError("服务暂时不可用，请稍后重试");
    }
  }, []);

  const handleDelete = useCallback((scheme: PreferenceScheme) => {
    setError(null);
    setDeleteTarget(scheme);
  }, []);

  // 确认删除：调用接口成功后从列表移除并关闭对话框。
  const confirmDelete = useCallback(async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      const envelope = await deleteScheme({ id: deleteTarget.id });
      if (envelope.code !== 200) {
        setError(envelope.message || "删除失败");
        setDeleteTarget(null);
        return;
      }
      setError(null);
      setSchemes((prev) => prev.filter((item) => item.id !== deleteTarget.id));
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
        <h1 className="text-2xl font-bold leading-8 text-gray-800">
          料理偏好方案
        </h1>

        {loading && (
          <div className="flex items-center justify-center gap-3 py-8">
            <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            <p className="text-sm text-gray-500">正在加载方案…</p>
          </div>
        )}

        {error && (
          <div className="rounded-xl border-2 border-red-200 bg-red-50 p-4 text-center text-sm text-red-600">
            {error}
          </div>
        )}

        {!loading && !error && schemes.length === 0 && (
          <div className="rounded-xl border-2 border-dashed border-gray-200 p-6 text-center text-sm text-gray-500">
            还没有保存的方案，去设置页勾选偏好后保存一个吧
          </div>
        )}

        {!loading && schemes.length > 0 && (
          <div className="flex flex-col gap-3">
            {schemes.map((scheme) => (
              <article
                key={scheme.id}
                className="flex flex-col gap-3 rounded-xl border border-gray-200 bg-white p-4"
              >
                <div className="flex items-center justify-between gap-3">
                  <h2 className="truncate text-xl font-semibold text-gray-800">
                    {scheme.name}
                  </h2>
                  <label className="flex shrink-0 items-center gap-2 text-sm text-gray-600">
                    <span>默认</span>
                    <input
                      type="checkbox"
                      checked={scheme.is_default === 1}
                      onChange={() => handleDefaultToggle(scheme)}
                      className="h-5 w-5 accent-blue-600"
                    />
                  </label>
                </div>

                <p className="text-sm text-gray-500">
                  {schemeSummary(scheme.element_ids)}
                </p>

                <div className="flex justify-end gap-4 pt-2">
                  <button
                    type="button"
                    onClick={() =>
                      navigate(`/preferences?scheme_id=${scheme.id}`)
                    }
                    className="text-base font-medium text-blue-600"
                  >
                    调出
                  </button>
                  <button
                    type="button"
                    onClick={() =>
                      navigate(`/preferences?edit_scheme_id=${scheme.id}`)
                    }
                    className="text-base font-medium text-blue-600"
                  >
                    编辑
                  </button>
                  <button
                    type="button"
                    onClick={() => handleDelete(scheme)}
                    className="text-base font-medium text-red-600"
                  >
                    删除
                  </button>
                </div>
              </article>
            ))}
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
          <ActionButton
            type="button"
            onClick={() => navigate("/preferences?mode=create")}
          >
            新建方案
          </ActionButton>
        </div>
      </div>

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title="删除方案"
        description={
          deleteTarget ? `确定删除方案「${deleteTarget.name}」？` : ""
        }
        confirmText="删除"
        danger
        loading={deleting}
        onConfirm={confirmDelete}
      />
    </main>
  );
}

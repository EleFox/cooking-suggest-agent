import { ArrowLeft } from "lucide-react";
import Markdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { useCallback, useEffect, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { getRecipeDetails } from "../api/recipes";
import type { RecipeDetail } from "../types/recipe";

/**
 * 菜谱详情页：按 query id 拉取详情，将做法 Markdown 渲染展示。
 *
 * 无 UI 原型要求，仅做轻量展示：标题 + prose 排版正文 + 返回按钮。
 */
export default function RecipeDetailPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const [detail, setDetail] = useState<RecipeDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // 从 query 解析菜谱 id，非法时直接提示错误不再请求。
  const id = Number(searchParams.get("id"));
  const idValid = Number.isInteger(id) && id > 0;

  const fetchDetail = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const envelope = await getRecipeDetails([id]);
      if (envelope.code !== 200) {
        setError(envelope.message || "加载菜谱详情失败");
        return;
      }
      const found = envelope.data?.[0] ?? null;
      if (!found) {
        setError("菜谱不存在或已被删除");
        return;
      }
      setDetail(found);
    } catch {
      setError("服务暂时不可用，请稍后重试");
    } finally {
      setLoading(false);
    }
  }, [id]);

  useEffect(() => {
    if (!idValid) {
      setError("缺少有效的菜谱 id");
      setLoading(false);
      return;
    }
    fetchDetail();
  }, [idValid, fetchDetail]);

  return (
    <main className="min-h-dvh bg-white">
      <div className="flex w-full flex-col gap-4 px-5 pb-10 pt-4">
        <div className="flex items-center gap-2">
          <button
            type="button"
            aria-label="返回"
            onClick={() => navigate(-1)}
            className="-ml-2 flex h-11 w-11 items-center justify-center rounded-full text-gray-600 hover:bg-gray-100"
          >
            <ArrowLeft className="h-6 w-6" />
          </button>
          <h1 className="min-w-0 truncate text-2xl font-bold leading-8 text-gray-800">
            {detail?.name ?? "菜谱详情"}
          </h1>
        </div>

        {loading && (
          <p className="py-8 text-center text-sm text-gray-500">
            正在加载菜谱详情…
          </p>
        )}

        {error && !loading && (
          <div className="rounded-xl border-2 border-red-200 bg-red-50 p-4 text-center text-sm text-red-600">
            {error}
          </div>
        )}

        {!loading &&
          !error &&
          detail &&
          (detail.detail ? (
            // prose 基础排版 + 移动端字号收敛，适配窄屏自适应方案。
            <article className="prose prose-sm sm:prose-base max-w-none prose-headings:text-gray-800 prose-p:text-gray-700 prose-li:text-gray-700 prose-strong:text-gray-800 prose-code:rounded prose-code:bg-gray-100 prose-code:px-1 prose-code:text-gray-800 prose-pre:bg-gray-900 prose-pre:text-gray-100">
              <Markdown remarkPlugins={[remarkGfm]}>{detail.detail}</Markdown>
            </article>
          ) : (
            <div className="rounded-xl border-2 border-dashed border-gray-200 p-6 text-center text-sm text-gray-500">
              该菜谱暂无做法详情
            </div>
          ))}
      </div>
    </main>
  );
}

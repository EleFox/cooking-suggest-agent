import { Loader2, Search } from "lucide-react";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import { deleteRecipe, listRecipes } from "../api/recipes";
import RecipeCard from "../components/RecipeCard";
import ActionButton from "../components/ui/ActionButton";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import { removeRecipeFromCache } from "../lib/resultsCache";
import type { RecipeSummary } from "../types/recipe";

/** 每页条数。 */
const PAGE_SIZE = 20;

/** 菜谱管理页：全池菜谱分页列表 + 搜索 + 新增 / 编辑 / 删除。 */
export default function RecipesPage() {
  const navigate = useNavigate();

  const [keyword, setKeyword] = useState("");
  const [appliedKeyword, setAppliedKeyword] = useState("");
  const [recipes, setRecipes] = useState<RecipeSummary[]>([]);
  const [page, setPage] = useState(1);
  const [hasNext, setHasNext] = useState(false);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<RecipeSummary | null>(null);
  const [deleting, setDeleting] = useState(false);

  const fetchPage = useCallback(
    async (pageToLoad: number, append: boolean) => {
      setLoading(true);
      setError(null);
      try {
        const envelope = await listRecipes({
          keyword: appliedKeyword || undefined,
          page: pageToLoad,
          page_size: PAGE_SIZE,
        });
        if (envelope.code !== 200 || !envelope.data) {
          setError(envelope.message || "加载菜谱失败");
          if (!append) setRecipes([]);
          return;
        }
        const data = envelope.data;
        setRecipes((prev) => (append ? [...prev, ...data.list] : data.list));
        setHasNext(data.has_next);
        setPage(data.page);
      } catch {
        setError("服务暂时不可用，请稍后重试");
        if (!append) setRecipes([]);
      } finally {
        setLoading(false);
      }
    },
    [appliedKeyword],
  );

  useEffect(() => {
    fetchPage(1, false);
  }, [fetchPage]);

  const confirmDelete = useCallback(async () => {
    if (!deleteTarget) return;
    setDeleting(true);
    try {
      const envelope = await deleteRecipe({ id: deleteTarget.id });
      if (envelope.code !== 200) {
        setError(envelope.message || "删除失败");
        setDeleteTarget(null);
        return;
      }
      setRecipes((prev) => prev.filter((item) => item.id !== deleteTarget.id));
      // 同步结果缓存，避免返回推荐页时仍显示已删菜谱。
      removeRecipeFromCache(deleteTarget.id);
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
      <div className="flex w-full flex-col gap-3 px-5 pb-40 pt-4">
        <h1 className="text-2xl font-bold leading-8 text-gray-800">菜谱管理</h1>

        <form
          onSubmit={(e) => {
            e.preventDefault();
            setAppliedKeyword(keyword.trim());
          }}
          className="flex h-11 items-center gap-2 rounded-lg border-2 border-gray-200 px-3"
        >
          <Search className="h-5 w-5 shrink-0 text-gray-400" />
          <input
            type="text"
            value={keyword}
            onChange={(e) => setKeyword(e.target.value)}
            placeholder="搜索菜谱"
            className="min-w-0 flex-1 bg-transparent text-base text-gray-800 outline-none"
          />
        </form>

        {loading && recipes.length === 0 && (
          <div className="flex items-center justify-center gap-3 py-8">
            <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            <p className="text-sm text-gray-500">正在加载菜谱…</p>
          </div>
        )}

        {error && (
          <div className="rounded-xl border-2 border-red-200 bg-red-50 p-4 text-center text-sm text-red-600">
            {error}
          </div>
        )}

        {!loading && !error && recipes.length === 0 && (
          <div className="rounded-xl border-2 border-dashed border-gray-200 p-6 text-center text-sm text-gray-500">
            没有找到菜谱，试试新增一道吧
          </div>
        )}

        {recipes.length > 0 && (
          <div className="flex flex-col gap-3">
            {recipes.map((recipe) => (
              <RecipeCard
                key={recipe.id}
                card={recipe}
                onEdit={() => navigate(`/recipes/form?id=${recipe.id}`)}
                onDelete={() => setDeleteTarget(recipe)}
                onOpen={() => navigate(`/recipes/detail?id=${recipe.id}`)}
              />
            ))}
          </div>
        )}

        {hasNext && (
          <button
            type="button"
            onClick={() => fetchPage(page + 1, true)}
            disabled={loading}
            className="h-11 w-full rounded-lg border-2 border-blue-600 text-base font-medium text-blue-600 transition hover:bg-blue-50 disabled:opacity-40"
          >
            {loading ? "加载中…" : "加载更多"}
          </button>
        )}
      </div>

      <div className="fixed inset-x-0 bottom-0 z-30 bg-white shadow-[0_-2px_12px_rgba(0,0,0,0.06)]">
        <div className="flex w-full flex-col gap-2 px-5 pb-4 pt-2">
          <ActionButton
            type="button"
            variant="secondary"
            onClick={() => navigate("/results")}
          >
            返回菜单推荐
          </ActionButton>
          <ActionButton type="button" onClick={() => navigate("/recipes/form")}>
            新增菜谱
          </ActionButton>
        </div>
      </div>

      <ConfirmDialog
        open={deleteTarget !== null}
        onOpenChange={(open) => {
          if (!open) setDeleteTarget(null);
        }}
        title="删除菜谱"
        description={
          deleteTarget
            ? `确定删除菜谱「${deleteTarget.name}」？删除后不可恢复。`
            : ""
        }
        confirmText="删除"
        danger
        loading={deleting}
        onConfirm={confirmDelete}
      />
    </main>
  );
}

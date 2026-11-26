import { Loader2 } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { requestDecisions } from "../api/decisions";
import { deleteRecipe } from "../api/recipes";
import RecipeCard from "../components/RecipeCard";
import ActionButton from "../components/ui/ActionButton";
import ConfirmDialog from "../components/ui/ConfirmDialog";
import {
  consumeNewDecision,
  readResultsCache,
  removeRecipeFromCache,
  writeResultsCache,
} from "../lib/resultsCache";
import { elementTypeById, useElementStore } from "../stores/elementStore";
import { useMemberStore } from "../stores/memberStore";
import type {
  DecisionElement,
  RecipeCard as RecipeCardType,
} from "../types/decision";

/** 结果卡片列表页：新决策时按偏好 element_ids + 启用成员发起，返回时回显 sessionStorage 缓存。 */
export default function ResultsPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();

  const techniques = useElementStore((s) => s.techniques);
  const timeTiers = useElementStore((s) => s.timeTiers);
  const optionsError = useElementStore((s) => s.error);
  const loadOptions = useElementStore((s) => s.load);

  const members = useMemberStore((s) => s.members);
  const loadMembers = useMemberStore((s) => s.load);

  const [cards, setCards] = useState<RecipeCardType[]>([]);
  const [loading, setLoading] = useState(false);
  const [notice, setNotice] = useState<string | null>(null);
  const [error, setError] = useState<string | null>(null);
  // 成员列表就绪标记：新决策需在首次生成前完成成员加载，才能展开成员要素。
  const [membersReady, setMembersReady] = useState(false);
  // 进入模式：new = 执行新决策；restore = 回显缓存；null = 初始化中。
  const [mode, setMode] = useState<"new" | "restore" | null>(null);
  const [deleteTarget, setDeleteTarget] = useState<RecipeCardType | null>(null);
  const [deleting, setDeleting] = useState(false);

  // 用 ref 持有去重列表、卡片与请求中标记，避免回调闭包读到过期状态。
  const dedupRef = useRef<number[]>([]);
  const cardsRef = useRef<RecipeCardType[]>([]);
  const loadingRef = useRef(false);
  const generateStartedRef = useRef(false);
  const elementsRef = useRef<DecisionElement[]>([]);
  const countRef = useRef(1);
  // 首次自动生成使用的数量（来自设置页步进器）；消费一次后置空，
  // 之后的「再来一道」一律只增加 1 道。
  const initialCountRef = useRef<number | null>(null);
  const initializedRef = useRef(false);

  // 从 query 解析勾选要素 id，等待要素选项加载完成后做 id→type 映射。
  const elementIds = useMemo(() => {
    const raw = searchParams.get("element_ids");
    if (!raw) return [];
    return raw
      .split(",")
      .map((value) => Number(value))
      .filter((value) => Number.isInteger(value) && value > 0);
  }, [searchParams]);

  // 从 query 解析启用成员 id。
  const memberIds = useMemo(() => {
    const raw = searchParams.get("member_ids");
    if (!raw) return [];
    return raw
      .split(",")
      .map((value) => Number(value))
      .filter((value) => Number.isInteger(value) && value > 0);
  }, [searchParams]);

  // 从 query 解析生成数量，非法或缺省时回退为 1。
  const count = useMemo(() => {
    const raw = searchParams.get("count");
    if (!raw || !/^\d+$/.test(raw)) return 1;
    const n = Number(raw);
    return n >= 1 ? n : 1;
  }, [searchParams]);

  // 初始化：优先消费「新决策」标记；否则回显缓存（从菜谱管理返回不重新决策）。
  useEffect(() => {
    if (initializedRef.current) return;
    initializedRef.current = true;

    const forceNew = consumeNewDecision();
    const cache = readResultsCache();
    if (!forceNew && cache) {
      cardsRef.current = cache.cards;
      dedupRef.current = cache.dedupIds;
      elementsRef.current = cache.elements;
      countRef.current = cache.count;
      setCards(cache.cards);
      setNotice(cache.notice);
      setMode("restore");
      return;
    }
    countRef.current = count;
    setMode("new");
  }, [count]);

  useEffect(() => {
    loadOptions();
  }, [loadOptions]);

  // 加载成员列表（新决策展开成员要素用）。
  useEffect(() => {
    let active = true;
    loadMembers().finally(() => {
      if (active) setMembersReady(true);
    });
    return () => {
      active = false;
    };
  }, [loadMembers]);

  const optionsReady = techniques.length > 0 && timeTiers.length > 0;

  // 组装 elements：设置页勾选恒 relation_type=preference；启用成员偏好=preference、
  // 禁忌=taboo；与设置页勾选同 id 冲突时以设置页为准；偏好×禁忌交叉冲突原样传入。
  useEffect(() => {
    if (mode !== "new") return;
    const base: DecisionElement[] = elementIds.flatMap((id) => {
      const type = elementTypeById(id);
      return type
        ? [{ type, element_id: id, relation_type: "preference" as const }]
        : [];
    });
    const settingsIds = new Set(base.map((item) => item.element_id));
    const preferenceMap = new Map<number, DecisionElement>();
    const tabooMap = new Map<number, DecisionElement>();

    const enabledIds = new Set(memberIds);
    for (const member of members.filter((item) => enabledIds.has(item.id))) {
      for (const preference of member.preferences) {
        if (settingsIds.has(preference.id)) continue;
        preferenceMap.set(preference.id, {
          type: preference.type,
          element_id: preference.id,
          relation_type: "preference",
        });
      }
      for (const taboo of member.taboos) {
        if (settingsIds.has(taboo.id)) continue;
        tabooMap.set(taboo.id, {
          type: taboo.type,
          element_id: taboo.id,
          relation_type: "taboo",
        });
      }
    }

    elementsRef.current = [
      ...base,
      ...preferenceMap.values(),
      ...tabooMap.values(),
    ];
  }, [mode, elementIds, memberIds, techniques, timeTiers, members]);

  const persist = useCallback((noticeValue: string | null) => {
    writeResultsCache({
      elements: elementsRef.current,
      count: countRef.current,
      dedupIds: dedupRef.current,
      cards: cardsRef.current,
      notice: noticeValue,
    });
  }, []);

  const generate = useCallback(async () => {
    if (loadingRef.current) return;
    loadingRef.current = true;
    setLoading(true);
    setError(null);
    setNotice(null);
    // 首次生成按设置页步进器数量，其余（「再来一道」）每次只增加 1 道。
    const requestCount = initialCountRef.current ?? 1;
    initialCountRef.current = null;
    try {
      const envelope = await requestDecisions({
        count: requestCount,
        dedup_ids: dedupRef.current,
        elements: elementsRef.current,
      });
      if (envelope.code !== 200 || !envelope.data) {
        setError(envelope.message || "服务暂时不可用，请稍后重试");
        return;
      }
      const newCards = envelope.data;
      if (newCards.length === 0) {
        const message = envelope.message || "没有合适的菜了";
        setNotice(message);
        persist(message);
        return;
      }
      const nextCards = [...cardsRef.current, ...newCards];
      cardsRef.current = nextCards;
      dedupRef.current = [...dedupRef.current, ...newCards.map((c) => c.id)];
      setCards(nextCards);
      persist(null);
    } catch {
      setError("服务暂时不可用，请稍后重试");
    } finally {
      loadingRef.current = false;
      setLoading(false);
    }
  }, [persist]);

  // 新决策：成员列表就绪，且（有设置页勾选时）要素选项就绪后才自动发起一次。
  // 设置页勾选需要经要素选项做 id→type 映射，选项未就绪时不得生成，
  // 否则会静默丢弃设置页要素；无设置页勾选时仅靠成员要素即可生成。
  const settingsResolved = elementIds.length === 0 || optionsReady;
  const dataReady = mode === "new" && membersReady && settingsResolved;

  useEffect(() => {
    if (mode !== "new") return;
    if (generateStartedRef.current) return;
    if (!dataReady) return;
    generateStartedRef.current = true;
    // 标记首次生成使用 query 携带的生成数量；「再来一道」不再沿用该值。
    initialCountRef.current = countRef.current;
    generate();
  }, [mode, dataReady, generate]);

  const requestDelete = useCallback((id: number) => {
    const target = cardsRef.current.find((card) => card.id === id) ?? null;
    setDeleteTarget(target);
  }, []);

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
      const nextCards = cardsRef.current.filter(
        (card) => card.id !== deleteTarget.id,
      );
      cardsRef.current = nextCards;
      setCards(nextCards);
      // 同步缓存，避免从菜谱管理返回时又出现已删卡片。
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
        <h1 className="text-2xl font-bold leading-8 text-gray-800">
          为你挑了以下菜品
        </h1>

        <div className="flex flex-col gap-4">
          {cards.map((card) => (
            <RecipeCard
              key={card.id}
              card={card}
              onDelete={requestDelete}
              onOpen={() => navigate(`/recipes/detail?id=${card.id}`)}
            />
          ))}
        </div>

        {loading && (
          <div className="flex flex-col items-center gap-3 py-8">
            <Loader2 className="h-8 w-8 animate-spin text-blue-600" />
            <p className="text-sm text-gray-500">正在为你挑选菜品…</p>
          </div>
        )}

        {notice && !loading && (
          <p className="py-4 text-center text-sm text-gray-500">{notice}</p>
        )}

        {error && !loading && (
          <div className="rounded-xl border-2 border-red-200 bg-red-50 p-4 text-center text-sm text-red-600">
            {error}
          </div>
        )}

        {optionsError && elementIds.length > 0 && !optionsReady && !loading && (
          <div className="flex flex-col items-center gap-3 rounded-xl border-2 border-red-200 bg-red-50 p-4 text-center text-sm text-red-600">
            <span>偏好选项加载失败，无法组装偏好要素</span>
            <button
              type="button"
              onClick={loadOptions}
              className="rounded-full bg-red-600 px-4 py-1.5 text-white"
            >
              重试
            </button>
          </div>
        )}
      </div>

      <div className="fixed inset-x-0 bottom-0 z-30 bg-white shadow-[0_-2px_12px_rgba(0,0,0,0.06)]">
        <div className="flex w-full flex-col gap-2 px-5 pb-4 pt-2">
          <ActionButton type="button" onClick={generate} disabled={loading}>
            {loading ? "生成中…" : "再来一道"}
          </ActionButton>
          <ActionButton
            type="button"
            variant="secondary"
            onClick={() => navigate("/recipes")}
          >
            菜谱管理
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

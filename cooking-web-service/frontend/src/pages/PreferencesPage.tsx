import { Loader2, ChevronRight } from "lucide-react";
import { useCallback, useEffect, useMemo, useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import {
  createScheme,
  getDefaultScheme,
  listSchemes,
  updateScheme,
} from "../api/preferenceSchemes";
import ActionButton from "../components/ui/ActionButton";
import Dialog from "../components/ui/Dialog";
import { cn } from "../lib/utils";
import { markNewDecision } from "../lib/resultsCache";
import { timeTierLabel, useElementStore } from "../stores/elementStore";
import { useMemberStore } from "../stores/memberStore";

/** 可点击的勾选 chip，选中态为蓝底蓝边。 */
function Chip({
  selected,
  onClick,
  children,
  fullWidth = false,
}: {
  selected: boolean;
  onClick: () => void;
  children: React.ReactNode;
  fullWidth?: boolean;
}) {
  return (
    <button
      type="button"
      onClick={onClick}
      className={cn(
        "rounded-full border-2 px-4 py-2 text-base font-medium transition",
        fullWidth && "w-full",
        selected
          ? "border-blue-600 bg-blue-50 text-blue-600"
          : "border-gray-200 bg-white text-gray-700",
      )}
    >
      {children}
    </button>
  );
}

/** 料理偏好设置页：勾选手段/时间，可保存/调出/编辑方案，进入结果页。 */
export default function PreferencesPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();

  const techniques = useElementStore((s) => s.techniques);
  const timeTiers = useElementStore((s) => s.timeTiers);
  const optionsLoading = useElementStore((s) => s.loading);
  const optionsError = useElementStore((s) => s.error);
  const loadOptions = useElementStore((s) => s.load);

  const members = useMemberStore((s) => s.members);
  const membersLoading = useMemberStore((s) => s.loading);
  const membersError = useMemberStore((s) => s.error);
  const loadMembers = useMemberStore((s) => s.load);

  // 进入模式：normal（默认，自动应用默认方案）/ recall（调出）/ edit（编辑）/ create（新建）。
  const createMode = searchParams.get("mode") === "create";
  const editMode = searchParams.get("edit_scheme_id") !== null;
  const recallMode = searchParams.get("scheme_id") !== null;
  const normalMode = !createMode && !editMode && !recallMode;
  // 新建/编辑为方案管理流程，不展示「我的方案」与「查看菜谱」。
  const isSchemeManagement = createMode || editMode;

  // 勾选状态：仅前端内存态，不持久化。
  const [selectedTechniqueIds, setSelectedTechniqueIds] = useState<Set<number>>(
    new Set(),
  );
  const [selectedTimeId, setSelectedTimeId] = useState<number | null>(null);

  // 编辑模式目标方案 id（从 query 进入），非空时保存为更新。
  const [editSchemeId, setEditSchemeId] = useState<number | null>(null);
  const [schemeName, setSchemeName] = useState("");
  const [dialogOpen, setDialogOpen] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);
  const [locating, setLocating] = useState(false);

  // 生成数量：仅参与「查看菜谱」时作为 count 传入，不计入方案缓存。
  const [count, setCount] = useState("1");
  const [countError, setCountError] = useState<string | null>(null);

  // 成员启停：记录「停用」的成员 id，默认全启用、仅前端内存态、不持久化。
  const [disabledMemberIds, setDisabledMemberIds] = useState<Set<number>>(
    new Set(),
  );

  const locatedRef = useRef(false);

  useEffect(() => {
    loadOptions();
  }, [loadOptions]);

  useEffect(() => {
    loadMembers();
  }, [loadMembers]);

  const toggleMember = useCallback((id: number) => {
    setDisabledMemberIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const elementTypeIsTechnique = useCallback(
    (id: number) => {
      return techniques.some((item) => item.id === id);
    },
    [techniques],
  );

  const elementTypeIsTime = useCallback(
    (id: number) => {
      return timeTiers.some((item) => item.id === id);
    },
    [timeTiers],
  );

  const optionsReady = techniques.length > 0 && timeTiers.length > 0;

  // 应用方案的勾选集合：按 id 区分手段/时间类型。
  const applySchemeSelection = useCallback(
    (elementIds: number[]) => {
      setSelectedTechniqueIds(
        new Set(elementIds.filter((id) => elementTypeIsTechnique(id))),
      );
      const timeId = elementIds.find((id) => elementTypeIsTime(id));
      setSelectedTimeId(timeId ?? null);
    },
    [elementTypeIsTechnique, elementTypeIsTime],
  );

  // 调出/编辑：按 query 定位方案并填充勾选（编辑还预填方案名）。
  // 等待要素选项加载完成后再做 id→类型映射，避免误判勾选。
  useEffect(() => {
    if (normalMode || locatedRef.current) return;
    if (!optionsReady) return;

    const editIdParam = searchParams.get("edit_scheme_id");
    const targetId = Number(editIdParam ?? searchParams.get("scheme_id"));
    if (!Number.isInteger(targetId)) return;

    locatedRef.current = true;
    setLocating(true);
    listSchemes()
      .then((envelope) => {
        if (envelope.code !== 200 || !envelope.data) return;
        const scheme = envelope.data.list.find((item) => item.id === targetId);
        // 方案已被删除时回退为空勾选（新建模式）。
        if (!scheme) return;
        applySchemeSelection(scheme.element_ids);
        if (editMode) {
          setEditSchemeId(targetId);
          setSchemeName(scheme.name);
        }
      })
      .finally(() => setLocating(false));
  }, [searchParams, optionsReady, normalMode, editMode, applySchemeSelection]);

  // 首次打开（normal 模式）：查询默认方案并自动应用；新建/编辑/调出模式不做此查询。
  useEffect(() => {
    if (!normalMode || locatedRef.current) return;
    if (!optionsReady) return;

    locatedRef.current = true;
    setLocating(true);
    getDefaultScheme()
      .then((envelope) => {
        if (envelope.code === 200 && envelope.data) {
          applySchemeSelection(envelope.data.element_ids);
        }
      })
      .finally(() => setLocating(false));
  }, [normalMode, optionsReady, applySchemeSelection]);

  const toggleTechnique = useCallback((id: number) => {
    setSelectedTechniqueIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) {
        next.delete(id);
      } else {
        next.add(id);
      }
      return next;
    });
  }, []);

  const selectTime = useCallback((id: number) => {
    setSelectedTimeId((prev) => (prev === id ? null : id));
  }, []);

  // 解析生成数量：仅接受正整数；非法或为空返回 null（生成时校验）。
  const parseCount = useCallback((value: string): number | null => {
    if (!/^\d+$/.test(value)) return null;
    const n = Number(value);
    return n >= 1 ? n : null;
  }, []);

  const decrementCount = useCallback(() => {
    setCountError(null);
    setCount((prev) => {
      const n = Number(prev || 0);
      return String(Math.max(1, n - 1));
    });
  }, []);

  const incrementCount = useCallback(() => {
    setCountError(null);
    setCount((prev) => {
      const n = Number(prev || 0);
      return String(n + 1);
    });
  }, []);

  // 手动输入仅保留数字（正整数）；空值允许暂存，生成时校验。
  const handleCountInput = useCallback((value: string) => {
    setCountError(null);
    setCount(value.replace(/\D/g, ""));
  }, []);

  const selectedIds = useMemo(() => {
    const ids = [...selectedTechniqueIds];
    if (selectedTimeId !== null) ids.push(selectedTimeId);
    return ids;
  }, [selectedTechniqueIds, selectedTimeId]);

  // 启用成员 id：全部成员去掉已停用项。
  const enabledMemberIds = useMemo(
    () => members.filter((m) => !disabledMemberIds.has(m.id)).map((m) => m.id),
    [members, disabledMemberIds],
  );

  // 点「查看菜谱」：以 query 携带当前勾选 element_ids、启用成员 member_ids 与生成数量。
  const handleGenerate = useCallback(() => {
    const countNum = parseCount(count);
    if (countNum === null) {
      setCountError("请输入正整数（至少 1）");
      return;
    }
    const params = new URLSearchParams();
    if (selectedIds.length > 0)
      params.set("element_ids", selectedIds.join(","));
    if (enabledMemberIds.length > 0) {
      params.set("member_ids", enabledMemberIds.join(","));
    }
    params.set("count", String(countNum));
    markNewDecision();
    navigate(`/results?${params.toString()}`);
  }, [navigate, selectedIds, enabledMemberIds, count, parseCount]);

  const openSaveDialog = useCallback(() => {
    setSaveMessage(null);
    setDialogOpen(true);
  }, []);

  const handleSave = useCallback(async () => {
    if (!schemeName.trim()) {
      setSaveMessage("请输入方案名");
      return;
    }
    setSaving(true);
    setSaveMessage(null);
    try {
      if (editSchemeId !== null) {
        const envelope = await updateScheme({
          id: editSchemeId,
          name: schemeName.trim(),
          element_ids: selectedIds,
          is_default: 0,
        });
        if (envelope.code !== 200) {
          setSaveMessage(envelope.message || "保存失败");
          return;
        }
      } else {
        const envelope = await createScheme({
          name: schemeName.trim(),
          element_ids: selectedIds,
        });
        if (envelope.code !== 200) {
          setSaveMessage(envelope.message || "保存失败");
          return;
        }
      }
      setDialogOpen(false);
      if (isSchemeManagement) {
        // replace 方式返回方案页，避免路由返回逻辑错乱。
        navigate("/schemes", { replace: true });
      } else {
        setSaveMessage("方案已保存");
      }
    } catch {
      setSaveMessage("服务暂时不可用，请稍后重试");
    } finally {
      setSaving(false);
    }
  }, [editSchemeId, schemeName, selectedIds, isSchemeManagement, navigate]);

  const formReady = !optionsLoading && !optionsError;

  return (
    <main className="min-h-dvh bg-white">
      <div
        className={cn(
          "flex w-full flex-col gap-4 px-5 pt-4",
          // 为底部悬浮按钮组预留空间，避免表单内容被遮盖。
          isSchemeManagement ? "pb-28" : "pb-40",
        )}
      >
        <h1 className="text-2xl font-bold leading-8 text-gray-800">
          料理偏好设置
        </h1>

        {locating && (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            正在调出方案…
          </div>
        )}

        {optionsLoading && !optionsReady && (
          <div className="flex items-center justify-center gap-3 py-8">
            <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            <p className="text-sm text-gray-500">正在加载选项…</p>
          </div>
        )}

        {optionsError && (
          <div className="flex flex-col items-center gap-3 rounded-xl border-2 border-red-200 bg-red-50 p-4 text-center text-sm text-red-600">
            <span>{optionsError}</span>
            <button
              type="button"
              onClick={loadOptions}
              className="rounded-full bg-red-600 px-4 py-1.5 text-white"
            >
              重试
            </button>
          </div>
        )}

        {formReady && (
          <>
            <section className="flex flex-col gap-3">
              <h2 className="text-base font-medium text-gray-800">料理手段</h2>
              <div className="flex flex-wrap gap-3">
                {techniques.map((item) => (
                  <Chip
                    key={item.id}
                    selected={selectedTechniqueIds.has(item.id)}
                    onClick={() => toggleTechnique(item.id)}
                  >
                    {item.name}
                  </Chip>
                ))}
              </div>
            </section>

            <section className="flex flex-col gap-3">
              <h2 className="text-base font-medium text-gray-800">料理时间</h2>
              <div className="flex flex-col gap-3">
                {timeTiers.map((item) => (
                  <Chip
                    key={item.id}
                    selected={selectedTimeId === item.id}
                    onClick={() => selectTime(item.id)}
                    fullWidth
                  >
                    {timeTierLabel(item.name)}
                  </Chip>
                ))}
              </div>
            </section>

            {!isSchemeManagement && (
              <section className="flex flex-col gap-3">
                <h2 className="text-base font-medium text-gray-800">
                  生成数量
                </h2>
                <div className="flex h-11 items-center rounded-full border-2 border-gray-200 bg-white">
                  <button
                    type="button"
                    onClick={decrementCount}
                    aria-label="减少数量"
                    className="flex h-full w-16 items-center justify-center text-2xl text-gray-500 transition hover:bg-gray-50"
                  >
                    −
                  </button>
                  <input
                    type="text"
                    inputMode="numeric"
                    value={count}
                    onChange={(e) => handleCountInput(e.target.value)}
                    className="h-full min-w-0 flex-1 bg-transparent text-center text-base text-gray-800 outline-none"
                  />
                  <button
                    type="button"
                    onClick={incrementCount}
                    aria-label="增加数量"
                    className="flex h-full w-16 items-center justify-center text-2xl text-gray-500 transition hover:bg-gray-50"
                  >
                    +
                  </button>
                </div>
                {countError && (
                  <p className="text-xs text-red-600">{countError}</p>
                )}
              </section>
            )}

            {!isSchemeManagement && (
              <section className="flex flex-col gap-3">
                <h2 className="text-base font-medium text-gray-800">成员</h2>
                {membersLoading && members.length === 0 && (
                  <div className="flex items-center gap-2 text-sm text-gray-500">
                    <Loader2 className="h-4 w-4 animate-spin" />
                    正在加载成员…
                  </div>
                )}
                {membersError && (
                  <p className="text-sm text-red-600">{membersError}</p>
                )}
                {members.length > 0 && (
                  <div className="flex flex-col gap-3">
                    {members.map((member) => {
                      const enabled = !disabledMemberIds.has(member.id);
                      return (
                        <div
                          key={member.id}
                          className="flex items-center justify-between rounded-xl border border-gray-200 bg-white px-4 py-3"
                        >
                          <span className="text-base text-gray-800">
                            {member.name}
                          </span>
                          <button
                            type="button"
                            role="switch"
                            aria-checked={enabled}
                            aria-label={`启用 ${member.name}`}
                            onClick={() => toggleMember(member.id)}
                            className={cn(
                              "relative h-7 w-12 rounded-full transition",
                              enabled ? "bg-blue-600" : "bg-gray-300",
                            )}
                          >
                            <span
                              className={cn(
                                "absolute top-1 h-5 w-5 rounded-full bg-white transition",
                                enabled ? "left-6" : "left-1",
                              )}
                            />
                          </button>
                        </div>
                      );
                    })}
                  </div>
                )}
                <button
                  type="button"
                  onClick={() => navigate("/members")}
                  className="flex w-full items-center justify-between rounded-xl border border-gray-200 bg-white px-4 py-4"
                >
                  <span className="text-base font-semibold text-gray-800">
                    管理成员
                  </span>
                  <ChevronRight className="h-5 w-5 text-gray-400" />
                </button>
              </section>
            )}

            {!isSchemeManagement && (
              <button
                type="button"
                onClick={() => navigate("/schemes")}
                className="flex w-full items-center justify-between rounded-xl border border-gray-200 bg-white px-4 py-4"
              >
                <span className="text-lg font-semibold text-gray-800">
                  我的方案
                </span>
                <ChevronRight className="h-5 w-5 text-gray-400" />
              </button>
            )}
          </>
        )}

        {saveMessage && (
          <p className="text-center text-sm text-gray-500">{saveMessage}</p>
        )}

        <Dialog
          open={dialogOpen}
          onOpenChange={setDialogOpen}
          title={editSchemeId !== null ? "编辑方案" : "保存方案"}
        >
          <input
            type="text"
            value={schemeName}
            onChange={(e) => setSchemeName(e.target.value)}
            placeholder="请输入方案名"
            className="w-full rounded-xl border-2 border-gray-200 px-4 py-3 text-base text-gray-800 outline-none focus:border-blue-600"
          />
          <div className="mt-4 flex justify-end gap-3">
            <button
              type="button"
              onClick={() => setDialogOpen(false)}
              className="rounded-full border-2 border-gray-200 px-5 py-2 text-sm text-gray-600"
            >
              取消
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="rounded-full bg-blue-600 px-5 py-2 text-sm text-white disabled:opacity-40"
            >
              {saving ? "保存中…" : "保存"}
            </button>
          </div>
        </Dialog>
      </div>

      {formReady && (
        <div className="fixed inset-x-0 bottom-0 z-30 bg-white shadow-[0_-2px_12px_rgba(0,0,0,0.06)]">
          <div className="flex w-full flex-col gap-2 px-5 pb-4 pt-2">
            <ActionButton
              type="button"
              variant="secondary"
              onClick={openSaveDialog}
            >
              保存方案
            </ActionButton>
            {!isSchemeManagement && (
              <ActionButton type="button" onClick={handleGenerate}>
                查看菜谱
              </ActionButton>
            )}
          </div>
        </div>
      )}
    </main>
  );
}

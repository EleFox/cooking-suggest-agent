import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useSearchParams } from "react-router-dom";
import { createRecipe, getRecipeDetails, updateRecipe } from "../api/recipes";
import ChipInput from "../components/ChipInput";
import OptionChip from "../components/OptionChip";
import ActionButton from "../components/ui/ActionButton";
import Dialog from "../components/ui/Dialog";
import {
  recipeFormSchema,
  type RecipeChipValue,
  type RecipeFormValues,
} from "../schemas/recipe";
import { useElementStore } from "../stores/elementStore";
import type { ElementItem } from "../types/element";
import type { RecipeDetail, RecipeOperate, RecipeRef } from "../types/recipe";

/** 空表单初值（时间默认 30 分钟）。 */
const EMPTY_VALUES: RecipeFormValues = {
  name: "",
  ingredients: [],
  techniques: [],
  time: "30",
  difficulty: null,
  detail: "",
};

/** 把菜谱详情转换为表单值（要素按类型拆分）。 */
function detailToForm(detail: RecipeDetail): RecipeFormValues {
  const ingredients = detail.elements
    .filter((item) => item.type === "ingredient")
    .map((item) => ({
      id: item.id,
      name: item.name,
      type: "ingredient" as const,
    }));
  const techniques = detail.elements
    .filter((item) => item.type === "technique")
    .map((item) => ({
      id: item.id,
      name: item.name,
      type: "technique" as const,
    }));
  const timeElement = detail.elements.find((item) => item.type === "time");
  const difficultyElement = detail.elements.find(
    (item) => item.type === "difficulty",
  );

  return {
    name: detail.name,
    ingredients,
    techniques,
    time: timeElement ? timeElement.name : "30",
    difficulty: difficultyElement
      ? {
          id: difficultyElement.id,
          name: difficultyElement.name,
          type: "difficulty" as const,
        }
      : null,
    detail: detail.detail ?? "",
  };
}

/** 对回显快照做差异，生成增量 operate 数组（当前 UI 仅产生 add / remove）。 */
function diffOps(
  original: RecipeChipValue[],
  current: RecipeChipValue[],
): RecipeOperate[] {
  const ops: RecipeOperate[] = [];
  const originalIds = new Set(
    original.filter((c) => c.id !== undefined).map((c) => c.id as number),
  );
  const currentIds = new Set(
    current.filter((c) => c.id !== undefined).map((c) => c.id as number),
  );
  for (const chip of original) {
    if (chip.id !== undefined && !currentIds.has(chip.id)) {
      ops.push({
        id: chip.id,
        name: chip.name,
        type: chip.type,
        operate: "remove",
      });
    }
  }
  for (const chip of current) {
    if (chip.id === undefined || !originalIds.has(chip.id)) {
      ops.push({ name: chip.name, type: chip.type, operate: "add" });
    }
  }
  return ops;
}

/** 单值要素（时间 / 难度）的差异：改名等价 remove + add。 */
function diffSingle(
  original: RecipeChipValue | null,
  current: RecipeChipValue | null,
  type: "time" | "difficulty",
): RecipeOperate[] {
  if (original && current) {
    if (original.name === current.name) return [];
    return [
      { id: original.id, name: original.name, type, operate: "remove" },
      { name: current.name, type, operate: "add" },
    ];
  }
  if (original && !current) {
    return [{ id: original.id, name: original.name, type, operate: "remove" }];
  }
  if (!original && current) {
    return [{ name: current.name, type, operate: "add" }];
  }
  return [];
}

/** 菜谱表单页：新增 / 编辑共用（query ``id`` 区分模式）。 */
export default function RecipeFormPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const idParam = searchParams.get("id");
  const parsedId = idParam !== null ? Number(idParam) : NaN;
  const editId = Number.isInteger(parsedId) && parsedId > 0 ? parsedId : null;

  const techniques = useElementStore((s) => s.techniques);
  const difficulties = useElementStore((s) => s.difficulties);
  const optionsLoading = useElementStore((s) => s.loading);
  const optionsError = useElementStore((s) => s.error);
  const loadOptions = useElementStore((s) => s.load);

  const [editMode] = useState(editId !== null);
  const [loading, setLoading] = useState(editId !== null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  // 编辑目标不存在（并发删除等异常情况）时的提示弹窗。
  const [notFound, setNotFound] = useState(false);
  const [saving, setSaving] = useState(false);
  const originalRef = useRef<RecipeFormValues | null>(null);
  // 编辑回显的原始详情，用于单值要素（时间 / 难度）差异计算。
  const originalDetailRef = useRef<RecipeDetail | null>(null);
  const locatedRef = useRef(false);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<RecipeFormValues>({
    resolver: zodResolver(recipeFormSchema),
    defaultValues: EMPTY_VALUES,
  });

  useEffect(() => {
    loadOptions();
  }, [loadOptions]);

  // 编辑模式：拉取菜谱详情回显；不存在时弹窗提示（视为并发删除等异常）。
  useEffect(() => {
    if (editId === null || locatedRef.current) return;
    locatedRef.current = true;
    setLoading(true);
    getRecipeDetails([editId])
      .then((envelope) => {
        const detail = envelope.data?.[0] ?? null;
        if (envelope.code !== 200 || !detail) {
          setNotFound(true);
          return;
        }
        const values = detailToForm(detail);
        originalRef.current = values;
        originalDetailRef.current = detail;
        reset(values);
      })
      .catch(() => setStatusMessage("服务暂时不可用，请稍后重试"))
      .finally(() => setLoading(false));
  }, [editId, reset]);

  const handleNotFoundBack = () => {
    setNotFound(false);
    if (window.history.length > 1) {
      navigate(-1);
    } else {
      navigate("/recipes", { replace: true });
    }
  };

  const name = watch("name");
  const ingredients = watch("ingredients");
  const selectedTechniques = watch("techniques");
  const time = watch("time");
  const difficulty = watch("difficulty");

  const addIngredient = (value: string) => {
    if (ingredients.some((chip) => chip.name === value)) return;
    setValue(
      "ingredients",
      [...ingredients, { name: value, type: "ingredient" }],
      { shouldDirty: true },
    );
  };

  const removeIngredient = (index: number) => {
    setValue(
      "ingredients",
      ingredients.filter((_, i) => i !== index),
      { shouldDirty: true },
    );
  };

  const toggleTechnique = (item: ElementItem) => {
    if (selectedTechniques.some((chip) => chip.id === item.id)) {
      setValue(
        "techniques",
        selectedTechniques.filter((chip) => chip.id !== item.id),
        { shouldDirty: true },
      );
    } else {
      setValue(
        "techniques",
        [
          ...selectedTechniques,
          { id: item.id, name: item.name, type: "technique" },
        ],
        { shouldDirty: true },
      );
    }
  };

  const selectDifficulty = (item: ElementItem) => {
    if (difficulty && difficulty.id === item.id) {
      setValue("difficulty", null, { shouldDirty: true });
    } else {
      setValue(
        "difficulty",
        { id: item.id, name: item.name, type: "difficulty" },
        { shouldDirty: true },
      );
    }
  };

  const stepTime = (delta: number) => {
    const current = Number(time || 0);
    setValue("time", String(Math.max(1, current + delta)), {
      shouldValidate: true,
      shouldDirty: true,
    });
  };

  const onSubmit = async (values: RecipeFormValues) => {
    setSaving(true);
    setStatusMessage(null);
    try {
      if (editMode && editId !== null && originalRef.current) {
        const original = originalRef.current;
        const detail = originalDetailRef.current;
        const originalTime = detail?.elements.find(
          (item) => item.type === "time",
        );
        const originalDifficulty = detail?.elements.find(
          (item) => item.type === "difficulty",
        );
        const elements: RecipeOperate[] = [
          ...diffOps(original.ingredients, values.ingredients),
          ...diffOps(original.techniques, values.techniques),
          ...diffSingle(
            originalTime
              ? {
                  id: originalTime.id,
                  name: originalTime.name,
                  type: "time",
                }
              : null,
            { name: values.time, type: "time" },
            "time",
          ),
          ...diffSingle(
            originalDifficulty
              ? {
                  id: originalDifficulty.id,
                  name: originalDifficulty.name,
                  type: "difficulty",
                }
              : null,
            values.difficulty,
            "difficulty",
          ),
        ];
        const envelope = await updateRecipe({
          id: editId,
          name: values.name.trim(),
          elements,
          detail: values.detail,
        });
        if (envelope.code !== 200) {
          setStatusMessage(envelope.message || "保存失败");
          return;
        }
      } else {
        const elements: RecipeRef[] = [
          ...values.ingredients.map((chip) => ({
            name: chip.name,
            type: "ingredient" as const,
          })),
          ...values.techniques.map((chip) => ({
            name: chip.name,
            type: "technique" as const,
          })),
          { name: values.time, type: "time" as const },
          ...(values.difficulty
            ? [
                {
                  name: values.difficulty.name,
                  type: "difficulty" as const,
                },
              ]
            : []),
        ];
        const envelope = await createRecipe({
          name: values.name.trim(),
          elements,
          detail: values.detail,
        });
        if (envelope.code !== 200) {
          setStatusMessage(envelope.message || "保存失败");
          return;
        }
      }
      // 用后退语义返回管理页：不在历史栈留下表单，列表重新挂载即刷新，
      // 且从列表再后退可直接回到上一页（而非表单页）。
      if (window.history.length > 1) {
        navigate(-1);
      } else {
        navigate("/recipes", { replace: true });
      }
    } catch {
      setStatusMessage("服务暂时不可用，请稍后重试");
    } finally {
      setSaving(false);
    }
  };

  return (
    <main className="min-h-dvh bg-white">
      <div className="flex w-full flex-col gap-4 px-5 pb-28 pt-4">
        <h1 className="text-2xl font-bold leading-8 text-gray-800">
          {editMode ? "编辑菜谱" : "新增菜谱"}
        </h1>

        {loading && (
          <div className="flex items-center justify-center gap-3 py-6">
            <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            <p className="text-sm text-gray-500">正在加载菜谱…</p>
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

        {!loading && (
          <form
            id="recipe-form"
            onSubmit={handleSubmit(onSubmit)}
            className="flex flex-col gap-5"
            noValidate
          >
            <section className="flex flex-col gap-2">
              <label
                htmlFor="recipe-name"
                className="text-base font-medium text-gray-800"
              >
                名称
              </label>
              <input
                id="recipe-name"
                type="text"
                placeholder="请输入菜谱名称"
                {...register("name")}
                className="h-11 rounded-lg border-2 border-gray-200 px-4 text-base text-gray-800 outline-none focus:border-blue-600"
              />
              {errors.name && (
                <p className="text-sm text-red-600">{errors.name.message}</p>
              )}
            </section>

            <section className="flex flex-col gap-2">
              <h2 className="text-base font-medium text-gray-800">主要食材</h2>
              <ChipInput
                chips={ingredients.map((chip) => chip.name)}
                onAdd={addIngredient}
                onRemove={removeIngredient}
                placeholder="如：牛腩、番茄…"
              />
            </section>

            <section className="flex flex-col gap-3">
              <h2 className="text-base font-medium text-gray-800">料理手段</h2>
              <div className="flex flex-wrap gap-3">
                {techniques.map((item) => (
                  <OptionChip
                    key={item.id}
                    selected={selectedTechniques.some(
                      (chip) => chip.id === item.id,
                    )}
                    onClick={() => toggleTechnique(item)}
                  >
                    {item.name}
                  </OptionChip>
                ))}
              </div>
            </section>

            <section className="flex flex-col gap-3">
              <h2 className="text-base font-medium text-gray-800">预估时间</h2>
              <div className="flex h-11 items-center rounded-full border-2 border-gray-200 bg-white">
                <button
                  type="button"
                  onClick={() => stepTime(-1)}
                  aria-label="减少时间"
                  className="flex h-full w-16 items-center justify-center text-2xl text-gray-500 transition hover:bg-gray-50"
                >
                  −
                </button>
                <div className="flex min-w-0 flex-1 items-center justify-center gap-1">
                  <input
                    type="text"
                    inputMode="numeric"
                    {...register("time")}
                    className="w-14 bg-transparent text-center text-base text-gray-800 outline-none"
                  />
                  <span className="text-base text-gray-500">分钟</span>
                </div>
                <button
                  type="button"
                  onClick={() => stepTime(1)}
                  aria-label="增加时间"
                  className="flex h-full w-16 items-center justify-center text-2xl text-gray-500 transition hover:bg-gray-50"
                >
                  +
                </button>
              </div>
              {errors.time && (
                <p className="text-sm text-red-600">{errors.time.message}</p>
              )}
            </section>

            <section className="flex flex-col gap-3">
              <h2 className="text-base font-medium text-gray-800">难度</h2>
              <div className="flex flex-wrap gap-3">
                {difficulties.map((item) => (
                  <OptionChip
                    key={item.id}
                    selected={difficulty?.id === item.id}
                    onClick={() => selectDifficulty(item)}
                  >
                    {item.name}
                  </OptionChip>
                ))}
              </div>
            </section>

            <section className="flex flex-col gap-2">
              <label
                htmlFor="recipe-detail"
                className="text-base font-medium text-gray-800"
              >
                做法
              </label>
              <textarea
                id="recipe-detail"
                rows={5}
                placeholder="请输入做法步骤…"
                {...register("detail")}
                className="rounded-lg border-2 border-gray-200 px-4 py-3 text-base text-gray-800 outline-none focus:border-blue-600"
              />
            </section>
          </form>
        )}

        {optionsLoading && techniques.length === 0 && (
          <div className="flex items-center gap-2 text-sm text-gray-500">
            <Loader2 className="h-4 w-4 animate-spin" />
            正在加载选项…
          </div>
        )}

        {statusMessage && (
          <p className="text-center text-sm text-gray-500">{statusMessage}</p>
        )}
      </div>

      {!loading && (
        <div className="fixed inset-x-0 bottom-0 z-30 bg-white shadow-[0_-2px_12px_rgba(0,0,0,0.06)]">
          <div className="flex w-full flex-col gap-3 px-5 pb-4 pt-2">
            <ActionButton
              type="submit"
              form="recipe-form"
              disabled={saving || !name.trim()}
            >
              {saving ? "保存中…" : "保存"}
            </ActionButton>
          </div>
        </div>
      )}

      <Dialog
        open={notFound}
        onOpenChange={(open) => {
          if (!open) handleNotFoundBack();
        }}
        title="菜谱不存在"
      >
        <p className="text-sm text-gray-600">
          该菜谱可能已被删除，请返回列表重试。
        </p>
        <div className="mt-5 flex justify-end">
          <button
            type="button"
            onClick={handleNotFoundBack}
            className="rounded-full bg-blue-600 px-5 py-2 text-sm text-white transition hover:bg-blue-700"
          >
            返回
          </button>
        </div>
      </Dialog>
    </main>
  );
}

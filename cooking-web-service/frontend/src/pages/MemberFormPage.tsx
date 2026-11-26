import { zodResolver } from "@hookform/resolvers/zod";
import { Loader2 } from "lucide-react";
import { useEffect, useRef, useState } from "react";
import { useForm } from "react-hook-form";
import { useNavigate, useSearchParams } from "react-router-dom";
import { createMember, listMembers, updateMember } from "../api/members";
import ChipInput from "../components/ChipInput";
import ActionButton from "../components/ui/ActionButton";
import {
  memberFormSchema,
  type MemberChipValue,
  type MemberFormValues,
} from "../schemas/member";
import type { Member, MemberOperate, MemberRef } from "../types/member";

/** 空表单初值。 */
const EMPTY_VALUES: MemberFormValues = {
  name: "",
  prefIngredients: [],
  prefTastes: [],
  taboos: [],
};

/** 把成员对象转换为表单值（偏好按食材 / 口味拆分）。 */
function memberToForm(member: Member): MemberFormValues {
  return {
    name: member.name,
    prefIngredients: member.preferences
      .filter((item) => item.type === "ingredient")
      .map((item) => ({
        id: item.id,
        name: item.name,
        type: "ingredient" as const,
      })),
    prefTastes: member.preferences
      .filter((item) => item.type === "taste")
      .map((item) => ({
        id: item.id,
        name: item.name,
        type: "taste" as const,
      })),
    taboos: member.taboos.map((item) => ({
      id: item.id,
      name: item.name,
      type: "ingredient" as const,
    })),
  };
}

/** 对回显快照做差异，生成增量 operate 数组（当前 UI 仅产生 add / remove）。 */
function diffOps(
  original: MemberChipValue[],
  current: MemberChipValue[],
): MemberOperate[] {
  const ops: MemberOperate[] = [];
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

type ChipField = "prefIngredients" | "prefTastes" | "taboos";

/** 成员表单页：新增 / 编辑共用（query ``id`` 区分模式）。 */
export default function MemberFormPage() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const idParam = searchParams.get("id");
  const parsedId = idParam !== null ? Number(idParam) : NaN;
  const editId = Number.isInteger(parsedId) && parsedId > 0 ? parsedId : null;

  const [editMode, setEditMode] = useState(editId !== null);
  const [loading, setLoading] = useState(editId !== null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);
  // 编辑模式回显快照，用于提交时生成增量操作。
  const originalRef = useRef<MemberFormValues | null>(null);
  const locatedRef = useRef(false);

  const {
    register,
    handleSubmit,
    setValue,
    watch,
    reset,
    formState: { errors },
  } = useForm<MemberFormValues>({
    resolver: zodResolver(memberFormSchema),
    defaultValues: EMPTY_VALUES,
  });

  // 编辑模式：拉取成员列表定位目标；不存在则回退新建模式。
  useEffect(() => {
    if (editId === null || locatedRef.current) return;
    locatedRef.current = true;
    setLoading(true);
    listMembers()
      .then((envelope) => {
        if (envelope.code !== 200 || !envelope.data) {
          setStatusMessage(envelope.message || "加载成员失败");
          return;
        }
        const member = envelope.data.find((item) => item.id === editId);
        if (!member) {
          setEditMode(false);
          reset(EMPTY_VALUES);
          setStatusMessage("成员不存在，已切换为新增");
          return;
        }
        const values = memberToForm(member);
        originalRef.current = values;
        reset(values);
      })
      .catch(() => setStatusMessage("服务暂时不可用，请稍后重试"))
      .finally(() => setLoading(false));
  }, [editId, reset]);

  const name = watch("name");
  const prefIngredients = watch("prefIngredients");
  const prefTastes = watch("prefTastes");
  const taboos = watch("taboos");

  // 添加 chip：同分区同名去重。
  const addChip = (field: ChipField, chip: MemberChipValue) => {
    const current = watch(field);
    if (current.some((item) => item.name === chip.name)) return;
    setValue(field, [...current, chip], { shouldDirty: true });
  };

  const removeChip = (field: ChipField, index: number) => {
    const current = watch(field);
    setValue(
      field,
      current.filter((_, i) => i !== index),
      { shouldDirty: true },
    );
  };

  const onSubmit = async (values: MemberFormValues) => {
    setSaving(true);
    setStatusMessage(null);
    try {
      if (editMode && editId !== null && originalRef.current) {
        const original = originalRef.current;
        const preferences = [
          ...diffOps(original.prefIngredients, values.prefIngredients),
          ...diffOps(original.prefTastes, values.prefTastes),
        ];
        const updatedTaboos = diffOps(original.taboos, values.taboos);
        const envelope = await updateMember({
          id: editId,
          name: values.name.trim(),
          preferences,
          taboos: updatedTaboos,
        });
        if (envelope.code !== 200) {
          setStatusMessage(envelope.message || "保存失败");
          return;
        }
      } else {
        const preferences: MemberRef[] = [
          ...values.prefIngredients,
          ...values.prefTastes,
        ].map((chip) => ({ name: chip.name, type: chip.type }));
        const createdTaboos: MemberRef[] = values.taboos.map((chip) => ({
          name: chip.name,
          type: chip.type,
        }));
        const envelope = await createMember({
          name: values.name.trim(),
          preferences,
          taboos: createdTaboos,
        });
        if (envelope.code !== 200) {
          setStatusMessage(envelope.message || "保存失败");
          return;
        }
      }
      // 用后退语义返回列表页：不在历史栈留下表单，列表重新挂载即刷新，
      // 且从列表再后退可直接回到设置页（而非表单页）。
      if (window.history.length > 1) {
        navigate(-1);
      } else {
        navigate("/members", { replace: true });
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
          {editMode ? "编辑成员" : "新增成员"}
        </h1>

        {loading && (
          <div className="flex items-center justify-center gap-3 py-6">
            <Loader2 className="h-6 w-6 animate-spin text-blue-600" />
            <p className="text-sm text-gray-500">正在加载成员…</p>
          </div>
        )}

        {!loading && (
          <form
            id="member-form"
            onSubmit={handleSubmit(onSubmit)}
            className="flex flex-col gap-5"
            noValidate
          >
            <section className="flex flex-col gap-2">
              <label
                htmlFor="member-name"
                className="text-base font-medium text-gray-800"
              >
                姓名
              </label>
              <input
                id="member-name"
                type="text"
                placeholder="请输入成员姓名"
                {...register("name")}
                className="h-11 rounded-lg border-2 border-gray-200 px-4 text-base text-gray-800 outline-none focus:border-blue-600"
              />
              {errors.name && (
                <p className="text-sm text-red-600">{errors.name.message}</p>
              )}
            </section>

            <section className="flex flex-col gap-3">
              <h2 className="text-base font-medium text-gray-800">偏好</h2>

              <div className="flex flex-col gap-2">
                <p className="text-sm text-gray-500">食材</p>
                <ChipInput
                  chips={prefIngredients.map((chip) => chip.name)}
                  onAdd={(name) =>
                    addChip("prefIngredients", { name, type: "ingredient" })
                  }
                  onRemove={(index) => removeChip("prefIngredients", index)}
                  placeholder="如：牛肉"
                />
              </div>

              <div className="flex flex-col gap-2">
                <p className="text-sm text-gray-500">口味</p>
                <ChipInput
                  chips={prefTastes.map((chip) => chip.name)}
                  onAdd={(name) =>
                    addChip("prefTastes", { name, type: "taste" })
                  }
                  onRemove={(index) => removeChip("prefTastes", index)}
                  placeholder="如：微辣"
                />
              </div>
            </section>

            <section className="flex flex-col gap-2">
              <h2 className="text-base font-medium text-gray-800">食材禁忌</h2>
              <ChipInput
                chips={taboos.map((chip) => chip.name)}
                onAdd={(name) =>
                  addChip("taboos", { name, type: "ingredient" })
                }
                onRemove={(index) => removeChip("taboos", index)}
                placeholder="如：香菜"
              />
            </section>
          </form>
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
              form="member-form"
              disabled={saving || !name.trim()}
            >
              {saving ? "保存中…" : "保存"}
            </ActionButton>
          </div>
        </div>
      )}
    </main>
  );
}

import { create } from "zustand";
import { fetchElements } from "../api/elements";
import type { ElementType } from "../types/decision";
import type { ElementItem } from "../types/element";

interface ElementStore {
  /** 料理手段选项。 */
  techniques: ElementItem[];
  /** 料理时间档位选项。 */
  timeTiers: ElementItem[];
  /** 烹饪难度选项。 */
  difficulties: ElementItem[];
  loading: boolean;
  error: string | null;
  /** 加载全部要素选项（设置页、方案页与菜谱表单共享，仅加载一次）。 */
  load: () => Promise<void>;
}

/** 要素选项共享缓存：设置页 / 方案页 / 菜谱表单共用的 id ↔ name 映射来源。 */
export const useElementStore = create<ElementStore>((set, get) => ({
  techniques: [],
  timeTiers: [],
  difficulties: [],
  loading: false,
  error: null,
  load: async () => {
    if (get().loading) return;
    set({ loading: true, error: null });
    try {
      const [techEnvelope, timeEnvelope, difficultyEnvelope] =
        await Promise.all([
          fetchElements("technique"),
          fetchElements("time"),
          fetchElements("difficulty"),
        ]);
      set({
        techniques:
          techEnvelope.code === 200 && techEnvelope.data
            ? techEnvelope.data
            : [],
        timeTiers:
          timeEnvelope.code === 200 && timeEnvelope.data
            ? timeEnvelope.data
            : [],
        difficulties:
          difficultyEnvelope.code === 200 && difficultyEnvelope.data
            ? difficultyEnvelope.data
            : [],
        loading: false,
      });
    } catch {
      set({ loading: false, error: "要素选项加载失败" });
    }
  },
}));

/** 按要素 id 反查要素类型，查不到返回 null。 */
export function elementTypeById(id: number): ElementType | null {
  const { techniques, timeTiers, difficulties } = useElementStore.getState();
  if (techniques.some((item) => item.id === id)) return "technique";
  if (timeTiers.some((item) => item.id === id)) return "time";
  if (difficulties.some((item) => item.id === id)) return "difficulty";
  return null;
}

/** 按要素 id 反查要素名，查不到返回 null。 */
export function elementNameById(id: number): string | null {
  const { techniques, timeTiers, difficulties } = useElementStore.getState();
  const item =
    techniques.find((candidate) => candidate.id === id) ??
    timeTiers.find((candidate) => candidate.id === id) ??
    difficulties.find((candidate) => candidate.id === id);
  return item ? item.name : null;
}

/** 时间档位的展示文案（如 "30" → "30分钟以内"）。 */
export function timeTierLabel(name: string): string {
  return `${name}分钟以内`;
}

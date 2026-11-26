import { z } from "zod";

/** 菜谱表单 chip 项：已存在项带 element id（用于编辑时生成差异）。 */
export const recipeChipSchema = z.object({
  id: z.number().optional(),
  name: z.string(),
  type: z.enum(["ingredient", "technique", "time", "difficulty"]),
});

/** 菜谱表单校验：名称必填；时间须为正整数分钟；食材 / 手段 / 难度可空。 */
export const recipeFormSchema = z.object({
  name: z.string().trim().min(1, "请输入菜谱名称"),
  ingredients: z.array(recipeChipSchema),
  techniques: z.array(recipeChipSchema),
  time: z
    .string()
    .trim()
    .regex(/^\d+$/, "请输入分钟数")
    .refine((value) => Number(value) >= 1, "时间至少 1 分钟"),
  difficulty: recipeChipSchema.nullable(),
  detail: z.string(),
});

export type RecipeChipValue = z.infer<typeof recipeChipSchema>;
export type RecipeFormValues = z.infer<typeof recipeFormSchema>;

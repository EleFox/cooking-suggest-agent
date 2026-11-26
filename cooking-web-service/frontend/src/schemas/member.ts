import { z } from "zod";

/** 成员表单 chip 项：已存在项带 element id（用于编辑时生成差异）。 */
export const memberChipSchema = z.object({
  id: z.number().optional(),
  name: z.string(),
  type: z.enum(["ingredient", "taste"]),
});

/** 成员表单校验：姓名必填；偏好（食材 / 口味）与食材禁忌均可空。 */
export const memberFormSchema = z.object({
  name: z.string().trim().min(1, "请输入成员姓名"),
  prefIngredients: z.array(memberChipSchema),
  prefTastes: z.array(memberChipSchema),
  taboos: z.array(memberChipSchema),
});

export type MemberChipValue = z.infer<typeof memberChipSchema>;
export type MemberFormValues = z.infer<typeof memberFormSchema>;

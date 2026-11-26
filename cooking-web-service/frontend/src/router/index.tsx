import { createBrowserRouter } from "react-router-dom";
import MemberFormPage from "../pages/MemberFormPage";
import MembersPage from "../pages/MembersPage";
import PreferencesPage from "../pages/PreferencesPage";
import RecipeDetailPage from "../pages/RecipeDetailPage";
import RecipeFormPage from "../pages/RecipeFormPage";
import RecipesPage from "../pages/RecipesPage";
import ResultsPage from "../pages/ResultsPage";
import SchemesPage from "../pages/SchemesPage";

/**
 * 应用路由配置：/ 与 /preferences 均进入料理偏好设置页（先进设置再进结果），
 * /schemes 为方案管理页，/results 为菜谱结果页，/members 为成员管理页，
 * /members/form 为成员表单页，/recipes 为菜谱管理页，/recipes/form 为菜谱表单页
 * （表单页均以 query id 区分新建 / 编辑），/recipes/detail 为菜谱详情页
 * （query id 指定菜谱）。
 */
export const router = createBrowserRouter([
  {
    path: "/",
    element: <PreferencesPage />,
  },
  {
    path: "/preferences",
    element: <PreferencesPage />,
  },
  {
    path: "/schemes",
    element: <SchemesPage />,
  },
  {
    path: "/results",
    element: <ResultsPage />,
  },
  {
    path: "/members",
    element: <MembersPage />,
  },
  {
    path: "/members/form",
    element: <MemberFormPage />,
  },
  {
    path: "/recipes",
    element: <RecipesPage />,
  },
  {
    path: "/recipes/form",
    element: <RecipeFormPage />,
  },
  {
    path: "/recipes/detail",
    element: <RecipeDetailPage />,
  },
]);

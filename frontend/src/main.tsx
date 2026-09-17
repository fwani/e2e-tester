import { StrictMode } from "react";
import { createRoot } from "react-dom/client";

import { AppRoot, createBrowserApp } from "./app/AppRoot";
// 정본(`theme/tokens.css`)은 `tailwind.css` 가 @import 로 끌어온다. 여기서 따로
// 불러오면 같은 시트가 두 번 실리고, 나중에 순서가 어긋났을 때 원인을 찾기 어렵다.
import "./theme/tailwind.css";

const root = document.getElementById("root");
if (root === null) throw new Error("#root 를 찾을 수 없습니다.");

// 라우터는 여기서 한 번만 만든다 — `AppRoot` 머리주석.
const app = createBrowserApp();

createRoot(root).render(
  <StrictMode>
    <AppRoot {...app} />
  </StrictMode>,
);

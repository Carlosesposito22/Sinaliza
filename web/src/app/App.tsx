import { Route, Routes } from "react-router-dom";
import { AboutPage } from "../features/about/AboutPage";
import { LessonPage } from "../features/lesson/LessonPage";
import { TrailPage } from "../features/trail/TrailPage";
import { TranslatorPage } from "../features/translator/TranslatorPage";
import { AvatarProvider } from "./AvatarContext";
import { Layout } from "./Layout";

export function App() {
  return (
    <AvatarProvider>
      <Routes>
        <Route element={<Layout />}>
          <Route path="/" element={<TrailPage />} />
          <Route path="/licao/:id" element={<LessonPage />} />
          <Route path="/tradutor" element={<TranslatorPage />} />
          <Route path="/sobre" element={<AboutPage />} />
          <Route path="*" element={<TrailPage />} />
        </Route>
      </Routes>
    </AvatarProvider>
  );
}

import { Route, Routes } from "react-router-dom";
import { AboutPage } from "../about/AboutPage";
import { LessonPage } from "../lesson/LessonPage";
import { LearnProvider } from "../features/progress/LearnContext";
import { ProfilePage } from "../features/progress/ProfilePage";
import { TrailPage } from "../features/trail/TrailPage";
import { TranslatorPage } from "../translator/Translatorpage";
import { AvatarProvider } from "./AvatarContext";
import { Layout } from "./Layout";

export function App() {
  return (
    <AvatarProvider>
      <LearnProvider>
        <Routes>
          <Route element={<Layout />}>
            <Route path="/" element={<TrailPage />} />
            <Route path="/licao/:id" element={<LessonPage />} />
            <Route path="/perfil" element={<ProfilePage />} />
            <Route path="/tradutor" element={<TranslatorPage />} />
            <Route path="/sobre" element={<AboutPage />} />
            <Route path="*" element={<TrailPage />} />
          </Route>
        </Routes>
      </LearnProvider>
    </AvatarProvider>
  );
}

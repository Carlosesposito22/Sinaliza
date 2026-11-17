import { Route, Routes } from "react-router-dom";
import { AboutPage } from "../about/AboutPage";
import { LessonPage } from "../lesson/LessonPage";
import { ExamPage } from "../features/exam/ExamPage";
import { AchievementsPage } from "../features/achievements/AchievementsPage";
import { DictionaryPage } from "../features/dictionary/DictionaryPage";
import { HomePage } from "../features/home/HomePage";
import { PracticePage } from "../features/practice/PracticePage";
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
            <Route path="/" element={<HomePage />} />
            <Route path="/trilha" element={<TrailPage />} />
            <Route path="/licao/:id" element={<LessonPage />} />
            <Route path="/prova/:themeId" element={<ExamPage />} />
            <Route path="/revisao" element={<PracticePage key="review" kind="review" />} />
            <Route path="/desafio" element={<PracticePage key="challenge" kind="challenge" />} />
            <Route path="/dicionario" element={<DictionaryPage />} />
            <Route path="/conquistas" element={<AchievementsPage />} />
            <Route path="/perfil" element={<ProfilePage />} />
            <Route path="/tradutor" element={<TranslatorPage />} />
            <Route path="/sobre" element={<AboutPage />} />
            <Route path="*" element={<HomePage />} />
          </Route>
        </Routes>
      </LearnProvider>
    </AvatarProvider>
  );
}

import { createContext, useCallback, useContext, useEffect, useState, type ReactNode } from "react";
import { toVlibrasGloss, vlibrasPlayer } from "../vlibras";

interface AvatarValue {
  glosses: string[];
  setGlosses: (glosses: string[]) => void;
}

const AvatarContext = createContext<AvatarValue>({ glosses: [], setGlosses: () => {} });

export function AvatarProvider({ children }: { children: ReactNode }) {
  const [glosses, setGlosses] = useState<string[]>([]);
  return <AvatarContext.Provider value={{ glosses, setGlosses }}>{children}</AvatarContext.Provider>;
}

export const useAvatar = () => useContext(AvatarContext);

// Telas usam isto para mandar sinais ao único avatar, que fica montado no Layout.
export function useAvatarGlosses(glosses: string[]) {
  const { setGlosses } = useAvatar();
  const key = glosses.join("|");
  useEffect(() => {
    setGlosses(glosses);
    return () => setGlosses([]);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key]);
}

// Toca uma sequência no avatar a pedido (botão "ver o sinal"). Se já é a sequência atual, toca de novo;
// se é outra, ela vira a atual (e o "Repetir" do avatar passa a repeti-la).
export function usePlayGlosses(): (glosses: string[]) => void {
  const { glosses, setGlosses } = useAvatar();
  return useCallback(
    (next: string[]) => {
      if (next.join("|") === glosses.join("|")) vlibrasPlayer().play(toVlibrasGloss(next));
      else setGlosses(next);
    },
    [glosses, setGlosses],
  );
}

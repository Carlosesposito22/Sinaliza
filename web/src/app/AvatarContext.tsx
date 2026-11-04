import { createContext, useContext, useEffect, useState, type ReactNode } from "react";

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

import type { ComponentType } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import { BookOpenText, House, Route, Trophy, User, type LucideProps } from "lucide-react";
import { VLibrasAvatar } from "../VLibrasAvatar";
import { AchievementToast } from "../features/achievements/AchievementToast";
import { Logo } from "../ui/Logo";
import { ThemeToggle } from "../ui/ThemeToggle";
import { useAvatar } from "./AvatarContext";
import "./app.css";

// Menu principal: no celular, barra de baixo com ícones; no computador, barra de cima com a logo.
// "Texto em sinais" (tradutor) e "Sobre" ficam na página inicial e no Perfil.
const TABS: { to: string; label: string; end: boolean; icon: ComponentType<LucideProps> }[] = [
  { to: "/", label: "Início", end: true, icon: House },
  { to: "/trilha", label: "Trilha", end: false, icon: Route },
  { to: "/dicionario", label: "Dicionário", end: false, icon: BookOpenText },
  { to: "/conquistas", label: "Conquistas", end: false, icon: Trophy },
  { to: "/perfil", label: "Perfil", end: false, icon: User },
];

// Telas de foco (aula, prova, revisão, desafio): avatar em cima, sem menu, "Sair" no topo.
const FOCUS = ["/licao", "/prova", "/revisao", "/desafio"];

// O player do VLibras é um singleton pesado: fica montado aqui para sempre e só muda de lugar na tela.
export function Layout() {
  const { glosses } = useAvatar();
  const { pathname } = useLocation();
  const focus = FOCUS.some((p) => pathname.startsWith(p));
  const dictionary = pathname.startsWith("/dicionario");
  const home = pathname === "/";
  const showAvatar = focus || dictionary || pathname.startsWith("/tradutor");
  const className = [
    "shell",
    focus || dictionary ? "avatar-first" : "",
    focus ? "focus-mode" : "",
    dictionary ? "dictionary-mode" : "",
    home ? "home-mode" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={className}>
      <AchievementToast />
      {!focus && (
        <header className="topbar">
          <Link to="/" className="topbar-brand" aria-label="Sinaliza: página inicial">
            <Logo size="sm" />
          </Link>
          <nav className="topbar-nav" aria-label="Navegação principal">
            {TABS.map(({ to, label, end, icon: Icon }) => (
              <NavLink key={to} to={to} end={end} className="topbar-link">
                <Icon aria-hidden="true" />
                {label}
              </NavLink>
            ))}
            <ThemeToggle />
          </nav>
        </header>
      )}
      <div className="shell-content">
        <Outlet />
      </div>
      <div className={showAvatar ? "avatar-dock" : "avatar-dock avatar-dock-hidden"} aria-hidden={!showAvatar}>
        <VLibrasAvatar glosses={glosses} />
      </div>
      {!focus && (
        <nav className="bottom-nav" aria-label="Navegação principal">
          {TABS.map(({ to, label, end, icon: Icon }) => (
            <NavLink key={to} to={to} end={end} className="tab">
              <Icon aria-hidden="true" />
              <span>{label}</span>
            </NavLink>
          ))}
        </nav>
      )}
    </div>
  );
}

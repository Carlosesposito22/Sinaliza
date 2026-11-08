import { NavLink, Outlet, useLocation } from "react-router-dom";
import { VLibrasAvatar } from "../VLibrasAvatar";
import { useAvatar } from "./AvatarContext";
import "./app.css";

const TABS = [
  { to: "/", label: "Trilha", end: true },
  { to: "/tradutor", label: "Tradutor", end: false },
  { to: "/sobre", label: "Sobre", end: false },
];

// O player do VLibras é um singleton pesado: fica montado aqui para sempre e só muda de lugar na tela.
export function Layout() {
  const { glosses } = useAvatar();
  const { pathname } = useLocation();
  const showAvatar = pathname.startsWith("/licao") || pathname.startsWith("/tradutor");
  return (
    <div className="shell">
      <div className="shell-content">
        <Outlet />
      </div>
      <div className={showAvatar ? "avatar-dock" : "avatar-dock avatar-dock-hidden"} aria-hidden={!showAvatar}>
        <VLibrasAvatar glosses={glosses} />
      </div>
      <nav className="bottom-nav" aria-label="Navegação principal">
        {TABS.map((t) => (
          <NavLink key={t.to} to={t.to} end={t.end} className="tab">
            {t.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}

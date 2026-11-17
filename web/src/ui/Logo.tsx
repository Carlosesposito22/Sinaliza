// A marca do Sinaliza: o símbolo (mão com moldura, recortado da logo oficial em public/logos/logo.png) e o nome
// escrito em texto, para ficar legível no tema claro e no escuro. Só front; não é ML.

interface LogoProps {
  size?: "sm" | "md" | "hero";
  tagline?: boolean;
}

export function Logo({ size = "md", tagline = false }: LogoProps) {
  return (
    <span className={`logo logo-${size}`}>
      <img className="logo-mark" src="/logos/logo-mark.png" alt="" aria-hidden="true" />
      <span className="logo-text">
        <span className="logo-name">Sinaliza</span>
        {tagline && <span className="logo-tagline">Aprendizado ativo em Libras</span>}
      </span>
    </span>
  );
}

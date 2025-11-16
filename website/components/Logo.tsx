/**
 * Stratcon Logo Component
 */

import Image from "next/image";

interface LogoProps {
  variant?: "white" | "black" | "fullColor" | "brandmark";
  width?: number;
  height?: number;
  className?: string;
}

export default function Logo({
  variant = "fullColor",
  width = 200,
  height = 60,
  className = "",
}: LogoProps) {
  const logoMap = {
    white: "/logos/Stratcon.ph White.png",
    black: "/logos/Stratcon.ph Black.png",
    fullColor: "/logos/Stratcon.ph Full Color3.png",
    brandmark: "/logos/Stratcon Brandmark.png",
  };

  return (
    <Image
      src={logoMap[variant]}
      alt="Stratcon Logo"
      width={width}
      height={height}
      className={className}
      style={{ width: "auto", height: "auto" }}
      priority
    />
  );
}

import AppShell from "@/components/AppShell";
import { ColorConfig, FontConfig } from "@/lib/config";
import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import OidcProvider from "./providers/OidcProvider";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Stratcon - Electricity Report Generator",
  description: "Generate electricity consumption reports",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body
        className={`${geistSans.variable} ${geistMono.variable} antialiased`}
        style={
          {
            // Set CSS variables from config.ts (single source of truth)
            // Fonts
            "--font-heading": FontConfig.HEADING_FONT_FAMILY,
            "--font-body": FontConfig.BODY_FONT_FAMILY,

            // Background and foreground
            "--background": ColorConfig.BACKGROUND,
            "--foreground": ColorConfig.TEXT_DARK,

            // Primary Green (Client) - two shades
            "--stratcon-dark-green": ColorConfig.STRATCON_DARK_GREEN,
            "--stratcon-primary-green": ColorConfig.STRATCON_PRIMARY_GREEN,

            // Additional green shades
            "--stratcon-medium-green": ColorConfig.STRATCON_MEDIUM_GREEN,
            "--stratcon-light-green": ColorConfig.STRATCON_LIGHT_GREEN,

            // UI Background Colors
            "--explorer-background": ColorConfig.EXPLORER_BACKGROUND,
            "--top-bar": ColorConfig.TOP_BAR,
            "--card-background": ColorConfig.CARD_BACKGROUND,
            "--card-border": ColorConfig.CARD_BORDER,
            "--field-background": ColorConfig.FIELD_BACKGROUND,
            "--highlight": ColorConfig.HIGHLIGHT,

            // Text Colors
            "--text-dark": ColorConfig.TEXT_DARK,
            "--text-medium": ColorConfig.TEXT_MEDIUM,

            // Button Colors
            "--primary-button": ColorConfig.PRIMARY_BUTTON,
            "--secondary-button": ColorConfig.SECONDARY_BUTTON,

            // Legacy colors (kept for backward compatibility)
            "--stratcon-yellow": ColorConfig.STRATCON_YELLOW,
            "--stratcon-black": ColorConfig.STRATCON_BLACK,
            "--stratcon-dark-grey": ColorConfig.STRATCON_DARK_GREY,
            "--stratcon-medium-grey": ColorConfig.STRATCON_MEDIUM_GREY,
            "--stratcon-grey": ColorConfig.STRATCON_GREY,
            "--stratcon-light-grey": ColorConfig.STRATCON_LIGHT_GREY,
            "--stratcon-very-light-grey": ColorConfig.STRATCON_VERY_LIGHT_GREY,
          } as React.CSSProperties
        }
      >
        <OidcProvider>
          <AppShell>{children}</AppShell>
        </OidcProvider>
      </body>
    </html>
  );
}

"use client";

import { SelectionProvider } from "@/app/providers/SelectionProvider";
import { usePathname } from "next/navigation";
import AuthButtons from "./AuthButtons";
import Explorer from "./Explorer";

export default function AppShell({ children }: { children: React.ReactNode }) {
  const pathname = usePathname();
  const isLoginPage = pathname === "/login";

  // For login page, render children without header/sidebar
  if (isLoginPage) {
    return <>{children}</>;
  }

  // For other pages, render with header and sidebar
  return (
    <div className="min-h-screen flex flex-col">
      {/* Top menu bar */}
      <header
        className="w-full py-3 px-4 flex items-center justify-between"
        style={{
          backgroundColor: "var(--top-bar)",
          borderBottom: "1px solid #D4D4D4",
          color: "var(--text-dark)",
        }}
      >
        <div className="flex items-center gap-6">
          <span className="text-sm text-gray-700 font-semibold">Stratcon</span>
          <nav className="flex items-center gap-4">
            <a
              href="/reports"
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              Reports
            </a>
            <a
              href="/meters"
              className="text-sm text-gray-600 hover:text-gray-900"
            >
              Meters
            </a>
          </nav>
        </div>
        <div className="flex items-center gap-3">
          {/* Settings placeholder */}
          <button
            className="text-sm text-gray-600 hover:text-gray-900"
            aria-label="Settings"
          >
            Settings
          </button>
          <AuthButtons />
        </div>
      </header>

      {/* App shell: sidebar + content */}
      <SelectionProvider>
        <div className="flex flex-1 min-h-0">
          {/* Explorer sidebar */}
          <aside
            className="shrink-0 border-r hidden md:flex md:flex-col"
            style={{
              width: 256,
              backgroundColor: "var(--explorer-background)",
              borderColor: "var(--card-border)",
              height: "100%",
              minHeight: "calc(100vh - 3.5rem)", // Full viewport minus header height
            }}
          >
            <div className="p-4 text-white text-sm font-semibold tracking-wide shrink-0">
              Explorer
            </div>
            <div className="flex-1 overflow-auto">
              <Explorer />
            </div>
          </aside>

          {/* Main content area */}
          <main className="flex-1 overflow-auto">{children}</main>
        </div>
      </SelectionProvider>
    </div>
  );
}

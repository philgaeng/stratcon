"use client";

import { usePathname, useRouter } from "next/navigation";
import { useEffect } from "react";
import { useAuth } from "react-oidc-context";
import { useUserInfo } from "./useUserInfo";

// Role definitions matching backend
export enum UserRole {
  SUPER_ADMIN = "super_admin",
  CLIENT_ADMIN = "client_admin",
  CLIENT_MANAGER = "client_manager",
  VIEWER = "viewer",
  TENANT_USER = "tenant_user",
  ENCODER = "encoder",
  TENANT_APPROVER = "tenant_approver",
}

// App-level permissions
const APP_PERMISSIONS = {
  reports: [
    UserRole.SUPER_ADMIN,
    UserRole.CLIENT_ADMIN,
    UserRole.CLIENT_MANAGER,
    UserRole.VIEWER,
  ],
  meters: [UserRole.SUPER_ADMIN, UserRole.CLIENT_ADMIN, UserRole.ENCODER],
};

/**
 * Hook to protect routes based on user role.
 *
 * Usage:
 * ```tsx
 * export default function MetersPage() {
 *   useRouteGuard("meters");
 *   // ... rest of component
 * }
 * ```
 *
 * @param appName - "reports" or "meters"
 * @param redirectTo - Where to redirect if access denied (default: "/login")
 */
export function useRouteGuard(
  appName: "reports" | "meters",
  redirectTo?: string
) {
  const router = useRouter();
  const pathname = usePathname();
  const auth = useAuth();
  const { userInfo, isLoading } = useUserInfo();

  useEffect(() => {
    // Don't redirect while loading user info or auth
    if (isLoading || auth.isLoading) {
      return;
    }

    // If user is not authenticated, redirect to login
    if (!auth.isAuthenticated) {
      const target = redirectTo || "/login";
      console.log("[useRouteGuard] Not authenticated, redirecting to", target);
      router.push(target);
      return;
    }

    // If authenticated but no user info yet, wait a bit more
    // (userInfo might still be loading from API)
    if (!userInfo) {
      console.log(
        "[useRouteGuard] Authenticated but userInfo not loaded yet, waiting..."
      );
      return;
    }

    // Check if user role has access to this app
    const allowedRoles = APP_PERMISSIONS[appName];

    // Convert role (number or string) to UserRole enum
    let userRole: UserRole | undefined;
    if (typeof userInfo.role === "string") {
      userRole = userInfo.role as UserRole;
    } else if (typeof userInfo.role === "number") {
      // Map numeric role to UserRole enum
      const roleMap: Record<number, UserRole> = {
        7: UserRole.SUPER_ADMIN,
        6: UserRole.CLIENT_ADMIN,
        5: UserRole.CLIENT_MANAGER,
        4: UserRole.VIEWER,
        3: UserRole.TENANT_USER,
        2: UserRole.ENCODER,
        1: UserRole.TENANT_APPROVER,
      };
      userRole = roleMap[userInfo.role];
    }

    console.log("[useRouteGuard] Checking access:", {
      appName,
      userRoleRaw: userInfo.role,
      userRoleMapped: userRole,
      allowedRoles: allowedRoles.map((r) => r),
      hasAccess: userRole && allowedRoles.includes(userRole),
      pathname,
    });

    if (!userRole || !allowedRoles.includes(userRole)) {
      // User doesn't have access - redirect to reports (default) or specified redirect
      const target = redirectTo || "/reports";
      console.warn(
        `[useRouteGuard] User with role ${userInfo.role} (${
          userRole || "unknown"
        }) attempted to access ${appName} app - redirecting to ${target}`
      );
      router.push(target);
      return;
    }

    // User has access - no redirect needed
    console.log("[useRouteGuard] Access granted for", appName);
  }, [
    userInfo,
    isLoading,
    appName,
    router,
    redirectTo,
    pathname,
    auth.isAuthenticated,
    auth.isLoading,
  ]);
}

/**
 * Check if user has access to an app without redirecting.
 * Useful for conditional rendering.
 *
 * @param userRole - User role as string (e.g., "super_admin") or number
 * @param appName - "reports" or "meters"
 */
export function hasAppAccess(
  userRole: string | number | null | undefined,
  appName: "reports" | "meters"
): boolean {
  if (!userRole) {
    return false;
  }

  // If it's already a string, use it directly
  let role: UserRole | undefined;
  if (typeof userRole === "string") {
    role = userRole as UserRole;
  } else {
    // Map number to role (matching backend ROLE_HIERARCHY)
    const roleMap: Record<number, UserRole> = {
      7: UserRole.SUPER_ADMIN,
      6: UserRole.CLIENT_ADMIN,
      5: UserRole.CLIENT_MANAGER,
      4: UserRole.VIEWER,
      3: UserRole.TENANT_USER,
      2: UserRole.ENCODER,
      1: UserRole.TENANT_APPROVER,
    };
    role = roleMap[userRole];
  }

  if (!role || !Object.values(UserRole).includes(role)) {
    return false;
  }

  const allowedRoles = APP_PERMISSIONS[appName];
  return allowedRoles.includes(role);
}

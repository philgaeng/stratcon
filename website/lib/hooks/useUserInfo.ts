"use client";

import api from "@/lib/api-client";
import { useCallback, useEffect, useState } from "react";
import { useAuthCompat } from "./useAuthCompat";

export interface UserInfo {
  user_id: number;
  role: number | string; // Role as number (hierarchy value) or string (e.g., "super_admin", "encoder")
  entity_id: number | null;
  email: string;
  company: string | null;
}

/**
 * Custom hook to fetch and manage user information from the database.
 *
 * This hook:
 * 1. Fetches user info (user_id, role, entity_id) from the backend after login
 * 2. Stores it in localStorage for persistence
 * 3. Provides the user info to components
 *
 * Usage:
 * ```tsx
 * const { userInfo, isLoading, error } = useUserInfo();
 *
 * if (isLoading) return <div>Loading user info...</div>;
 * if (error) return <div>Error: {error}</div>;
 * if (userInfo) {
 *   console.log(userInfo.role); // User role from database
 * }
 * ```
 */
export function useUserInfo() {
  const auth = useAuthCompat();
  const [userInfo, setUserInfo] = useState<UserInfo | null>(null);
  const [isLoading, setIsLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const fetchUserInfo = useCallback(async () => {
    // Get email from user object (works for both mock and real auth)
    const email = auth.user?.email || auth.user?.profile?.email;
    
    if (!auth.isAuthenticated || !email) {
      setIsLoading(false);
      return;
    }

    // Check localStorage first for quick initial render
    const storedUserInfo = localStorage.getItem("userInfo");
    if (storedUserInfo) {
      try {
        const parsed = JSON.parse(storedUserInfo);
        // Verify it's for the same email and has valid role
        if (parsed.email === email && parsed.role !== undefined) {
          // Use stored data for immediate render, but fetch fresh data below
          setUserInfo(parsed);
        } else {
          // Stale or invalid data, clear it
          localStorage.removeItem("userInfo");
        }
      } catch {
        // Invalid stored data, clear it
        localStorage.removeItem("userInfo");
      }
    }

    // Fetch from backend
    try {
      setIsLoading(true);
      setError(null);
      const info = await api.getUserInfoByEmail(email);
      // API returns role as number (hierarchy value), keep it as-is
      setUserInfo({
        ...info,
        role: info.role, // Keep as number (hierarchy value)
      });
      // Store in localStorage for future use
      localStorage.setItem("userInfo", JSON.stringify(info));
      // Also store userId separately for backward compatibility
      localStorage.setItem("userId", info.user_id.toString());
    } catch (err) {
      const errorMessage =
        err instanceof Error ? err.message : "Failed to fetch user info";
      setError(errorMessage);
      console.error("Failed to fetch user info:", err);
    } finally {
      setIsLoading(false);
    }
  }, [auth.isAuthenticated, auth.user]);

  // Fetch user info when authenticated
  useEffect(() => {
    if (auth.isAuthenticated && !auth.isLoading) {
      void fetchUserInfo();
    } else if (!auth.isAuthenticated) {
      // Clear user info on logout
      setUserInfo(null);
      setIsLoading(false);
      localStorage.removeItem("userInfo");
      localStorage.removeItem("userId");
    }
  }, [auth.isAuthenticated, auth.isLoading, fetchUserInfo]);

  return {
    userInfo,
    isLoading,
    error,
    refetch: fetchUserInfo,
  };
}

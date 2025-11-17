"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

interface MockUser {
  sub: string;
  email: string;
  email_verified: boolean;
  name?: string;
}

interface MockAuthContextType {
  isAuthenticated: boolean;
  isLoading: boolean;
  user: MockUser | null;
  error: Error | null;
  signinRedirect: () => Promise<void>;
  signoutRedirect: () => Promise<void>;
}

const MockAuthContext = createContext<MockAuthContextType | null>(null);

export function useMockAuth() {
  const context = useContext(MockAuthContext);
  if (!context) {
    throw new Error("useMockAuth must be used within MockAuthProvider");
  }
  return context;
}

type MockAuthProviderProps = {
  children: React.ReactNode;
};

export default function MockAuthProvider({ children }: MockAuthProviderProps) {
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [isLoading, setIsLoading] = useState(true);
  const [user, setUser] = useState<MockUser | null>(null);
  const [error, setError] = useState<Error | null>(null);

  useEffect(() => {
    // Check if user is already "authenticated" (stored in sessionStorage)
    const storedAuth = sessionStorage.getItem("mock_auth");
    if (storedAuth === "true") {
      const storedUser = sessionStorage.getItem("mock_user");
      if (storedUser) {
        try {
          setUser(JSON.parse(storedUser));
          setIsAuthenticated(true);
        } catch (e) {
          // Invalid stored user, clear it
          sessionStorage.removeItem("mock_auth");
          sessionStorage.removeItem("mock_user");
        }
      }
    }
    setIsLoading(false);
  }, []);

  const signinRedirect = async () => {
    setIsLoading(true);
    try {
      // Simulate a login - just set authenticated state
      const mockUser: MockUser = {
        sub: "mock-user-123",
        email: "demo@stratcon.ph",
        email_verified: true,
        name: "Demo User",
      };
      setUser(mockUser);
      setIsAuthenticated(true);
      sessionStorage.setItem("mock_auth", "true");
      sessionStorage.setItem("mock_user", JSON.stringify(mockUser));
      setError(null);
    } catch (err) {
      const error = err instanceof Error ? err : new Error("Mock auth failed");
      setError(error);
    } finally {
      setIsLoading(false);
    }
  };

  const signoutRedirect = async () => {
    setIsAuthenticated(false);
    setUser(null);
    sessionStorage.removeItem("mock_auth");
    sessionStorage.removeItem("mock_user");
    setError(null);
  };

  const value: MockAuthContextType = {
    isAuthenticated,
    isLoading,
    user,
    error,
    signinRedirect,
    signoutRedirect,
  };

  return (
    <MockAuthContext.Provider value={value}>{children}</MockAuthContext.Provider>
  );
}


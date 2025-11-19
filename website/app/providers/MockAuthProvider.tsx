"use client";

import React, { createContext, useContext, useEffect, useState } from "react";

interface MockUser {
  sub: string;
  email: string;
  email_verified: boolean;
  name?: string;
  // Optional profile for compatibility with real auth providers
  profile?: {
    email?: string;
    name?: string;
    sub?: string;
  };
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

const DEFAULT_USER_ID = "6";
const DEFAULT_USER: MockUser = {
  sub: "mock-user-123",
  email: "philippe@stratcon.ph",
  email_verified: true,
  name: "Philippe Stratcon",
};

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
          const parsedUser: MockUser = JSON.parse(storedUser);
          const hydratedUser: MockUser = {
            ...parsedUser,
            email: DEFAULT_USER.email,
            name: parsedUser.name ?? DEFAULT_USER.name,
            sub: parsedUser.sub ?? DEFAULT_USER.sub,
            email_verified:
              parsedUser.email_verified ?? DEFAULT_USER.email_verified,
          };
          setUser(hydratedUser);
          setIsAuthenticated(true);
          localStorage.setItem("userId", DEFAULT_USER_ID);
          sessionStorage.setItem("mock_user", JSON.stringify(hydratedUser));
        } catch (e) {
          // Invalid stored user, clear it
          sessionStorage.removeItem("mock_auth");
          sessionStorage.removeItem("mock_user");
          localStorage.removeItem("userId");
        }
      }
    }
    setIsLoading(false);
  }, []);

  const signinRedirect = async () => {
    setIsLoading(true);
    try {
      // Simulate a login - just set authenticated state
      const mockUser: MockUser = { ...DEFAULT_USER };
      setUser(mockUser);
      setIsAuthenticated(true);
      sessionStorage.setItem("mock_auth", "true");
      sessionStorage.setItem("mock_user", JSON.stringify(mockUser));
      localStorage.setItem("userId", DEFAULT_USER_ID);
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
    localStorage.removeItem("userId");
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
    <MockAuthContext.Provider value={value}>
      {children}
    </MockAuthContext.Provider>
  );
}

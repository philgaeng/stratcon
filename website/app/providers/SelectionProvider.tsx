"use client";

import React, {
  createContext,
  useCallback,
  useContext,
  useMemo,
  useState,
} from "react";

type Selection = {
  client?: string;
  building?: string;
  tenant?: string;
  unit?: string;
};

type SelectionContextValue = {
  selection: Selection;
  setClient: (client?: string) => void;
  setBuilding: (building?: string) => void;
  setTenant: (tenant?: string) => void;
  setUnit: (unit?: string) => void;
};

const SelectionContext = createContext<SelectionContextValue | undefined>(
  undefined
);

export function SelectionProvider({ children }: { children: React.ReactNode }) {
  const [selection, setSelection] = useState<Selection>({});

  const setClient = useCallback((client?: string) => {
    setSelection(() => ({
      client,
      building: undefined,
      tenant: undefined,
      unit: undefined,
    }));
  }, []);

  const setBuilding = useCallback((building?: string) => {
    setSelection((prev) => ({
      ...prev,
      building,
      tenant: undefined,
      unit: undefined,
    }));
  }, []);

  const setTenant = useCallback((tenant?: string) => {
    setSelection((prev) => ({ ...prev, tenant, unit: undefined }));
  }, []);

  const setUnit = useCallback((unit?: string) => {
    setSelection((prev) => ({ ...prev, unit }));
  }, []);

  const value = useMemo(
    () => ({ selection, setClient, setBuilding, setTenant, setUnit }),
    [selection, setClient, setBuilding, setTenant, setUnit]
  );

  return (
    <SelectionContext.Provider value={value}>
      {children}
    </SelectionContext.Provider>
  );
}

export function useSelection() {
  const ctx = useContext(SelectionContext);
  if (!ctx)
    throw new Error("useSelection must be used within SelectionProvider");
  return ctx;
}

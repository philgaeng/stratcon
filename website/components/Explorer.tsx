"use client";

import { useSelection } from "@/app/providers/SelectionProvider";
import api from "@/lib/api-client";
import { useEffect, useMemo, useState } from "react";

export default function Explorer() {
  const { selection, setClient, setTenant } = useSelection();
  const [clients, setClients] = useState<string[]>([]);
  const [tenants, setTenants] = useState<string[]>([]);
  const [loadingClients, setLoadingClients] = useState(false);
  const [loadingTenants, setLoadingTenants] = useState(false);
  const [searchQuery, setSearchQuery] = useState("");
  const [expandedSections, setExpandedSections] = useState({
    clients: true,
    tenants: true,
  });

  useEffect(() => {
    const load = async () => {
      setLoadingClients(true);
      try {
        const res = await api.getClients();
        setClients(res.clients || []);
        if (!selection.client && res.clients?.length) setClient(res.clients[0]);
      } catch (error) {
        console.error("Failed to load clients:", error);
        // Set empty array on error to show "No clients" message
        setClients([]);
      } finally {
        setLoadingClients(false);
      }
    };
    load();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    const loadTenants = async () => {
      if (!selection.client) {
        setTenants([]);
        return;
      }
      setLoadingTenants(true);
      try {
        const res = await api.getTenants(selection.client);
        setTenants(res.tenants || []);
      } catch (error) {
        console.error("Failed to load tenants:", error);
        // Set empty array on error to show "No tenants" message
        setTenants([]);
      } finally {
        setLoadingTenants(false);
      }
    };
    loadTenants();
  }, [selection.client]);

  // Filter clients and tenants based on search
  const filteredClients = useMemo(() => {
    if (!searchQuery) return clients;
    const query = searchQuery.toLowerCase();
    return clients.filter((c) => c.toLowerCase().includes(query));
  }, [clients, searchQuery]);

  const filteredTenants = useMemo(() => {
    if (!searchQuery) return tenants;
    const query = searchQuery.toLowerCase();
    return tenants.filter((t) => t.toLowerCase().includes(query));
  }, [tenants, searchQuery]);

  const toggleSection = (section: "clients" | "tenants") => {
    setExpandedSections((prev) => ({ ...prev, [section]: !prev[section] }));
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Search */}
      <div className="px-3 py-2 shrink-0 border-b border-white/10">
        <input
          type="text"
          placeholder="Search..."
          value={searchQuery}
          onChange={(e) => setSearchQuery(e.target.value)}
          className="w-full rounded bg-white/10 text-white placeholder-white/60 px-2 py-1.5 text-xs outline-none focus:bg-white/15 focus:ring-1 focus:ring-white/30"
        />
      </div>

      {/* Scrollable content */}
      <div className="flex-1 overflow-auto text-white/90 text-sm">
        {/* Clients Section */}
        <div>
          <button
            onClick={() => toggleSection("clients")}
            className="w-full px-3 py-2 uppercase text-[10px] tracking-wider text-white/70 hover:bg-white/5 flex items-center justify-between"
          >
            <span>Clients ({filteredClients.length})</span>
            <svg
              className={`w-3 h-3 transition-transform ${
                expandedSections.clients ? "rotate-90" : ""
              }`}
              fill="none"
              stroke="currentColor"
              viewBox="0 0 24 24"
            >
              <path
                strokeLinecap="round"
                strokeLinejoin="round"
                strokeWidth={2}
                d="M9 5l7 7-7 7"
              />
            </svg>
          </button>
          {expandedSections.clients && (
            <ul className="px-2 pb-2 space-y-1">
              {loadingClients ? (
                <li className="opacity-80 px-2 py-1 text-xs">Loading…</li>
              ) : filteredClients.length === 0 ? (
                <li className="opacity-60 px-2 py-1 text-xs">
                  {searchQuery ? "No matches" : "No clients"}
                </li>
              ) : (
                filteredClients.map((c) => (
                  <li key={c}>
                    <button
                      className={`w-full text-left px-2 py-1.5 rounded hover:bg-white/10 transition-colors ${
                        selection.client === c ? "bg-white/15 font-medium" : ""
                      }`}
                      onClick={() => setClient(c)}
                    >
                      {c}
                    </button>
                  </li>
                ))
              )}
            </ul>
          )}
        </div>

        {/* Tenants Section */}
        {selection.client && (
          <div className="border-t border-white/10">
            <button
              onClick={() => toggleSection("tenants")}
              className="w-full px-3 py-2 uppercase text-[10px] tracking-wider text-white/70 hover:bg-white/5 flex items-center justify-between"
            >
              <span>
                Tenants ({filteredTenants.length})
                {selection.client && ` • ${selection.client}`}
              </span>
              <svg
                className={`w-3 h-3 transition-transform ${
                  expandedSections.tenants ? "rotate-90" : ""
                }`}
                fill="none"
                stroke="currentColor"
                viewBox="0 0 24 24"
              >
                <path
                  strokeLinecap="round"
                  strokeLinejoin="round"
                  strokeWidth={2}
                  d="M9 5l7 7-7 7"
                />
              </svg>
            </button>
            {expandedSections.tenants && (
              <ul className="px-2 pb-2 space-y-1">
                {loadingTenants ? (
                  <li className="opacity-80 px-2 py-1 text-xs">Loading…</li>
                ) : filteredTenants.length === 0 ? (
                  <li className="opacity-60 px-2 py-1 text-xs">
                    {searchQuery ? "No matches" : "No tenants"}
                  </li>
                ) : (
                  filteredTenants.map((t) => (
                    <li key={t}>
                      <button
                        className={`w-full text-left px-2 py-1.5 rounded hover:bg-white/10 transition-colors ${
                          selection.tenant === t
                            ? "bg-white/15 font-medium"
                            : ""
                        }`}
                        onClick={() => setTenant(t)}
                      >
                        {t}
                      </button>
                    </li>
                  ))
                )}
              </ul>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

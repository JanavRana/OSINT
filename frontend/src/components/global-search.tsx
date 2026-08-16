/**
 * global-search.tsx
 *
 * Global search component that searches investigations and identifiers.
 * Integrated into the app-shell topbar search input.
 */

import { useState, useEffect, useRef, useCallback } from "react";
import { useNavigate } from "@tanstack/react-router";
import { Search, Loader2, FileSearch, Hash, X } from "lucide-react";
import { Input } from "@/components/ui/input";
import { Command } from "lucide-react";
import { cn } from "@/lib/utils";
import { getDataProvider } from "@/lib/api/data-provider";
import type { Investigation, Identifier } from "@/types/domain";

interface SearchResult {
  type: "investigation" | "identifier";
  id: string;
  title: string;
  subtitle: string;
  metadata: string;
  investigationId?: string;
}

const DEBOUNCE_MS = 300;
const MAX_RESULTS = 10;

export function GlobalSearch() {
  const [query, setQuery] = useState("");
  const [isOpen, setIsOpen] = useState(false);
  const [results, setResults] = useState<SearchResult[]>([]);
  const [isLoading, setIsLoading] = useState(false);
  const [selectedIndex, setSelectedIndex] = useState(0);
  const searchRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceTimerRef = useRef<NodeJS.Timeout | null>(null);
  const navigate = useNavigate();

  // Close on outside click
  useEffect(() => {
    function handleClickOutside(event: MouseEvent) {
      if (searchRef.current && !searchRef.current.contains(event.target as Node)) {
        setIsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Search function
  const performSearch = useCallback(async (searchQuery: string) => {
    if (!searchQuery.trim()) {
      setResults([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    try {
      const provider = getDataProvider();
      
      // Fetch investigations and identifiers
      const [investigations, allIdentifiers] = await Promise.all([
        provider.listInvestigations(),
        // Get all investigations first, then fetch their identifiers
        provider.listInvestigations().then(async (invs) => {
          const identifierArrays = await Promise.all(
            invs.map((inv) => provider.listIdentifiers(inv.id))
          );
          return identifierArrays.flat().map((identifier, idx) => ({
            ...identifier,
            investigationId: invs[Math.floor(idx / (identifierArrays.reduce((sum, arr) => sum + arr.length, 0) / invs.length))]?.id
          }));
        })
      ]);

      const lowerQuery = searchQuery.toLowerCase();
      const searchResults: SearchResult[] = [];

      // Search investigations
      for (const inv of investigations) {
        if (
          inv.name.toLowerCase().includes(lowerQuery) ||
          inv.target.toLowerCase().includes(lowerQuery) ||
          inv.id.toLowerCase().includes(lowerQuery)
        ) {
          searchResults.push({
            type: "investigation",
            id: inv.id,
            title: inv.name,
            subtitle: inv.target,
            metadata: `${inv.status} • ${inv.identifiers} identifiers • ${inv.connectors} connectors`,
            investigationId: inv.id,
          });
        }
      }

      // Search identifiers
      const identifierMap = new Map<string, { identifier: Identifier & { investigationId?: string }, investigation: Investigation }>();
      
      for (const inv of investigations) {
        const identifiers = await provider.listIdentifiers(inv.id);
        for (const identifier of identifiers) {
          if (identifier.value.toLowerCase().includes(lowerQuery)) {
            identifierMap.set(identifier.id, { identifier: { ...identifier, investigationId: inv.id }, investigation: inv });
          }
        }
      }

      for (const { identifier, investigation } of identifierMap.values()) {
        searchResults.push({
          type: "identifier",
          id: identifier.id,
          title: identifier.value,
          subtitle: `${identifier.type} • ${identifier.confidence}% confidence`,
          metadata: `From: ${investigation.name}`,
          investigationId: investigation.id,
        });
      }

      setResults(searchResults.slice(0, MAX_RESULTS));
      setSelectedIndex(0);
    } catch (error) {
      console.error("Search error:", error);
      setResults([]);
    } finally {
      setIsLoading(false);
    }
  }, []);

  // Debounced search
  useEffect(() => {
    if (debounceTimerRef.current) {
      clearTimeout(debounceTimerRef.current);
    }

    if (!query.trim()) {
      setResults([]);
      setIsLoading(false);
      return;
    }

    setIsLoading(true);
    debounceTimerRef.current = setTimeout(() => {
      performSearch(query);
    }, DEBOUNCE_MS);

    return () => {
      if (debounceTimerRef.current) {
        clearTimeout(debounceTimerRef.current);
      }
    };
  }, [query, performSearch]);

  // Keyboard navigation
  const handleKeyDown = (e: React.KeyboardEvent) => {
    if (!isOpen) return;

    switch (e.key) {
      case "ArrowDown":
        e.preventDefault();
        setSelectedIndex((prev) => Math.min(prev + 1, results.length - 1));
        break;
      case "ArrowUp":
        e.preventDefault();
        setSelectedIndex((prev) => Math.max(prev - 1, 0));
        break;
      case "Enter":
        e.preventDefault();
        if (results[selectedIndex]) {
          handleSelectResult(results[selectedIndex]);
        }
        break;
      case "Escape":
        e.preventDefault();
        setIsOpen(false);
        inputRef.current?.blur();
        break;
    }
  };

  // Handle result selection
  const handleSelectResult = (result: SearchResult) => {
    if (result.investigationId) {
      navigate({ to: `/investigations/${result.investigationId}` });
    }
    setIsOpen(false);
    setQuery("");
    setResults([]);
  };

  // Handle input change
  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const value = e.target.value;
    setQuery(value);
    setIsOpen(value.trim().length > 0);
  };

  // Handle input focus
  const handleInputFocus = () => {
    if (query.trim().length > 0) {
      setIsOpen(true);
    }
  };

  // Clear search
  const handleClear = () => {
    setQuery("");
    setResults([]);
    setIsOpen(false);
    inputRef.current?.focus();
  };

  return (
    <div ref={searchRef} className="relative flex-1 max-w-xl">
      {/* Search input bar */}
      <Search className="absolute left-2.5 top-1/2 -translate-y-1/2 h-3.5 w-3.5 text-muted-foreground pointer-events-none" />
      <Input
        ref={inputRef}
        type="text"
        placeholder="Query target, case ID, IP, domain, hash, email..."
        value={query}
        onChange={handleInputChange}
        onFocus={handleInputFocus}
        onKeyDown={handleKeyDown}
        className="pl-8 pr-14 h-8 bg-surface-2 border-border text-xs font-mono focus-visible:ring-primary/40"
      />
      {query && (
        <button
          onClick={handleClear}
          className="absolute right-12 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition"
          aria-label="Clear search"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
      <kbd className="absolute right-2 top-1/2 -translate-y-1/2 h-5 px-1 rounded-sm border border-border bg-surface text-[9px] font-mono text-muted-foreground flex items-center gap-0.5 pointer-events-none">
        <Command className="h-2.5 w-2.5" />K
      </kbd>

      {/* Search results dropdown */}
      {isOpen && (
        <div className="absolute top-full mt-1.5 left-0 right-0 bg-surface border border-border rounded-sm shadow-2xl max-h-96 overflow-y-auto z-50 font-mono text-xs">
          {isLoading && (
            <div className="flex items-center justify-center gap-2 p-3 text-muted-foreground">
              <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
              <span className="text-xs">Searching registry...</span>
            </div>
          )}

          {!isLoading && results.length === 0 && query.trim() && (
            <div className="flex flex-col items-center justify-center gap-1.5 p-6 text-muted-foreground">
              <FileSearch className="h-6 w-6 opacity-40" />
              <p className="text-xs font-bold text-foreground">NO MATCHES FOUND</p>
              <p className="text-[11px] text-muted-foreground">No entity or investigation matches "{query}"</p>
            </div>
          )}

          {!isLoading && results.length > 0 && (
            <div className="py-1">
              <div className="px-3 py-1 text-[9px] uppercase font-bold text-muted-foreground border-b border-border/60 bg-surface-2">
                MATCHES ({results.length})
              </div>
              {results.map((result, index) => (
                <button
                  key={result.id}
                  onClick={() => handleSelectResult(result)}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={cn(
                    "w-full text-left px-3 py-2 flex items-start gap-2.5 transition-colors border-l-2",
                    index === selectedIndex
                      ? "bg-surface-2 border-primary"
                      : "border-transparent hover:bg-surface-2/60"
                  )}
                >
                  <div className={cn(
                    "h-6 w-6 rounded-sm border grid place-items-center shrink-0 mt-0.5",
                    result.type === "investigation"
                      ? "bg-primary/10 border-primary/30 text-primary"
                      : "bg-accent/10 border-accent/30 text-accent"
                  )}>
                    {result.type === "investigation" ? (
                      <FileSearch className="h-3 w-3" />
                    ) : (
                      <Hash className="h-3 w-3" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-xs font-bold text-foreground truncate font-sans">
                      {result.title}
                    </div>
                    <div className="text-[10px] text-muted-foreground truncate font-mono">
                      {result.subtitle}
                    </div>
                    <div className="text-[10px] text-muted-foreground/70 truncate">
                      {result.metadata}
                    </div>
                  </div>
                </button>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}


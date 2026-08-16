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
      <Search className="absolute left-3 top-1/2 -translate-y-1/2 h-4 w-4 text-muted-foreground pointer-events-none" />
      <Input
        ref={inputRef}
        type="text"
        placeholder="Search identifiers, investigations, wallets, domains…"
        value={query}
        onChange={handleInputChange}
        onFocus={handleInputFocus}
        onKeyDown={handleKeyDown}
        className="pl-9 pr-16 h-10 bg-surface/60 border-border/60 focus-visible:ring-primary/40"
      />
      {query && (
        <button
          onClick={handleClear}
          className="absolute right-14 top-1/2 -translate-y-1/2 text-muted-foreground hover:text-foreground transition"
          aria-label="Clear search"
        >
          <X className="h-3.5 w-3.5" />
        </button>
      )}
      <kbd className="absolute right-2 top-1/2 -translate-y-1/2 h-6 px-1.5 rounded-md border border-border/70 bg-surface text-[10px] font-mono text-muted-foreground flex items-center gap-1 pointer-events-none">
        <Command className="h-3 w-3" />K
      </kbd>

      {/* Search results dropdown */}
      {isOpen && (
        <div className="absolute top-full mt-2 left-0 right-0 bg-background/95 backdrop-blur-xl border border-border/60 rounded-lg shadow-xl max-h-96 overflow-y-auto z-50">
          {isLoading && (
            <div className="flex items-center justify-center gap-2 p-4 text-muted-foreground">
              <Loader2 className="h-4 w-4 animate-spin" />
              <span className="text-sm">Searching...</span>
            </div>
          )}

          {!isLoading && results.length === 0 && query.trim() && (
            <div className="flex flex-col items-center justify-center gap-2 p-8 text-muted-foreground">
              <FileSearch className="h-8 w-8 opacity-50" />
              <p className="text-sm">No results found for "{query}"</p>
              <p className="text-xs text-muted-foreground">Try a different search term</p>
            </div>
          )}

          {!isLoading && results.length > 0 && (
            <div className="py-2">
              <div className="px-3 py-1.5 text-xs font-medium text-muted-foreground uppercase tracking-wider">
                {results.length} result{results.length !== 1 ? "s" : ""}
              </div>
              {results.map((result, index) => (
                <button
                  key={result.id}
                  onClick={() => handleSelectResult(result)}
                  onMouseEnter={() => setSelectedIndex(index)}
                  className={cn(
                    "w-full text-left px-3 py-2.5 flex items-start gap-3 transition-colors",
                    index === selectedIndex
                      ? "bg-primary/10 border-l-2 border-primary"
                      : "hover:bg-white/5 border-l-2 border-transparent"
                  )}
                >
                  <div className={cn(
                    "h-8 w-8 rounded-lg grid place-items-center shrink-0 mt-0.5",
                    result.type === "investigation"
                      ? "bg-primary/15 text-primary"
                      : "bg-accent/15 text-accent"
                  )}>
                    {result.type === "investigation" ? (
                      <FileSearch className="h-4 w-4" />
                    ) : (
                      <Hash className="h-4 w-4" />
                    )}
                  </div>
                  <div className="flex-1 min-w-0">
                    <div className="text-sm font-medium text-foreground truncate">
                      {result.title}
                    </div>
                    <div className="text-xs text-muted-foreground truncate mt-0.5">
                      {result.subtitle}
                    </div>
                    <div className="text-xs text-muted-foreground/70 truncate mt-1">
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

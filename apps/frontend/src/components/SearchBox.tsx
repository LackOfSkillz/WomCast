import { useState, useEffect, useCallback } from 'react';
import './SearchBox.css';

export interface SearchBoxProps {
  onSearch: (query: string) => void;
  placeholder?: string;
  debounceMs?: number;
  value?: string;
  onValueChange?: (value: string) => void;
}

export function SearchBox({
  onSearch,
  placeholder = 'Search media...',
  debounceMs = 300,
  value,
  onValueChange,
}: SearchBoxProps) {
  const [internalValue, setInternalValue] = useState(value ?? '');

  useEffect(() => {
    if (value !== undefined) {
      setInternalValue(value);
    }
  }, [value]);

  const effectiveValue = value !== undefined ? value : internalValue;

  const updateValue = useCallback(
    (nextValue: string) => {
      if (value === undefined) {
        setInternalValue(nextValue);
      }
      if (onValueChange) {
        onValueChange(nextValue);
      }
    },
    [value, onValueChange]
  );

  useEffect(() => {
    const timer = setTimeout(() => {
      onSearch(effectiveValue);
    }, debounceMs);

    return () => {
      clearTimeout(timer);
    };
  }, [effectiveValue, debounceMs, onSearch]);

  const handleClear = () => {
    updateValue('');
  };

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Escape') {
      handleClear();
    }
  };

  return (
    <div className="search-box">
      <input
        type="text"
        className="search-box__input"
        value={effectiveValue}
        onChange={(e) => {
          updateValue(e.target.value);
        }}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        aria-label="Search media files"
      />
      {effectiveValue && (
        <button
          className="search-box__clear"
          onClick={handleClear}
          aria-label="Clear search"
          type="button"
        >
          ✕
        </button>
      )}
    </div>
  );
}

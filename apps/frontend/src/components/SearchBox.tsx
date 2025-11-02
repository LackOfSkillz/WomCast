import { useState, useEffect, useCallback } from 'react';
import './SearchBox.css';

export interface SearchBoxProps {
  onSearch: (query: string) => void;
  placeholder?: string;
  debounceMs?: number;
}

export function SearchBox({
  onSearch,
  placeholder = 'Search media...',
  debounceMs = 300,
}: SearchBoxProps) {
  const [value, setValue] = useState('');

  const handleSearch = useCallback(
    (query: string) => {
      onSearch(query);
    },
    [onSearch]
  );

  useEffect(() => {
    const timer = setTimeout(() => {
      handleSearch(value);
    }, debounceMs);

    return () => {
      clearTimeout(timer);
    };
  }, [value, debounceMs, handleSearch]);

  const handleClear = () => {
    setValue('');
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
        value={value}
        onChange={(e) => {
          setValue(e.target.value);
        }}
        onKeyDown={handleKeyDown}
        placeholder={placeholder}
        aria-label="Search media files"
      />
      {value && (
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

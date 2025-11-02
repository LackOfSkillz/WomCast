import { describe, it, expect } from 'vitest';
import { render } from '@testing-library/react';
import { App } from './App';

describe('App', () => {
  it('renders the library view', () => {
    render(<App />);
    // Just check that the component renders without crashing
    // Detailed testing will be in LibraryView.test.tsx
    expect(document.querySelector('.app')).toBeDefined();
  });
});

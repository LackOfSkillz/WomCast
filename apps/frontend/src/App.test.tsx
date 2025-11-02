import { describe, it, expect } from 'vitest';
import { render, screen } from '@testing-library/react';
import { App } from './App';

describe('App', () => {
  it('renders with default title', () => {
    render(<App />);
    expect(screen.getByText('WomCast')).toBeDefined();
  });

  it('renders with custom title', () => {
    render(<App title="Custom Title" />);
    expect(screen.getByText('Custom Title')).toBeDefined();
  });

  it('renders tagline', () => {
    render(<App />);
    expect(screen.getByText('Local-first entertainment OS')).toBeDefined();
  });
});

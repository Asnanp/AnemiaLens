import React from 'react';
import { render, RenderOptions } from '@testing-library/react';
import { BrowserRouter } from 'react-router-dom';
import { vi } from 'vitest';

// Import providers that may be needed globally
// Currently the app uses AuthProvider and others, but for unit tests
// we keep the wrapper minimal and add providers as needed per test

interface AllProvidersProps {
  children: React.ReactNode;
}

function AllProviders({ children }: AllProvidersProps) {
  return (
    <BrowserRouter>
      {children}
    </BrowserRouter>
  );
}

/**
 * Custom render function that wraps children with all necessary providers.
 * Use this instead of the raw `render` from Testing Library.
 */
function customRender(ui: React.ReactElement, options?: Omit<RenderOptions, 'wrapper'>) {
  return render(ui, { wrapper: AllProviders, ...options });
}

// Re-export everything from Testing Library
export * from '@testing-library/react';

// Override render method
export { customRender as render };

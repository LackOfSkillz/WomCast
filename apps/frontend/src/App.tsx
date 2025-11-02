import React from 'react';

export interface AppProps {
  title?: string;
}

export function App({ title = 'WomCast' }: AppProps): React.JSX.Element {
  return (
    <div className="app">
      <h1>{title}</h1>
      <p>Local-first entertainment OS</p>
    </div>
  );
}

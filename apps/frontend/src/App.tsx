import { LibraryView } from './views/Library/LibraryView';
import './App.css';

export interface AppProps {
  title?: string;
}

export function App(): React.JSX.Element {
  return (
    <div className="app">
      <LibraryView />
    </div>
  );
}

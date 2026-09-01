import { createContext, useContext, useState } from 'react';
import type { ReactNode } from 'react';
import { useQueryClient } from '@tanstack/react-query';

interface ProjectContextType {
  activeProjectId: string | null;
  setActiveProjectId: (id: string | null) => void;
}

const ProjectContext = createContext<ProjectContextType | undefined>(undefined);

export const ProjectProvider = ({ children }: { children: ReactNode }) => {
  const [activeProjectId, setActiveProjectId] = useState<string | null>(null);
  const queryClient = useQueryClient();

  const handleSetProjectId = (newId: string | null) => {
    if (activeProjectId && activeProjectId !== newId) {
      // Explicitly purge the old project's cache as per security design
      queryClient.removeQueries({ predicate: (query) => query.queryKey.includes(activeProjectId) });
    }
    setActiveProjectId(newId);
  };

  return (
    <ProjectContext.Provider value={{ activeProjectId, setActiveProjectId: handleSetProjectId }}>
      {children}
    </ProjectContext.Provider>
  );
};

export const useProject = () => {
  const context = useContext(ProjectContext);
  if (context === undefined) {
    throw new Error('useProject must be used within a ProjectProvider');
  }
  return context;
};


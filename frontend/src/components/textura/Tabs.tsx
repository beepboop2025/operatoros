import { ReactNode, useState } from 'react';
import { LucideIcon } from 'lucide-react';

interface TabItem {
  id: string;
  label: string;
  icon?: LucideIcon;
  content: ReactNode;
}

interface TabsProps {
  tabs: TabItem[];
  defaultTab?: string;
  activeTab?: string;
  onChange?: (id: string) => void;
  className?: string;
}

export default function Tabs({ tabs, defaultTab, activeTab: controlledActive, onChange, className = '' }: TabsProps) {
  const [internalActive, setInternalActive] = useState<string>(defaultTab || tabs[0]?.id || '');
  const active = controlledActive ?? internalActive;

  const handleChange = (id: string) => {
    setInternalActive(id);
    onChange?.(id);
  };

  return (
    <div className={className}>
      <div className="flex gap-1 border-b border-textura-line-subtle">
        {tabs.map((tab) => {
          const Icon = tab.icon;
          const isActive = active === tab.id;
          return (
            <button
              key={tab.id}
              onClick={() => handleChange(tab.id)}
              className={`relative flex items-center gap-2 px-4 py-3 text-sm font-medium transition-colors duration-300 ease-textura rounded-t-xl
                ${isActive ? 'text-textura-accent' : 'text-textura-muted hover:text-textura-text'}`}
            >
              {Icon && <Icon className="w-4 h-4" />}
              {tab.label}
              {isActive && (
                <span className="absolute bottom-0 left-2 right-2 h-0.5 bg-gradient-to-r from-textura-warm to-textura-accent rounded-full origin-left animate-[tab-underline_0.35s_var(--ease-textura)_forwards]" />
              )}
            </button>
          );
        })}
      </div>
      <div className="pt-4">
        {tabs.map((tab) => (
          <div
            key={tab.id}
            className={`${active === tab.id ? 'block animate-[tab-fade_0.3s_var(--ease-textura)_forwards]' : 'hidden'}`}
          >
            {tab.content}
          </div>
        ))}
      </div>
    </div>
  );
}

interface TabPanelsProps {
  children: ReactNode;
}

export function TabPanels({ children }: TabPanelsProps) {
  return <div>{children}</div>;
}

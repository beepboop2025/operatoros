import { ReactNode } from 'react';

interface DataTableProps {
  children: ReactNode;
  className?: string;
}

export function DataTable({ children, className = '' }: DataTableProps) {
  return (
    <div className={`overflow-x-auto ${className}`}>
      <table className="w-full">{children}</table>
    </div>
  );
}

interface DataTableHeaderProps {
  children: ReactNode;
}

export function DataTableHeader({ children }: DataTableHeaderProps) {
  return (
    <thead>
      <tr className="border-b border-textura-line-subtle bg-textura-panel-raised/40">
        {children}
      </tr>
    </thead>
  );
}

interface DataTableHeadProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
}

export function DataTableHead({ children, className = '', onClick }: DataTableHeadProps) {
  return (
    <th className={`text-left px-5 py-3 text-xs font-semibold uppercase tracking-wider text-textura-muted ${className}`}>
      {onClick ? (
        <button onClick={onClick} className="flex items-center gap-1 hover:text-textura-text transition-colors">
          {children}
        </button>
      ) : (
        children
      )}
    </th>
  );
}

interface DataTableBodyProps {
  children: ReactNode;
  className?: string;
}

export function DataTableBody({ children, className = '' }: DataTableBodyProps) {
  return <tbody className={`divide-y divide-textura-line-subtle ${className}`}>{children}</tbody>;
}

interface DataTableRowProps {
  children: ReactNode;
  className?: string;
  onClick?: () => void;
}

export function DataTableRow({ children, className = '', onClick }: DataTableRowProps) {
  return (
    <tr
      onClick={onClick}
      className={`transition-colors duration-200 hover:bg-textura-accent/[0.03] ${onClick ? 'cursor-pointer' : ''} ${className}`}
    >
      {children}
    </tr>
  );
}

interface DataTableCellProps {
  children: ReactNode;
  className?: string;
}

export function DataTableCell({ children, className = '' }: DataTableCellProps) {
  return <td className={`px-5 py-3 text-sm ${className}`}>{children}</td>;
}

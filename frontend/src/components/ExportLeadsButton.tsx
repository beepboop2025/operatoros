import { useState } from 'react';
import { Download } from 'lucide-react';
import { waitlistApi } from '../api/client';
import { useAuth } from '../hooks/useAuth';
import { useToast } from './Toast';
import Button from './textura/Button';

/**
 * ExportLeadsButton — admin-only CSV download of the waitlist.
 *
 * Fetches /api/waitlist/export.csv as a Blob (the axios interceptor attaches the JWT,
 * which a plain anchor `href` download could not carry), then triggers a client-side
 * download via a temporary object URL. Renders nothing for non-admins.
 */
export default function ExportLeadsButton() {
  const { user } = useAuth();
  const toast = useToast();
  const [loading, setLoading] = useState(false);

  // Gate on role — the endpoint also enforces this server-side; this just hides the UI.
  if (user?.role !== 'admin') return null;

  const handleExport = async () => {
    setLoading(true);
    try {
      const blob = await waitlistApi.exportCsv();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement('a');
      anchor.href = url;
      anchor.download = `operatoros-waitlist-${new Date().toISOString().slice(0, 10)}.csv`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
      toast.success('Leads exported.');
    } catch {
      toast.error('Could not export leads. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  return (
    <Button
      variant="ghost"
      size="sm"
      onClick={handleExport}
      loading={loading}
      icon={!loading && <Download className="w-4 h-4" />}
      data-cursor-label="Export"
    >
      Export leads
    </Button>
  );
}

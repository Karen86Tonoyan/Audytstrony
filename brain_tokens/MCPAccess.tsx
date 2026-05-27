import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Select, SelectContent, SelectItem, SelectTrigger, SelectValue,
} from '@/components/ui/select';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import {
  Card, CardContent, CardDescription, CardHeader, CardTitle,
} from '@/components/ui/card';
import { toast } from 'sonner';
import {
  Copy, Plus, Trash2, Server, Eye, EyeOff, Loader2, CheckCircle2,
} from 'lucide-react';

const MCP_URL = 'https://ocbwiopyscjdpjewsssx.functions.supabase.co/mcp-server';

interface TokenRow {
  id: string;
  label: string;
  owner_email: string | null;
  scope: string;
  created_at: string;
  expires_at: string | null;
  status: string;
  last_used_at: string | null;
  use_count: number;
}

function copy(text: string, msg = 'Skopiowano') {
  navigator.clipboard.writeText(text).then(() => toast.success(msg));
}

function ScopeBadge({ scope }: { scope: string }) {
  const variant =
    scope === 'admin' ? 'destructive' :
    scope === 'write' ? 'default' : 'secondary';
  return <Badge variant={variant as 'destructive' | 'default' | 'secondary'}>{scope}</Badge>;
}

export default function MCPAccess() {
  const qc = useQueryClient();

  // ── Token list ──────────────────────────────────────────────────────────────
  const { data: tokens = [], isLoading } = useQuery<TokenRow[]>({
    queryKey: ['brain-tokens'],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('brain_tokens_admin')
        .select('*')
        .order('created_at', { ascending: false });
      if (error) throw new Error(error.message);
      return (data ?? []) as TokenRow[];
    },
  });

  // ── Revoke ──────────────────────────────────────────────────────────────────
  const revoke = useMutation({
    mutationFn: async (id: string) => {
      const { error } = await supabase.rpc('revoke_brain_token', { p_token_id: id });
      if (error) throw new Error(error.message);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['brain-tokens'] });
      toast.success('Token unieważniony');
    },
    onError: (e: Error) => toast.error(e.message),
  });

  // ── Create dialog state ─────────────────────────────────────────────────────
  const [open, setOpen] = useState(false);
  const [label, setLabel] = useState('');
  const [scope, setScope] = useState('read');
  const [days, setDays] = useState('');
  const [createdToken, setCreatedToken] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);

  const resetDialog = () => {
    setLabel(''); setScope('read'); setDays('');
    setCreatedToken(null); setVisible(false);
  };

  const create = useMutation({
    mutationFn: async () => {
      const { data, error } = await supabase.rpc('create_brain_token', {
        p_label: label,
        p_owner_email: null,
        p_scope: scope,
        p_expires_days: days ? Number(days) : null,
      });
      if (error) throw new Error(error.message);
      return (data as { token: string; token_id: string }[])[0];
    },
    onSuccess: (res) => {
      setCreatedToken(res.token);
      qc.invalidateQueries({ queryKey: ['brain-tokens'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const claudeConfig = createdToken
    ? JSON.stringify({
        mcpServers: {
          'alfa-knowledge': {
            url: MCP_URL,
            transport: 'http',
            headers: { Authorization: `Bearer ${createdToken}` },
          },
        },
      }, null, 2)
    : '';

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Page header */}
      <div>
        <h1 className="text-2xl font-bold">Dostęp MCP</h1>
        <p className="text-sm text-muted-foreground mt-1">
          Zarządzaj tokenami dostępu do ALFA Brain przez protokół MCP.
          Każdy klient (Claude Desktop, Cursor, Cline) powinien mieć własny token.
        </p>
      </div>

      {/* Endpoint card */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Server className="w-4 h-4 text-primary" />
            Endpoint serwera MCP
          </CardTitle>
          <CardDescription className="text-xs">
            Wklej ten URL w ustawieniach klienta MCP jako adres serwera.
          </CardDescription>
        </CardHeader>
        <CardContent>
          <div className="flex items-center gap-2">
            <code className="flex-1 text-xs bg-muted px-3 py-2 rounded-md font-mono truncate">
              {MCP_URL}
            </code>
            <Button variant="outline" size="icon" onClick={() => copy(MCP_URL, 'URL skopiowany')}>
              <Copy className="w-3.5 h-3.5" />
            </Button>
          </div>
          <p className="text-xs text-muted-foreground mt-2">
            Transport: HTTP · Autoryzacja: <code>Authorization: Bearer &lt;token&gt;</code>
          </p>
        </CardContent>
      </Card>

      {/* Tokens */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-sm">Tokeny dostępu</CardTitle>
            <CardDescription className="text-xs">
              {tokens.filter(t => t.status === 'active').length} aktywnych tokenów
            </CardDescription>
          </div>

          <Dialog open={open} onOpenChange={(v) => { setOpen(v); if (!v) resetDialog(); }}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="w-3.5 h-3.5 mr-1" /> Nowy token
              </Button>
            </DialogTrigger>

            <DialogContent className="sm:max-w-md">
              <DialogHeader>
                <DialogTitle>
                  {createdToken ? 'Token wygenerowany' : 'Nowy token MCP'}
                </DialogTitle>
              </DialogHeader>

              {/* ── After creation: show token ── */}
              {createdToken ? (
                <div className="space-y-4">
                  <div className="flex items-center gap-2 p-3 rounded-lg bg-amber-50 dark:bg-amber-950/30 border border-amber-200 dark:border-amber-800">
                    <CheckCircle2 className="w-4 h-4 text-amber-600 shrink-0" />
                    <p className="text-xs text-amber-700 dark:text-amber-400 font-medium">
                      Zapisz token teraz — nie zobaczysz go ponownie.
                    </p>
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs">Token</Label>
                    <div className="flex items-center gap-2">
                      <code className="flex-1 text-xs bg-muted px-3 py-2 rounded-md font-mono break-all">
                        {visible ? createdToken : '•'.repeat(48)}
                      </code>
                      <Button variant="outline" size="icon" onClick={() => setVisible(v => !v)}>
                        {visible ? <EyeOff className="w-3.5 h-3.5" /> : <Eye className="w-3.5 h-3.5" />}
                      </Button>
                      <Button variant="outline" size="icon"
                        onClick={() => copy(createdToken, 'Token skopiowany!')}>
                        <Copy className="w-3.5 h-3.5" />
                      </Button>
                    </div>
                  </div>

                  <div className="space-y-1.5">
                    <Label className="text-xs">Konfiguracja Claude Desktop</Label>
                    <div className="relative">
                      <pre className="text-xs bg-muted px-3 py-2 rounded-md font-mono overflow-x-auto whitespace-pre-wrap">
                        {claudeConfig}
                      </pre>
                      <Button variant="ghost" size="icon"
                        className="absolute top-1 right-1 h-6 w-6"
                        onClick={() => copy(claudeConfig, 'Konfiguracja skopiowana')}>
                        <Copy className="w-3 h-3" />
                      </Button>
                    </div>
                  </div>

                  <Button className="w-full" onClick={() => setOpen(false)}>Gotowe</Button>
                </div>
              ) : (
                /* ── Create form ── */
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <Label>Nazwa tokenu</Label>
                    <Input
                      placeholder="np. Claude Desktop · Biuro"
                      value={label}
                      onChange={e => setLabel(e.target.value)}
                    />
                  </div>

                  <div className="space-y-1.5">
                    <Label>Uprawnienia (scope)</Label>
                    <Select value={scope} onValueChange={setScope}>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                      <SelectContent>
                        <SelectItem value="read">read — tylko odczyt pamięci</SelectItem>
                        <SelectItem value="write">write — odczyt + zapis (add_memory)</SelectItem>
                        <SelectItem value="admin">admin — pełny dostęp</SelectItem>
                      </SelectContent>
                    </Select>
                  </div>

                  <div className="space-y-1.5">
                    <Label>Ważność w dniach <span className="text-muted-foreground">(puste = nie wygasa)</span></Label>
                    <Input
                      type="number"
                      min={1}
                      placeholder="np. 30"
                      value={days}
                      onChange={e => setDays(e.target.value)}
                    />
                  </div>

                  <Button
                    className="w-full"
                    disabled={!label.trim() || create.isPending}
                    onClick={() => create.mutate()}
                  >
                    {create.isPending
                      ? <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      : <Plus className="w-4 h-4 mr-2" />}
                    Wygeneruj token
                  </Button>
                </div>
              )}
            </DialogContent>
          </Dialog>
        </CardHeader>

        <CardContent>
          {isLoading ? (
            <div className="flex justify-center py-10">
              <Loader2 className="w-5 h-5 animate-spin text-muted-foreground" />
            </div>
          ) : tokens.length === 0 ? (
            <p className="text-sm text-muted-foreground text-center py-10">
              Brak tokenów. Utwórz pierwszy token żeby podłączyć klienta MCP.
            </p>
          ) : (
            <div className="divide-y divide-border">
              {tokens.map(t => (
                <div key={t.id}
                  className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{t.label}</p>
                    <p className="text-xs text-muted-foreground">
                      {t.use_count} użyć
                      {t.last_used_at
                        ? ` · ostatnio ${new Date(t.last_used_at).toLocaleDateString('pl')}`
                        : ' · nigdy nie użyty'}
                      {t.expires_at
                        ? ` · wygasa ${new Date(t.expires_at).toLocaleDateString('pl')}`
                        : ''}
                    </p>
                  </div>

                  <ScopeBadge scope={t.scope} />

                  <Badge
                    variant={t.status === 'active' ? 'outline' : 'destructive'}
                    className="text-xs shrink-0">
                    {t.status === 'active' ? 'aktywny'
                      : t.status === 'expired' ? 'wygasły'
                      : 'unieważniony'}
                  </Badge>

                  {t.status === 'active' && (
                    <Button
                      variant="ghost" size="icon"
                      className="text-destructive hover:text-destructive shrink-0"
                      disabled={revoke.isPending}
                      onClick={() => revoke.mutate(t.id)}
                    >
                      <Trash2 className="w-4 h-4" />
                    </Button>
                  )}
                </div>
              ))}
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
}

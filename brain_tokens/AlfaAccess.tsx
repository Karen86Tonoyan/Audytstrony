import { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { useAuth } from '@/hooks/useAuth';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import {
  Card, CardContent, CardDescription, CardHeader, CardTitle,
} from '@/components/ui/card';
import {
  Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger,
} from '@/components/ui/dialog';
import { Badge } from '@/components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { toast } from 'sonner';
import {
  KeyRound, Copy, Plus, Trash2, Eye, EyeOff, Loader2, Terminal, Book,
} from 'lucide-react';

const MCP_URL = 'https://ocbwiopyscjdpjewsssx.functions.supabase.co/mcp-server';

interface TokenRow {
  id: string;
  label: string;
  scope: string;
  created_at: string;
  expires_at: string | null;
  status: string;
  use_count: number;
}

function copy(text: string, msg = 'Skopiowano') {
  navigator.clipboard.writeText(text).then(() => toast.success(msg));
}

const CLIENTS = [
  {
    id: 'claude',
    name: 'Claude Desktop',
    config: (token: string) => JSON.stringify({
      mcpServers: {
        'alfa-brain': {
          url: MCP_URL,
          transport: 'http',
          headers: { Authorization: `Bearer ${token}` },
        },
      },
    }, null, 2),
    path: '~/Library/Application Support/Claude/claude_desktop_config.json',
    note: 'Uruchom ponownie Claude Desktop po zapisaniu pliku.',
  },
  {
    id: 'cursor',
    name: 'Cursor / Cline',
    config: (token: string) =>
      `MCP Server URL:\n${MCP_URL}\n\nHeader:\nAuthorization: Bearer ${token}`,
    path: 'Settings → MCP → Add Server',
    note: 'Wklej URL i dodaj nagłówek Authorization.',
  },
  {
    id: 'api',
    name: 'REST API / Python',
    config: (token: string) =>
`import httpx

headers = {"Authorization": f"Bearer ${token}"}
resp = httpx.post(
    "${MCP_URL}",
    headers=headers,
    json={
        "jsonrpc": "2.0",
        "method": "tools/call",
        "params": {"name": "search_notes", "arguments": {"query": "test"}},
        "id": 1,
    },
)
print(resp.json())`,
    path: 'Python / httpx',
    note: 'Działa z dowolnym klientem HTTP obsługującym JSON-RPC.',
  },
];

export default function AlfaAccess() {
  const { user } = useAuth();
  const qc = useQueryClient();

  const { data: tokens = [], isLoading } = useQuery<TokenRow[]>({
    queryKey: ['alfa-tokens', user?.id],
    queryFn: async () => {
      const { data, error } = await supabase
        .from('brain_tokens_admin')
        .select('*')
        .order('created_at', { ascending: false });
      if (error) throw new Error(error.message);
      return (data ?? []) as TokenRow[];
    },
  });

  const revoke = useMutation({
    mutationFn: async (id: string) => {
      const { error } = await supabase.rpc('revoke_brain_token', { p_token_id: id });
      if (error) throw new Error(error.message);
    },
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['alfa-tokens'] });
      toast.success('Token unieważniony');
    },
    onError: (e: Error) => toast.error(e.message),
  });

  // Create dialog
  const [open, setOpen] = useState(false);
  const [tokenLabel, setTokenLabel] = useState('');
  const [createdToken, setCreatedToken] = useState<string | null>(null);
  const [visible, setVisible] = useState(false);
  const [activeClient, setActiveClient] = useState('claude');

  const resetDialog = () => {
    setTokenLabel(''); setCreatedToken(null); setVisible(false); setActiveClient('claude');
  };

  const create = useMutation({
    mutationFn: async () => {
      const { data, error } = await supabase.rpc('create_brain_token', {
        p_label: tokenLabel || `${user?.full_name ?? 'User'} · ${new Date().toLocaleDateString('pl')}`,
        p_owner_email: user?.email ?? null,
        p_scope: 'write',
        p_expires_days: null,
      });
      if (error) throw new Error(error.message);
      return (data as { token: string; token_id: string }[])[0];
    },
    onSuccess: (res) => {
      setCreatedToken(res.token);
      qc.invalidateQueries({ queryKey: ['alfa-tokens'] });
    },
    onError: (e: Error) => toast.error(e.message),
  });

  const activeConfig = CLIENTS.find(c => c.id === activeClient);

  return (
    <div className="space-y-6 max-w-3xl">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold flex items-center gap-2">
          <KeyRound className="w-6 h-6 text-primary" />
          Dostęp ALFA API
        </h1>
        <p className="text-sm text-muted-foreground mt-1">
          Wygeneruj token API żeby podłączyć zewnętrzne narzędzia do ALFA Brain.
        </p>
      </div>

      {/* Quick start */}
      <Card>
        <CardHeader className="pb-3">
          <CardTitle className="text-sm flex items-center gap-2">
            <Book className="w-4 h-4 text-primary" /> Szybki start
          </CardTitle>
          <CardDescription className="text-xs">
            Utwórz token poniżej i wybierz swojego klienta — wygenerujemy gotową konfigurację.
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
        </CardContent>
      </Card>

      {/* Tokens */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between pb-3">
          <div>
            <CardTitle className="text-sm">Twoje tokeny API</CardTitle>
            <CardDescription className="text-xs">
              {tokens.filter(t => t.status === 'active').length} aktywnych
            </CardDescription>
          </div>

          <Dialog open={open} onOpenChange={v => { setOpen(v); if (!v) resetDialog(); }}>
            <DialogTrigger asChild>
              <Button size="sm">
                <Plus className="w-3.5 h-3.5 mr-1" /> Nowy token
              </Button>
            </DialogTrigger>

            <DialogContent className="sm:max-w-lg">
              <DialogHeader>
                <DialogTitle>
                  {createdToken ? 'Token gotowy' : 'Nowy token ALFA API'}
                </DialogTitle>
              </DialogHeader>

              {createdToken ? (
                <div className="space-y-4">
                  {/* Token value */}
                  <div className="space-y-1.5">
                    <Label className="text-xs">Token (zapisz teraz)</Label>
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

                  {/* Client config tabs */}
                  <div className="space-y-1.5">
                    <Label className="text-xs flex items-center gap-1.5">
                      <Terminal className="w-3.5 h-3.5" /> Konfiguracja klienta
                    </Label>
                    <Tabs value={activeClient} onValueChange={setActiveClient}>
                      <TabsList className="h-8 text-xs">
                        {CLIENTS.map(c => (
                          <TabsTrigger key={c.id} value={c.id} className="text-xs px-3">
                            {c.name}
                          </TabsTrigger>
                        ))}
                      </TabsList>
                      {CLIENTS.map(c => (
                        <TabsContent key={c.id} value={c.id} className="mt-2">
                          <div className="relative">
                            <pre className="text-xs bg-muted p-3 rounded-md font-mono overflow-x-auto whitespace-pre-wrap max-h-52 overflow-y-auto">
                              {c.config(createdToken)}
                            </pre>
                            <Button
                              variant="ghost" size="icon"
                              className="absolute top-1 right-1 h-6 w-6"
                              onClick={() => copy(c.config(createdToken), 'Konfiguracja skopiowana')}>
                              <Copy className="w-3 h-3" />
                            </Button>
                          </div>
                          <p className="text-xs text-muted-foreground mt-1.5">
                            📁 {c.path}
                          </p>
                          <p className="text-xs text-muted-foreground">{c.note}</p>
                        </TabsContent>
                      ))}
                    </Tabs>
                  </div>

                  <Button className="w-full" onClick={() => setOpen(false)}>
                    Zamknij
                  </Button>
                </div>
              ) : (
                <div className="space-y-4">
                  <div className="space-y-1.5">
                    <Label>Nazwa tokenu <span className="text-muted-foreground">(opcjonalnie)</span></Label>
                    <Input
                      placeholder={`${user?.full_name ?? 'Użytkownik'} · Claude Desktop`}
                      value={tokenLabel}
                      onChange={e => setTokenLabel(e.target.value)}
                    />
                  </div>
                  <p className="text-xs text-muted-foreground">
                    Token zostanie wygenerowany z uprawnieniami <strong>write</strong> (odczyt + zapis pamięci).
                    Możesz mieć wiele tokenów dla różnych klientów.
                  </p>
                  <Button
                    className="w-full"
                    disabled={create.isPending}
                    onClick={() => create.mutate()}
                  >
                    {create.isPending
                      ? <Loader2 className="w-4 h-4 animate-spin mr-2" />
                      : <KeyRound className="w-4 h-4 mr-2" />}
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
            <div className="text-center py-10 space-y-2">
              <KeyRound className="w-8 h-8 text-muted-foreground/40 mx-auto" />
              <p className="text-sm text-muted-foreground">
                Brak tokenów. Utwórz pierwszy żeby połączyć klienta AI.
              </p>
            </div>
          ) : (
            <div className="divide-y divide-border">
              {tokens.map(t => (
                <div key={t.id} className="flex items-center gap-3 py-3 first:pt-0 last:pb-0">
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{t.label}</p>
                    <p className="text-xs text-muted-foreground">
                      {t.use_count} użyć ·{' '}
                      {new Date(t.created_at).toLocaleDateString('pl')}
                      {t.expires_at
                        ? ` · wygasa ${new Date(t.expires_at).toLocaleDateString('pl')}`
                        : ''}
                    </p>
                  </div>

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

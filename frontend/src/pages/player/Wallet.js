import React, { useState, useEffect, useMemo } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Textarea } from '../../components/ui/textarea';
import { Label } from '../../components/ui/label';
import { toast } from 'sonner';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import {
  Wallet,
  ArrowDownRight,
  ArrowUpRight,
  Loader2,
  TrendingUp,
  TrendingDown,
  ChevronRight,
  Copy,
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useCurrency } from '../../hooks/useCurrency';
import {
  convertAmount,
  formatMoney,
  getMoneyConfig,
  getPresetLabel,
  normalizeSubmitAmount,
  parseMoneyInputToNumber,
  sanitizeMoneyInputByCurrency,
} from '../../lib/currency';

export default function PlayerWalletPage() {
  const { api, user, updateWalletBalance, secureApiCall } = useAuth();
  const { formatAppMoney, currency, isDemoMode, MONEY_DISPLAY_CLASSES } = useCurrency();
  const activeMoneyConfig = useMemo(() => getMoneyConfig({ currency, isDemoMode }), [currency, isDemoMode]);
  const navigate = useNavigate();
  const [balance, setBalance] = useState(user?.wallet_balance || 0);
  const [rawAmountInput, setRawAmountInput] = useState('');
  const [amountValue, setAmountValue] = useState(null);
  const [loading, setLoading] = useState(false);
  const [recentTx, setRecentTx] = useState([]);

  const [bankAccounts, setBankAccounts] = useState([]);
  const [selectedBank, setSelectedBank] = useState('');
  const [bankNote, setBankNote] = useState('');
  const [proofFile, setProofFile] = useState(null);
  const [bankLoading, setBankLoading] = useState(false);

  useEffect(() => {
    setBalance(user?.wallet_balance || 0);
    fetchRecentTransactions();
    fetchBankAccounts();
  }, [user?.wallet_balance]);

  const fetchBankAccounts = async () => {
    try {
      const res = await api.get('/player/bank-accounts');
      setBankAccounts(res.data || []);
      if (res.data?.[0]?.id) setSelectedBank((prev) => prev || res.data[0].id);
    } catch {
      // ignore
    }
  };

  const fetchRecentTransactions = async () => {
    try {
      const response = await api.get('/transactions', {
        params: { limit: 5, type: 'deposit,withdrawal' },
      });
      setRecentTx(response.data);
    } catch (err) {
      console.error('Failed to fetch transactions:', err);
    }
  };

  const minError = amountValue !== null && amountValue < activeMoneyConfig.minDeposit;
  const validationError = minError ? `Deposit minimum ${formatAppMoney(activeMoneyConfig.minDeposit)}` : null;

  const canSubmit = rawAmountInput !== '' && amountValue !== null && !validationError;

  const handleDeposit = async () => {
    const submitAmount = normalizeSubmitAmount(amountValue, currency);
    if (!submitAmount) {
      toast.error('Masukkan jumlah yang valid');
      return;
    }

    if (validationError) {
      toast.error(validationError);
      return;
    }

    setLoading(true);
    try {
      const response = await api.post('/wallet/deposit', { amount: submitAmount, currency });
      setBalance(response.data.balance_after);
      updateWalletBalance(response.data.balance_after);
      setRawAmountInput('');
      setAmountValue(null);
      toast.success(`Berhasil +${formatAppMoney(submitAmount)}`);
      fetchRecentTransactions();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Gagal');
    } finally {
      setLoading(false);
    }
  };

  const handleBankDeposit = async () => {
    const submitAmount = normalizeSubmitAmount(amountValue, currency);
    if (!selectedBank) {
      toast.error('Pilih rekening tujuan dahulu');
      return;
    }
    if (!submitAmount) {
      toast.error('Masukkan nominal deposit');
      return;
    }

    setBankLoading(true);
    try {
      let proofUrl;
      if (proofFile) {
        const fd = new FormData();
        fd.append('file', proofFile);
        const uploadRes = await api.post('/uploads/proof', fd, {
          headers: { 'Content-Type': 'multipart/form-data' },
        });
        proofUrl = uploadRes.data?.proof_url;
      }

      await secureApiCall('post', '/payments/deposit/bank/create', {
        amount: submitAmount,
        currency,
        bank_account_id: selectedBank,
        note: bankNote || undefined,
        proof_url: proofUrl,
      });
      setRawAmountInput('');
      setAmountValue(null);
      setBankNote('');
      setProofFile(null);
      toast.success('Deposit bank berhasil dibuat. Menunggu approval operator.');
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Gagal membuat order deposit bank');
    } finally {
      setBankLoading(false);
    }
  };

  const formatTransactionAmount = (txAmount, txCurrency) => {
    const normalizedTxCurrency = String(txCurrency || currency).toUpperCase();
    const convertedAmount = convertAmount(txAmount, {
      fromCurrency: normalizedTxCurrency,
      toCurrency: currency,
    });
    return formatAppMoney(convertedAmount ?? txAmount);
  };

  const estimateText = useMemo(() => {
    if (amountValue === null) return null;

    const estimateAmount = convertAmount(amountValue, { fromCurrency: currency, toCurrency: 'USD' });

    return `Estimasi (USD): ${formatMoney(estimateAmount, {
      currency: 'USD',
      locale: 'en-US',
    })}`;
  }, [amountValue, currency]);

  const selectedBankDetail = bankAccounts.find((item) => item.id === selectedBank);

  return (
    <div className="space-y-3" data-testid="player-wallet-page">
      <div className="relative overflow-hidden rounded-xl border border-border/40 p-4" style={{ background: 'linear-gradient(135deg, hsl(var(--primary) / 0.12) 0%, hsl(var(--card)) 40%, hsl(var(--accent) / 0.08) 100%)', boxShadow: '0 4px 16px -4px hsl(var(--primary) / 0.15), inset 0 1px 0 hsl(var(--foreground) / 0.03)' }}>
        <div className="flex items-center justify-between mb-3">
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 rounded-lg bg-primary/20 flex items-center justify-center"><Wallet className="w-4 h-4 text-primary" /></div>
            <div>
              <p className="text-[10px] text-muted-foreground uppercase tracking-wider">Saldo Anda</p>
              <p className={`text-xl font-bold text-primary ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(balance)}>{formatAppMoney(balance)}</p>
            </div>
          </div>
          <Button variant="outline" size="sm" className="h-7 text-[10px]" onClick={() => navigate('/play/withdraw')}><ArrowUpRight className="w-3 h-3 mr-1" />Tarik</Button>
        </div>
      </div>

      <div className="bg-card rounded-xl border border-border/40 p-3" style={{ boxShadow: '0 2px 8px -2px hsl(var(--background) / 0.3)' }}>
        <Tabs defaultValue="instant" className="space-y-3">
          <TabsList className="grid grid-cols-2 w-full">
            <TabsTrigger value="instant">Deposit Instan</TabsTrigger>
            <TabsTrigger value="bank">Deposit Bank</TabsTrigger>
          </TabsList>
          <TabsContent value="instant" className="space-y-3">
            <h2 className="text-sm font-semibold flex items-center gap-1.5"><ArrowDownRight className="w-4 h-4 text-green-500" />Deposit</h2>
            <div className="grid grid-cols-3 sm:grid-cols-6 gap-1.5">
              {activeMoneyConfig.presetsDeposit.map((amount) => (
                <Button key={amount} variant={amountValue === amount ? 'default' : 'outline'} size="sm" onClick={() => { setRawAmountInput(`${amount}`); setAmountValue(amount); }} className="h-8 text-[10px] px-1">{getPresetLabel(amount, currency, formatAppMoney)}</Button>
              ))}
            </div>
            <div className="flex gap-2">
              <Input type="text" inputMode="decimal" placeholder="0" value={rawAmountInput} onChange={(e) => { const sanitized = sanitizeMoneyInputByCurrency(e.target.value, undefined, currency); setRawAmountInput(sanitized); setAmountValue(parseMoneyInputToNumber(sanitized, currency)); }} className="h-9 text-sm" data-testid="deposit-amount" />
              <Button onClick={handleDeposit} disabled={loading || !canSubmit} className="h-9 px-4">{loading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Deposit'}</Button>
            </div>
          </TabsContent>
          <TabsContent value="bank" className="space-y-3">
            <h2 className="text-sm font-semibold">Deposit Bank (Manual Transfer)</h2>
            <div>
              <Label>Pilih Rekening Tujuan</Label>
              <Select value={selectedBank} onValueChange={setSelectedBank}>
                <SelectTrigger><SelectValue placeholder="Pilih rekening" /></SelectTrigger>
                <SelectContent>
                  {bankAccounts.map((item) => <SelectItem key={item.id} value={item.id}>{item.bank_name} - {item.account_number}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            {selectedBankDetail && (
              <div className="rounded-lg border border-border/50 p-3 bg-muted/20">
                <p className="text-sm font-semibold">{selectedBankDetail.bank_name}</p>
                <p className="text-sm font-mono">{selectedBankDetail.account_number}</p>
                <p className="text-xs text-muted-foreground mb-2">a/n {selectedBankDetail.account_name}</p>
                <Button size="sm" variant="outline" onClick={() => { navigator.clipboard.writeText(selectedBankDetail.account_number); toast.success('Nomor rekening disalin'); }}><Copy className="w-4 h-4 mr-1" />Copy Rekening</Button>
              </div>
            )}
            <div>
              <Label>Nominal</Label>
              <Input type="text" inputMode="decimal" placeholder="0" value={rawAmountInput} onChange={(e) => { const sanitized = sanitizeMoneyInputByCurrency(e.target.value, undefined, currency); setRawAmountInput(sanitized); setAmountValue(parseMoneyInputToNumber(sanitized, currency)); }} />
            </div>
            <div>
              <Label>Catatan (opsional)</Label>
              <Textarea rows={3} value={bankNote} onChange={(e) => setBankNote(e.target.value)} placeholder="Contoh: transfer dari BCA pribadi" />
            </div>
            <div>
              <Label>Bukti Transfer (opsional)</Label>
              <Input type="file" accept=".jpg,.jpeg,.png,.webp,.pdf" onChange={(e) => setProofFile(e.target.files?.[0] || null)} />
            </div>
            <Button onClick={handleBankDeposit} disabled={bankLoading}>{bankLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : 'Buat Deposit Order'}</Button>
            <p className="text-xs text-yellow-500">Status: Menunggu approval operator.</p>
          </TabsContent>
        </Tabs>

        {rawAmountInput && amountValue !== null && (
          <div className="mt-1.5 text-center space-y-0.5">
            <p className="text-[10px] text-muted-foreground">Format ({currency}): {formatAppMoney(amountValue)}</p>
            {estimateText && <p className="text-[10px] text-muted-foreground">{estimateText}</p>}
            {validationError && <p className="text-[10px] text-red-400">{validationError}</p>}
          </div>
        )}
      </div>

      <div className="bg-card rounded-xl border border-border/40 p-3" style={{ boxShadow: '0 2px 8px -2px hsl(var(--background) / 0.3)' }}>
        <div className="flex items-center justify-between mb-2">
          <h3 className="text-xs font-semibold">Aktivitas Wallet</h3>
          <Button variant="ghost" size="sm" className="h-5 px-1.5 text-[9px]" onClick={() => navigate('/play/history')}>Semua <ChevronRight className="w-2.5 h-2.5 ml-0.5" /></Button>
        </div>

        {recentTx.length === 0 ? (
          <div className="empty-state-compact"><Wallet className="w-5 h-5 text-muted-foreground/30" /><p>Belum ada aktivitas</p></div>
        ) : (
          <div className="space-y-1">
            {recentTx.map((tx, idx) => {
              const isDeposit = tx.type === 'deposit';
              return (
                <div key={idx} className="flex items-center justify-between py-1.5 border-b border-border/50 last:border-0">
                  <div className="flex items-center gap-2">
                    <div className={cn('w-6 h-6 rounded-full flex items-center justify-center', isDeposit ? 'bg-green-500/10' : 'bg-red-500/10')}>
                      {isDeposit ? <TrendingUp className="w-3 h-3 text-green-500" /> : <TrendingDown className="w-3 h-3 text-red-400" />}
                    </div>
                    <div>
                      <p className="text-[10px] font-medium">{isDeposit ? 'Deposit' : 'Withdraw'}</p>
                      <p className="text-[9px] text-muted-foreground">{new Date(tx.timestamp).toLocaleDateString('id-ID')}</p>
                    </div>
                  </div>
                  <p className={cn(`text-[10px] font-mono font-medium ${MONEY_DISPLAY_CLASSES}`, isDeposit ? 'text-green-500' : 'text-red-400')} title={formatTransactionAmount(tx.amount, tx.currency)}>{isDeposit ? '+' : '-'}{formatTransactionAmount(tx.amount, tx.currency)}</p>
                </div>
              );
            })}
          </div>
        )}
      </div>
    </div>
  );
}

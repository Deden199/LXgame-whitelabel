import React, { useState, useEffect, useMemo } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Skeleton } from '../../components/ui/skeleton';
import { toast } from 'sonner';
import { Wallet, ArrowUpRight, Loader2, AlertCircle, CheckCircle2, Clock } from 'lucide-react';
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

export default function PlayerWithdrawPage() {
  const { api, user, updateWalletBalance, secureApiCall } = useAuth();
  const { formatAppMoney, currency, isDemoMode, MONEY_DISPLAY_CLASSES } = useCurrency();
  const activeMoneyConfig = useMemo(() => getMoneyConfig({ currency, isDemoMode }), [currency, isDemoMode]);
  const [balance, setBalance] = useState(user?.wallet_balance || 0);
  const [rawAmountInput, setRawAmountInput] = useState('');
  const [amountValue, setAmountValue] = useState(null);
  const [loading, setLoading] = useState(false);
  const [recentWithdrawals, setRecentWithdrawals] = useState([]);
  const [loadingTx, setLoadingTx] = useState(true);
  const [bankName, setBankName] = useState('');
  const [accountNumber, setAccountNumber] = useState('');
  const [accountName, setAccountName] = useState('');

  useEffect(() => {
    setBalance(user?.wallet_balance || 0);
    fetchRecentWithdrawals();
  }, [user?.wallet_balance]);

  const estimateText = useMemo(() => {
    if (amountValue === null) return null;

    const estimateAmount = convertAmount(amountValue, { fromCurrency: currency, toCurrency: 'USD' });
    return `Estimasi (USD): ${formatMoney(estimateAmount, { currency: 'USD', locale: 'en-US' })}`;
  }, [amountValue, currency]);


  const formatTransactionAmount = (txAmount, txCurrency) => {
    const normalizedTxCurrency = String(txCurrency || currency).toUpperCase();
    const convertedAmount = convertAmount(txAmount, {
      fromCurrency: normalizedTxCurrency,
      toCurrency: currency,
    });
    return formatAppMoney(convertedAmount ?? txAmount);
  };

  const fetchRecentWithdrawals = async () => {
    try {
      const response = await api.get('/transactions', {
        params: { type: 'withdrawal', limit: 5 },
      });
      setRecentWithdrawals(response.data);
    } catch (err) {
      console.error('Failed to fetch withdrawals:', err);
    } finally {
      setLoadingTx(false);
    }
  };

  const minError = amountValue !== null && amountValue < activeMoneyConfig.minWithdraw;
  const maxError = activeMoneyConfig.maxWithdraw !== null && amountValue !== null && amountValue > activeMoneyConfig.maxWithdraw;
  const balanceError = amountValue !== null && amountValue > balance;
  const validationError = minError
    ? `Penarikan minimum ${formatAppMoney(activeMoneyConfig.minWithdraw)}`
    : maxError
    ? `Penarikan maksimum ${formatAppMoney(activeMoneyConfig.maxWithdraw)}`
    : balanceError
    ? 'Saldo tidak mencukupi'
    : null;

  const handleWithdraw = async () => {
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
      if (!bankName || !accountNumber || !accountName) {
        toast.error('Lengkapi data rekening bank terlebih dahulu');
        setLoading(false);
        return;
      }
      const response = await secureApiCall('post', '/payments/withdraw/create', {
        amount: submitAmount,
        currency,
        provider: 'dummy',
        bank_info: { bank_name: bankName, account_number: accountNumber, account_name: accountName },
      });
      const nextBalance = (response.data?.order?.amount !== undefined) ? (balance - submitAmount) : balance;
      setBalance(nextBalance);
      updateWalletBalance(nextBalance);
      setRawAmountInput('');
      setAmountValue(null);
      toast.success(`Penarikan ${formatAppMoney(submitAmount)} diproses!`);
      fetchRecentWithdrawals();
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Penarikan gagal');
    } finally {
      setLoading(false);
    }
  };

  const handleQuickWithdraw = (amount) => {
    setRawAmountInput(`${amount}`);
    setAmountValue(amount);
  };

  return (
    <div className="space-y-6" data-testid="player-withdraw-page">
      <div>
        <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Tarik Dana</h1>
        <p className="text-muted-foreground mt-1">Ajukan penarikan ke rekening bank Anda</p>
      </div>

      <Card className="glass-card border-primary/20 glow-primary">
        <CardContent className="pt-6">
          <div className="flex flex-col md:flex-row md:items-center md:justify-between gap-4">
            <div className="flex items-center gap-4">
              <div className="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
                <Wallet className="w-8 h-8 text-primary" />
              </div>
              <div className="min-w-0 flex-1">
                <p className="text-sm text-muted-foreground">Saldo Tersedia</p>
                <p className={`text-4xl font-bold text-primary ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(balance)}>{formatAppMoney(balance)}</p>
              </div>
            </div>
            <div className="text-sm text-muted-foreground">
              <div className="flex items-center gap-2">
                <Clock className="w-4 h-4" />
                <span>Waktu proses: 1-3 hari kerja</span>
              </div>
            </div>
          </div>
        </CardContent>
      </Card>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <ArrowUpRight className="w-5 h-5 text-primary" />
              Ajukan Penarikan
            </CardTitle>
            <CardDescription>Dana akan dikirim ke rekening bank terdaftar Anda</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <p className="text-xs text-muted-foreground">
              Mata uang aktif: <span className="font-semibold text-foreground">{currency}</span>
            </p>
            <div>
              <Label className="text-sm text-muted-foreground mb-2 block">Pilih Cepat</Label>
              <div className="grid grid-cols-3 sm:grid-cols-5 gap-2">
                {activeMoneyConfig.presetsWithdraw.map((amount) => (
                  <Button
                    key={amount}
                    variant="outline"
                    size="sm"
                    onClick={() => handleQuickWithdraw(amount)}
                    className={cn('transition-colors text-xs', amountValue === amount && 'bg-primary/10 border-primary')}
                    data-testid={`quick-withdraw-${amount}`}
                  >
                    {getPresetLabel(amount, currency, formatAppMoney)}
                  </Button>
                ))}
              </div>
            </div>

            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
              <div className="space-y-2">
                <Label>Bank</Label>
                <Input value={bankName} onChange={(e) => setBankName(e.target.value)} placeholder="Contoh: BCA" />
              </div>
              <div className="space-y-2">
                <Label>No. Rekening</Label>
                <Input value={accountNumber} onChange={(e) => setAccountNumber(e.target.value.replace(/\D/g, ''))} placeholder="1234567890" />
              </div>
              <div className="space-y-2">
                <Label>Nama Rekening</Label>
                <Input value={accountName} onChange={(e) => setAccountName(e.target.value)} placeholder="Nama pemilik" />
              </div>
            </div>

            <div className="space-y-2">
              <Label htmlFor="amount">Jumlah Kustom</Label>
              <div className="flex gap-2">
                <div className="relative flex-1">
                  <Input
                    id="amount"
                    type="text"
                    inputMode="decimal"
                    placeholder="0"
                    value={rawAmountInput}
                    onChange={(e) => {
                      const sanitized = sanitizeMoneyInputByCurrency(e.target.value, undefined, currency);
                      setRawAmountInput(sanitized);
                      setAmountValue(parseMoneyInputToNumber(sanitized, currency));
                    }}
                    className="pl-3"
                    data-testid="withdraw-amount-input"
                  />
                </div>
                <Button
                  onClick={handleWithdraw}
                  disabled={loading || rawAmountInput === '' || amountValue === null || !!validationError}
                  className="glow-primary"
                  data-testid="withdraw-btn"
                >
                  {loading ? <Loader2 className="w-4 h-4 animate-spin" /> : <><ArrowUpRight className="w-4 h-4 mr-2" />Tarik</>}
                </Button>
              </div>
              {rawAmountInput && amountValue !== null && (
                <div className="space-y-0.5">
                  <p className="text-xs text-muted-foreground">Format ({currency}): {formatAppMoney(amountValue)}</p>
                  {estimateText && <p className="text-xs text-muted-foreground">{estimateText}</p>}
                  {validationError && <p className="text-xs text-red-400">{validationError}</p>}
                </div>
              )}
            </div>

            <div className="p-4 rounded-lg bg-yellow-500/10 border border-yellow-500/20">
              <div className="flex items-start gap-3">
                <AlertCircle className="w-5 h-5 text-yellow-500 mt-0.5" />
                <div className="text-sm">
                  <p className="font-medium text-yellow-500">Info Penarikan</p>
                  <ul className="text-muted-foreground mt-1 space-y-1">
                    <li>• Penarikan minimum: {formatAppMoney(activeMoneyConfig.minWithdraw)}</li>
                    {activeMoneyConfig.maxWithdraw !== null && <li>• Penarikan maksimum: {formatAppMoney(activeMoneyConfig.maxWithdraw)}</li>}
                    <li>• Waktu proses: 1-3 hari kerja</li>
                    <li>• Dana dikirim ke rekening bank terdaftar</li>
                  </ul>
                </div>
              </div>
            </div>

            <p className="text-xs text-muted-foreground">Ini adalah penarikan simulasi untuk demonstrasi saja.</p>
          </CardContent>
        </Card>

        <Card className="glass-card">
          <CardHeader>
            <CardTitle className="flex items-center gap-2">
              <Clock className="w-5 h-5 text-primary" />
              Penarikan Terbaru
            </CardTitle>
          </CardHeader>
          <CardContent>
            {loadingTx ? (
              <div className="space-y-3">{[...Array(3)].map((_, i) => <Skeleton key={i} className="h-16" />)}</div>
            ) : recentWithdrawals.length === 0 ? (
              <p className="text-center text-muted-foreground py-8">Belum ada riwayat penarikan</p>
            ) : (
              <div className="space-y-3">
                {recentWithdrawals.map((tx) => (
                  <div key={tx.id} className="flex items-center justify-between p-3 rounded-lg bg-muted/30">
                    <div className="flex items-center gap-3">
                      <div className="w-10 h-10 rounded-full bg-red-500/10 flex items-center justify-center">
                        <ArrowUpRight className="w-5 h-5 text-red-400" />
                      </div>
                      <div>
                        <p className="font-medium">Penarikan</p>
                        <p className="text-xs text-muted-foreground">{new Date(tx.timestamp).toLocaleString('id-ID')}</p>
                      </div>
                    </div>
                    <div className="text-right min-w-0">
                      <p className={`font-mono font-medium text-red-400 ${MONEY_DISPLAY_CLASSES}`} title={formatTransactionAmount(tx.amount, tx.currency)}>-{formatTransactionAmount(tx.amount, tx.currency)}</p>
                      <div className="flex items-center gap-1 text-xs text-green-500">
                        <CheckCircle2 className="w-3 h-3" />
                        Selesai
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </CardContent>
        </Card>
      </div>
    </div>
  );
}

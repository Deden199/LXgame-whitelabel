import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Button } from '../../components/ui/button';
import { Badge } from '../../components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { 
  Receipt, 
  Filter,
  ArrowUpRight,
  ArrowDownRight,
  Gamepad2,
  TrendingUp,
  TrendingDown,
  Gift,
  Calendar,
  ChevronLeft,
  ChevronRight
} from 'lucide-react';
import { cn } from '../../lib/utils';
import { useCurrency } from '../../hooks/useCurrency';
import { convertAmount } from '../../lib/currency';

export default function PlayerHistoryPage() {
  const { api } = useAuth();
  const { formatAppMoney, currency, MONEY_DISPLAY_CLASSES } = useCurrency();
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [typeFilter, setTypeFilter] = useState('all');
  const [activeTab, setActiveTab] = useState('all');
  const [stats, setStats] = useState({
    totalDeposits: 0,
    totalBets: 0,
    totalWins: 0
  });


  const normalizeTransactionAmount = (amount, txCurrency) => {
    const normalizedTxCurrency = String(txCurrency || currency).toUpperCase();
    return convertAmount(amount, {
      fromCurrency: normalizedTxCurrency,
      toCurrency: currency,
    });
  };

  useEffect(() => {
    fetchTransactions();
  }, [typeFilter, activeTab]);

  const fetchTransactions = async () => {
    setLoading(true);
    try {
      const params = { limit: 100 };
      
      // Apply tab filter
      if (activeTab === 'games') {
        params.type = 'bet,win';
      } else if (activeTab === 'wallet') {
        params.type = 'deposit,withdrawal';
      } else if (typeFilter !== 'all') {
        params.type = typeFilter;
      }
      
      const response = await api.get('/transactions', { params });
      setTransactions(response.data);
      
      // Calculate stats
      const deposits = response.data
        .filter(tx => tx.type === 'deposit')
        .reduce((sum, tx) => sum + (normalizeTransactionAmount(tx.amount, tx.currency) ?? tx.amount), 0);
      const bets = response.data
        .filter(tx => tx.type === 'bet')
        .reduce((sum, tx) => sum + (normalizeTransactionAmount(tx.amount, tx.currency) ?? tx.amount), 0);
      const wins = response.data
        .filter(tx => tx.type === 'win')
        .reduce((sum, tx) => sum + (normalizeTransactionAmount(tx.amount, tx.currency) ?? tx.amount), 0);
      
      setStats({ totalDeposits: deposits, totalBets: bets, totalWins: wins });
    } catch (err) {
      console.error('Failed to fetch transactions:', err);
    } finally {
      setLoading(false);
    }
  };

  const typeLabels = {
    deposit: 'Deposit',
    withdrawal: 'Withdraw',
    bet: 'Bet',
    win: 'Win',
    bonus: 'Bonus',
    rollback: 'Rollback'
  };

  const typeIcons = {
    deposit: ArrowDownRight,
    withdrawal: ArrowUpRight,
    bet: Gamepad2,
    win: Gift,
    bonus: Gift,
    rollback: TrendingDown
  };

  // Transaction Row Component - Compact
  const TransactionRow = ({ tx }) => {
    const Icon = typeIcons[tx.type] || Receipt;
    const isPositive = ['deposit', 'win', 'bonus'].includes(tx.type);
    
    return (
      <div className="flex items-center gap-2 py-2 px-2 border-b border-border/50 last:border-0 hover:bg-muted/30">
        <div className={cn(
          "w-7 h-7 rounded-full flex items-center justify-center flex-shrink-0",
          isPositive ? "bg-green-500/10" : "bg-red-500/10"
        )}>
          <Icon className={cn("w-3.5 h-3.5", isPositive ? "text-green-500" : "text-red-400")} />
        </div>
        
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-1.5">
            <span className="text-xs font-medium">{typeLabels[tx.type] || tx.type}</span>
            {tx.game_id && (
              <span className="text-[10px] text-muted-foreground truncate">• {tx.game_id}</span>
            )}
          </div>
          <p className="text-[10px] text-muted-foreground">
            {new Date(tx.timestamp).toLocaleString('id-ID', { 
              day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' 
            })}
          </p>
        </div>
        
        <div className="text-right flex-shrink-0 min-w-0">
          <p className={cn(
            `text-xs font-mono font-medium ${MONEY_DISPLAY_CLASSES}`,
            isPositive ? "text-green-500" : "text-red-400"
          )} title={formatAppMoney(normalizeTransactionAmount(tx.amount, tx.currency) ?? tx.amount)}>
            {isPositive ? '+' : '-'}{formatAppMoney(normalizeTransactionAmount(tx.amount, tx.currency) ?? tx.amount)}
          </p>
          <p className={`text-[9px] text-muted-foreground font-mono ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(normalizeTransactionAmount(tx.balance_after, tx.currency) ?? tx.balance_after)}>
            Bal: {formatAppMoney(normalizeTransactionAmount(tx.balance_after, tx.currency) ?? tx.balance_after)}
          </p>
        </div>
      </div>
    );
  };

  if (loading && transactions.length === 0) {
    return (
      <div className="space-y-3" data-testid="player-history-page">
        <div className="h-8 w-48 bg-muted rounded animate-pulse" />
        <div className="grid grid-cols-3 gap-2">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-14 rounded-md bg-muted animate-pulse" />
          ))}
        </div>
        <div className="h-64 rounded-lg bg-muted animate-pulse" />
      </div>
    );
  }

  return (
    <div className="space-y-3" data-testid="player-history-page">
      {/* Header - Compact */}
      <div className="flex items-center justify-between">
        <h1 className="text-sm font-semibold">Riwayat</h1>
        <Select value={typeFilter} onValueChange={setTypeFilter}>
          <SelectTrigger className="w-28 h-7 text-xs">
            <Filter className="w-3 h-3 mr-1" />
            <SelectValue placeholder="Filter" />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value="all" className="text-xs">Semua</SelectItem>
            <SelectItem value="deposit" className="text-xs">Deposit</SelectItem>
            <SelectItem value="bet" className="text-xs">Bet</SelectItem>
            <SelectItem value="win" className="text-xs">Win</SelectItem>
          </SelectContent>
        </Select>
      </div>

      {/* Stats - Premium Row */}
      <div className="grid grid-cols-3 gap-2">
        <div 
          className="bg-card rounded-xl border border-border/40 p-2 min-w-0"
          style={{ boxShadow: '0 2px 8px -2px hsl(var(--background) / 0.3)' }}
        >
          <div className="flex items-center gap-1.5 mb-1">
            <ArrowDownRight className="w-3.5 h-3.5 text-green-500" />
            <span className="text-[10px] text-muted-foreground">Deposit</span>
          </div>
          <p className={`text-sm font-bold text-green-500 ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(stats.totalDeposits)}>
            {formatAppMoney(stats.totalDeposits)}
          </p>
        </div>
        <div 
          className="bg-card rounded-xl border border-border/40 p-2 min-w-0"
          style={{ boxShadow: '0 2px 8px -2px hsl(var(--background) / 0.3)' }}
        >
          <div className="flex items-center gap-1.5 mb-1">
            <Gamepad2 className="w-3.5 h-3.5 text-yellow-500" />
            <span className="text-[10px] text-muted-foreground">Total Bet</span>
          </div>
          <p className={`text-sm font-bold text-yellow-500 ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(stats.totalBets)}>
            {formatAppMoney(stats.totalBets)}
          </p>
        </div>
        <div 
          className="bg-card rounded-xl border border-border/40 p-2 min-w-0"
          style={{ boxShadow: '0 2px 8px -2px hsl(var(--background) / 0.3)' }}
        >
          <div className="flex items-center gap-1.5 mb-1">
            <TrendingUp className="w-3.5 h-3.5 text-blue-500" />
            <span className="text-[10px] text-muted-foreground">Menang</span>
          </div>
          <p className={`text-sm font-bold text-blue-500 ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(stats.totalWins)}>
            {formatAppMoney(stats.totalWins)}
          </p>
        </div>
      </div>

      {/* Tabs */}
      <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
        <TabsList className="w-full h-8 p-0.5 bg-muted/50">
          <TabsTrigger value="all" className="flex-1 h-7 text-xs">Semua</TabsTrigger>
          <TabsTrigger value="games" className="flex-1 h-7 text-xs">Game</TabsTrigger>
          <TabsTrigger value="wallet" className="flex-1 h-7 text-xs">Wallet</TabsTrigger>
        </TabsList>

        <TabsContent value={activeTab} className="mt-2">
          {/* Transactions List */}
          <div 
            className="bg-card rounded-xl border border-border/40 overflow-hidden"
            style={{ boxShadow: '0 2px 8px -2px hsl(var(--background) / 0.3)' }}
          >
            {transactions.length === 0 ? (
              <div className="text-center py-8">
                <Receipt className="w-8 h-8 mx-auto text-muted-foreground/30 mb-2" />
                <p className="text-xs text-muted-foreground">Tidak ada transaksi</p>
              </div>
            ) : (
              <div className="max-h-[calc(100vh-320px)] overflow-y-auto scrollbar-thin">
                {transactions.map((tx) => (
                  <TransactionRow key={tx.id} tx={tx} />
                ))}
              </div>
            )}
          </div>
          
          {/* Transaction Count */}
          <p className="text-[10px] text-muted-foreground text-center mt-2">
            {transactions.length} transaksi
          </p>
        </TabsContent>
      </Tabs>
    </div>
  );
}

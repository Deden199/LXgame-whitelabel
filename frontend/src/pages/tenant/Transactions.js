import React, { useState, useEffect } from 'react';
import { useAuth } from '../../context/AuthContext';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Skeleton } from '../../components/ui/skeleton';
import { Badge } from '../../components/ui/badge';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '../../components/ui/select';
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from '../../components/ui/table';
import { 
  Receipt, 
  Search,
  Filter,
  ArrowUpRight,
  ArrowDownRight,
  RotateCcw,
  Gift,
  Gamepad2
} from 'lucide-react';
import { useCurrency } from '../../hooks/useCurrency';

const TX_TYPE_ICONS = {
  deposit: ArrowDownRight,
  withdrawal: ArrowUpRight,
  bet: Gamepad2,
  win: Gift,
  rollback: RotateCcw,
  bonus: Gift,
  adjustment: RotateCcw
};

const TX_TYPE_COLORS = {
  deposit: 'text-green-500 bg-green-500/10',
  withdrawal: 'text-red-500 bg-red-500/10',
  bet: 'text-yellow-500 bg-yellow-500/10',
  win: 'text-blue-500 bg-blue-500/10',
  rollback: 'text-orange-500 bg-orange-500/10',
  bonus: 'text-purple-500 bg-purple-500/10',
  adjustment: 'text-gray-500 bg-gray-500/10'
};

export default function TransactionsPage() {
  const { api, tenant, isSuperAdmin } = useAuth();
  const { formatAppMoney, MONEY_DISPLAY_CLASSES } = useCurrency();
  const [transactions, setTransactions] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('all');
  const [totalCount, setTotalCount] = useState(0);

  useEffect(() => {
    fetchTransactions();
    fetchCount();
  }, [tenant?.id, typeFilter]);

  const fetchTransactions = async () => {
    try {
      const params = {};
      if (typeFilter !== 'all') params.type = typeFilter;
      
      const response = await api.get('/transactions', { params });
      setTransactions(response.data);
    } catch (err) {
      console.error('Failed to fetch transactions:', err);
    } finally {
      setLoading(false);
    }
  };

  const fetchCount = async () => {
    try {
      const params = {};
      if (typeFilter !== 'all') params.type = typeFilter;
      
      const response = await api.get('/transactions/count', { params });
      setTotalCount(response.data.count);
    } catch (err) {
      console.error('Failed to fetch count:', err);
    }
  };

  const filteredTransactions = transactions.filter(tx =>
    tx.player_id?.toLowerCase().includes(search.toLowerCase()) ||
    tx.tx_id?.toLowerCase().includes(search.toLowerCase())
  );

  if (loading) {
    return (
      <div className="space-y-6" data-testid="transactions-page">
        <Skeleton className="h-10 w-64" />
        <Skeleton className="h-96 w-full rounded-xl" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="transactions-page">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl md:text-3xl font-bold tracking-tight">Buku Besar Transaksi</h1>
          <p className="text-muted-foreground mt-1">
            Jejak audit semua transaksi • {totalCount.toLocaleString('id-ID')} total
          </p>
        </div>
      </div>

      {/* Filters */}
      <Card className="glass-card">
        <CardContent className="pt-6">
          <div className="flex flex-col sm:flex-row gap-4">
            <div className="relative flex-1">
              <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-muted-foreground" />
              <Input
                placeholder="Search by TX ID or Player ID..."
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                className="pl-9"
                data-testid="search-transactions"
              />
            </div>
            <Select value={typeFilter} onValueChange={setTypeFilter}>
              <SelectTrigger className="w-[180px]" data-testid="filter-type">
                <Filter className="w-4 h-4 mr-2" />
                <SelectValue placeholder="Filter jenis" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">Semua Jenis</SelectItem>
                <SelectItem value="deposit">Setoran</SelectItem>
                <SelectItem value="bet">Taruhan</SelectItem>
                <SelectItem value="win">Kemenangan</SelectItem>
                <SelectItem value="withdrawal">Penarikan</SelectItem>
                <SelectItem value="rollback">Rollback</SelectItem>
                <SelectItem value="bonus">Bonus</SelectItem>
              </SelectContent>
            </Select>
          </div>
        </CardContent>
      </Card>

      {/* Transactions Table */}
      <Card className="glass-card">
        <CardHeader>
          <CardTitle className="flex items-center gap-2">
            <Receipt className="w-5 h-5 text-primary" />
            Transactions
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>ID TX</TableHead>
                  <TableHead>Jenis</TableHead>
                  <TableHead>Pemain</TableHead>
                  <TableHead>Permainan</TableHead>
                  <TableHead className="text-right">Jumlah</TableHead>
                  <TableHead className="text-right">Saldo Setelah</TableHead>
                  <TableHead>Waktu</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {filteredTransactions.map((tx) => {
                  const Icon = TX_TYPE_ICONS[tx.type] || Receipt;
                  const colorClass = TX_TYPE_COLORS[tx.type] || 'text-gray-500 bg-gray-500/10';
                  const typeLabels = { deposit: 'Setoran', withdrawal: 'Penarikan', bet: 'Taruhan', win: 'Menang', bonus: 'Bonus', rollback: 'Rollback', adjustment: 'Penyesuaian' };
                  
                  return (
                    <TableRow key={tx.id}>
                      <TableCell>
                        <code className="text-xs bg-muted px-2 py-1 rounded">
                          {tx.tx_id?.slice(0, 12)}...
                        </code>
                      </TableCell>
                      <TableCell>
                        <div className={`inline-flex items-center gap-1.5 px-2 py-1 rounded-md text-xs font-medium ${colorClass}`}>
                          <Icon className="w-3 h-3" />
                          {typeLabels[tx.type] || tx.type}
                        </div>
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {tx.player_id?.slice(0, 16)}...
                      </TableCell>
                      <TableCell className="text-muted-foreground">
                        {tx.game_id || '-'}
                      </TableCell>
                      <TableCell className={`text-right font-mono ${MONEY_DISPLAY_CLASSES} ${
                        ['deposit', 'win', 'bonus'].includes(tx.type) 
                          ? 'text-green-500' 
                          : 'text-red-400'
                      }`} title={formatAppMoney(tx.amount || 0)}>
                        {['deposit', 'win', 'bonus'].includes(tx.type) ? '+' : '-'}
                        {formatAppMoney(tx.amount || 0)}
                      </TableCell>
                      <TableCell className={`text-right font-mono ${MONEY_DISPLAY_CLASSES}`} title={formatAppMoney(tx.balance_after || 0)}>
                        {formatAppMoney(tx.balance_after || 0)}
                      </TableCell>
                      <TableCell className="text-muted-foreground text-sm">
                        {new Date(tx.timestamp).toLocaleString('id-ID')}
                      </TableCell>
                    </TableRow>
                  );
                })}
              </TableBody>
            </Table>
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

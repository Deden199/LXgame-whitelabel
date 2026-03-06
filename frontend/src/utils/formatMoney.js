/**
 * LooxGame Money Formatting Utility
 * ==================================
 * Centralized utility for consistent money formatting across the platform.
 * 
 * RULES:
 * - IDR: Integer only, no decimals, format thousands local (7.750.000)
 * - USD/USDT: 2 decimals fixed (12.50)
 * 
 * Usage:
 *   import { formatMoney, formatCompact, formatMoneyWithSign } from '@/utils/formatMoney';
 */

const ZERO_DECIMAL_CURRENCIES = ['IDR', 'JPY', 'KRW', 'VND'];

const CURRENCY_CONFIG = {
  IDR: { locale: 'id-ID', decimals: 0, symbol: 'Rp', compact: true },
  USD: { locale: 'en-US', decimals: 2, symbol: '$', compact: false },
  USDT: { locale: 'en-US', decimals: 2, symbol: 'USDT', compact: false },
};

/**
 * Check if currency uses zero decimals
 */
export const isZeroDecimalCurrency = (currency = 'IDR') => 
  ZERO_DECIMAL_CURRENCIES.includes(String(currency || 'IDR').toUpperCase());

/**
 * Normalize currency code to uppercase
 */
export const normalizeCurrency = (currency) => 
  String(currency || 'IDR').toUpperCase();

/**
 * Get currency configuration
 */
export const getCurrencyConfig = (currency = 'IDR') => {
  const normalized = normalizeCurrency(currency);
  return CURRENCY_CONFIG[normalized] || CURRENCY_CONFIG.IDR;
};

/**
 * Format money amount based on currency
 * 
 * @param {number|string} amount - The amount to format
 * @param {Object} options - Formatting options
 * @param {string} options.currency - Currency code (IDR, USD, USDT)
 * @param {boolean} options.showSymbol - Whether to show currency symbol
 * @param {string} options.locale - Override locale
 * @returns {string} Formatted money string
 * 
 * @example
 * formatMoney(7750000, { currency: 'IDR' }) // "Rp 7.750.000"
 * formatMoney(12.50, { currency: 'USD' }) // "$12.50"
 * formatMoney(1234.56, { currency: 'USDT' }) // "USDT 1,234.56"
 */
export const formatMoney = (amount, options = {}) => {
  const { 
    currency = 'IDR', 
    showSymbol = true,
    locale: overrideLocale,
    minimumFractionDigits,
    maximumFractionDigits
  } = options;

  // Handle invalid/null amounts
  if (amount === null || amount === undefined || amount === '' || Number.isNaN(Number(amount))) {
    return '-';
  }

  const numericAmount = Number(amount);
  const normalizedCurrency = normalizeCurrency(currency);
  const config = getCurrencyConfig(normalizedCurrency);
  const locale = overrideLocale || config.locale;

  // Determine decimal places based on currency
  const minDigits = minimumFractionDigits ?? config.decimals;
  const maxDigits = maximumFractionDigits ?? config.decimals;

  try {
    // Use Intl.NumberFormat for proper localization
    const formatter = new Intl.NumberFormat(locale, {
      style: showSymbol && normalizedCurrency !== 'USDT' ? 'currency' : 'decimal',
      currency: normalizedCurrency !== 'USDT' ? normalizedCurrency : undefined,
      minimumFractionDigits: minDigits,
      maximumFractionDigits: maxDigits,
    });

    const formatted = formatter.format(numericAmount);

    // Handle USDT special case (not a standard Intl currency)
    if (normalizedCurrency === 'USDT' && showSymbol) {
      return `USDT ${formatted}`;
    }

    return formatted;
  } catch (error) {
    // Fallback for unsupported currencies
    const formatted = new Intl.NumberFormat(locale, {
      minimumFractionDigits: minDigits,
      maximumFractionDigits: maxDigits,
    }).format(numericAmount);
    
    return showSymbol ? `${config.symbol} ${formatted}` : formatted;
  }
};

/**
 * Format money with compact notation for large IDR amounts
 * Useful for buttons and space-constrained UI
 * 
 * @example
 * formatCompact(7750000, 'IDR') // "7.75jt"
 * formatCompact(775000, 'IDR') // "775rb"
 * formatCompact(1234.56, 'USD') // "$1,234.56" (no compact for USD)
 */
export const formatCompact = (amount, currency = 'IDR') => {
  if (amount === null || amount === undefined || Number.isNaN(Number(amount))) {
    return '-';
  }

  const numericAmount = Number(amount);
  const normalizedCurrency = normalizeCurrency(currency);

  // Only apply compact notation for IDR
  if (normalizedCurrency === 'IDR') {
    const absAmount = Math.abs(numericAmount);
    const sign = numericAmount < 0 ? '-' : '';
    
    if (absAmount >= 1_000_000_000) {
      // Miliar (billion IDR)
      const value = absAmount / 1_000_000_000;
      return `${sign}${value.toFixed(value % 1 === 0 ? 0 : 2)}M`;
    }
    if (absAmount >= 1_000_000) {
      // Juta (million IDR)
      const value = absAmount / 1_000_000;
      return `${sign}${value.toFixed(value % 1 === 0 ? 0 : 2)}jt`;
    }
    if (absAmount >= 1_000) {
      // Ribu (thousand IDR)
      const value = absAmount / 1_000;
      return `${sign}${value.toFixed(value % 1 === 0 ? 0 : 0)}rb`;
    }
    return formatMoney(numericAmount, { currency: 'IDR', showSymbol: false });
  }

  // For USD/USDT, use standard formatting
  return formatMoney(numericAmount, { currency: normalizedCurrency });
};

/**
 * Format money with sign prefix (+/-)
 * Useful for transaction history
 * 
 * @example
 * formatMoneyWithSign(50000, { currency: 'IDR', isPositive: true }) // "+Rp 50.000"
 * formatMoneyWithSign(50000, { currency: 'IDR', isPositive: false }) // "-Rp 50.000"
 */
export const formatMoneyWithSign = (amount, options = {}) => {
  const { currency = 'IDR', isPositive = true } = options;
  const formatted = formatMoney(Math.abs(amount), { currency });
  const sign = isPositive ? '+' : '-';
  return `${sign}${formatted}`;
};

/**
 * Get preset label for deposit/withdraw buttons
 * IDR uses compact notation (7.75jt, 775rb)
 * 
 * @example
 * getPresetLabel(7750000, 'IDR') // "7.75jt"
 * getPresetLabel(100, 'USD') // "$100"
 */
export const getPresetLabel = (amount, currency = 'IDR') => {
  const normalizedCurrency = normalizeCurrency(currency);
  
  if (normalizedCurrency === 'IDR') {
    // Use Indonesian compact notation
    const absAmount = Math.abs(Number(amount));
    
    if (absAmount >= 1_000_000) {
      const juta = absAmount / 1_000_000;
      // Format without trailing zeros
      return `${juta % 1 === 0 ? juta : juta.toFixed(2).replace(/\.?0+$/, '')}jt`;
    }
    if (absAmount >= 1_000) {
      const ribu = absAmount / 1_000;
      return `${ribu % 1 === 0 ? ribu : ribu.toFixed(1).replace(/\.?0+$/, '')}rb`;
    }
    return `${absAmount}`;
  }

  // For USD/USDT, format normally but without "Rp" prefix
  return formatMoney(amount, { currency: normalizedCurrency, minimumFractionDigits: 0 });
};

/**
 * Truncate large number display with tooltip
 * Returns object with display value and full value for tooltip
 * 
 * @example
 * truncateForDisplay(12345678901234) 
 * // { display: "12.3T", full: "Rp 12.345.678.901.234", shouldTruncate: true }
 */
export const truncateForDisplay = (amount, currency = 'IDR') => {
  const full = formatMoney(amount, { currency });
  const numericAmount = Number(amount);
  
  // For very large numbers, use compact display
  const shouldTruncate = Math.abs(numericAmount) >= 1_000_000_000_000;
  
  if (!shouldTruncate) {
    return { display: full, full, shouldTruncate: false };
  }

  const display = formatCompact(amount, currency);
  return { display, full, shouldTruncate: true };
};

/**
 * CSS classes for money display to prevent overflow
 * Apply these to elements displaying money values
 */
export const moneyDisplayClasses = 'min-w-0 overflow-hidden text-ellipsis whitespace-nowrap';

/**
 * CSS classes for money container (flex parent)
 * Ensures children with money don't break layout
 */
export const moneyContainerClasses = 'flex items-center min-w-0';

export default {
  formatMoney,
  formatCompact,
  formatMoneyWithSign,
  getPresetLabel,
  truncateForDisplay,
  isZeroDecimalCurrency,
  normalizeCurrency,
  getCurrencyConfig,
  moneyDisplayClasses,
  moneyContainerClasses,
};

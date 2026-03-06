const DEFAULT_LOCALE = 'id-ID';
const DEFAULT_CURRENCY = 'IDR';
export const CURRENCY_CONVERSION_RATE = 16832.8;
const ZERO_DECIMAL_CURRENCIES = ['IDR', 'JPY', 'KRW', 'VND'];
const SUPPORTED_INTL_CURRENCIES =
  typeof Intl.supportedValuesOf === 'function' ? new Set(Intl.supportedValuesOf('currency')) : null;
const CURRENCY_DEFAULT_LOCALES = {
  IDR: 'id-ID',
  USD: 'en-US',
  USDT: 'en-US',
  PHP: 'en-PH',
  TRY: 'tr-TR',
};

const CURRENCY_MONEY_CONFIG = {
  IDR: {
    decimals: 0,
    minDeposit: 10000,
    maxDeposit: null,
    minWithdraw: 10000,
    maxWithdraw: 250000000,
    presetsDeposit: [775000, 1550000, 3875000, 7750000, 1000000, 2500000],
    presetsWithdraw: [775000, 1550000, 3875000, 7750000, 15500000],
  },
  USD: {
    decimals: 2,
    minDeposit: 10,
    maxDeposit: null,
    minWithdraw: 10,
    maxWithdraw: 10000,
    presetsDeposit: [50, 100, 250, 500, 1000, 2500],
    presetsWithdraw: [50, 100, 250, 500, 1000],
  },
  USDT: {
    decimals: 2,
    minDeposit: 10,
    maxDeposit: null,
    minWithdraw: 10,
    maxWithdraw: 10000,
    presetsDeposit: [50, 100, 250, 500, 1000, 2500],
    presetsWithdraw: [50, 100, 250, 500, 1000],
  },
  PHP: {
    decimals: 2,
    minDeposit: 100,
    maxDeposit: null,
    minWithdraw: 100,
    maxWithdraw: 500000,
    presetsDeposit: [500, 1000, 2500, 5000, 10000, 25000],
    presetsWithdraw: [500, 1000, 2500, 5000, 10000],
  },
  TRY: {
    decimals: 2,
    minDeposit: 100,
    maxDeposit: null,
    minWithdraw: 100,
    maxWithdraw: 500000,
    presetsDeposit: [500, 1000, 2500, 5000, 10000, 25000],
    presetsWithdraw: [500, 1000, 2500, 5000, 10000],
  },
};

const IDR_PRESET_LABELS = {
  775000: '775k',
  1550000: '1550k',
  3875000: '3875k',
  7750000: '7750k',
  1000000: '1jt',
  2500000: '2.5jt',
};

export const isZeroDecimalCurrency = (currency = DEFAULT_CURRENCY) =>
  ZERO_DECIMAL_CURRENCIES.includes(String(currency || '').toUpperCase());

const escapeRegExp = (value) => String(value).replace(/[.*+?^${}()|[\]\\]/g, '\\$&');

const toNumber = (value) => {
  if (value === null || value === undefined || value === '') return null;
  if (typeof value === 'number') return Number.isFinite(value) ? value : null;
  if (typeof value === 'string') {
    const normalized = value.trim().replace(/,/g, '');
    if (!normalized) return null;
    const parsed = Number(normalized);
    return Number.isFinite(parsed) ? parsed : null;
  }
  return null;
};

const supportsIntlCurrency = (currency) => {
  const normalizedCurrency = String(currency || '').toUpperCase();
  if (!normalizedCurrency) return false;

  if (SUPPORTED_INTL_CURRENCIES) {
    return SUPPORTED_INTL_CURRENCIES.has(normalizedCurrency);
  }

  try {
    new Intl.NumberFormat(DEFAULT_LOCALE, {
      style: 'currency',
      currency: normalizedCurrency,
    });
    return true;
  } catch {
    return false;
  }
};

const getBaseConfigForCurrency = (currency = DEFAULT_CURRENCY) => {
  const normalizedCurrency = String(currency || DEFAULT_CURRENCY).toUpperCase();
  return CURRENCY_MONEY_CONFIG[normalizedCurrency] || CURRENCY_MONEY_CONFIG[DEFAULT_CURRENCY];
};

export const getMoneyConfig = ({ currency = DEFAULT_CURRENCY, isDemoMode = false } = {}) => {
  const normalizedCurrency = String(currency || DEFAULT_CURRENCY).toUpperCase();
  const baseConfig = getBaseConfigForCurrency(normalizedCurrency);

  return {
    currency: normalizedCurrency,
    ...baseConfig,
    maxDeposit: isDemoMode ? null : baseConfig.maxDeposit,
    maxWithdraw: isDemoMode ? null : baseConfig.maxWithdraw,
  };
};

export const resolveLocaleCurrency = ({ tenantConfig, userPreference } = {}) => {
  const currency = userPreference?.currency || tenantConfig?.currency || DEFAULT_CURRENCY;
  const normalizedCurrency = String(currency).toUpperCase();

  const userLocale = userPreference?.locale;
  const tenantLocale = tenantConfig?.locale;
  const userCurrency = userPreference?.currency;
  const tenantCurrency = tenantConfig?.currency;

  const shouldUseCurrencyLocale =
    !userLocale &&
    Boolean(userCurrency) &&
    String(userCurrency).toUpperCase() !== String(tenantCurrency || DEFAULT_CURRENCY).toUpperCase();

  const locale =
    userLocale ||
    (shouldUseCurrencyLocale ? CURRENCY_DEFAULT_LOCALES[normalizedCurrency] : null) ||
    tenantLocale ||
    CURRENCY_DEFAULT_LOCALES[normalizedCurrency] ||
    DEFAULT_LOCALE;

  return { locale, currency: normalizedCurrency };
};

export const formatMoney = (
  amount,
  { currency = DEFAULT_CURRENCY, locale = DEFAULT_LOCALE, minimumFractionDigits, maximumFractionDigits } = {}
) => {
  const numeric = toNumber(amount);
  if (numeric === null) return '-';
  const normalizedCurrency = String(currency || DEFAULT_CURRENCY).toUpperCase();

  const minDigits = minimumFractionDigits ?? (isZeroDecimalCurrency(normalizedCurrency) ? 0 : 2);
  const maxDigits = maximumFractionDigits ?? minDigits;

  if (!supportsIntlCurrency(normalizedCurrency)) {
    const formattedNumber = new Intl.NumberFormat(locale, {
      minimumFractionDigits: minDigits,
      maximumFractionDigits: maxDigits,
    }).format(numeric);
    return `${normalizedCurrency} ${formattedNumber}`;
  }

  return new Intl.NumberFormat(locale, {
    style: 'currency',
    currency: normalizedCurrency,
    minimumFractionDigits: minDigits,
    maximumFractionDigits: maxDigits,
  }).format(numeric);
};

export const toDisplayMoney = (amount, conversionRate = CURRENCY_CONVERSION_RATE) => {
  const numeric = toNumber(amount);
  if (numeric === null) return null;
  return numeric * conversionRate;
};

export const convertAmount = (
  amount,
  {
    fromCurrency = DEFAULT_CURRENCY,
    toCurrency = DEFAULT_CURRENCY,
    conversionRate = CURRENCY_CONVERSION_RATE,
  } = {}
) => {
  const numeric = toNumber(amount);
  if (numeric === null) return null;

  const sourceCurrency = String(fromCurrency || DEFAULT_CURRENCY).toUpperCase();
  const targetCurrency = String(toCurrency || DEFAULT_CURRENCY).toUpperCase();
  const normalizedSourceCurrency = sourceCurrency === 'USDT' ? 'USD' : sourceCurrency;
  const normalizedTargetCurrency = targetCurrency === 'USDT' ? 'USD' : targetCurrency;

  if (sourceCurrency === targetCurrency) return numeric;

  let converted = numeric;

  if (normalizedSourceCurrency === normalizedTargetCurrency) {
    converted = numeric;
  } else if (normalizedSourceCurrency === 'IDR' && normalizedTargetCurrency === 'USD') {
    converted = numeric / conversionRate;
  } else if (normalizedSourceCurrency === 'USD' && normalizedTargetCurrency === 'IDR') {
    converted = numeric * conversionRate;
  }

  const { decimals } = getMoneyConfig({ currency: targetCurrency });
  if (decimals === 0) {
    return Math.round(converted);
  }

  const factor = 10 ** decimals;
  return Math.round((converted + Number.EPSILON) * factor) / factor;
};

export const DEFAULT_MONEY_CONFIG = {
  locale: DEFAULT_LOCALE,
  currency: DEFAULT_CURRENCY,
};

export const sanitizeMoneyInput = (input, locale = DEFAULT_LOCALE) => {
  if (input === null || input === undefined) return '';
  const raw = String(input).trim();
  if (!raw) return '';

  const isEnglish = String(locale).toLowerCase().startsWith('en');
  const thousandSep = isEnglish ? ',' : '.';
  const decimalSep = isEnglish ? '.' : ',';

  const escapedThousandSep = escapeRegExp(thousandSep);
  const escapedDecimalSep = escapeRegExp(decimalSep);

  let cleaned = raw
    .replace(new RegExp(`[^0-9${escapedThousandSep}${escapedDecimalSep}]`, 'g'), '')
    .replace(new RegExp(escapedThousandSep, 'g'), '');

  if (decimalSep !== '.') {
    cleaned = cleaned.replace(new RegExp(escapedDecimalSep, 'g'), '.');
  }

  const parts = cleaned.split('.');
  if (parts.length <= 1) return parts[0] || '';
  return `${parts[0]}.${parts.slice(1).join('')}`;
};

export const sanitizeMoneyInputByCurrency = (input, locale = DEFAULT_LOCALE, currency = DEFAULT_CURRENCY) => {
  const normalized = sanitizeMoneyInput(input, locale);
  if (!normalized) return '';

  const { decimals } = getMoneyConfig({ currency });
  if (decimals === 0) {
    return normalized.split('.')[0] || '';
  }

  const [integerPart = '', ...decimalParts] = normalized.split('.');
  if (!decimalParts.length) return integerPart;
  return `${integerPart}.${decimalParts.join('').slice(0, decimals)}`;
};

export const parseMoneyInputToNumber = (sanitizedInput, currency = DEFAULT_CURRENCY) => {
  if (sanitizedInput === '' || sanitizedInput === null || sanitizedInput === undefined) {
    return null;
  }

  const amount = Number(sanitizedInput);
  if (!Number.isFinite(amount)) return null;

  const { decimals } = getMoneyConfig({ currency });
  if (decimals === 0) {
    return Math.trunc(amount);
  }

  return amount;
};

export const normalizeSubmitAmount = (amountValue, currency = DEFAULT_CURRENCY) => {
  if (!Number.isFinite(amountValue) || amountValue <= 0) return null;

  const { decimals } = getMoneyConfig({ currency });
  if (decimals === 0) {
    return Number.isInteger(amountValue) ? amountValue : null;
  }

  const factor = 10 ** decimals;
  return Math.round((amountValue + Number.EPSILON) * factor) / factor;
};

export const getPresetLabel = (amount, currency, formatMoneyFn) => {
  if (currency === 'IDR') {
    if (IDR_PRESET_LABELS[amount]) return IDR_PRESET_LABELS[amount];

    if (amount >= 1000000) {
      return `${(amount / 1000000).toLocaleString('en-US', { maximumFractionDigits: 3 }).replace(/\.0+$/, '')}jt`;
    }

    return `${(amount / 1000).toLocaleString('en-US', { maximumFractionDigits: 0 })}k`;
  }

  return typeof formatMoneyFn === 'function'
    ? formatMoneyFn(amount, { minimumFractionDigits: 0, maximumFractionDigits: 2 })
    : amount.toString();
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
export const formatCompact = (amount, currency = DEFAULT_CURRENCY, locale = DEFAULT_LOCALE) => {
  const numeric = toNumber(amount);
  if (numeric === null) return '-';
  
  const normalizedCurrency = String(currency || DEFAULT_CURRENCY).toUpperCase();
  
  // Only apply compact notation for IDR
  if (normalizedCurrency === 'IDR') {
    const absAmount = Math.abs(numeric);
    const sign = numeric < 0 ? '-' : '';
    
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
      return `${sign}${value.toFixed(0)}rb`;
    }
    return formatMoney(numeric, { currency: 'IDR', locale });
  }
  
  // For USD/USDT, use standard formatting
  return formatMoney(numeric, { currency: normalizedCurrency, locale });
};

/**
 * CSS classes for money display to prevent overflow
 * Apply these to elements displaying money values
 */
export const MONEY_DISPLAY_CLASSES = 'min-w-0 overflow-hidden text-ellipsis whitespace-nowrap tabular-nums';

/**
 * CSS classes for money container (flex parent)
 * Ensures children with money don't break layout
 */
export const MONEY_CONTAINER_CLASSES = 'flex items-center min-w-0';

/**
 * Truncate large number display with tooltip
 * Returns object with display value and full value for tooltip
 */
export const truncateForDisplay = (amount, currency = DEFAULT_CURRENCY, locale = DEFAULT_LOCALE) => {
  const full = formatMoney(amount, { currency, locale });
  const numeric = toNumber(amount);
  
  if (numeric === null) {
    return { display: '-', full: '-', shouldTruncate: false };
  }
  
  // For very large numbers, use compact display
  const shouldTruncate = Math.abs(numeric) >= 1_000_000_000;
  
  if (!shouldTruncate) {
    return { display: full, full, shouldTruncate: false };
  }
  
  const display = formatCompact(amount, currency, locale);
  return { display, full, shouldTruncate: true };
};

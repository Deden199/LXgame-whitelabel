import {
  CURRENCY_CONVERSION_RATE,
  convertAmount,
  formatMoney,
  getMoneyConfig,
  getPresetLabel,
  normalizeSubmitAmount,
  parseMoneyInputToNumber,
  sanitizeMoneyInput,
  sanitizeMoneyInputByCurrency,
  resolveLocaleCurrency,
} from './currency';

describe('formatMoney', () => {
  test('1000 -> Rp 1.000', () => {
    expect(formatMoney(1000, { locale: 'id-ID', currency: 'IDR' })).toBe('Rp 1.000');
  });

  test('38758990 -> Rp 38.758.990', () => {
    expect(formatMoney(38758990, { locale: 'id-ID', currency: 'IDR' })).toBe('Rp 38.758.990');
  });

  test('"15000" -> Rp 15.000', () => {
    expect(formatMoney('15000', { locale: 'id-ID', currency: 'IDR' })).toBe('Rp 15.000');
  });

  test('null -> -', () => {
    expect(formatMoney(null, { locale: 'id-ID', currency: 'IDR' })).toBe('-');
  });

  test('USD en-US -> $15,000.00', () => {
    expect(formatMoney(15000, { locale: 'en-US', currency: 'USD' })).toBe('$15,000.00');
  });

  test('USDT falls back to currency code formatting when Intl currency code is unsupported', () => {
    expect(formatMoney(15000, { locale: 'en-US', currency: 'USDT' })).toBe('USDT 15,000.00');
  });
});



describe('convertAmount', () => {
  test('converts IDR to USD using conversion rate', () => {
    expect(convertAmount(CURRENCY_CONVERSION_RATE, { fromCurrency: 'IDR', toCurrency: 'USD' })).toBe(1);
  });

  test('converts USD to IDR using conversion rate and rounds for IDR', () => {
    expect(convertAmount(10.5, { fromCurrency: 'USD', toCurrency: 'IDR' })).toBe(176744);
  });

  test('returns unchanged amount for same currency', () => {
    expect(convertAmount(250, { fromCurrency: 'USD', toCurrency: 'USD' })).toBe(250);
  });

  test('treats USDT equivalent to USD for conversion to IDR', () => {
    expect(convertAmount(1, { fromCurrency: 'USDT', toCurrency: 'IDR' })).toBe(16833);
  });

  test('treats USD equivalent to USDT for conversion from IDR', () => {
    expect(convertAmount(CURRENCY_CONVERSION_RATE, { fromCurrency: 'IDR', toCurrency: 'USDT' })).toBe(1);
  });
});



describe('resolveLocaleCurrency', () => {
  test('uses currency default locale when user only changes currency from tenant default', () => {
    expect(
      resolveLocaleCurrency({
        tenantConfig: { locale: 'id-ID', currency: 'IDR' },
        userPreference: { currency: 'USD' },
      })
    ).toEqual({ locale: 'en-US', currency: 'USD' });
  });

  test('keeps explicit user locale when provided', () => {
    expect(
      resolveLocaleCurrency({
        tenantConfig: { locale: 'id-ID', currency: 'IDR' },
        userPreference: { locale: 'id-ID', currency: 'USD' },
      })
    ).toEqual({ locale: 'id-ID', currency: 'USD' });
  });
});

describe('sanitizeMoneyInput', () => {
  test('id-ID 10.000 -> 10000', () => {
    expect(sanitizeMoneyInput('10.000', 'id-ID')).toBe('10000');
  });

  test('en-US 10,000 -> 10000', () => {
    expect(sanitizeMoneyInput('10,000', 'en-US')).toBe('10000');
  });
});

describe('sanitizeMoneyInputByCurrency', () => {
  test('IDR removes decimal separator', () => {
    expect(sanitizeMoneyInputByCurrency('10.000,50', 'id-ID', 'IDR')).toBe('10000');
  });

  test('USD keeps max two decimals', () => {
    expect(sanitizeMoneyInputByCurrency('100.5678', 'en-US', 'USD')).toBe('100.56');
  });
});

describe('parseMoneyInputToNumber', () => {
  test('IDR returns integer', () => {
    expect(parseMoneyInputToNumber('1000.88', 'IDR')).toBe(1000);
  });

  test('USD returns decimal', () => {
    expect(parseMoneyInputToNumber('100.5', 'USD')).toBe(100.5);
  });
});

describe('normalizeSubmitAmount', () => {
  test('IDR requires integer', () => {
    expect(normalizeSubmitAmount(1000.25, 'IDR')).toBeNull();
  });

  test('USD rounds to two decimal', () => {
    expect(normalizeSubmitAmount(250.005, 'USD')).toBe(250.01);
  });
});


describe('getMoneyConfig', () => {
  test('IDR deposit presets use integer rupiah values', () => {
    const config = getMoneyConfig({ currency: 'IDR', isDemoMode: false });
    expect(config.presetsDeposit).toEqual([775000, 1550000, 3875000, 7750000, 1000000, 2500000]);
  });

  test('demo mode removes max limits', () => {
    const config = getMoneyConfig({ currency: 'IDR', isDemoMode: true });
    expect(config.maxDeposit).toBeNull();
    expect(config.maxWithdraw).toBeNull();
  });

  test('USD keeps 2 decimals presets and no hard max deposit', () => {
    const config = getMoneyConfig({ currency: 'USD', isDemoMode: false });
    expect(config.decimals).toBe(2);
    expect(config.presetsDeposit).toContain(250);
    expect(config.maxDeposit).toBeNull();
  });
});


describe('getPresetLabel', () => {
  test('uses expected IDR shorthand labels for wallet presets', () => {
    expect(getPresetLabel(775000, 'IDR')).toBe('775k');
    expect(getPresetLabel(1550000, 'IDR')).toBe('1550k');
    expect(getPresetLabel(3875000, 'IDR')).toBe('3875k');
    expect(getPresetLabel(7750000, 'IDR')).toBe('7750k');
    expect(getPresetLabel(1000000, 'IDR')).toBe('1jt');
    expect(getPresetLabel(2500000, 'IDR')).toBe('2.5jt');
  });
});

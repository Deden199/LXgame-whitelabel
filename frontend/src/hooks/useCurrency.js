import { useMemo } from 'react';
import { useAuth } from '../context/AuthContext';
import {
  convertAmount,
  formatMoney,
  formatCompact,
  getMoneyConfig,
  parseMoneyInputToNumber,
  resolveLocaleCurrency,
  sanitizeMoneyInputByCurrency,
  truncateForDisplay,
  MONEY_DISPLAY_CLASSES,
  MONEY_CONTAINER_CLASSES,
} from '../lib/currency';

const readTenantConfig = (tenant) => ({
  locale: tenant?.config?.locale || tenant?.settings?.locale || tenant?.locale,
  currency: tenant?.config?.currency || tenant?.settings?.currency || tenant?.currency,
});

const readUserPreference = (user) => ({
  locale: user?.preferences?.locale || user?.locale,
  currency: user?.preferred_currency || user?.preferences?.currency || user?.currency,
});

const resolveDemoMode = ({ tenant, user }) => {
  const explicitMode = [
    tenant?.mode,
    tenant?.app_mode,
    tenant?.config?.mode,
    tenant?.settings?.mode,
    user?.mode,
    user?.preferences?.mode,
  ].find((value) => typeof value === 'string');

  if (explicitMode) return explicitMode.toLowerCase() === 'demo';

  const explicitFlag = [
    tenant?.is_demo,
    tenant?.demo_mode,
    tenant?.config?.is_demo,
    tenant?.settings?.is_demo,
    user?.is_demo,
    user?.demo_mode,
  ].find((value) => typeof value === 'boolean');

  if (typeof explicitFlag === 'boolean') return explicitFlag;

  return true;
};

export const useCurrency = () => {
  const { tenant, user } = useAuth();

  const moneyContext = useMemo(() => {
    const localeCurrency = resolveLocaleCurrency({ tenantConfig: readTenantConfig(tenant), userPreference: readUserPreference(user) });
    const isDemoMode = resolveDemoMode({ tenant, user });
    return {
      ...localeCurrency,
      isDemoMode,
      moneyConfig: getMoneyConfig({ currency: localeCurrency.currency, isDemoMode }),
    };
  }, [tenant, user]);

  const formatAppMoney = (amount, options = {}) => formatMoney(amount, { ...moneyContext, ...options });


  const walletBaseCurrency = String(readTenantConfig(tenant)?.currency || 'IDR').toUpperCase();

  const convertFromWalletCurrency = (amount, options = {}) =>
    convertAmount(amount, {
      fromCurrency: walletBaseCurrency,
      toCurrency: options.toCurrency || moneyContext.currency,
      conversionRate: options.conversionRate,
    });

  const convertToWalletCurrency = (amount, options = {}) =>
    convertAmount(amount, {
      fromCurrency: options.fromCurrency || moneyContext.currency,
      toCurrency: walletBaseCurrency,
      conversionRate: options.conversionRate,
    });

  const formatWalletMoney = (amount, options = {}) => {
    const converted = convertFromWalletCurrency(amount, options);

    return formatMoney(converted, { ...moneyContext, ...options });
  };
  const sanitizeMoneyInput = (input) => sanitizeMoneyInputByCurrency(input, moneyContext.locale, moneyContext.currency);
  const parseInputToNumber = (sanitizedInput) => parseMoneyInputToNumber(sanitizedInput, moneyContext.currency);

  return {
    ...moneyContext,
    formatAppMoney,
    formatWalletMoney,
    formatCompact: (amount, opts = {}) => formatCompact(amount, opts.currency || moneyContext.currency, moneyContext.locale),
    truncateForDisplay: (amount, opts = {}) => truncateForDisplay(amount, opts.currency || moneyContext.currency, moneyContext.locale),
    convertFromWalletCurrency,
    convertToWalletCurrency,
    walletBaseCurrency,
    sanitizeMoneyInput,
    parseMoneyInputToNumber: parseInputToNumber,
    MONEY_DISPLAY_CLASSES,
    MONEY_CONTAINER_CLASSES,
  };
};

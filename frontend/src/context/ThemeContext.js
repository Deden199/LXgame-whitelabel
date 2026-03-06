import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const THEME_PRESETS = {
  royal_gold: {
    name: 'Royal Gold',
    mode: 'dark',
    icon: 'Crown',
    description: 'Luxurious dark theme with golden accents'
  },
  midnight_blue: {
    name: 'Midnight Blue',
    mode: 'dark',
    icon: 'Waves',
    description: 'Deep blue theme with cyan highlights'
  },
  emerald_green: {
    name: 'Emerald Green',
    mode: 'dark',
    icon: 'Gem',
    description: 'Rich green theme for a natural feel'
  },
  crimson_red: {
    name: 'Crimson Red',
    mode: 'dark',
    icon: 'Flame',
    description: 'Bold red theme with intensity'
  },
  purple_night: {
    name: 'Purple Night',
    mode: 'dark',
    icon: 'Moon',
    description: 'Mystical purple theme'
  },
  light_professional: {
    name: 'Light Professional',
    mode: 'light',
    icon: 'Sun',
    description: 'Clean light theme for business'
  }
};

const ThemeContext = createContext(undefined);

export const ThemeProvider = ({ children, defaultTheme = 'royal_gold' }) => {
  const [theme, setThemeState] = useState(defaultTheme);
  const [customColors, setCustomColors] = useState(null);

  useEffect(() => {
    // Apply theme class to document
    const root = document.documentElement;
    
    // Remove all theme classes
    Object.keys(THEME_PRESETS).forEach(key => {
      root.classList.remove(`theme-${key}`);
    });
    
    // Add current theme class
    root.classList.add(`theme-${theme}`);
    
    // Apply custom colors if set
    if (customColors) {
      if (customColors.primary) {
        root.style.setProperty('--primary', customColors.primary);
      }
      if (customColors.accent) {
        root.style.setProperty('--accent', customColors.accent);
      }
    } else {
      root.style.removeProperty('--primary');
      root.style.removeProperty('--accent');
    }
  }, [theme, customColors]);

  const setTheme = useCallback((newTheme) => {
    if (THEME_PRESETS[newTheme]) {
      setThemeState(newTheme);
      setCustomColors(null);
    }
  }, []);

  const applyCustomColors = (colors) => {
    setCustomColors(colors);
  };

  const resetCustomColors = () => {
    setCustomColors(null);
  };

  const value = {
    theme,
    setTheme,
    themePresets: THEME_PRESETS,
    currentPreset: THEME_PRESETS[theme],
    customColors,
    applyCustomColors,
    resetCustomColors,
    isDark: THEME_PRESETS[theme]?.mode === 'dark'
  };

  return (
    <ThemeContext.Provider value={value}>
      {children}
    </ThemeContext.Provider>
  );
};

export const useTheme = () => {
  const context = useContext(ThemeContext);
  if (context === undefined) {
    throw new Error('useTheme must be used within a ThemeProvider');
  }
  return context;
};

export { THEME_PRESETS };

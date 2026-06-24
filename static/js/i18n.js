(function (global) {
  function createI18n(strings) {
    const catalog = strings || {};

    function t(key, vars) {
      let text = catalog[key] ?? key;
      if (!vars) return text;
      return Object.keys(vars).reduce((result, name) => {
        const value = vars[name];
        return result.replaceAll(`{${name}}`, String(value));
      }, text);
    }

    function list(key) {
      const values = [];
      for (let i = 0; i < 100; i += 1) {
        const item = catalog[`${key}.${i}`];
        if (item === undefined) break;
        values.push(item);
      }
      if (values.length) return values;
      const direct = catalog[key];
      return Array.isArray(direct) ? direct : [];
    }

    function dateLocale() {
      return catalog["meta.date_locale"] || "en-US";
    }

    function formatNumber(value) {
      return Number(value).toLocaleString(dateLocale());
    }

    return { t, list, dateLocale, formatNumber, catalog };
  }

  global.I18n = createI18n(global.__I18N__ || {});
})(typeof window !== "undefined" ? window : globalThis);

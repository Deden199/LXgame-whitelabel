import React, { useEffect, useState } from 'react';
import { Helmet } from 'react-helmet-async';
import { useAuth } from '../context/AuthContext';

// Default SEO values
const DEFAULT_TITLE = 'LooxGame – Gaming Platform';
const DEFAULT_DESC = 'Premium gaming platform with seamless wallet architecture.';
const DEFAULT_KEYWORDS = 'casino, slots, gaming, online';

/**
 * Dynamic SEO component that fetches tenant meta settings
 * and injects them into the document head
 */
export const SEOHead = () => {
  const { tenant, api } = useAuth();
  const [meta, setMeta] = useState(null);
  const [loaded, setLoaded] = useState(false);

  useEffect(() => {
    const fetchMeta = async () => {
      if (tenant?.id && api) {
        try {
          const res = await api.get('/tenant-meta/' + tenant.id);
          setMeta(res.data);
        } catch (err) {
          // Silent fail - use defaults
        }
      }
      setLoaded(true);
    };

    // Only fetch if we have tenant, otherwise just mark as loaded
    if (tenant?.id) {
      fetchMeta();
    } else {
      setLoaded(true);
    }
  }, [tenant?.id, api]);

  // Build safe string values
  const seo = meta?.seo || {};
  const branding = meta?.branding || {};
  const tenantName = String(meta?.tenant_name || tenant?.name || 'LooxGame');

  // Use defaults if values are empty/null
  const title = (seo.meta_title && String(seo.meta_title).trim()) || (tenantName + ' – Gaming Platform') || DEFAULT_TITLE;
  const description = (seo.meta_description && String(seo.meta_description).trim()) || DEFAULT_DESC;
  const keywords = (seo.meta_keywords && String(seo.meta_keywords).trim()) || DEFAULT_KEYWORDS;
  const ogTitle = (seo.og_title && String(seo.og_title).trim()) || title;
  const ogDescription = (seo.og_description && String(seo.og_description).trim()) || description;
  const robotsContent = seo.robots_index !== false ? 'index, follow' : 'noindex, nofollow';

  // Don't render until loaded to avoid empty title error
  if (!loaded) {
    return (
      <Helmet>
        <title>{DEFAULT_TITLE}</title>
      </Helmet>
    );
  }

  return (
    <Helmet>
      <title>{title || DEFAULT_TITLE}</title>
      <meta name="description" content={description || DEFAULT_DESC} />
      <meta name="keywords" content={keywords || DEFAULT_KEYWORDS} />
      <meta name="robots" content={robotsContent} />
      <meta property="og:type" content="website" />
      <meta property="og:title" content={ogTitle || DEFAULT_TITLE} />
      <meta property="og:description" content={ogDescription || DEFAULT_DESC} />
      <meta property="og:site_name" content={tenantName || 'LooxGame'} />
      {seo.og_image_url && <meta property="og:image" content={String(seo.og_image_url)} />}
      <meta name="twitter:card" content="summary_large_image" />
      <meta name="twitter:title" content={ogTitle || DEFAULT_TITLE} />
      <meta name="twitter:description" content={ogDescription || DEFAULT_DESC} />
      {seo.og_image_url && <meta name="twitter:image" content={String(seo.og_image_url)} />}
      {seo.canonical_base_url && <link rel="canonical" href={String(seo.canonical_base_url)} />}
      {seo.favicon_url && <link rel="icon" href={String(seo.favicon_url)} />}
      {branding?.primary_color && <meta name="theme-color" content={String(branding.primary_color)} />}
    </Helmet>
  );
};

/**
 * Custom HTML injection component
 */
export const CustomHTMLInjector = () => {
  const { tenant, api } = useAuth();
  const [customHeader, setCustomHeader] = useState(null);

  useEffect(() => {
    const fetchCustomHeader = async () => {
      if (tenant?.id && api) {
        try {
          const res = await api.get('/tenant-meta/' + tenant.id);
          if (res.data?.custom_header?.enable_custom_html) {
            setCustomHeader(res.data.custom_header);
          }
        } catch (err) {
          // Silent fail
        }
      }
    };

    fetchCustomHeader();
  }, [tenant?.id, api]);

  useEffect(() => {
    if (customHeader?.enable_custom_html && customHeader?.custom_head_html) {
      const tempDiv = document.createElement('div');
      tempDiv.innerHTML = customHeader.custom_head_html;
      
      const scripts = tempDiv.querySelectorAll('script, link, style');
      scripts.forEach(el => {
        const newEl = el.cloneNode(true);
        newEl.setAttribute('data-custom-injection', 'true');
        document.head.appendChild(newEl);
      });
    }

    return () => {
      document.querySelectorAll('[data-custom-injection="true"]').forEach(el => el.remove());
    };
  }, [customHeader]);

  if (customHeader?.enable_custom_html && customHeader?.custom_body_html) {
    return (
      <div 
        id="custom-body-injection"
        dangerouslySetInnerHTML={{ __html: customHeader.custom_body_html }}
      />
    );
  }

  return null;
};

export default SEOHead;

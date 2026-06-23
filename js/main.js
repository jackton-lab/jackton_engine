/**
 * JACKTON REAL ESTATE — HUB
 * main.js | v1.0
 *
 * Minimal JS: hanya untuk enhanced interactions.
 * Tidak ada fetch, tidak ada form, tidak ada backend.
 */

(function () {
  'use strict';

  /* ── PAGE LOAD — trigger animasi setelah DOM ready ─── */
  document.addEventListener('DOMContentLoaded', function () {
    const loader = document.getElementById('intro-loader');
    const ctaCards = document.querySelectorAll('.cta-card');
    
    // Hide loader and play entry animations after 2500ms
    setTimeout(function () {
      if (loader) {
        loader.classList.add('fade-out');
        loader.addEventListener('transitionend', function () {
          loader.remove();
        });
      }
      document.body.classList.add('loaded');
    }, 2500);

    /* Staggered card entry animation fallback */
    const animatedEls = document.querySelectorAll('.animate-fade-up');
    animatedEls.forEach(function (el) {
      el.style.visibility = 'visible';
    });

    /* ── SCROLL REVEAL OBSERVER FOR CTA CARDS ─── */
    if ('IntersectionObserver' in window) {
      const ctaSection = document.querySelector('.cta-section');
      if (ctaSection) {
        const observer = new IntersectionObserver(function (entries) {
          entries.forEach(function (entry) {
            if (entry.isIntersecting) {
              ctaSection.classList.add('in-view');
              observer.unobserve(entry.target);
            }
          });
        }, {
          threshold: 0.15
        });
        observer.observe(ctaSection);
      }
    } else {
      // Fallback if IntersectionObserver is not supported
      const ctaSection = document.querySelector('.cta-section');
      if (ctaSection) {
        ctaSection.classList.add('in-view');
      }
    }

    /* CTA card click & keyboard accessibility */
    const ctaBuyer = document.getElementById('cta-buyer');
    if (ctaBuyer) {
      ctaBuyer.addEventListener('click', function (e) {
        if (e.target.closest('.tier-link')) {
          return;
        }
        const isExpanded = ctaBuyer.classList.toggle('show-tiers');
        ctaBuyer.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
      });
    }

    ctaCards.forEach(function (card) {
      card.addEventListener('keydown', function (e) {
        if (e.target.closest('a')) {
          return;
        }
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          const href = card.getAttribute('href');
          if (href) {
            window.location.href = href;
          } else if (card.id === 'cta-buyer') {
            const isExpanded = card.classList.toggle('show-tiers');
            card.setAttribute('aria-expanded', isExpanded ? 'true' : 'false');
          }
        }
      });
    });

    /* Subtle parallax tilt on CTA cards (desktop only) */
    if (window.matchMedia('(hover: hover) and (pointer: fine)').matches) {
      ctaCards.forEach(function (card) {
        card.addEventListener('mousemove', function (e) {
          if (card.classList.contains('show-tiers')) {
            card.style.transform = '';
            card.style.transformOrigin = '';
            return;
          }
          const rect = card.getBoundingClientRect();
          const x = (e.clientX - rect.left) / rect.width - 0.5;
          const y = (e.clientY - rect.top) / rect.height - 0.5;
          const rotateX = (-y * 4).toFixed(2);
          const rotateY = (x * 4).toFixed(2);
          card.style.transform =
            'translateY(-5px) rotateX(' + rotateX + 'deg) rotateY(' + rotateY + 'deg)';
          card.style.transformOrigin = 'center center';
        });

        card.addEventListener('mouseleave', function () {
          card.style.transform = '';
          card.style.transformOrigin = '';
        });
      });
    }

    /* ── YOUTUBE LITE FACADE ─── */
    var ytFacade = document.getElementById('yt-facade');
    if (ytFacade) {
      function loadYouTube() {
        var iframe = document.createElement('iframe');
        iframe.src = 'https://www.youtube.com/embed/uC-W9Gh2E0Y?autoplay=1';
        iframe.title = 'Jackton Real Estate - Video Pengenalan';
        iframe.frameBorder = '0';
        iframe.allow = 'accelerometer; autoplay; clipboard-write; encrypted-media; gyroscope; picture-in-picture; web-share';
        iframe.referrerPolicy = 'strict-origin-when-cross-origin';
        iframe.allowFullscreen = true;
        iframe.style.cssText = 'position:absolute;inset:0;width:100%;height:100%;border:none;display:block;';
        ytFacade.textContent = '';
        ytFacade.appendChild(iframe);
        ytFacade.removeAttribute('role');
        ytFacade.removeAttribute('tabindex');
        ytFacade.removeAttribute('aria-label');
      }
      ytFacade.addEventListener('click', loadYouTube);
      ytFacade.addEventListener('keydown', function (e) {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault();
          loadYouTube();
        }
      });
    }

  });

})();

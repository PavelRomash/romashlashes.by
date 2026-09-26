(() => {
  const header = document.getElementById('header');
  const progress = document.getElementById('scrollProgress');
  const reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;

  const onScroll = () => {
    const y = window.scrollY;
    header?.classList.toggle('scrolled', y > 24);
    if (progress) {
      const max = document.documentElement.scrollHeight - window.innerHeight;
      progress.style.width = `${max > 0 ? Math.min(100, (y / max) * 100) : 0}%`;
    }

    if (!reduceMotion) {
      document.querySelectorAll('[data-parallax]').forEach(el => {
        const rect = el.getBoundingClientRect();
        const factor = Number(el.dataset.parallax || 0);
        const offset = (window.innerHeight / 2 - (rect.top + rect.height / 2)) * factor;
        el.style.transform = `translate3d(0, ${offset}px, 0)`;
      });
    }
  };
  window.addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  const reveals = document.querySelectorAll('.reveal');
  if (reduceMotion || !('IntersectionObserver' in window)) {
    reveals.forEach(el => el.classList.add('is-visible'));
  } else {
    const observer = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          entry.target.classList.add('is-visible');
          observer.unobserve(entry.target);
        }
      });
    }, { threshold: 0.12, rootMargin: '0px 0px -5% 0px' });
    reveals.forEach(el => observer.observe(el));
  }

  const year = document.getElementById('year');
  if (year) year.textContent = new Date().getFullYear();

  // Portfolio videos are only loaded when they approach the viewport.
  document.querySelectorAll('[data-autoplay-video]').forEach(video => {
    const loadVideo = () => {
      const source = video.querySelector('source[data-src]');
      if (source?.dataset.src && !source.hasAttribute('src')) {
        source.src = source.dataset.src;
        video.load();
      }
    };

    if (!('IntersectionObserver' in window)) {
      loadVideo();
      if (!reduceMotion) video.play().catch(() => {});
      return;
    }

    const videoObserver = new IntersectionObserver(entries => {
      entries.forEach(entry => {
        if (entry.isIntersecting) {
          loadVideo();
          if (!reduceMotion) video.play().catch(() => {});
        } else {
          video.pause();
        }
      });
    }, { rootMargin: '180px 0px', threshold: 0.15 });
    videoObserver.observe(video);
  });

  const lightbox = document.getElementById('lightbox');
  const lightboxImage = document.getElementById('lightboxImage');
  const lightboxVideo = document.getElementById('lightboxVideo');
  const lightboxTitle = document.getElementById('lightboxTitle');
  const lightboxClose = document.querySelector('.lightbox-close');

  const resetLightboxMedia = () => {
    if (lightboxImage) {
      lightboxImage.classList.remove('active');
      lightboxImage.removeAttribute('src');
    }
    if (lightboxVideo) {
      lightboxVideo.pause();
      lightboxVideo.classList.remove('active');
      lightboxVideo.removeAttribute('src');
      lightboxVideo.removeAttribute('poster');
      lightboxVideo.load();
    }
  };

  const closeLightbox = () => {
    lightbox?.classList.remove('open');
    lightbox?.setAttribute('aria-hidden', 'true');
    document.body.classList.remove('lightbox-open');
    setTimeout(resetLightboxMedia, 180);
  };

  document.querySelectorAll('[data-lightbox]').forEach(card => {
    card.addEventListener('click', () => {
      const source = card.dataset.lightbox;
      const media = card.dataset.media || 'image';
      resetLightboxMedia();

      if (media === 'video' && lightboxVideo) {
        lightboxVideo.src = source;
        if (card.dataset.poster) lightboxVideo.poster = card.dataset.poster;
        lightboxVideo.classList.add('active');
        lightboxVideo.play().catch(() => {});
      } else if (lightboxImage) {
        lightboxImage.src = source;
        lightboxImage.classList.add('active');
      }

      if (lightboxTitle) lightboxTitle.textContent = card.dataset.title || '';
      lightbox?.classList.add('open');
      lightbox?.setAttribute('aria-hidden', 'false');
      document.body.classList.add('lightbox-open');
    });
  });

  lightboxClose?.addEventListener('click', closeLightbox);
  lightbox?.addEventListener('click', e => { if (e.target === lightbox) closeLightbox(); });
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeLightbox(); });

})();
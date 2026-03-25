/* ============================================
   FairClaims.us — Main JavaScript
   Scroll animations, navigation, form handling
   ============================================ */

document.addEventListener('DOMContentLoaded', () => {
  // --- Mobile Navigation Toggle ---
  const toggle = document.querySelector('.navbar__toggle');
  const mobileMenu = document.querySelector('.navbar__mobile');

  if (toggle && mobileMenu) {
    toggle.addEventListener('click', () => {
      mobileMenu.classList.toggle('active');
      toggle.classList.toggle('active');
    });

    // Close mobile menu when a link is clicked
    mobileMenu.querySelectorAll('a').forEach(link => {
      link.addEventListener('click', () => {
        mobileMenu.classList.remove('active');
        toggle.classList.remove('active');
      });
    });
  }

  // --- Scroll-Triggered Fade-In Animations ---
  const fadeElements = document.querySelectorAll('.fade-in');

  const observerOptions = {
    root: null,
    rootMargin: '0px 0px -60px 0px',
    threshold: 0.1
  };

  const fadeObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        entry.target.classList.add('visible');
        fadeObserver.unobserve(entry.target);
      }
    });
  }, observerOptions);

  fadeElements.forEach(el => fadeObserver.observe(el));

  // --- Animated Stat Counters ---
  const statNumbers = document.querySelectorAll('.stat-block__number[data-target]');

  const counterObserver = new IntersectionObserver((entries) => {
    entries.forEach(entry => {
      if (entry.isIntersecting) {
        animateCounter(entry.target);
        counterObserver.unobserve(entry.target);
      }
    });
  }, { threshold: 0.5 });

  statNumbers.forEach(el => counterObserver.observe(el));

  function animateCounter(el) {
    const target = el.getAttribute('data-target');
    const prefix = el.getAttribute('data-prefix') || '';
    const suffix = el.getAttribute('data-suffix') || '';
    const targetNum = parseFloat(target);
    const duration = 1500;
    const startTime = performance.now();

    function update(currentTime) {
      const elapsed = currentTime - startTime;
      const progress = Math.min(elapsed / duration, 1);
      const eased = 1 - Math.pow(1 - progress, 3);
      const current = targetNum * eased;

      if (Number.isInteger(targetNum)) {
        el.textContent = prefix + Math.round(current).toLocaleString() + suffix;
      } else {
        el.textContent = prefix + current.toFixed(1) + suffix;
      }

      if (progress < 1) {
        requestAnimationFrame(update);
      }
    }

    requestAnimationFrame(update);
  }

  // --- Navbar Background on Scroll ---
  const navbar = document.querySelector('.navbar');
  if (navbar) {
    window.addEventListener('scroll', () => {
      if (window.scrollY > 50) {
        navbar.style.background = 'rgba(11, 29, 58, 0.98)';
      } else {
        navbar.style.background = 'rgba(11, 29, 58, 0.95)';
      }
    });
  }

  // --- Smooth Scroll for Anchor Links ---
  document.querySelectorAll('a[href^="#"]').forEach(anchor => {
    anchor.addEventListener('click', function (e) {
      const targetId = this.getAttribute('href');
      if (targetId === '#') return;
      const targetEl = document.querySelector(targetId);
      if (targetEl) {
        e.preventDefault();
        const offset = 80;
        const targetPosition = targetEl.getBoundingClientRect().top + window.scrollY - offset;
        window.scrollTo({ top: targetPosition, behavior: 'smooth' });
      }
    });
  });

  // --- Form Submission (Get Started Page) ---
  const intakeForm = document.getElementById('intake-form');
  if (intakeForm) {
    intakeForm.addEventListener('submit', (e) => {
      e.preventDefault();
      const formData = new FormData(intakeForm);
      const data = Object.fromEntries(formData.entries());
      console.log('FairClaims Intake Submission:', data);

      // Show success message
      const successMsg = document.createElement('div');
      successMsg.style.cssText = 'background: #3A8A6A; color: white; padding: 1.5rem; border-radius: 8px; text-align: center; margin-top: 1.5rem; font-family: var(--font-ui);';
      successMsg.innerHTML = '<strong>Thank you!</strong> A FairClaims Navigator will reach out within 48 hours.';
      intakeForm.parentNode.insertBefore(successMsg, intakeForm.nextSibling);
      intakeForm.reset();
      intakeForm.style.display = 'none';
    });
  }
});

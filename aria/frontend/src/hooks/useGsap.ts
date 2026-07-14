/**
 * useGsap — Reusable GSAP animation hooks for the Aria Dashboard
 */
import { useEffect, useRef } from 'react';
import gsap from 'gsap';
import { ScrollTrigger } from 'gsap/ScrollTrigger';

gsap.registerPlugin(ScrollTrigger);

// ── Page entrance: fade + slide up ────────────────────────────────────────────
export function usePageEntrance() {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const ctx = gsap.context(() => {
      gsap.fromTo(
        el,
        { opacity: 0, y: 24 },
        { opacity: 1, y: 0, duration: 0.5, ease: 'power3.out' }
      );
    }, el);

    return () => ctx.revert();
  }, []);

  return ref;
}

// ── Stagger children: fade + slide up ─────────────────────────────────────────
export function useStaggerEntrance(selector = '.stagger-item', delay = 0) {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const ctx = gsap.context(() => {
      const items = el.querySelectorAll(selector);
      if (items.length === 0) return;
      gsap.fromTo(
        items,
        { opacity: 0, y: 20 },
        {
          opacity: 1,
          y: 0,
          duration: 0.45,
          ease: 'power2.out',
          stagger: 0.08,
          delay,
        }
      );
    }, el);

    return () => ctx.revert();
  }, [selector, delay]);

  return ref;
}

// ── Counter animation for numeric stat cards ──────────────────────────────────
export function useCountUp(target: number, duration = 1.2) {
  const ref = useRef<HTMLSpanElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el || isNaN(target)) return;

    const obj = { val: 0 };
    const ctx = gsap.context(() => {
      gsap.to(obj, {
        val: target,
        duration,
        ease: 'power2.out',
        onUpdate() {
          if (el) el.textContent = Math.round(obj.val).toLocaleString();
        },
      });
    });

    return () => ctx.revert();
  }, [target, duration]);

  return ref;
}

// ── Scroll-triggered reveal for cards ─────────────────────────────────────────
export function useScrollReveal(selector = '.scroll-reveal') {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const ctx = gsap.context(() => {
      const items = el.querySelectorAll(selector);
      items.forEach((item) => {
        gsap.fromTo(
          item,
          { opacity: 0, y: 30 },
          {
            opacity: 1,
            y: 0,
            duration: 0.55,
            ease: 'power2.out',
            scrollTrigger: {
              trigger: item,
              start: 'top 92%',
              toggleActions: 'play none none none',
            },
          }
        );
      });
    }, el);

    return () => ctx.revert();
  }, [selector]);

  return ref;
}

// ── Sidebar nav stagger (runs once on mount) ──────────────────────────────────
export function useSidebarStagger() {
  const ref = useRef<HTMLElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const ctx = gsap.context(() => {
      gsap.fromTo(
        el.querySelectorAll('button, a'),
        { opacity: 0, x: -16 },
        {
          opacity: 1,
          x: 0,
          duration: 0.4,
          ease: 'power2.out',
          stagger: 0.07,
          delay: 0.15,
        }
      );
    }, el);

    return () => ctx.revert();
  }, []);

  return ref;
}

// ── Glow pulse on an element ──────────────────────────────────────────────────
export function useGlowPulse(color = 'rgba(20,184,166,0.35)') {
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = ref.current;
    if (!el) return;

    const ctx = gsap.context(() => {
      gsap.to(el, {
        boxShadow: `0 0 24px ${color}`,
        repeat: -1,
        yoyo: true,
        duration: 1.8,
        ease: 'sine.inOut',
      });
    });

    return () => ctx.revert();
  }, [color]);

  return ref;
}

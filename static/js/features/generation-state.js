import { hide } from '../utils.js?v=8';

const FADE_MS = 180;
const reducedMotion = window.matchMedia('(prefers-reduced-motion: reduce)');

// Transition the page into its completed state by hiding the generation-only
// configuration controls. Driven by the actual generation lifecycle.
// Pass immediate = true when a result is already present on load (history),
// so the controls never flash before disappearing.
export function enterCompletedState(immediate = false) {
  const controls = document.getElementById('feature-controls');
  if (!controls || controls.hidden) return;

  if (immediate || reducedMotion.matches) {
    hideControls(controls);
    return;
  }

  controls.classList.add('is-fading-out');
  setTimeout(() => {
    if (!controls.classList.contains('is-fading-out')) return;
    hideControls(controls);
  }, FADE_MS);
}

function hideControls(controls) {
  controls.classList.remove('is-fading-out');
  hide(controls);
}

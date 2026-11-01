// Shared by the root layout (server) and ThemeToggle (client).

export const THEME_KEY = "nexvm-theme";

/** Runs before first paint (see app/layout.tsx) so a saved theme never flashes the other one. */
export const THEME_SCRIPT = `try{var t=localStorage.getItem("${THEME_KEY}");if(t==="light"||t==="dark")document.documentElement.dataset.theme=t}catch(e){}`;

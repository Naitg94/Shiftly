import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";
import "./globals.css";
import { AuthProvider } from "@/context/AuthContext";
import { PreferencesProvider } from "@/context/PreferencesContext";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Shiftly — Find what matters",
  description: "Shiftly is an AI-powered communication intelligence layer.",
  verification: {
    google: "dCS_8UM9diToGgzGks281uZqLYFGdiOPKTrHrhrX3c8",
  },
};

const themeInitScript = `
(function() {
  try {
    var raw = null;
    for (var i = 0; i < localStorage.length; i++) {
      var k = localStorage.key(i);
      if (k && k.indexOf('sb-') === 0 && k.indexOf('-auth-token') !== -1) {
        try {
          var sessionData = JSON.parse(localStorage.getItem(k));
          var userId = sessionData && (sessionData.user ? sessionData.user.id : (sessionData.currentSession && sessionData.currentSession.user ? sessionData.currentSession.user.id : null));
          if (userId) {
            raw = localStorage.getItem('shiftly:appearance:user:' + userId);
            break;
          }
        } catch(e) {}
      }
    }
    if (!raw) {
      raw = localStorage.getItem('shiftly:appearance:guest');
    }
    var prefs = raw ? JSON.parse(raw) : null;
    var theme = (prefs && prefs.theme) || 'system';
    if (theme === 'system') {
      theme = window.matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light';
    }
    var root = document.documentElement;
    root.setAttribute('data-theme', theme);
    var accent = (prefs && (prefs.accent || prefs.accentColor)) || 'blue';
    root.setAttribute('data-accent', accent);
    if (prefs) {
      if (prefs.font) root.setAttribute('data-font', prefs.font);
      if (prefs.textSize) root.setAttribute('data-text-size', prefs.textSize);
      var anim = prefs.animations !== undefined ? prefs.animations : prefs.animationsEnabled;
      if (anim !== undefined) root.setAttribute('data-animations', String(anim));
      if (prefs.reduceMotion !== undefined) root.setAttribute('data-reduce-motion', String(prefs.reduceMotion));
      var customColor = prefs.customAccent || prefs.customAccentColor;
      if (accent === 'custom' && customColor) {
        var hex = customColor.replace(/^#/, '');
        if (hex.length === 3) hex = hex.split('').map(function(c) { return c + c; }).join('');
        var num = parseInt(hex, 16);
        var r = (num >> 16) & 255, g = (num >> 8) & 255, b = num & 255;
        root.style.setProperty('--accent', '#' + hex);
        root.style.setProperty('--accent-ring', 'rgba(' + r + ',' + g + ',' + b + ',0.25)');
        if (theme === 'dark') {
          root.style.setProperty('--accent-soft', 'rgba(' + r + ',' + g + ',' + b + ',0.15)');
          root.style.setProperty('--accent-border', 'rgba(' + r + ',' + g + ',' + b + ',0.35)');
        } else {
          root.style.setProperty('--accent-soft', 'rgba(' + r + ',' + g + ',' + b + ',0.10)');
          root.style.setProperty('--accent-border', 'rgba(' + r + ',' + g + ',' + b + ',0.30)');
        }
      }
    }
  } catch(e) {}
})();
`;

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html
      lang="en"
      className={`${geistSans.variable} ${geistMono.variable} min-h-full antialiased`}
      suppressHydrationWarning
    >
      <head>
        <script dangerouslySetInnerHTML={{ __html: themeInitScript }} />
      </head>
      <body className="min-h-full flex flex-col">
        <AuthProvider>
          <PreferencesProvider>{children}</PreferencesProvider>
        </AuthProvider>
      </body>
    </html>
  );
}

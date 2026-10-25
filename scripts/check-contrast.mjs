import { readFileSync } from "node:fs";
import { resolve } from "node:path";

const css = readFileSync(resolve("app/globals.css"), "utf8");
const declarations = [...css.matchAll(/(:root(?:\[data-theme="dark"\])?)\s*\{([^}]+)\}/g)];

function getTokens(theme) {
  const values = {};
  for (const [, selector, body] of declarations) {
    const isDark = selector.includes('data-theme="dark"');
    if (theme === "dark" ? isDark : !isDark) {
      for (const [, key, value] of body.matchAll(/--([\w-]+):\s*(#[\da-fA-F]{3,8})\s*;/g)) {
        values[key] = value;
      }
    }
  }
  return values;
}

function rgb(hex) {
  let value = hex.slice(1);
  if (value.length === 3) value = [...value].map((part) => part + part).join("");
  if (value.length === 8) value = value.slice(0, 6);
  if (value.length !== 6) throw new Error(`Unsupported color token: ${hex}`);
  return [0, 2, 4].map((offset) => Number.parseInt(value.slice(offset, offset + 2), 16) / 255);
}

function luminance(hex) {
  const [r, g, b] = rgb(hex).map((channel) => channel <= 0.04045 ? channel / 12.92 : ((channel + 0.055) / 1.055) ** 2.4);
  return 0.2126 * r + 0.7152 * g + 0.0722 * b;
}

function contrast(foreground, background) {
  const values = [luminance(foreground), luminance(background)].sort((a, b) => b - a);
  return (values[0] + 0.05) / (values[1] + 0.05);
}

const checks = [
  ["ink", "paper", 7, "primary text"],
  ["ink", "surface", 7, "primary text"],
  ["ink", "surface-2", 7, "primary text"],
  ["muted", "paper", 4.5, "secondary text"],
  ["muted", "surface", 4.5, "secondary text"],
  ["muted", "surface-2", 4.5, "secondary text"],
  ["accent", "paper", 4.5, "accent text"],
  ["accent", "surface", 4.5, "accent text"],
  ["green", "paper", 4.5, "success text"],
  ["green", "surface", 4.5, "success text"],
  ["amber", "paper", 4.5, "warning text"],
  ["amber", "surface", 4.5, "warning text"],
  ["red", "paper", 4.5, "error text"],
  ["red", "surface", 4.5, "error text"],
  ["band-fg", "band-bg", 7, "dark section text"],
  ["band-accent", "band-bg", 4.5, "dark section accent text"],
  ["button-fg", "button-bg", 4.5, "button label"],
  ["button-fg", "button-hover", 4.5, "button hover label"],
  ["line", "paper", 3, "visible boundary"],
  ["line", "surface", 3, "visible boundary"],
  ["line", "surface-2", 3, "visible boundary"],
  ["accent", "paper", 3, "focus indicator"],
  ["accent", "surface", 3, "focus indicator"],
];

let failed = false;
console.log("Theme | Foreground / background | Ratio | Minimum | Result");
console.log("--- | --- | ---: | ---: | ---");
for (const theme of ["light", "dark"]) {
  const tokens = getTokens(theme);
  for (const [foregroundKey, backgroundKey, minimum, role] of checks) {
    const foreground = tokens[foregroundKey];
    const background = tokens[backgroundKey];
    if (!foreground || !background) throw new Error(`Missing ${theme} token for ${role}: ${foregroundKey}/${backgroundKey}`);
    const ratio = contrast(foreground, background);
    const passed = ratio >= minimum;
    if (!passed) failed = true;
    console.log(`${theme} | ${role}: ${foregroundKey} / ${backgroundKey} | ${ratio.toFixed(2)}:1 | ${minimum.toFixed(1)}:1 | ${passed ? "PASS" : "FAIL"}`);
  }
}

if (failed) process.exitCode = 1;

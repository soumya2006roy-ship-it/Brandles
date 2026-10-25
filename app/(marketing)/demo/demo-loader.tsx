"use client";

import dynamic from "next/dynamic";

const DemoExperience = dynamic(() => import("@/app/(marketing)/demo/demo-experience").then((module) => module.DemoExperience), {
  ssr: false,
  loading: () => <div className="demo-workspace" aria-label="Loading campaign simulation" aria-busy="true"><div className="skeleton skeleton-row"/><div className="skeleton skeleton-row short"/><div className="skeleton skeleton-card"/><span className="visually-hidden">Loading the campaign simulation…</span></div>,
});

export function DemoLoader() {
  return <DemoExperience />;
}

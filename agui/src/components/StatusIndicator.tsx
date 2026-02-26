"use client";

import React from "react";

// The accepted states for the visual indicator
export type StatusType = "ready" | "processing" | "done";

interface StatusIndicatorProps {
    status: StatusType;
}

// A simple fixed overlay component that provides quick visual feedback on whether the Agent is processing via CopilotKit
export function StatusIndicator({ status }: StatusIndicatorProps) {
    return (
        <div className="fixed top-4 right-4 z-50 flex items-center gap-3 bg-background/80 backdrop-blur-md px-4 py-2 rounded-full border border-border/50 shadow-sm transition-all duration-300">
            <div className="relative flex items-center justify-center w-6 h-6">
                {status === "ready" && (
                    <div className="w-3 h-3 bg-emerald-500 rounded-full animate-pulse shadow-[0_0_8px_rgba(16,185,129,0.5)]" />
                )}

                {status === "processing" && (
                    <svg className="animate-spin w-5 h-5 text-primary" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                        <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                        <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                    </svg>
                )}

                {status === "done" && (
                    <svg className="w-5 h-5 text-emerald-500 animate-in zoom-in duration-300" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={3} d="M5 13l4 4L19 7" />
                    </svg>
                )}
            </div>

            <span className={`text-sm font-medium transition-colors duration-300 ${status === "ready" ? "text-emerald-600 dark:text-emerald-400" :
                status === "processing" ? "text-primary" :
                    "text-emerald-600 dark:text-emerald-400"
                }`}>
                {status === "ready" ? "System Ready" :
                    status === "processing" ? "Processing Review..." :
                        "Analysis Complete"}
            </span>
        </div>
    );
}

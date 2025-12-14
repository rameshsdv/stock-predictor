'use client';

import { cn } from '@/lib/utils';
import { Activity, TrendingUp, BarChart2, Hash, Layers } from 'lucide-react';
import { useState } from 'react';

interface TechnicalSummaryProps {
    data: {
        indicators: any;
        summary: any;
    };
}

export function TechnicalSummary({ data }: TechnicalSummaryProps) {
    if (!data || !data.indicators) return null;

    const ind = data.indicators;
    const sum = data.summary || {};

    // --- 1. Official Recommendation Engine ---
    const recommendation = sum.RECOMMENDATION || "NEUTRAL";
    const buyCount = sum.BUY || 0;
    const sellCount = sum.SELL || 0;
    const neutralCount = sum.NEUTRAL || 0;
    const total = buyCount + sellCount + neutralCount || 1;

    let signalColor = "text-yellow-400";
    let signalBg = "bg-yellow-500/10";
    if (recommendation.includes("BUY")) {
        signalColor = "text-emerald-400";
        signalBg = "bg-emerald-500/10";
    } else if (recommendation.includes("SELL")) {
        signalColor = "text-red-400";
        signalBg = "bg-red-500/10";
    }

    // --- 2. Pivot Points (The "Deep" Data) ---
    const pivotType = "Fibonacci"; // Defaulting to the most useful one for Quants

    const pivots = {
        s3: ind[`Pivot.M.${pivotType}.S3`],
        s2: ind[`Pivot.M.${pivotType}.S2`],
        s1: ind[`Pivot.M.${pivotType}.S1`],
        p: ind[`Pivot.M.${pivotType}.Middle`],
        r1: ind[`Pivot.M.${pivotType}.R1`],
        r2: ind[`Pivot.M.${pivotType}.R2`],
        r3: ind[`Pivot.M.${pivotType}.R3`],
    };

    // --- 3. Key Indicators extraction ---
    const rows = [
        { label: 'RSI (14)', val: ind['RSI'], signal: 'Neutral' },
        { label: 'Stoch %K', val: ind['Stoch.K'], signal: 'Neutral' },
        { label: 'CCI (20)', val: ind['CCI20'], signal: 'Neutral' },
        { label: 'ADX (14)', val: ind['ADX'], signal: 'Neutral' },
        { label: 'AO', val: ind['AO'], signal: 'Neutral' },
        { label: 'Mom', val: ind['Mom'], signal: 'Neutral' },
        { label: 'MACD Level', val: ind['MACD.macd'], signal: 'Neutral' },
    ];

    // Simple Badge Helper
    const SignalBadge = ({ label, val }: { label: string, val: number }) => {
        let color = "text-slate-400";
        if (label.includes("RSI")) {
            if (val < 30) color = "text-emerald-400";
            else if (val > 70) color = "text-red-400";
        }
        return <span className={cn("font-mono", color)}>{val?.toFixed(2)}</span>;
    };

    return (
        <div className="glass-card p-0 rounded-2xl overflow-hidden border border-slate-800/50">
            {/* Header: Official Signal */}
            <div className="p-6 border-b border-slate-800 bg-slate-900/50">
                <div className="flex items-center justify-between mb-4">
                    <h3 className="text-lg font-bold text-white flex items-center gap-2">
                        <Activity className="w-5 h-5 text-primary" />
                        TradingView Technicals
                    </h3>
                    <div className={cn("px-4 py-2 rounded-lg border border-opacity-20 backdrop-blur-md", signalBg, signalColor.replace('text-', 'border-'))}>
                        <span className="text-xs font-semibold opacity-70 block uppercase tracking-wider">Verdict</span>
                        <span className={cn("text-2xl font-black tracking-tight", signalColor)}>{recommendation.replace('_', ' ')}</span>
                    </div>
                </div>

                {/* Speedometer Bar */}
                <div className="flex items-center gap-1 h-2 w-full rounded-full overflow-hidden bg-slate-800 relative group">
                    <div className="h-full bg-red-500 transition-all duration-500" style={{ width: `${(sellCount / total) * 100}%` }} />
                    <div className="h-full bg-yellow-500 transition-all duration-500" style={{ width: `${(neutralCount / total) * 100}%` }} />
                    <div className="h-full bg-emerald-500 transition-all duration-500" style={{ width: `${(buyCount / total) * 100}%` }} />
                </div>
                <div className="flex justify-between text-xs text-slate-400 mt-2 font-mono">
                    <span className="text-red-400">SELL {sellCount}</span>
                    <span className="text-yellow-400">NEUT {neutralCount}</span>
                    <span className="text-emerald-400">BUY {buyCount}</span>
                </div>
            </div>

            <div className="grid grid-cols-1 lg:grid-cols-2 divide-y lg:divide-y-0 lg:divide-x divide-slate-800">

                {/* Left: Pivot Points (Fibonacci) */}
                <div className="p-6">
                    <h4 className="text-sm font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2 mb-4">
                        <Layers className="w-4 h-4" /> Fibonacci Pivot Levels
                    </h4>

                    <div className="space-y-2 text-sm">
                        {pivots.r3 && (
                            <div className="flex justify-between items-center text-red-300/60">
                                <span>Res 3</span> <span className="font-mono">{pivots.r3.toFixed(2)}</span>
                            </div>
                        )}
                        {pivots.r2 && (
                            <div className="flex justify-between items-center text-red-300/80">
                                <span>Res 2</span> <span className="font-mono">{pivots.r2.toFixed(2)}</span>
                            </div>
                        )}
                        {pivots.r1 && (
                            <div className="flex justify-between items-center text-red-400 font-medium">
                                <span>Res 1</span> <span className="font-mono">{pivots.r1.toFixed(2)}</span>
                            </div>
                        )}

                        <div className="flex justify-between items-center text-yellow-400 font-bold py-2 border-y border-slate-800 my-2">
                            <span>PIVOT</span> <span className="font-mono">{pivots.p?.toFixed(2)}</span>
                        </div>

                        {pivots.s1 && (
                            <div className="flex justify-between items-center text-emerald-400 font-medium">
                                <span>Sup 1</span> <span className="font-mono">{pivots.s1.toFixed(2)}</span>
                            </div>
                        )}
                        {pivots.s2 && (
                            <div className="flex justify-between items-center text-emerald-300/80">
                                <span>Sup 2</span> <span className="font-mono">{pivots.s2.toFixed(2)}</span>
                            </div>
                        )}
                        {pivots.s3 && (
                            <div className="flex justify-between items-center text-emerald-300/60">
                                <span>Sup 3</span> <span className="font-mono">{pivots.s3.toFixed(2)}</span>
                            </div>
                        )}
                    </div>
                </div>

                {/* Right: Key Indicators */}
                <div className="p-6">
                    <h4 className="text-sm font-semibold text-slate-400 uppercase tracking-wider flex items-center gap-2 mb-4">
                        <BarChart2 className="w-4 h-4" /> Oscillator Snapshot
                    </h4>
                    <div className="space-y-3">
                        {rows.map((r) => (
                            <div key={r.label} className="flex justify-between items-center text-sm border-b border-slate-800/50 pb-2 last:border-0 last:pb-0">
                                <span className="text-slate-300">{r.label}</span>
                                <SignalBadge label={r.label} val={r.val} />
                            </div>
                        ))}

                        {/* Bollinger Bands Context */}
                        {ind['BB.upper'] && (
                            <div className="mt-4 pt-4 border-t border-slate-800">
                                <div className="flex justify-between text-xs text-slate-500 mb-1">
                                    <span>BB Lower</span>
                                    <span>BB Upper</span>
                                </div>
                                <div className="relative h-1 bg-slate-800 rounded-full w-full">
                                    {/* Visual placeholder - hard to make dynamic without more context, but presence is key */}
                                    <div className="absolute top-0 bottom-0 left-0 right-0 bg-slate-700/30 rounded-full"></div>
                                </div>
                                <div className="flex justify-between font-mono text-xs text-slate-300">
                                    <span>{ind['BB.lower']?.toFixed(1)}</span>
                                    <span className="text-primary font-bold">{ind['close'] || ind['Probable Close'] || ''}</span>
                                    <span>{ind['BB.upper']?.toFixed(1)}</span>
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            </div>
        </div>
    );
}

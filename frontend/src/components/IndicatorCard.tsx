'use client';

import { cn } from '@/lib/utils';
import { ArrowUpRight, ArrowDownRight, Minus } from 'lucide-react';

interface IndicatorCardProps {
    title: string;
    value: string | number;
    subValue?: string;
    trend?: 'up' | 'down' | 'neutral';
    description?: string;
}

export function IndicatorCard({ title, value, subValue, trend, description }: IndicatorCardProps) {
    return (
        <div className="glass-card p-5 rounded-2xl relative overflow-hidden group">
            <div className="absolute top-0 right-0 p-4 opacity-10 group-hover:opacity-20 transition-opacity">
                {trend === 'up' && <ArrowUpRight className="w-12 h-12 text-green-500" />}
                {trend === 'down' && <ArrowDownRight className="w-12 h-12 text-red-500" />}
                {trend === 'neutral' && <Minus className="w-12 h-12 text-slate-500" />}
            </div>

            <h3 className="text-slate-400 text-sm font-medium uppercase tracking-wider">{title}</h3>
            <div className="mt-2 flex items-baseline gap-2">
                <span className={cn(
                    "text-3xl font-bold",
                    trend === 'up' ? "text-green-400" :
                        trend === 'down' ? "text-red-400" : "text-white"
                )}>
                    {value}
                </span>
                {subValue && <span className="text-sm text-slate-500">{subValue}</span>}
            </div>

            {description && (
                <p className="mt-2 text-xs text-slate-400">
                    {description}
                </p>
            )}

            {/* Glow Effect */}
            <div className={cn(
                "absolute -bottom-10 -right-10 w-24 h-24 blur-3xl rounded-full opacity-20",
                trend === 'up' ? "bg-green-500" :
                    trend === 'down' ? "bg-red-500" : "bg-slate-500"
            )} />
        </div>
    );
}

'use client';

import { useState } from 'react';
import { Search, ArrowRight } from 'lucide-react';
import { cn } from '@/lib/utils';
import { motion } from 'framer-motion';

interface StockSearchProps {
    onSearch: (symbol: string) => void;
    isLoading?: boolean;
}

export function StockSearch({ onSearch, isLoading = false }: StockSearchProps) {
    const [symbol, setSymbol] = useState('');

    const handleSubmit = (e: React.FormEvent) => {
        e.preventDefault();
        if (symbol.trim()) {
            onSearch(symbol.toUpperCase());
        }
    };

    return (
        <div className="w-full max-w-2xl mx-auto p-6">
            <motion.form
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ duration: 0.5 }}
                onSubmit={handleSubmit}
                className="relative group"
            >
                <div className="absolute inset-y-0 left-4 flex items-center pointer-events-none text-muted-foreground group-focus-within:text-primary transition-colors">
                    <Search className="w-6 h-6" />
                </div>
                <input
                    type="text"
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value)}
                    placeholder="Enter NSE Stock Symbol (e.g. RELIANCE)"
                    className="w-full pl-14 pr-32 py-5 text-lg bg-slate-900/50 backdrop-blur-xl border border-white/10 rounded-2xl shadow-2xl focus:outline-none focus:ring-2 focus:ring-primary/50 focus:border-primary/50 transition-all text-white placeholder:text-slate-500"
                    disabled={isLoading}
                />
                <button
                    type="submit"
                    disabled={!symbol || isLoading}
                    className="absolute right-2 top-2 bottom-2 bg-primary hover:bg-primary/90 text-black font-semibold px-6 rounded-xl flex items-center gap-2 transition-all disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    {isLoading ? (
                        <span className="animate-pulse">Analyzing...</span>
                    ) : (
                        <>
                            Predict <ArrowRight className="w-4 h-4" />
                        </>
                    )}
                </button>
            </motion.form>

            {/* Quick suggestions or trend tags could go here */}
            <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                transition={{ delay: 0.3 }}
                className="mt-4 flex gap-3 justify-center text-sm text-slate-400"
            >
                <span>Popular:</span>
                {['RELIANCE', 'TCS', 'INFY', 'HDFCBANK'].map((s) => (
                    <button
                        key={s}
                        type="button"
                        onClick={() => {
                            setSymbol(s);
                            onSearch(s);
                        }}
                        className="hover:text-primary transition-colors cursor-pointer"
                    >
                        {s}
                    </button>
                ))}
            </motion.div>
        </div>
    );
}

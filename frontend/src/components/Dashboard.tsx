'use client';

import { useState } from 'react';
import { StockSearch } from './StockSearch';
import { PredictionChart, ChartDataPoint } from './PredictionChart';
import { IndicatorCard } from './IndicatorCard';
import { motion } from 'framer-motion';

const fetchPrediction = async (symbol: string) => {
    try {
        const response = await fetch(`http://localhost:8000/predict`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ symbol })
        });

        if (!response.ok) {
            throw new Error('Failed to fetch prediction');
        }

        return await response.json();
    } catch (error) {
        console.error(error);
        return null;
    }
};

export function Dashboard() {
    const [stockSymbol, setStockSymbol] = useState<string | null>(null);
    const [data, setData] = useState<ChartDataPoint[] | null>(null);
    const [analysis, setAnalysis] = useState<any | null>(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState<string | null>(null);

    const handleSearch = async (symbol: string) => {
        setLoading(true);
        setError(null);
        setAnalysis(null);

        // Slight delay to show animation (optional, but nice)
        // await new Promise(r => setTimeout(r, 800));

        const result = await fetchPrediction(symbol);

        if (result) {
            setStockSymbol(result.symbol);
            setData(result.chart_data);
            setAnalysis({
                marketPhase: result.market_phase, // Now comes as "Bullish/Trending" from GMM
                action: result.action_signal,
                trendStrength: result.trend_strength,
                rsi: result.rsi,
                macdSignal: result.macd_signal,
                currentPrice: result.current_price,
                significantFeatures: result.significant_features
            });
        } else {
            setError("Failed to fetch data. Please check the symbol or try again.");
        }
        setLoading(false);
    };

    return (
        <div className="min-h-screen bg-background text-foreground pb-20">
            <header className="fixed top-0 w-full z-50 glass border-b border-slate-800">
                <div className="max-w-7xl mx-auto px-6 h-16 flex items-center justify-between">
                    <h1 className="text-xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-primary to-secondary">
                        NSE Predictor.AI
                    </h1>
                    <nav className="text-sm text-slate-400 flex gap-4">
                        <a href="#" className="hover:text-white transition-colors">Dashboard</a>
                        <a href="#" className="hover:text-white transition-colors">Models</a>
                        <a href="#" className="hover:text-white transition-colors">About</a>
                    </nav>
                </div>
            </header>

            <main className="pt-24 px-6 max-w-7xl mx-auto space-y-8">
                <div className="text-center space-y-4 mb-12">
                    <h2 className="text-4xl md:text-5xl font-bold text-white tracking-tight">
                        Predict the Market Phase.
                    </h2>
                    <p className="text-slate-400 text-lg max-w-2xl mx-auto">
                        Advanced AI-driven forecasting for Indian stocks. Get 15-day price targets, Buy/Sell signals, and deep technical analysis.
                    </p>
                </div>

                <StockSearch onSearch={handleSearch} isLoading={loading} />

                {error && (
                    <div className="text-red-400 text-center bg-red-500/10 p-4 rounded-xl border border-red-500/20 max-w-2xl mx-auto">
                        {error}
                    </div>
                )}

                {data && stockSymbol && analysis && (
                    <motion.div
                        initial={{ opacity: 0, y: 20 }}
                        animate={{ opacity: 1, y: 0 }}
                        transition={{ duration: 0.5 }}
                        className="space-y-6"
                    >
                        {/* Main Chart */}
                        <PredictionChart data={data} symbol={stockSymbol} />

                        {/* Analysis Grid */}
                        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
                            <IndicatorCard
                                title="Market Regime (GMM)"
                                value={analysis.marketPhase}
                                trend={analysis.marketPhase.includes('Bullish') ? 'up' : analysis.marketPhase.includes('Bearish') ? 'down' : 'neutral'}
                                description={`Action Signal: ${analysis.action}`}
                            />
                            <IndicatorCard
                                title="RSI (14)"
                                value={analysis.rsi?.toFixed(2) || 'N/A'}
                                subValue={analysis.rsi > 70 ? 'Overbought' : analysis.rsi < 30 ? 'Oversold' : 'Neutral'}
                                trend="neutral"
                                description="Momentum Oscillator"
                            />
                            <IndicatorCard
                                title="MACD Signal"
                                value={analysis.macdSignal}
                                trend={analysis.macdSignal === 'Buy' ? 'up' : 'down'}
                                description="MACD vs Signal Line crossover."
                            />
                            <IndicatorCard
                                title="Trend Strength"
                                value={analysis.trendStrength}
                                trend="neutral"
                                description={`Drivers: ${analysis.significantFeatures?.join(', ')}`}
                            />
                        </div>

                        <div className="p-4 rounded-xl border border-yellow-500/20 bg-yellow-500/5 text-yellow-200 text-sm flex gap-3 items-start">
                            <span>⚠️</span>
                            <p>
                                Disclaimer: This prediction is generated by an AI model and should not be considered financial advice.
                                Market conditions can change rapidly. Always do your own research.
                            </p>
                        </div>

                    </motion.div>
                )}
            </main>
        </div>
    );
}
